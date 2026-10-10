# Track C — Validation & Model Comparison

**You own:** scoring whether the simulation's output can be trusted, and
building the two baselines it gets compared against.

## Scope

- **Validation metrics**: total variation distance (TVD) between a scenario's
  `response_distribution` and the real answer distribution recovered from
  Track A's `heldout.csv`, plus held-out calibration error. See
  `docs/literature-review.md` for why TVD/held-out error (not raw accuracy
  alone) are the right metrics here.
- **Baseline 1 — equation-based**: a simple system-dynamics / differential-
  equation model that takes the same scenario input and produces a comparable
  `response_distribution`, with no agents at all. This is the "boring but
  honest" comparison point.
- **Baseline 2 — ML baseline**: a plain statistical model (e.g. logistic/
  multinomial regression on `personas.csv`'s demographic fields, fit on a
  held-out split) producing the same output shape.
- **Comparison report**: for each scenario, a table of the simulation engine
  vs. both baselines vs. the real held-out answer, with TVD for each.
- You decide when something "passes" — define the threshold and write down
  why, don't just eyeball it.

## What you ship

A validation/scoring module under `src/validation/` that takes one or more
`results.json` files (Track B's output) plus Track A's `heldout.csv`, and
produces a comparison report (markdown or a small table) scoring the agent-
based engine against both baselines.

## The contract you consume

Track B's `results.json` schema (see
[`../simulation/README.md`](../simulation/README.md)) and Track A's
`heldout.csv` schema (see [`../personas/README.md`](../personas/README.md)).
You don't produce a new contract — you're the last stage of the pipeline.

## Don't wait for anyone

Use [`../simulation/fixtures/results.sample.json`](../simulation/fixtures/results.sample.json)
and [`../personas/fixtures/heldout.sample.csv`](../personas/fixtures/heldout.sample.csv)
to build and test your scoring code today. Swap in real outputs from Tracks A
and B once they exist — your code shouldn't need to change, only its inputs.

## Definition of done

- [ ] TVD + held-out calibration error implemented and running against the fixtures
- [ ] Equation-based baseline implemented, producing the same output shape
- [ ] ML baseline implemented, producing the same output shape
- [ ] Comparison report generator, run on at least one real end-to-end scenario once Tracks A and B land
