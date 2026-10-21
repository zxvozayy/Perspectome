"""Shared PostgreSQL (Supabase) access for every track.

The CSV/JSON contracts stay the exchange format; the database is where the
shared copies live. Each track pushes what it owns and pulls what it reads:

    python -m src.common.db status
    python -m src.common.db push-personas --personas data/processed/personas.csv \
        --heldout data/processed/heldout.csv --source "WVS-7 Turkey" --seed 0     # Track A
    python -m src.common.db pull-personas --out data/processed/personas.csv      # B, C (real core)
    python -m src.common.db pull-personas --kind synthetic --out data/processed/personas_synthetic.csv
    python -m src.common.db pull-heldout  --out data/processed/heldout.csv       # C only
    python -m src.common.db push-runs results/*.json                             # Track B
    python -m src.common.db pull-runs --out-dir results                          # C, D
    python -m src.common.db push-report reports/comparison.json                  # Track C
    python -m src.common.db pull-report --out reports/comparison.json            # Track D

Admin only (the project owner's connection):

    python -m src.common.db migrate
    python -m src.common.db create-users        # one login per teammate -> tmp/db-users.local.txt

The connection string comes from DATABASE_URL (environment, or the repo's
git-ignored .env file). Never commit it and never print it.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import secrets
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote, urlsplit, urlunsplit

from src.common import env, paths, schema
from src.common.hashing import sha256_bytes
from src.common.labels import answer_label

MIGRATIONS = paths.REPO / "db" / "migrations"
USERS_FILE = paths.REPO / "tmp" / "db-users.local.txt"

# Personal logins and the track role each one gets.
PEOPLE = {"fatmanur": "track_a", "yigithan": "track_b", "hasan": "track_c", "ezgi": "track_d"}


# --- connection ----------------------------------------------------------------

def database_url(env_file: Path = env.ENV_FILE) -> str:
    """DATABASE_URL from the environment, else from the git-ignored .env file."""
    url = env.get("DATABASE_URL", env_file)
    if not url:
        raise RuntimeError("DATABASE_URL is not set (environment or .env). See docs/database.md.")
    return url


def redact(url: str) -> str:
    """The URL with its password replaced, safe for logs and errors."""
    parts = urlsplit(url)
    if parts.password is None:
        return url
    netloc = parts.netloc.replace(f":{parts.password}@", ":***@")
    return urlunsplit(parts._replace(netloc=netloc))


TRANSACTION_POOLER_PORT = 6543
# Query parameters some tools add to Supabase URLs that libpq doesn't know.
_NON_LIBPQ_PARAMS = {"pgbouncer", "connection_limit", "pool_timeout", "schema"}


def clean_url(url: str) -> str:
    """Drop non-libpq query parameters (e.g. Prisma's ?pgbouncer=true)."""
    parts = urlsplit(url)
    kept = [q for q in parts.query.split("&")
            if q and q.split("=", 1)[0].lower() not in _NON_LIBPQ_PARAMS]
    return urlunsplit(parts._replace(query="&".join(kept)))


def connect(url: Optional[str] = None):
    import psycopg  # optional dependency: pip install "psycopg[binary]"
    url = clean_url(url or database_url())
    # Supabase's transaction pooler (port 6543) can't keep prepared statements.
    kwargs = {"prepare_threshold": None} if urlsplit(url).port == TRANSACTION_POOLER_PORT else {}
    try:
        return psycopg.connect(url, connect_timeout=15, **kwargs)
    except psycopg.Error as e:
        # psycopg errors can echo the DSN; never let the password reach a log.
        raise RuntimeError(f"Could not connect to the database: {redact(str(e))}") from None


# --- pure helpers (tested without a database) ----------------------------------

def read_csv_rows(data: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def validate_personas(rows: list[dict]) -> list[str]:
    """Problems that block a push: wrong columns, unknown categories, leaked held-out fields."""
    problems = []
    if not rows:
        return ["personas.csv is empty"]
    cols = set(rows[0])
    missing = [c for c in schema.PERSONA_COLUMNS if c not in cols]
    if missing:
        problems.append(f"missing columns: {missing}")
    leaked = sorted(cols & set(schema.HELDOUT_FIELDS))
    if leaked:
        problems.append(f"held-out fields in personas.csv: {leaked}")
    for field, allowed in schema.CATEGORIES.items():
        allowed = {str(v) for v in allowed}
        bad = sorted({answer_label(r.get(field)) for r in rows} - allowed - {None})
        if bad:
            problems.append(f"{field}: values not in schema.py: {bad[:5]}")
    ids = [r.get("persona_id") for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate persona_id")
    return problems


def validate_heldout(rows: list[dict], persona_ids: set) -> list[str]:
    problems = []
    if not rows:
        return ["heldout.csv is empty"]
    unknown = sorted(set(rows[0]) - {"persona_id", *schema.HELDOUT_FIELDS})
    if unknown:
        problems.append(f"columns not in schema.HELDOUT_FIELDS: {unknown}")
    orphans = {r["persona_id"] for r in rows} - persona_ids
    if orphans:
        problems.append(f"{len(orphans)} held-out rows have no persona")
    return problems


def heldout_long(rows: list[dict]) -> list[tuple]:
    """Wide held-out rows -> (persona_id, item, label) with blanks as null."""
    return [(r["persona_id"], item, answer_label(r[item]))
            for r in rows for item in schema.HELDOUT_FIELDS if item in r]


def user_url(admin_url: str, role: str, password: str) -> str:
    """Swap the login in a Supabase pooler URL ("postgres.<ref>" -> "<role>.<ref>")."""
    parts = urlsplit(admin_url)
    user = parts.username or ""
    ref = user.split(".", 1)[1] if "." in user else None
    login = f"{role}.{ref}" if ref else role
    host = parts.hostname + (f":{parts.port}" if parts.port else "")
    return urlunsplit(parts._replace(netloc=f"{quote(login)}:{quote(password)}@{host}"))


# --- admin ------------------------------------------------------------------------

def migrate(conn) -> list[str]:
    """Apply db/migrations/*.sql not yet recorded, in file-name order."""
    with conn.cursor() as cur:
        cur.execute("create schema if not exists meta")
        cur.execute("create table if not exists meta.schema_migrations "
                    "(version text primary key, applied_at timestamptz not null default now())")
        cur.execute("select version from meta.schema_migrations")
        done = {r[0] for r in cur.fetchall()}
        applied = []
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.stem in done:
                continue
            cur.execute(path.read_text(encoding="utf-8"))
            cur.execute("insert into meta.schema_migrations (version) values (%s)", (path.stem,))
            applied.append(path.stem)
    conn.commit()
    return applied


def create_users(conn, admin_url: str, reset: bool = False, people: dict = PEOPLE) -> dict:
    """Create one login per teammate in their track role. Returns {name: url}.

    Passwords are random hex (URL-safe). Existing logins are left alone unless
    ``reset`` -- then they get a new password.
    """
    from psycopg import sql
    urls = {}
    with conn.cursor() as cur:
        for name, role in people.items():
            cur.execute("select 1 from pg_roles where rolname = %s", (name,))
            exists = cur.fetchone() is not None
            if exists and not reset:
                continue
            password = secrets.token_hex(16)
            verb = "alter" if exists else "create"
            cur.execute(sql.SQL(verb + " role {} with login password {}").format(
                sql.Identifier(name), sql.Literal(password)))
            cur.execute(sql.SQL("grant {} to {}").format(sql.Identifier(role), sql.Identifier(name)))
            urls[name] = user_url(admin_url, name, password)
    conn.commit()
    return urls


def status(conn) -> dict:
    out = {"user": None, "migrations": [], "counts": {}}
    with conn.cursor() as cur:
        cur.execute("select current_user")
        out["user"] = cur.fetchone()[0]
        try:
            cur.execute("select version from meta.schema_migrations order by version")
            out["migrations"] = [r[0] for r in cur.fetchall()]
        except Exception:
            conn.rollback()
        for table in ("personas.persona_sets", "personas.personas", "heldout.answers",
                      "sim.runs", "validation.reports"):
            try:
                cur.execute(f"select count(*) from {table}")
                out["counts"][table] = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                out["counts"][table] = "no access"
    return out


# --- Track A ------------------------------------------------------------------------

def push_personas(conn, personas_path, heldout_path=None, source: str = "",
                  seed: Optional[int] = None, notes: Optional[str] = None,
                  kind: str = "core", core_set_hash: Optional[str] = None) -> str:
    """Publish a frozen persona set (and its held-out answers). Returns its hash.

    ``kind="synthetic"`` sets are drawn from a real core (``core_set_hash``) and
    never carry held-out answers. Columns outside schema.PERSONA_COLUMNS
    (schema.SYNTHETIC_FIELDS) are stored per persona in ``attrs``.
    """
    if kind not in ("core", "synthetic"):
        raise ValueError(f"unknown persona set kind {kind!r}")
    if kind == "synthetic" and (heldout_path or not core_set_hash):
        raise ValueError("a synthetic set needs --core-hash and has no held-out answers")
    raw = Path(personas_path).read_bytes()
    rows = read_csv_rows(raw)
    problems = validate_personas(rows)
    held = read_csv_rows(Path(heldout_path).read_bytes()) if heldout_path else []
    if heldout_path:
        problems += validate_heldout(held, {r["persona_id"] for r in rows})
    if problems:
        raise ValueError("Refusing to push: " + "; ".join(problems))

    h = sha256_bytes(raw)
    with conn.cursor() as cur:
        cur.execute("select 1 from personas.persona_sets where persona_set_hash = %s", (h,))
        if cur.fetchone():
            raise ValueError(f"Persona set {h} already exists (a frozen set is never overwritten).")
        cur.execute("insert into personas.persona_sets (persona_set_hash, personas_csv, seed, source, "
                    "n_personas, notes, kind, core_set_hash) values (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (h, raw, seed, source, len(rows), notes, kind, core_set_hash))
        cols = schema.PERSONA_COLUMNS
        extra = [c for c in rows[0] if c not in cols]
        with cur.copy(f"copy personas.personas (persona_set_hash, {', '.join(cols)}, attrs) from stdin") as cp:
            for r in rows:
                values = {c: answer_label(r.get(c)) for c in cols}
                values["weight"] = float(r["weight"])
                if values["income_decile"] is not None:
                    values["income_decile"] = int(values["income_decile"])
                attrs = json.dumps({c: answer_label(r.get(c)) for c in extra}, ensure_ascii=False) if extra else None
                cp.write_row((h, *(values[c] for c in cols), attrs))
        if held:
            with cur.copy("copy heldout.answers (persona_set_hash, persona_id, item, value) "
                          "from stdin") as cp:
                for pid, item, value in heldout_long(held):
                    cp.write_row((h, pid, item, value))
    conn.commit()
    return h


def latest_persona_set(conn, kind: str = "core") -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("select persona_set_hash from personas.persona_sets where kind = %s "
                    "order by created_at desc limit 1", (kind,))
        row = cur.fetchone()
    return row[0] if row else None


def pull_personas(conn, out_path, persona_set_hash: Optional[str] = None, kind: str = "core") -> str:
    """Write the exact personas.csv bytes back out, so its hash is unchanged."""
    h = persona_set_hash or latest_persona_set(conn, kind)
    with conn.cursor() as cur:
        cur.execute("select personas_csv from personas.persona_sets where persona_set_hash = %s", (h,))
        row = cur.fetchone()
    if not row:
        raise ValueError(f"No persona set {h}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(bytes(row[0]))
    return h


def pull_heldout(conn, out_path, persona_set_hash: Optional[str] = None) -> str:
    """Track C only (the database refuses everyone else): wide heldout.csv."""
    h = persona_set_hash or latest_persona_set(conn)
    with conn.cursor() as cur:
        cur.execute("select persona_id, item, value from heldout.answers where persona_set_hash = %s "
                    "order by persona_id", (h,))
        rows = cur.fetchall()
    wide: dict[str, dict] = {}
    for pid, item, value in rows:
        wide.setdefault(pid, {"persona_id": pid})[item] = value
    items = [f for f in schema.HELDOUT_FIELDS if any(f in r for r in wide.values())]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["persona_id", *items])
        w.writeheader()
        w.writerows(wide.values())
    return h


# --- Track B ------------------------------------------------------------------------

def push_runs(conn, paths: Iterable) -> int:
    """Upload results/*.json documents. Re-pushing the same run replaces it."""
    from psycopg.types.json import Jsonb
    n = 0
    with conn.cursor() as cur:
        for p in paths:
            doc = json.loads(Path(p).read_text(encoding="utf-8"))
            meta = doc.get("metadata", {})
            h = meta.get("persona_set_hash", "")
            cur.execute(
                "insert into sim.runs (run_id, run_type, scenario_id, target_item, model, model_snapshot, "
                "seed, persona_set_hash, n_personas, result) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (run_id, model_snapshot, persona_set_hash) do update set "
                "result = excluded.result, created_at = now(), created_by = current_user",
                (doc["run_id"], doc["run_type"], doc["scenario_id"], doc.get("target_item"),
                 meta.get("model"), meta.get("model_snapshot") or "unknown", meta.get("seed"), h,
                 doc.get("n_personas"), Jsonb(doc)))
            n += 1
    conn.commit()
    return n


def pull_runs(conn, out_dir, persona_set_hash: Optional[str] = None) -> int:
    where, args = ("where persona_set_hash = %s", (persona_set_hash,)) \
        if persona_set_hash else ("", ())
    with conn.cursor() as cur:
        cur.execute(f"select run_id, model_snapshot, result from sim.runs {where} order by id", args)
        rows = cur.fetchall()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for run_id, snap, doc in rows:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{run_id}__{snap}")
        (out / f"{safe}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(rows)


# --- Track C / D --------------------------------------------------------------------

def push_report(conn, path) -> int:
    from psycopg.types.json import Jsonb
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    with conn.cursor() as cur:
        cur.execute("insert into validation.reports (persona_set_hash, report) values (%s, %s) "
                    "returning id", (doc.get("persona_set_hash"), Jsonb(doc)))
        rid = cur.fetchone()[0]
    conn.commit()
    return rid


def pull_report(conn, out_path) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("select id, report from validation.reports order by created_at desc limit 1")
        row = cur.fetchone()
    if not row:
        return None
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(row[1], indent=2, ensure_ascii=False), encoding="utf-8")
    return row[0]


# --- CLI ------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m src.common.db", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("status")
    cu = sub.add_parser("create-users")
    cu.add_argument("--reset", action="store_true", help="give existing logins a new password")
    pp = sub.add_parser("push-personas")
    pp.add_argument("--personas", required=True)
    pp.add_argument("--heldout")
    pp.add_argument("--source", required=True)
    pp.add_argument("--seed", type=int)
    pp.add_argument("--notes")
    pp.add_argument("--kind", choices=("core", "synthetic"), default="core")
    pp.add_argument("--core-hash", help="persona_set_hash of the core a synthetic set was drawn from")
    for name in ("pull-personas", "pull-heldout"):
        s = sub.add_parser(name)
        s.add_argument("--out", required=True)
        s.add_argument("--hash", help="persona_set_hash (default: latest)")
        if name == "pull-personas":
            s.add_argument("--kind", choices=("core", "synthetic"), default="core")
    pr = sub.add_parser("push-runs")
    pr.add_argument("files", nargs="+")
    pl = sub.add_parser("pull-runs")
    pl.add_argument("--out-dir", required=True)
    pl.add_argument("--hash")
    rp = sub.add_parser("push-report")
    rp.add_argument("file")
    rr = sub.add_parser("pull-report")
    rr.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    url = database_url()
    with connect(url) as conn:
        if args.cmd == "migrate":
            applied = migrate(conn)
            print("applied:", applied or "nothing new")
        elif args.cmd == "status":
            print(json.dumps(status(conn), indent=2))
        elif args.cmd == "create-users":
            urls = create_users(conn, url, reset=args.reset)
            if urls:
                USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(USERS_FILE, "a", encoding="utf-8") as f:
                    for name, u in urls.items():
                        f.write(f"{name} ({PEOPLE[name]}): DATABASE_URL={u}\n")
                print(f"created/updated: {sorted(urls)} -> connection strings in {USERS_FILE}")
            else:
                print("all logins already exist (use --reset for new passwords)")
        elif args.cmd == "push-personas":
            print("pushed persona set", push_personas(conn, args.personas, args.heldout, args.source, args.seed,
                                                      args.notes, args.kind, args.core_hash))
        elif args.cmd == "pull-personas":
            print("pulled", pull_personas(conn, args.out, args.hash, args.kind), "->", args.out)
        elif args.cmd == "pull-heldout":
            print("pulled held-out for", pull_heldout(conn, args.out, args.hash), "->", args.out)
        elif args.cmd == "push-runs":
            print("pushed runs:", push_runs(conn, args.files))
        elif args.cmd == "pull-runs":
            print("pulled runs:", pull_runs(conn, args.out_dir, args.hash), "->", args.out_dir)
        elif args.cmd == "push-report":
            print("pushed report id", push_report(conn, args.file))
        elif args.cmd == "pull-report":
            rid = pull_report(conn, args.out)
            print(f"pulled report {rid} -> {args.out}" if rid else "no report yet")


if __name__ == "__main__":
    main()
