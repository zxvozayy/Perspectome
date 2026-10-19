"""Shared PostgreSQL (Supabase) access for every track.

The CSV/JSON contracts stay the exchange format; the database is where the
shared copies live. Each track pushes what it owns and pulls what it reads:

    python -m src.common.db status
    python -m src.common.db push-personas --personas data/processed/personas.csv \
        --heldout data/processed/heldout.csv --source "WVS-7 Turkey" --seed 0     # Track A
    python -m src.common.db pull-personas --out data/processed/personas.csv      # B, C
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
import hashlib
import io
import json
import os
import re
import secrets
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote, urlsplit, urlunsplit

from src.common import schema

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "db" / "migrations"
USERS_FILE = REPO / "tmp" / "db-users.local.txt"

# Personal logins and the track role each one gets.
PEOPLE = {"fatmanur": "track_a", "yigithan": "track_b", "hasan": "track_c", "ezgi": "track_d"}

PERSONA_COLUMNS = ("persona_id", "cell_id", "weight", *[f for f in schema.CONDITIONING_FIELDS
                                                        if f != "persona_id"])
CATEGORY_CHECKS = {
    "age_band": schema.AGE_BANDS,
    "gender": schema.GENDERS,
    "education_level": schema.EDUCATION_LEVELS,
    "settlement_type": schema.SETTLEMENT_TYPES,
    "marital_status": schema.MARITAL_STATUSES,
    "employment_status": schema.EMPLOYMENT_STATUSES,
}


# --- connection ----------------------------------------------------------------

def database_url(env_file: Path = REPO / ".env") -> str:
    """DATABASE_URL from the environment, else from the git-ignored .env file."""
    url = os.environ.get("DATABASE_URL")
    if not url and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip("'\"")
                break
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


def connect(url: Optional[str] = None):
    import psycopg  # optional dependency: pip install "psycopg[binary]"
    try:
        return psycopg.connect(url or database_url(), connect_timeout=15)
    except psycopg.OperationalError as e:
        # psycopg errors can echo the DSN; never let the password reach a log.
        raise RuntimeError(f"Could not connect to the database: {redact(str(e))}") from None


# --- pure helpers (tested without a database) ----------------------------------

def normalize_hash(h: str) -> str:
    """Track A writes bare hex, Track B writes "sha256:<hex>"; store one form."""
    h = (h or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", h):
        return f"sha256:{h}"
    return h


def file_hash(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def read_csv_rows(data: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def validate_personas(rows: list[dict]) -> list[str]:
    """Problems that block a push: wrong columns, unknown categories, leaked held-out fields."""
    problems = []
    if not rows:
        return ["personas.csv is empty"]
    cols = set(rows[0])
    missing = [c for c in PERSONA_COLUMNS if c not in cols]
    if missing:
        problems.append(f"missing columns: {missing}")
    leaked = sorted(cols & set(schema.HELDOUT_FIELDS))
    if leaked:
        problems.append(f"held-out fields in personas.csv: {leaked}")
    for field, allowed in CATEGORY_CHECKS.items():
        bad = sorted({r.get(field) for r in rows if r.get(field) not in ("", None, *allowed)})
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
    """Wide held-out rows -> (persona_id, item, value) with empty strings as null."""
    out = []
    for r in rows:
        for item in schema.HELDOUT_FIELDS:
            if item in r:
                v = r[item]
                out.append((r["persona_id"], item, v if v not in ("", None) else None))
    return out


def user_url(admin_url: str, role: str, password: str) -> str:
    """Swap the login in a Supabase pooler URL ("postgres.<ref>" -> "<role>.<ref>")."""
    parts = urlsplit(admin_url)
    user = parts.username or ""
    ref = user.split(".", 1)[1] if "." in user else None
    login = f"{role}.{ref}" if ref else role
    host = parts.hostname + (f":{parts.port}" if parts.port else "")
    return urlunsplit(parts._replace(netloc=f"{quote(login)}:{quote(password)}@{host}"))


def _num(v, cast):
    return cast(v) if v not in ("", None) else None


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
                  seed: Optional[int] = None, notes: Optional[str] = None) -> str:
    """Publish a frozen persona set (and its held-out answers). Returns its hash."""
    raw = Path(personas_path).read_bytes()
    rows = read_csv_rows(raw)
    problems = validate_personas(rows)
    held = read_csv_rows(Path(heldout_path).read_bytes()) if heldout_path else []
    if heldout_path:
        problems += validate_heldout(held, {r["persona_id"] for r in rows})
    if problems:
        raise ValueError("Refusing to push: " + "; ".join(problems))

    h = file_hash(raw)
    with conn.cursor() as cur:
        cur.execute("select 1 from personas.persona_sets where persona_set_hash = %s", (h,))
        if cur.fetchone():
            raise ValueError(f"Persona set {h} already exists (a frozen set is never overwritten).")
        cur.execute("insert into personas.persona_sets (persona_set_hash, personas_csv, seed, source, "
                    "n_personas, notes) values (%s, %s, %s, %s, %s, %s)",
                    (h, raw, seed, source, len(rows), notes))
        with cur.copy("copy personas.personas (persona_set_hash, persona_id, cell_id, weight, age_band, "
                      "gender, education_level, region, settlement_type, marital_status, "
                      "employment_status, income_decile) from stdin") as cp:
            for r in rows:
                cp.write_row((h, r["persona_id"], r.get("cell_id") or None, float(r["weight"]),
                              *[r.get(f) or None for f in ("age_band", "gender", "education_level",
                                                           "region", "settlement_type",
                                                           "marital_status", "employment_status")],
                              _num(r.get("income_decile"), lambda v: int(float(v)))))
        if held:
            with cur.copy("copy heldout.answers (persona_set_hash, persona_id, item, value) "
                          "from stdin") as cp:
                for pid, item, value in heldout_long(held):
                    cp.write_row((h, pid, item, value))
    conn.commit()
    return h


def latest_persona_set(conn) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("select persona_set_hash from personas.persona_sets order by created_at desc limit 1")
        row = cur.fetchone()
    return row[0] if row else None


def pull_personas(conn, out_path, persona_set_hash: Optional[str] = None) -> str:
    """Write the exact personas.csv bytes back out, so its hash is unchanged."""
    h = normalize_hash(persona_set_hash) if persona_set_hash else latest_persona_set(conn)
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
    h = normalize_hash(persona_set_hash) if persona_set_hash else latest_persona_set(conn)
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
            h = normalize_hash(meta.get("persona_set_hash", ""))
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
    where, args = ("where persona_set_hash = %s", (normalize_hash(persona_set_hash),)) \
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
                    "returning id", (normalize_hash(doc.get("persona_set_hash") or ""), Jsonb(doc)))
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
    for name in ("pull-personas", "pull-heldout"):
        s = sub.add_parser(name)
        s.add_argument("--out", required=True)
        s.add_argument("--hash", help="persona_set_hash (default: latest)")
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
            print("pushed persona set", push_personas(conn, args.personas, args.heldout,
                                                      args.source, args.seed, args.notes))
        elif args.cmd == "pull-personas":
            print("pulled", pull_personas(conn, args.out, args.hash), "->", args.out)
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
