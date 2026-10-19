# Findings log

Every measurement, the same day it runs. Owner: Track C (anyone may add).
Newest at the bottom. Write the success criterion **before** the run
(see [`methodology-rules.md`](methodology-rules.md), rule 9).

## Template

```
### F-<number> — <short title>  (<YYYY-MM-DD>, <author>)
- Question:
- Success criterion (written before running):
- Config: model snapshot, seed, persona_set_hash, n, arms
- Result: numbers, with noise floor
- Status: valid | partial | retracted (by F-<n>)
- Notes:
```

## Entries

### F-1 — Pass/fail thresholds for the first real run  (2026-10-20, Hasan)
- Question: what does the engine have to show on real WVS-7 Turkey personas
  before we call the persona layer useful? Written **before** any real run.
- Success criterion (written before running). All judged on `test`-role
  held-out items only (`schema.HELDOUT_ROLE`); `fit` items may be used to tune
  and never count here. Six ordinal test items are available: trust_police,
  trust_parliament, life_satisfaction, competition, political_leaning,
  financial_satisfaction. Metrics come from `reports/comparison.json`.
  - **P1 — persona layer beats no persona.** On at least 4 of the 6 test items,
    engine TVD is lower than vanilla TVD by more than the probe noise floor
    (TVD between two seeds of the same probe). Reason: vanilla is the model's
    own prior; if personas don't beat it, the persona layer adds nothing
    (rule 5).
  - **P2 — close to what demographics alone can do.** Median engine TVD across
    the test items is at most the median ML-baseline TVD + 0.05. Reason: the ML
    baseline is trained on real answers to the same item, so it approximates
    how much the conditioning fields can explain at all (a within-demographic
    ceiling, as in recent silicon-sample evaluations). The engine never sees
    answers; landing within 5 points of that ceiling is the realistic target.
    Reported, not required for a pass.
  - **P3 — rankings survive.** Kendall tau-b between real and engine orderings
    of the test items (by mean scale position) is at least 0.6, and higher
    than vanilla's tau. Rankings, not shares, are what we claim (rule 1). With
    6 items tau >= 0.733 is needed for one-sided p < .05 (exact permutation
    test: n=6 -> 0.733, n=7 -> 0.619, n=8 -> 0.571), so 0.6 is reported as
    "directional", 0.733+ as "significant".
  - **P4 — two models agree.** P1 and P3 hold for at least two model
    snapshots (rule 14); where they disagree, the result is "model-dependent",
    not a pass.
  - **Scenarios** have no pass/fail on accuracy (there is no real
    before/after data yet). An effect is only reported when `measurable` is
    true: above the noise floor, placebo share for the option of interest
    inside 10–90 %, and at least the minimum detectable difference. Engine
    effects are shown next to the equation baseline, whose priors are
    registered in `src/validation/equation_params.yaml`.
  - **Overall pass:** P1 + P3 + P4. P2 and scenario effects are reported either way.
- Config: to be filled on the first real run (model snapshots, seeds,
  persona_set_hash, n, arms).
- Result: —
- Status: pre-registered
- Notes: TVD is order-blind; for ordinal items `comparison.json` also carries
  Wasserstein distance, which recent survey-simulation papers report next to
  TVD. If Wasserstein and TVD disagree on P1, both are reported and P1 is
  judged on TVD as registered here.
