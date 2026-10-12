# Track D — UI / Dashboard

**Owner:** Ezgi ([@ezgiscodess](https://github.com/ezgiscodess))

**You own:** making the results legible — and honest — to a human. Nothing
about how they were produced.

> **Room to improve.** Fixed: the honesty rules below and reading only from
> the contracts. Layout, charts, interaction and even Streamlit itself are
> yours to choose — look at how current survey/forecast dashboards show
> uncertainty and comparisons, and try alternatives with real users
> (teammates count). Open questions: best way to show "effect vs. noise
> floor"; how to make warnings noticeable without cluttering.

## Your branch

- Work **only** on the `ezgi` branch, inside `src/ui/`. Don't commit to
  anyone else's branch, and never push to `main` — it only accepts pull
  requests with a teammate's approval.
- Start every session with `git pull origin main`.
- Finished an issue? Push to `ezgi` and open a PR into `main` with
  `Closes #<issue>` in the description. Don't wait for the sprint to end.
- Full workflow: [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Scope

A Streamlit dashboard (pure Python, no separate frontend stack) that reads
Track B's `results/*.json` and Track C's `reports/comparison.json`.

Minimum views:

- **Scenario view** — for one scenario: treatment vs. placebo side by side
  (two bars per option), the **effect** (treatment − placebo) as the
  headline, and the vanilla arm shown as a grey reference. Subgroups appear
  as **direction arrows** from `subgroup_direction`, never as percentages.
  If `measurable` is false, the headline says "no effect measurable above
  noise" instead of a number.
- **Validation view** — for each probe: real vs. engine vs. vanilla vs. both
  baselines, with TVD for each, plus the rank-agreement table. This is the
  screen that answers "should we trust it."
- **Model view** — when `comparison.json` has more than one model, show them
  side by side and flag disagreement visibly.
- **Run details** — from any summary row, drill down to the run it came from:
  model snapshot, seed, `persona_set_hash`, option order, `option_usage`.

## Honesty rules for the UI

From [`docs/methodology-rules.md`](../../docs/methodology-rules.md),
rules 1–3 and 12:
- **No absolute "X% of Turkey supports…" headline anywhere.** Scenarios show
  differences; absolute shares appear only inside the validation view next
  to the real answer.
- Subgroups: direction only. Cells listed in `small_cells` are greyed out
  with "n < 30, not tested." Never show province-level or other ultra-thin
  breakdowns.
- Don't show an income breakdown unless Track C has explicitly marked it as
  confirmed in the real data.
- Show every string in `warnings` verbatim, near the top. Never remove the
  "this may reflect the model's prior, not the population" caveat on
  scenarios.
- Never compute or reinterpret a metric here. If a number isn't in
  `results.json` or `comparison.json`, it belongs in Track C.
- No individual-level views.

## What you consume

Track B's `results.json` ([`../simulation/README.md`](../simulation/README.md))
and Track C's `comparison.json` ([`../validation/README.md`](../validation/README.md)).
You don't define a contract; you're a pure consumer.

## Don't wait for anyone

Everything you need already exists as fixtures:
- [`../simulation/fixtures/results.sample.json`](../simulation/fixtures/results.sample.json) — a scenario run
- [`../simulation/fixtures/results.probe.sample.json`](../simulation/fixtures/results.probe.sample.json) — a probe run
- [`../validation/fixtures/comparison.sample.json`](../validation/fixtures/comparison.sample.json) — Track C's report

Swap in real files once Tracks B and C produce them; the dashboard code
shouldn't change, only its inputs.

## How to run

```bash
pip install -r src/ui/requirements.txt
cd src/ui && streamlit run app.py     # http://localhost:8501
python -m pytest src/ui/tests         # from the repo root
```

Run it from `src/ui/` so `.streamlit/config.toml` (the theme) is picked up.
With no `results/*.json` at the repo root the dashboard reads the fixtures and
shows a "Fixture verisi" badge. Point it at real output with
`PERSPECTOME_RESULTS_DIR` and `PERSPECTOME_COMPARISON`.

## Definition of done

- [ ] Scenario view: treatment vs. placebo, effect headline, vanilla reference, subgroup arrows
- [ ] Validation view: real vs. engine vs. vanilla vs. baselines, TVD, rank agreement
- [ ] Warnings and small-cell flags rendered; no absolute-share headline anywhere
- [ ] Run-details drill-down
- [ ] Runs against the fixtures with zero pipeline code installed
- [ ] Runs end-to-end on real `results.json` / `comparison.json`
