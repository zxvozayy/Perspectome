# Perspectome

**AI-Powered Digital Society Twin** — a computational social simulation platform.

Engineering Design II · Project 09 · 2026

## Objective

Build a virtual laboratory for society: large populations of synthetic AI agents with
diverse demographic, socioeconomic, and behavioral profiles, calibrated on anonymized
aggregate data. Run controlled social and economic scenarios, observe emergent
population-level patterns — never predicting individuals — and validate retrospectively
against historical data.

## Key activities

- **Synthetic populations** — generate heterogeneous agents with demographic,
  socioeconomic, and behavioral attributes.
- **Scenario simulation** — test policy shifts, economic shocks, and demographic change
  in a controlled setting.
- **Historical validation** — calibrate on real aggregate data; measure accuracy while
  preserving individual privacy.
- **Model comparison** — contrast agent-based, differential-equation, and
  machine-learning approaches.

## Example questions

- How do public attitudes shift when unemployment rises?
- How do younger and older groups react to rapid AI adoption?

## Tech stack

- **Python** (pandas, numpy, PyYAML) for every track; **pytest** for tests,
  run on every pull request by GitHub Actions.
- **PostgreSQL** (Supabase, EU) as the shared store, with one schema and one
  database role per track — see [`docs/database.md`](docs/database.md).
- **Dashboard:** a small web app on the Python standard library (no frontend
  build step).
- **LLM:** pluggable; a deterministic mock model is the default, real models
  only behind an explicit `--live` flag with a hard call cap.

## Team workstreams

The project splits into four independent tracks connected by fixed data
contracts, so no one has to wait on anyone else to start. Each track's full
spec — scope, the exact schema it ships or consumes, sample fixture data, and
definition of done — lives in its own README:

| Track | Owns | Spec |
|---|---|---|
| **A — Data & Persona Layer** | Survey ingestion, calibration, the synthetic population | [`src/personas/README.md`](src/personas/README.md) |
| **B — Scenario Simulation Engine** | Turning a population + scenario into a response distribution | [`src/simulation/README.md`](src/simulation/README.md) |
| **C — Validation & Model Comparison** | Scoring accuracy, the equation-based and ML baselines | [`src/validation/README.md`](src/validation/README.md) |
| **D — UI / Dashboard** | Making results legible: charts for scenarios and model comparisons | [`src/ui/README.md`](src/ui/README.md) |

A and B/C are connected by a producer/consumer schema; C and D both consume
B's output and C's report without touching each other's code. Each track
ships against a frozen schema (see its README) and a small fabricated fixture
file so the others can build and test against it from day one, before any
real data or code exists. Changing a schema is a PR + a heads-up to the
tracks that consume it, not a silent edit.

Shared ground for all tracks:
- [`docs/methodology-rules.md`](docs/methodology-rules.md) — a few fixed
  invariants plus starting defaults. Research current work before building,
  and replace a default only after a recorded test shows something better.
- [`docs/findings.md`](docs/findings.md) — every measurement, the day it runs.
- [`src/common/schema.py`](src/common/schema.py) — the one place category
  values and field lists are defined.
- [`docs/database.md`](docs/database.md) — the shared PostgreSQL database:
  who can read what, setup, and the push/pull commands for each track.

## Quick start

```bash
pip install -e ".[dev,llm,ml]"
python -m src.common.db pull-personas --out data/processed/personas.csv   # or python -m src.personas.generator
python -m src.pipeline --model claude-haiku-4-5-20251001   # real personas -> live model (2 seeds) -> report
python -m src.ui.server     # dashboard on http://localhost:8501
python -m pytest            # all tests
```

Everything runs on real data only: the pipeline needs the persona files under
`data/processed/` and an API key in `.env` (see `src/simulation/README.md`),
and the site shows nothing until a real run exists. `--synthetic` simulates the
20,000 synthetic personas, `--cells auto` uses question-specific cells. The
small fabricated files under `*/fixtures/` exist only for the automated tests.

## Status

| Track | Done | Next |
|---|---|---|
| A — Personas | WVS-7 Turkey ingest and cleaning, held-out split (12 items, fit/test roles), raked persona generator, frozen `persona_set_hash` | Publish the real persona set to the database; cross-tabulated raking |
| B — Simulation | Probe/scenario runner, three arms (treatment / placebo / vanilla), per-archetype querying, Friedkin–Johnsen update in code | Real-model runs at two seeds on the real personas |
| C — Validation | TVD, calibration error, Wasserstein, Kendall tau, noise floor, saturation, MDD, BH; ML and equation baselines; `comparison.json`; pass/fail thresholds pre-registered ([F-1](docs/findings.md)) | First end-to-end report on real data, two models |
| D — Dashboard | Intro page, sign-in, scenario and validation views following the honesty rules | Real pipeline output; accounts in the database |
| Shared | Supabase PostgreSQL with per-track roles (held-out readable by Track C only), CI | — |

Sprints run weekly on the [Iterative Development board](https://github.com/users/zxvozayy/projects/2).

## Team

- Project lead: Hasan Özay Yılmaz ([@zxvozayy](https://github.com/zxvozayy))
- Ezgi ([@ezgiscodess](https://github.com/ezgiscodess))
- Fatmanur ([@fatmanurdurak](https://github.com/fatmanurdurak))
- Yiğithan ([@DeFultt](https://github.com/DeFultt))

## License

See [LICENSE](LICENSE).
