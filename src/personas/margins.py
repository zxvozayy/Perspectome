"""Post-stratification target margins for Turkey, from the Eurostat pulls.

Turns the two registration-free Eurostat files (see fetch_eurostat_margins.py)
into four marginal target distributions the raking step calibrates to:

    age_band (6)  ·  gender (2)  ·  region (7)  ·  edu3 (3: low/mid/high)

All margins are computed on the 18+ population to match the WVS persona frame
(WVS is 18+). Documented approximations:

- Eurostat gives 5-year age groups, so the schema's 18-24 band is approximated
  as Y20-24 + 0.4·Y15-19 (18-19 are ~2 of the 5 years in 15-19). The other
  bands are exact sums.
- Education is national only (no region breakdown) and comes as percentages
  within a broad adult band (Y15-74); the two sexes are combined by their 18+
  population share. Region/gender/age margins come from the population counts.

These are a close stand-in for the designated TÜİK margins (Eurostat
re-publishes TÜİK aggregates) and must be verified against TÜİK before any
calibration claim -- see src/personas/NOTES.md.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.personas import wvs

EUROSTAT_DIR = Path("data/raw/eurostat")
POP_FILE = EUROSTAT_DIR / "tr_population_age_sex_nuts1.csv"
EDU_FILE = EUROSTAT_DIR / "tr_education_sex_age.csv"

# schema age_band -> (eurostat age code, weight) components, 18+ only.
AGE_BAND_COMPONENTS = {
    "18-24": [("Y15-19", 0.4), ("Y20-24", 1.0)],
    "25-34": [("Y25-29", 1.0), ("Y30-34", 1.0)],
    "35-44": [("Y35-39", 1.0), ("Y40-44", 1.0)],
    "45-54": [("Y45-49", 1.0), ("Y50-54", 1.0)],
    "55-64": [("Y55-59", 1.0), ("Y60-64", 1.0)],
    "65+": [("Y65-69", 1.0), ("Y70-74", 1.0), ("Y75-79", 1.0),
            ("Y80-84", 1.0), ("Y_GE85", 1.0)],
}
_EDU_AGE_BAND = "Y15-74"          # broad adult band for the education split
_EDU3 = {"ED0-2": "low", "ED3_4": "mid", "ED5-8": "high"}


def _normalize(counts: dict) -> dict:
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()} if total else counts


def _population_cells(pop_file=POP_FILE) -> pd.DataFrame:
    """18+ population as tidy rows: region, gender, age_band, count."""
    pop = pd.read_csv(pop_file)
    wide = pop.pivot_table(index=["geo", "sex"], columns="age",
                           values="value", aggfunc="sum")
    rows = []
    for (geo, sex), r in wide.iterrows():
        region = wvs.NUTS1_ALPHA_TO_REGION.get(geo)
        gender = {"M": "male", "F": "female"}.get(sex)
        if region is None or gender is None:
            continue
        for band, comps in AGE_BAND_COMPONENTS.items():
            count = sum(r.get(code, 0) * w for code, w in comps)
            rows.append({"region": region, "gender": gender,
                         "age_band": band, "count": count})
    return pd.DataFrame(rows)


def _education_margin(cells: pd.DataFrame, edu_file=EDU_FILE) -> dict:
    """National edu3 distribution, combining sexes by 18+ population share."""
    edu = pd.read_csv(edu_file)
    edu = edu[(edu["age"] == _EDU_AGE_BAND) & (edu["isced11"].isin(_EDU3))]
    sex_share = cells.groupby("gender")["count"].sum()
    sex_share = sex_share / sex_share.sum()

    out = {"low": 0.0, "mid": 0.0, "high": 0.0}
    for sex_code, gender in (("M", "male"), ("F", "female")):
        sub = edu[edu["sex"] == sex_code]
        pct = {_EDU3[i]: v for i, v in zip(sub["isced11"], sub["value"])}
        total = sum(pct.values())
        for g in out:
            out[g] += sex_share.get(gender, 0.0) * (pct.get(g, 0.0) / total)
    return _normalize(out)


def target_margins(pop_file=POP_FILE, edu_file=EDU_FILE) -> dict:
    """Return the four target marginal distributions (each sums to 1)."""
    cells = _population_cells(pop_file)
    return {
        "age_band": _normalize(cells.groupby("age_band")["count"].sum().to_dict()),
        "gender": _normalize(cells.groupby("gender")["count"].sum().to_dict()),
        "region": _normalize(cells.groupby("region")["count"].sum().to_dict()),
        "edu3": _education_margin(cells, edu_file),
    }
