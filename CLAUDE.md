# Perspectome — project context

**AI-Powered Digital Society Twin** — Engineering Design II, Project 09 (2026).

## What this project is

A computational social simulation platform: synthetic AI-agent populations with
demographic, socioeconomic, and behavioral profiles, calibrated on anonymized
aggregate survey data. The platform runs controlled social/economic scenarios
(policy shifts, economic shocks, demographic change), observes emergent
population-level patterns, and validates retrospectively against historical data.
See [`README.md`](README.md) for the full brief.

## Status

- Repo scaffolded: branch strategy, issue/PR templates, `main` branch-protected
  (PR + 1 review required).
- Literature review complete — 9 annotated academic sources, see
  [`docs/literature-review.md`](docs/literature-review.md).
- Field research presentation (topic/problem, literature, similar tools,
  methodology, stack, scope, sources) drafted.
- TÜBİTAK 2209-B research proposal form drafted from the official template.
- **Open decisions**: final tech stack (Python + Mesa is the current working
  proposal, not yet confirmed by the team), team member names still placeholders
  in the presentation and form.

## Conventions

- Branches: `main` (protected) ← `dev` ← `feature/<name>`. See
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Commits: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore:`).
- Project tracking: three GitHub Projects boards —
  **Iterative Development** (sprint planning), **Kanban** (Todo → In Progress →
  Review → Done), **Bug Tracker** (New → Triage → In Progress → Fixed/Done).
- Real datasets are never committed (`data/` is git-ignored); only public,
  appropriately licensed aggregate data is used for calibration.

## Deadlines

- Sprint 1 submission — **2026-09-30, 07:00**: field research presentation,
  TÜBİTAK 2209-B form, and this repository link (public, team added, base
  structure visible).
