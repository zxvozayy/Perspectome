# Track B — Scenario Simulation Engine

**You own:** turning a population + a scenario into a population-level
response distribution — and nothing about where the population came from or
how it's scored afterward.

## Scope

- Define a scenario format (YAML or JSON) describing a policy shift, economic
  shock, or demographic change to test.
- **Round 1 — independent stance:** each persona takes an initial position,
  independently.
- **Round 2 — calibrated deliberation:** do **not** just average independent
  votes. The literature review (`docs/literature-review.md`, Ozkan 2026) found
  that treating personas as fully independent agents causes "modal collapse"
  toward the majority answer. Use a distribution-first approach instead: model
  the population's response distribution directly and let each persona's
  `risk_tolerance` / `economic_optimism` (from Track A's held-out fields,
  used only at validation/analysis time, never fed back into generation)
  inform how much it shifts.
- **Round 3 — settle:** aggregate to a final population-level distribution,
  overall and broken out by at least one demographic subgroup (e.g. age_band).
- Never output an individual-level prediction — only population-level
  distributions. That's a hard project boundary, not a style preference.

## What you ship

A scenario runner under `src/simulation/` that takes a `personas.csv` (any
file matching Track A's schema) and a scenario definition, and produces one
`results/<scenario_id>.json` per run, matching the schema below.

## The contract (freeze this on day 1)

```json
{
  "scenario_id": "string, unique",
  "round": 3,
  "n_personas": 500,
  "response_distribution": {
    "support": 0.42,
    "oppose": 0.31,
    "uncertain": 0.27
  },
  "by_subgroup": {
    "age_band": {
      "18-24": {"support": 0.55, "oppose": 0.20, "uncertain": 0.25},
      "65+":   {"support": 0.30, "oppose": 0.45, "uncertain": 0.25}
    }
  },
  "metadata": {
    "model": "mock | <real model name>",
    "n_rounds": 3,
    "timestamp": "ISO 8601"
  }
}
```

A sample file matching this schema is in [`fixtures/`](fixtures/) — fabricated
numbers, just so Track C has something to validate against from day 1.

## Don't wait for anyone

Use [`../personas/fixtures/personas.sample.csv`](../personas/fixtures/personas.sample.csv)
to develop against. You do not need Track A's real pipeline finished — only
the schema, which is already frozen above. Swap in the real `personas.csv`
once it exists; nothing else should need to change.

## If you need to change the contract

Open a PR and say so in the team channel — Track C is coding its validation
step against `results.json`'s shape from day one.

## Definition of done

- [ ] Scenario definition format documented with at least 2 example scenarios
- [ ] Three-round simulation implemented (independent stance → calibrated deliberation → settle)
- [ ] Output matches the `results.json` schema above, including at least one subgroup breakdown
- [ ] Runs end-to-end against both the fixture personas and Track A's real `personas.csv`
