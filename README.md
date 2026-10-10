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

Python, pandas/numpy/scipy, pytest. Mesa is available for agent-based
modeling scaffolding if a track finds it useful — not required.

## Team workstreams

The project splits into three independent tracks connected by two fixed data
contracts, so no one has to wait on anyone else to start. Each track's full
spec — scope, the exact schema it ships or consumes, sample fixture data, and
definition of done — lives in its own README:

| Track | Owns | Spec |
|---|---|---|
| **A — Data & Persona Layer** | Survey ingestion, calibration, the synthetic population | [`src/personas/README.md`](src/personas/README.md) |
| **B — Scenario Simulation Engine** | Turning a population + scenario into a response distribution | [`src/simulation/README.md`](src/simulation/README.md) |
| **C — Validation & Model Comparison** | Scoring accuracy, the equation-based and ML baselines | [`src/validation/README.md`](src/validation/README.md) |

Each track ships against a frozen schema (see its README) and a small
fabricated fixture file so the other two tracks can build and test against it
from day one, before any real data or code exists. Changing a schema is a PR
+ a heads-up to the other two tracks, not a silent edit.

## Status

Repo and workflow scaffolded (branch protection, issue/PR templates, 3
GitHub Projects boards), literature review and calibration data source survey
done (see [`docs/`](docs/)), field research presentation and TÜBİTAK 2209-B
form drafted. Tech stack decided; team split into three parallel tracks above.

## Team

Project lead: [@zxvozayy](https://github.com/zxvozayy)

## License

See [LICENSE](LICENSE).
