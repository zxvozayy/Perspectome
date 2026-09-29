# Calibration Data Sources

Survey of public data sources for calibrating the general-population synthetic
panel, beyond the primary World Values Survey source. Researched fresh for
this project — no prior-project data reused.

## What calibration needs

(a) demographic/socioeconomic microdata or well-documented marginal
distributions for Turkey, and (b) attitudinal/behavioral survey data that can
be held out from persona generation and used to validate calibration
accuracy — i.e. real joint demographic+attitude distributions, not just
demographics.

## Recommended sources

1. **World Values Survey, Wave 7, Turkey** (primary). Real joint
   demographic+attitude microdata, n=2,414. Free after registration at
   [worldvaluessurvey.org](https://www.worldvaluessurvey.org/), research-use
   license (no redistribution). Turkey also fielded in Waves 3–6, giving a
   time series for historical-validation work.

2. **TÜİK aggregate bulletins** — Life Satisfaction Survey (annual,
   2020–2024), Population and Housing Census 2021, Household Consumption
   Expenditures. Freely downloadable at
   [data.tuik.gov.tr](https://data.tuik.gov.tr/), no registration. These are
   the authoritative population margins to post-stratify the WVS sample
   against — marginal distributions, not joint demographic-attitude data.

3. **ISSP Turkey modules** — 2008 (Religion), 2013 (National Identity), 2014
   (Citizenship II), 2015 (Work Orientations IV). Free download with
   documentation from the [GESIS ISSP
   archive](https://issp.org/data-download/archive/). Independent of WVS,
   useful for cross-validating calibration robustness outside WVS's own
   question set.

4. **Life in Transition Survey (EBRD/World Bank)** — Turkey included in LiTS
   I/II/III and a 2022–23 wave (~1,000–1,500 households). Free, direct
   download from the [World Bank Microdata
   Library](https://microdata.worldbank.org/index.php/catalog/584). Fielded
   by a different organization than WVS/ISSP, so it works as a genuinely
   independent held-out validation set, not just held-out variables from the
   same survey.

## Considered and deprioritized

| Source | Why not |
|---|---|
| EU-SILC Turkey (Eurostat) | Microdata restricted to "recognised research entities"; not publicly accessible |
| TÜİK microdata (E-VAM) | Pilot phase, applications only via 3 partner universities, hourly/annual fees (Turkish Statistics Law No. 5429) |
| European Social Survey | Turkey's participation in any round could not be confirmed |
| Gallup World Poll | Paywalled; only aggregate life-evaluation numbers are free (via the World Happiness Report data table) |
| KONDA raw data | Domestic pollster with strong reputation, but license/access terms for a usable dataset could not be confirmed (an open "Kontent" portal was in beta as of Dec 2024 — worth rechecking) |
| Candidate Countries Eurobarometer | Real Turkey-specific data via GESIS, but dated (2001–2004) — useful only as a historical reference point |
| Pew Global Attitudes | Free with account, but Turkey coverage is ad hoc by wave — useful for specific topical checks, not a full replacement source |
| Edelman Trust Barometer | Turkey's inclusion in the sampled countries could not be confirmed from the archive alone |

## Pitfalls to design around

- **Redistribution restrictions**: WVS/ISSP/LiTS are research-use licensed —
  fine to use for calibration, never to redistribute the raw files. `data/`
  stays git-ignored regardless of source.
- **Sentinel missing-value codes**: negative codes (don't know / no answer /
  not asked / missing) are near-universal across these surveys and must be
  recoded to null before use — build one generic recoding step, don't assume
  clean data.
- **Held-out leakage discipline**: keep attitude/opinion fields structurally
  separate from the fields used to condition persona generation, regardless
  of which survey(s) supply the data.
- **Joint vs. marginal-only risk**: TÜİK bulletins give strong marginal
  distributions (age × gender × region) but not joint demographic-attitude
  distributions. Use them only to reweight/post-stratify a real joint-
  microdata source (WVS/ISSP/LiTS) — never as a standalone source of
  attitude data.
- **Cross-source non-comparability**: WVS, ISSP, and LiTS use different
  question wordings/scales for superficially similar constructs (trust, life
  satisfaction). Consistent with the wording-sensitivity finding in
  [`literature-review.md`](literature-review.md) (Li & Conrad, 2026) — don't
  naively pool raw values across sources without harmonization.
