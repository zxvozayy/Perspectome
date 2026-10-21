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
  and never count here. Eight ordinal test items are available: trust_police,
  trust_parliament, life_satisfaction, competition, financial_satisfaction,
  gender_income, immigrant_jobs, science_future. Metrics come from `reports/comparison.json`.
  - **P1 — persona layer beats no persona.** On at least 5 of the 8 test items,
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
    (by mean scale position) is at least 0.6, and higher than vanilla's tau.
    Rankings, not shares, are what we claim (rule 1). Items are ranked only
    against items on the same answer scale: the four 1–10 test items
    (life_satisfaction, competition, financial_satisfaction, science_future)
    form the scored group; the trust battery (4-point, only 2 test items) is
    reported as a development check. With 4 items only tau = 1 reaches
    one-sided p < .05 (exact permutation test: n=4 -> 1.0, n=5 -> 0.8,
    n=6 -> 0.733), so 0.6 is reported as "directional", 1.0 as "significant".
    *Revised 2026-10-21, before any real run: the first version ranked all six
    ordinal test items together, mixing 4-point and 1–10 scales, whose mean
    positions aren't comparable.*
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
  - *Revised 2026-10-21, before any real run (project-lead decision): religiosity
    (Q164) and left–right (Q240) became persona conditioning fields, so they and
    the near-duplicate religious_identity (Q173) left the held-out set. New pairs,
    checked against the WVS-7 codebook and asked in the Türkiye file: gender roles
    Q33 (fit) / Q35 (test), migration Q34 (test), science Q158 (fit) / Q159 (test).
    P1 now needs 5 of 8 test items.*
- Config: to be filled on the first real run (model snapshots, seeds,
  persona_set_hash, n, arms).
- Result: —
- Status: pre-registered
- Notes: TVD is order-blind; for ordinal items `comparison.json` also carries
  Wasserstein distance, which recent survey-simulation papers report next to
  TVD. If Wasserstein and TVD disagree on P1, both are reported and P1 is
  judged on TVD as registered here.

### F-2 — Real persona set: calibration and weight cost  (2026-10-21, Hasan)
- Question: how well does the frozen persona set match the population margins,
  and what do the post-stratification weights cost?
- Success criterion (written before running): every raked margin within 1 pp of
  its target; Kish n_eff reported next to n.
- Config: `python -m src.personas.generator --seed 0`, WVS-7 Turkey v6 (n=2,415),
  Eurostat 2024 margins (age band, gender, NUTS-1 region, education), raking on
  four one-way margins. persona_set_hash
  `sha256:30961ad5ebfcda7a838e416dbb60250b0333caef61940283f5945723f109bc67`.
- Result: max calibration error 0.0000 pp on all four margins. Kish n_eff 1,022
  of 2,415 (42%); weights 0.52–16.36. The 65+ band has only 30 respondents, each
  carrying a mean weight of 11.1; every other band has 369–584 respondents with
  mean weights 0.71–1.03. 35 archetype cells (age × gender × education), 9 with
  fewer than 30 personas. 10 personas have no cell (a cell-defining field missing)
  and are left out of simulation runs.
- Status: valid
- Notes: anything said about the 65+ band rests on 30 people; report it as such
  or merge 55–64 and 65+ for subgroup tests. Margins match by construction, so
  this is a check on the raking, not evidence that the joint distribution is
  right. Eurostat re-publishes TÜİK figures; still to verify against TÜİK's own
  tables.

### F-3 — Synthetic persona set v2: calibration, weights and rare combinations  (2026-10-21, Hasan)
- Question: does a 20,000-persona set drawn from the real core keep the core's
  joint structure and hit the 2025 population targets, without inventing
  impossible or over-frequent combinations?
- Success criterion (written before running): zero hard-rule violations; every
  2025 joint target (region × age × sex, age × sex × education) within 0.1 pp;
  every soft-rule share at most 3× the real core's share or 0.1% if the core has none.
- Config: `python -m src.personas.generator --seed 0` (Bayesian network on the
  WVS-7 core, employment | age, sex, marital status; alpha 0.05; raked to
  Eurostat 2025 joint targets; LiTS IV donors; published tables). Real core
  `sha256:6c6addff…f770` (2,415, raked to 2025 one-way margins), synthetic
  `sha256:fcabc04f…f91d` (20,000). Same hashes in two processes with different
  PYTHONHASHSEED.
- Result: joint calibration error 0.0000 pp; Kish n_eff 16,640 of 20,000
  (core: 967 of 2,415); 65+ is 14.3% weighted, 2,786 personas. Hard rules: 0.
  Soft rules, core → synthetic: married student 0.041% → 0.080%, student 55+
  0.041% → 0.080%, divorced under 25 0.124% → 0.105%, retired under 35 0 → 0.020%,
  male homemaker 0 → 0.010%, graduate under 25 0 → 0.005%, widowed under 25 and
  unemployed top income 0 → 0. Daily smokers 30.1% (TÜİK 2025: 30.1%).
- Status: valid
- Notes: the first design (employment | age, sex; alpha 0.5) made married
  students 0.87% (21× the core) — fixed before adoption. The synthetic set adds
  no information beyond the 2,415 respondents: validation power is computed on
  the core's effective size, and held-out answers exist only for the core. The
  65+ structure still rests on 30 WVS respondents (smoothed); attached features
  carry the conditional-independence assumptions listed in the generator summary.
