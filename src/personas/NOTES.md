# Track A — real-data notes (WVS-7 Turkey)

Findings from running the ingest step (issue #6) against the real WVS Wave 7
Turkey file (country code 792, n=2415). Recorded here so #10/#14 don't
rediscover them. The raw file lives under git-ignored `data/` and is never
committed.

## Region coding (resolved)

- `N_REGION_ISO` is **entirely missing (-5)** for Turkey — do not use it.
- The live region variable is **`N_REG_NUTS1`** (İBBS Düzey-1 / NUTS-1, 12
  regions, coded `792NN`). `wvs.REGION_MAP` maps the 12 NUTS-1 regions onto
  the 7 schema regions. The `792NN -> NUTS-1` order is the standard İBBS
  numbering and is corroborated by the response counts (79201 = İstanbul is
  the largest cell). `N_REGION_WVS` and `N_REGION_NUTS2` are also available if
  a finer cut is ever needed.

## Education (real limitation, not a mapping bug)

- `Q275` (ISCED 2011) takes only `{0,1,2,3,6}` for Turkey — **no 4/5/7/8**.
  So `vocational` and `graduate` come out empty; Turkish vocational high
  schools fall under upper-secondary (3) and postgraduate degrees are not
  separated from bachelor (6) in the ISCED variable.
- The country-specific `Q275A` (codes `792001..792024`) carries finer Turkish
  categories and could recover vocational/graduate — but only after decoding
  it against the WVS Turkey codebook annex. Candidate enrichment for #10; do
  not guess the decode.

## Income

- `Q288` (self-placed income group 1-10) **is populated** for Turkey (≈86 of
  2415 missing). The harmonized `X047_WVS7` is the one missing for Turkey, not
  `Q288`.

## Post-stratification margins (issue #10 inputs)

- TÜİK (the designated authoritative source) and ISSP/LiTS **cannot be fetched
  programmatically**: TÜİK is an interactive JS portal with no stable file URL
  (no account needed, but a browser click-through is), ISSP needs a GESIS
  account, and LiTS shows "Data Access Not Available" on IHSN (EBRD/WB route is
  gated). These stay manual downloads into `data/raw/{tuik,issp,lits}/`.
- **Eurostat** IS registration-free and fetchable via its REST API
  (`src/personas/fetch_eurostat_margins.py`). It reports Turkey at **NUTS-1**,
  the same level as WVS `N_REG_NUTS1`, so region cells line up exactly. Pulled:
  - `data/raw/eurostat/tr_population_age_sex_nuts1.csv` — pop by 5-yr age ×
    sex × 12 NUTS-1 regions (2024)
  - `data/raw/eurostat/tr_education_sex_age.csv` — ISCED attainment × sex × age
    (%); note it carries the ED5-8 / ED3_4 split WVS `Q275` lacked.
- **VERIFY before any calibration claim:** Eurostat re-publishes TÜİK's
  aggregates, so it is a close stand-in, but confirm against TÜİK's own tables
  (and harmonize Eurostat's 5-year age groups to the schema bands -- 18-24 is
  not a clean Eurostat group) in #10. This source choice is not a silent swap.

## Calibration result (issue #10)

- Raking / IPF on four marginals (age_band, gender, region, edu3) against the
  Eurostat targets converges to **max calibration error ≈ 0.00 pp** — raking
  matches each marginal exactly by construction. Joint fit is not claimed; only
  marginals are calibrated.
- 2415 personas, deterministic (no sampling) -> stable `persona_set_hash`.
  10 respondents missing a raking variable keep weight 1.0 (warned, not dropped).
- The targets are Eurostat (TÜİK-sourced) + the 18-24 age approximation and the
  national-only education split noted above. **Verify against TÜİK's own tables
  before any calibration claim**, and re-run (the hash will change, which
  invalidates earlier Track B measurements -- so it's a PR, not a quiet rerun).
- This belongs in `docs/findings.md` too, but that file is Track C's (Hasan's)
  per CONTRIBUTING.md -- record it there via him / a small shared-file PR.

## Frozen persona set (issue #14)

Reproducible generation command (fixed seed, deterministic):

    python -m src.personas.generator --seed 0

Produces (git-ignored): `data/processed/personas.csv` + `data/processed/heldout.csv`.

    seed              : 0
    n_personas        : 2415
    persona_set_hash  : 30961ad5ebfcda7a838e416dbb60250b0333caef61940283f5945723f109bc67

Track B records this `persona_set_hash` on every run. The set is frozen:
regenerating it (new raw file, changed mapping/margins, or seed) changes the
hash and invalidates every earlier Track B measurement, so it is a PR with a
heads-up, never a quiet rerun. NB: the hash above is from the current Eurostat
margins; it will change once margins are verified/replaced against TÜİK.

## Still needs a cross-track decision

- The conditioning-vs-held-out split of the WVS value items needs **Track C
  (Hasan) sign-off** before it is locked into `src/common/schema.py` (persona
  README's "first decision"). The current held-out attitude mappings
  (`Q240/Q164/Q50/Q47` + the confidence battery) are defaults pending that.
- WVS Turkey fieldwork is 2018 — note time drift wherever results are shown.
