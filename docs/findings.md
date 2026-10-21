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
- Config: claude-haiku-4-5-20251001 and claude-haiku-5-5 (Anthropic API, thinking off,
  10 answers sampled per cell at temperature 1; the API has no log-probabilities),
  seeds 1 and 2, real core `sha256:6c6addff…f770` (2,415 personas, 35 age × gender ×
  education cells), arms treatment + vanilla (probes) and + placebo (scenarios),
  14 probes with WVS-7 wording + 2 scenarios. 2026-10-21. Report built per model.
- Result (TVD to the real weighted distribution; noise floor = largest gap between
  two seeds of the same config: Haiku 4.5 0.050, Haiku 5.5 0.078):

  | test item | 4.5 engine | 4.5 vanilla | 5.5 engine | 5.5 vanilla |
  |---|---|---|---|---|
  | trust_police | 0.387 | 0.411 | 0.528 | 0.533 |
  | trust_parliament | 0.708 | 0.523 | 0.295 | 0.708 |
  | life_satisfaction | 0.590 | 0.785 | 0.520 | 0.917 |
  | competition | 0.487 | 0.751 | 0.529 | 0.896 |
  | financial_satisfaction | 0.501 | refused | 0.501 | refused |
  | gender_income | 0.721 | 0.919 | 0.462 | 0.817 |
  | immigrant_jobs | 0.463 | 0.805 | 0.583 | 0.829 |
  | science_future | 0.736 | 0.883 | 0.714 | 0.714 |

  - **P1 ✓ (both models):** engine beats vanilla by more than the noise floor on
    5 of 8 test items for each model, but not the same five (4.5: competition,
    gender_income, immigrant_jobs, life_satisfaction, science_future; 5.5: the same
    minus science_future, plus trust_parliament). financial_satisfaction can't
    count: without a persona both models refuse ("I'm an AI and don't have a
    household"), so vanilla has no answer.
  - **P2 ✗ (reported only):** median test TVD 0.546 (4.5) / 0.524 (5.5) against
    0.005 for the ML baseline. See notes: P2 as registered can't be met by design.
  - **P3 partial:** tau on the four 1–10 test items is 1.0 for both models
    (≥ 0.6, the n = 4 "significant" level). "Higher than vanilla's tau" can't be
    checked: vanilla has no answer on financial_satisfaction, so it has no ranking
    of the four.
  - **P4:** P1 holds for both models; P3's first half holds for both.
  - Scenarios (Haiku 4.5): unemployment shock moves "support" by +55 points,
    AI adoption moves "oppose" by −29, both measurable (above the noise floor,
    placebo share inside 10–90 %, above the MDD). No real before/after data.
- Status: partial (P1 and P4 met; P3's vanilla comparison not determinable)
- Notes: TVD is order-blind; for ordinal items `comparison.json` also carries
  Wasserstein distance, which recent survey-simulation papers report next to
  TVD. If Wasserstein and TVD disagree on P1, both are reported and P1 is
  judged on TVD as registered here.
  - **Measurement bug found and fixed before this result:** answers were read from
    one output token, so a refusal starting "I can't…" or "I appreciate…" counted
    as option **I**, which is "9" on the 1–10 items. The first Haiku 4.5 run had
    financial_satisfaction vanilla at 100 % "9" this way. Answers now get three
    tokens and must be a bare letter; a cell refused in every repeat is left out
    and recorded (`metadata.refusals`). Every 10-option run was re-run; the
    numbers above are from the fixed code only.
  - Refusals are themselves a result: Haiku 5.5 refused some persona cells on 8
    of 14 probes (seed 1) (e.g. gender_jobs 10 cells / 767 personas, happiness 7 / 446),
    calling persona answers "fabricated"; Haiku 4.5 refused only the persona-less
    household question.
  - Absolute error is large (TVD ~0.5): both models put most cells on one or two
    options. Rankings come out right, shares don't (rule 1).
  - P2 design flaw, noticed only on the first run: the ML baseline is a model of
    the same item's real answers, and its weighted population average is the
    real marginal by construction (TVD ≈ 0.005). It is a ceiling only at the
    subgroup level; at population level the comparison says nothing about the
    engine. Not changed here; a subgroup-level P2 would be a new finding.

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

### F-4 — Realism of the synthetic persona set  (2026-10-21, Hasan)
- Question: can the 20,000 synthetic personas be told apart from the real core,
  and do they keep its joint structure better than a naive generator?
- Success criterion (written before running `python -m src.validation.realism`):
  - zero hard-rule violations;
  - structural zeros (synthetic personas with a pair of values no real respondent
    has) at most 3% — some unseen pairs are expected, since the core has 2,415 people;
  - C2ST AUC at most 0.60 (a cross-fitted classifier barely tells real from synthetic);
  - **relative**: the Bayesian network beats an independent-fields baseline (each
    field drawn from its own weighted marginal, same n) on 2-way SRMSE, 3-way
    SRMSE and C2ST AUC. Without this, the network adds nothing over margins.
- Config: core `sha256:6c6addff…f770`, synthetic `sha256:fcabc04f…f91d`, seed 0.
- Result (`reports/realism.json`):

  | | synthetic (BN) | independent baseline | criterion |
  |---|---|---|---|
  | hard-rule violations | 0 | — | 0 ✓ |
  | structural zeros | 4.32% | 22.43% | ≤ 3% ✗ |
  | SRMSE 2-way, mean | 0.190 | 0.283 | BN lower ✓ |
  | SRMSE 3-way, mean | 0.402 | 0.613 | BN lower ✓ |
  | C2ST AUC | 0.544 | 0.554 | ≤ 0.60 ✓, BN lower ✓ |
- Status: partial (structural-zero criterion missed)
- Notes: the worst unseen pair is age_band × region (672 personas): the core has
  65+ respondents in only 4 of 7 regions (Marmara 16, Ege 9, Akdeniz 3, İç Anadolu 2),
  while the synthetic set takes region × age × sex from the official 2025 table, so
  every region gets its elderly. Excluding the age/region/sex pairs fixed by official
  targets, the rate is 1.06%. These are sampling zeros of a 2,415-person core, not
  impossible people — but the criterion was registered as written and is reported as
  missed. Worst SRMSE tables involve region × religiosity (2-way 0.58) and
  region × income × religiosity (3-way 0.97): thin cells in the core. A fix (e.g. a
  LiTS-informed age × region structure, or TÜİK microdata) must be tested as a new
  finding, not tuned against this one. Measurement bug found and fixed before this
  result: income 4 vs 4.0 was counted as unseen (first run showed 100%).

### F-5 — Question-specific cells with anchor answers  (2026-10-21, Hasan)
- Question: do cells chosen per question (`cell_fields: auto`, `src/answering`)
  with the cell's answers to related anchor items in the prompt bring the engine
  closer to real answers than the default age × gender × education cells?
- Success criterion (written before any real-LLM run). Same model snapshot(s),
  seeds and persona set for both arms; `test`-role items only (the 8 of F-1):
  - **A1 — better on most items.** On at least 5 of the 8 test items, auto-cell
    TVD is lower than default-cell TVD by more than the probe noise floor.
  - **A2 — not worse overall.** Median TVD across the test items is not higher
    than the default's.
  - **A3 — rankings kept.** Kendall tau-b on the 1–10 test group (F-1 P3) is at
    least the default's.
  - **A4 — two models agree,** as in F-1 P4.
  - Pass: A1 + A2 + A4. A3 reported either way.
- Frozen settings: 3 anchors per question, similarity floor 0.1 (TF-IDF cosine
  on title + wording), 3 fields, MIN_CELL_N 30, anchors and exclusions as in
  `src/answering/anchors.yaml` at this commit. Any change to these is tuned on
  `fit` items only and recorded here before test items are scored.
- Config: claude-haiku-4-5-20251001, seeds 1 and 2, real core `sha256:6c6addff…f770`,
  same probes and sampling as F-1; `cell_fields: auto` (42–49 cells per probe,
  fields always region + religiosity, plus left–right or income). Compared with
  F-1's Haiku 4.5 default-cell runs. 2026-10-21.
- Result (test items, TVD default → auto; noise floor 0.050 default, 0.046 auto):
  trust_police 0.387 → 0.318, trust_parliament 0.708 → 0.600, life_satisfaction
  0.590 → 0.434, competition 0.487 → 0.406, financial_satisfaction 0.501 → 0.243,
  gender_income 0.721 → 0.279, immigrant_jobs 0.463 → 0.298, science_future
  0.736 → 0.610.
  - **A1 ✓:** lower by more than the noise floor on 8 of 8 test items.
  - **A2 ✓:** median test TVD 0.546 → 0.362.
  - **A3 ✓:** tau on the 1–10 test group 1.0, same as default.
  - **A4 not yet run:** the auto-cell runs exist for Haiku 4.5 only.
- Status: partial (A1–A3 met on one model; A4 pending a Haiku 5.5 auto run)
- Confound, stated before anyone reads more into it: auto mode changes two things
  at once (which fields define the cells, and the anchor answers in the prompt),
  and makes more cells (42–49 vs 35). Which of these helps is not separated here;
  a fields-only run (`cell_fields: [region, religiosity_band, ...]`, no anchors)
  would be the next finding.
- Notes:
  - Leakage guards: anchors are neither held-out items nor conditioning fields
    (test); every held-out target excludes its near-duplicate anchors (e.g. the
    confidence battery for the trust items); `src/answering` and `src/simulation`
    never import `src.validation` or open a held-out file (AST test).
  - Field importance on the real core (66 anchors, gradient boosting, permutation
    importance on 30% held back, mean over anchors): region 0.37, religiosity 0.21,
    left–right 0.14, income 0.10, settlement 0.06, every other field ≤ 0.03.
    Sensible spot checks: religious attendance → gender, news from social media
    → age, confidence in elections → left–right. Region's weight may partly be
    regional fieldwork differences in WVS-7 Türkiye, not only attitudes.
  - Known limit before running: lexical similarity finds no anchor above the
    floor for some test items (e.g. gender_income, science_future, whose closest
    anchors are excluded as near-duplicates); those use importance averaged over
    all anchors and get no anchor answers in the prompt. Semantic embeddings
    would be a new finding, not a change to this one.
  - Mock-model dry run (no accuracy meaning): 20,000 synthetic personas → 79 cells
    for the police-trust probe, 172 for the two scenarios (default: 48).

### F-6 — Calibration and stacking  (2026-10-21, Hasan)
- Question: does a temperature fitted on fit items make the engine's answer
  distributions closer to real ones on test items, and how much does the engine
  add to the ML baseline?
- Success criterion (written before any real-LLM run). Parameters from
  `python -m src.validation.calibration` on `fit`-role probes only; scored on the
  8 `test` items of F-1, same runs as the raw engine:
  - **C1 — calibration helps.** Median test-item TVD of `engine_calibrated` is
    lower than raw `engine` by more than the probe noise floor.
  - **C2 — it doesn't break rankings.** Kendall tau-b on the 1–10 test group is
    at least raw `engine`'s (a temperature per scale size can change the mean
    position of a skewed item).
  - **C3 — the engine adds something.** At least one fitted stack weight is
    above 0, and `stacked` has lower median test TVD than `ml_baseline` alone.
    If every weight is 0, the engine adds nothing beyond demographics on these
    items, and that is the result.
  - Pass: C1 + C2. C3 is reported either way.
- Frozen settings: temperature grid 0.5–5.0 step 0.1, weight grid 0–1 step 0.05,
  objective mean TVD, one parameter pair per answer-scale size (4, 5, 10 options;
  fit items: trust_government, trust_courts, happiness | gender_jobs |
  income_equality, science_life), ties broken toward no correction.
- Config: fitted on F-1's Haiku 4.5 default-cell runs, fit items only
  (`src/validation/calibration_params.yaml`); scored on the 8 test items of the same
  runs. Not applied to Haiku 5.5 (fitted on another model). 2026-10-21.
- Result: temperature 5.0 for every scale size (4, 5, 10 options), stack weight 0.
  - **C1 ✓:** median test TVD 0.546 (raw) → 0.367 (calibrated), a 0.18 gain over
    a 0.050 noise floor. Largest gains: immigrant_jobs 0.463 → 0.144, competition
    0.487 → 0.173, trust_police 0.387 → 0.177.
  - **C2 ✓:** tau on the 1–10 test group 1.0, same as raw.
  - **C3 ✗:** every stack weight is 0, so `stacked` = `ml_baseline` (0.005). With the
    ML baseline at the real marginal (see F-1's P2 note) this is expected, and says
    the engine adds nothing at population level beyond what that baseline holds.
- Status: valid (C1 + C2 met)
- The temperature sits on the upper edge of the frozen grid (5.0) for every scale:
  the optimum may be higher, and the raw answers are that over-confident. Widening
  the grid now would be tuning after seeing test items, so it is a new finding.
- Notes: `stacked` uses the ML baseline, which is trained on the item's real
  answers; it can't be used for a question without survey data, and is only a
  measure of what the engine adds. results.json stays raw; calibration lives in
  comparison.json only. Permuting test items' real answers leaves the parameters
  unchanged (test).
