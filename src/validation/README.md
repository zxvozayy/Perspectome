# Track C — Validation & Model Comparison

**Owner:** Hasan Özay Yılmaz ([@zxvozayy](https://github.com/zxvozayy))

**You own:** deciding what the simulation's output is allowed to claim,
scoring it against reality, and building the baselines it's compared
against. You also own [`docs/findings.md`](../../docs/findings.md).

## Scope

### Probes — does the engine match reality?
- For every `probe` run, compare each arm to the real distribution of
  `target_item` in Track A's `heldout.csv` (weighted by `weight`):
  total variation distance (TVD) and held-out calibration error.
- **Ranking agreement across probes** (e.g. Kendall's tau over items: "which
  institution is trusted more"). Rankings are what survives a model change;
  absolute shares don't ([rule 1](../../docs/methodology-rules.md)).
- Persona contribution = treatment vs. vanilla. If the persona arm isn't
  clearly closer to reality than vanilla, the persona layer isn't working.
- Reality checks beyond the marginals: inter-item consistency (simulated
  personas tend to be *too* consistent), between-persona diversity (tends to
  be too low), and level bias per item.

### Scenarios — is there an effect at all?
- Effect = treatment − placebo, per option and as TVD.
- **Noise floor first**: the same config at two seeds. An effect below the
  noise floor is reported as "not measurable" ([rule 6](../../docs/methodology-rules.md)).
- **Saturation screen**: placebo share outside 10–90% → item can't show an
  effect ([rule 7](../../docs/methodology-rules.md)).
- Before running, compute the minimum detectable difference for the n.
  Nulls are "not measurable at this n," never "no effect."
- Subgroups: **direction only**, Benjamini–Hochberg across cells, cells with
  `n` < 30 flagged and not tested. A subgroup gap is only reportable if the
  same gap exists in the real held-out data — simulated populations invent
  stereotyped gradients (income is a known offender).

### Baselines
- **Equation-based**: a small system-dynamics / ODE model that takes the same
  scenario input and produces a comparable distribution or effect, no agents.
  The "boring but honest" comparison point — population-model papers report
  gains against exactly this kind of emulator.
- **ML**: multinomial regression on the conditioning fields, fit on a train
  split of `heldout.csv`, scored on the test split. Applies to probes.
  Expect it to be weak — demographics carry little attitude signal — which
  is itself worth reporting.
- **Model sensitivity**: run probes on at least two LLMs; report where they
  agree ([rule 14](../../docs/methodology-rules.md)).

### Discipline
- Write the pass/fail threshold into `findings.md` **before** running
  ([rule 9](../../docs/methodology-rules.md)).
- Fit any correction on one split, measure on another. If you shrink
  over-confident distributions toward uniform, fit the factor separately by
  option count (binary / 3–4 / 5+) — shrinkage fixes over-confidence but
  makes direction errors worse.
- Compare discrete simulated answers with discrete human answers, and say
  which aggregation you used.
- Retrospective validation: prefer periods after the model's training cutoff,
  or flag the result as possibly contaminated ([rule 34](../../docs/methodology-rules.md)).
- Test the statistics core (TVD, n_eff, BH, tau) against hand-computed
  reference values.

## What you consume

Track B's `results.json` (see [`../simulation/README.md`](../simulation/README.md))
and Track A's `heldout.csv` (see [`../personas/README.md`](../personas/README.md)).

## What you ship — the contract Track D consumes (freeze this on day 1)

`reports/comparison.json`:

```json
{
  "generated_at": "ISO 8601",
  "persona_set_hash": "sha256 of personas.csv",
  "noise_floor_tvd": 0.04,
  "probes": [
    {
      "item": "trust_institutions",
      "options": ["1", "2", "3", "4", "5"],
      "real": {"1": 0.10, "2": 0.20, "3": 0.30, "4": 0.25, "5": 0.15},
      "methods": {
        "engine":            {"distribution": {"1": 0.07, "2": 0.20, "3": 0.33, "4": 0.27, "5": 0.13}, "tvd": 0.05},
        "vanilla":           {"distribution": {"1": 0.00, "2": 0.05, "3": 0.85, "4": 0.10, "5": 0.00}, "tvd": 0.55},
        "equation_baseline": {"distribution": {"...": 0}, "tvd": 0.12},
        "ml_baseline":       {"distribution": {"...": 0}, "tvd": 0.09}
      },
      "models": {"<model_snapshot>": {"tvd": 0.05}}
    }
  ],
  "rank_agreement": {
    "metric": "kendall_tau",
    "n_items": 5,
    "methods": {"engine": 0.6, "vanilla": 0.2, "ml_baseline": 0.4}
  },
  "scenarios": [
    {
      "scenario_id": "unemployment_shock_v1",
      "effect_vs_placebo": {"support": 0.14, "oppose": -0.07, "uncertain": -0.07},
      "effect_tvd": 0.14,
      "measurable": true,
      "saturated": false,
      "equation_baseline_effect": {"support": 0.08, "oppose": -0.08, "uncertain": 0.00},
      "subgroup_direction": {"age_band": {"18-24": "+", "65+": "0"}},
      "small_cells": ["45-54", "55-64", "65+"],
      "models_agree": null
    }
  ],
  "warnings": ["free-text caveats Track D must show verbatim"]
}
```

`real` appears only for probes. Scenarios carry effects, never absolute
shares. A sample is in [`fixtures/`](fixtures/) — fabricated numbers.

## Don't wait for anyone

Build against [`../simulation/fixtures/`](../simulation/fixtures/) (one
scenario run, one probe run) and
[`../personas/fixtures/heldout.sample.csv`](../personas/fixtures/heldout.sample.csv).
Swap in real outputs from Tracks A and B once they exist — your code
shouldn't need to change, only its inputs.

## Definition of done

- [ ] Signed off Track A's conditioning vs. held-out item lists
- [ ] TVD, calibration error, rank agreement, effect vs. placebo — tested against hand-computed values
- [ ] Noise floor, saturation screen, minimum detectable difference, BH + small-cell flags
- [ ] Equation-based and ML baselines producing comparable output
- [ ] `comparison.json` matching the schema above, generated from the fixtures
- [ ] Pass/fail thresholds written in `findings.md` before the first real run
- [ ] End-to-end report on real A + B outputs, at least two models
