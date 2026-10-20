# Database

A shared PostgreSQL database (Supabase, EU Central / Frankfurt) holds the
copies every track exchanges. The CSV/JSON contracts don't change — the
database is where the shared copies live, so nobody passes files around and
every result is tied to the persona set it came from.

## Who can see what

Access follows track ownership and is enforced by database roles, not by
convention:

| Schema | Holds | Writes | Reads |
|---|---|---|---|
| `personas` | persona sets (exact `personas.csv` bytes) and personas | A | A, B, C, D |
| `heldout` | held-out answers (one row per persona × item) | A | **C only** |
| `sim` | Track B runs (full `results.json` as JSONB) | B | B, C, D |
| `validation` | Track C reports (full `comparison.json`) | C | C, D |
| `app` | Track D site accounts and chats | D | D |

Held-out data is closed to Tracks B and D at the schema level: their logins
can't even list the schema. This is the "held-out never reaches generation or
simulation" invariant, enforced by the database.

## Setup (once per person)

1. Install the driver: `pip install "psycopg[binary]>=3.1"` (or `pip install -e ".[db]"`).
2. Hasan sends you your personal connection string. Put it in a file named
   `.env` at the repo root (git-ignored — never commit it, never paste it in
   chat or an issue):

   ```
   DATABASE_URL=postgresql://<you>.<project-ref>:<password>@aws-...pooler.supabase.com:5432/postgres
   ```

3. Check it: `python -m src.common.db status` shows your user and what you can read.

Use a **pooler** address on `pooler.supabase.com` — session (port 5432) or
transaction (port 6543) both work; `db.py` turns off prepared statements on
6543 and drops Prisma-style `?pgbouncer=true`. The "direct connection"
address is IPv6-only on the free plan and fails on most home networks.

## Daily use

```bash
# Track A — publish a frozen persona set (refused if it already exists)
python -m src.common.db push-personas --personas data/processed/personas.csv \
    --heldout data/processed/heldout.csv --source "WVS-7 Turkey + Eurostat margins" --seed 0

# Track B — get the personas (same bytes, same persona_set_hash), then upload runs
python -m src.common.db pull-personas --out data/processed/personas.csv
python -m src.common.db push-runs results/*.json

# Track C — pull everything, build the report, upload it
python -m src.common.db pull-personas --out data/processed/personas.csv
python -m src.common.db pull-heldout  --out data/processed/heldout.csv
python -m src.common.db pull-runs     --out-dir results
python -m src.validation.report
python -m src.common.db push-report reports/comparison.json

# Track D — latest report and runs for the site
python -m src.common.db pull-report --out reports/comparison.json
python -m src.common.db pull-runs   --out-dir results
```

Rules the code enforces:
- A persona set is frozen: pushing the same hash twice is refused.
  Regenerating means a new set (and a PR, per Track A's README).
- `personas.csv` is checked against `src/common/schema.py` before upload:
  required columns, known categories, unique ids, and **no held-out field**.
- A run can only be uploaded for a persona set that exists in the database.
- `persona_set_hash` is stored as `sha256:<hex>`. Track A's generator prints
  bare hex and Track B's loader prints `sha256:<hex>`; the database accepts
  both and stores one form.

## Admin (Hasan)

The owner connection (`postgres.<ref>`) is only for these:

```bash
python -m src.common.db migrate         # apply db/migrations/*.sql not yet applied
python -m src.common.db create-users    # one login per teammate -> tmp/db-users.local.txt
python -m src.common.db create-users --reset   # new passwords for everyone
```

`tmp/` is git-ignored. Send each person only their own line, privately.
Schema changes are new numbered files in `db/migrations/` and go through a PR
like any contract change.

## Free-plan notes

- The project pauses after a week without activity. "Restore" in the
  Supabase dashboard brings it back; nothing is lost.
- 500 MB storage — far more than we need.
- The Data API is off and automatic RLS is on, so tables are never exposed
  over HTTP. All access is through these logins.
- WVS is research-use licensed: the held-out answers are real respondents'
  answers. The project stays private to the team.
