"""EBRD Life in Transition Survey IV (2022–23), Türkiye: respondent-level features.

The Stata file is free to download (no registration) from the EBRD LiTS page;
it stays in git-ignored ``data/raw/lits/``. Türkiye is ``country == 35``,
n = 1,109, weight ``weight_trt`` (mean 1). Each row is one household's
primary respondent; their age and sex come from the household roster.

LiTS adds what WVS-7 lacks and is four years newer: household size, housing
tenure, sector, and whether the job comes with social security (informality).
Questions on work (section 3) are only asked of people who have worked, so
``employed`` is known for everyone but ``sector``/``informal`` only for workers.

    from src.personas.sources import lits
    frame = lits.load()
"""

from __future__ import annotations

import pandas as pd

from src.common import paths
from src.personas.sources import wvs

FILE = paths.DATA_RAW / "lits" / "lits_iv.dta"
TURKIYE = 35
WEIGHT = "weight_trt"

_SEX = {1: "male", 2: "female"}
# q109b highest education -> schema education_level (same ISCED grouping as WVS Q275)
_EDUCATION = {1: "primary", 2: "primary", 3: "secondary", 4: "secondary",
              5: "vocational", 6: "vocational", 7: "bachelor", 8: "graduate"}
# q107b marital status (separated -> divorced, as for WVS)
_MARITAL = {1: "single", 2: "married", 3: "widowed", 4: "divorced", 5: "divorced"}
_SETTLEMENT = {1: "urban", 2: "rural"}
# q209 ownership of the dwelling
TENURE = {1: "owner", 2: "tenant", 3: "tenant", 4: "rent_free"}
# q319 job sector -> broad TÜİK sectors
SECTOR = {1: "agriculture", 2: "industry", 3: "construction", 4: "industry", 5: "services", 6: "services",
          7: "services", 8: "services", 9: "services", 10: "public", 11: None}
# q304b main reason for not working in the last 7 days -> employment_status
_NOT_WORKING = {1: "employed", 2: "student", 5: "retired", 6: "homemaker", 10: "unemployed", 11: "unemployed"}

COLUMNS = ("lits_id", "weight", "age_band", "gender", "education_level", "region", "nuts1",
           "settlement_type", "marital_status", "employment_status", "household_size",
           "tenure", "sector", "informal")


def _code(series: pd.Series, table: dict) -> pd.Series:
    return series.map(lambda v: table.get(int(v)) if pd.notna(v) and v >= 0 else None)


def _respondent(df: pd.DataFrame, prefix: str) -> pd.Series:
    """The primary respondent's roster value (``rand_resp_code`` picks the roster column)."""
    return df.apply(lambda r: r.get(f"{prefix}{int(r['rand_resp_code'])}"), axis=1)


def _employment(df: pd.DataFrame) -> pd.Series:
    worked_last_week = df["q304"] == 1
    reason = _code(df["q304b"], _NOT_WORKING)
    return pd.Series(["employed" if w else r for w, r in zip(worked_last_week, reason)], index=df.index)


def load(path=FILE) -> pd.DataFrame:
    """Türkiye respondents mapped to schema categories plus LiTS-only fields."""
    raw = pd.read_stata(path, convert_categoricals=False)
    raw = raw[raw["country"] == TURKIYE].copy()
    employed = _employment(raw)
    working = employed == "employed"
    nuts1 = raw["region"].map(wvs.NUTS1_NAME_TO_ALPHA)
    out = pd.DataFrame({
        "lits_id": raw["hhid"].astype(str),
        "weight": raw[WEIGHT].astype(float),
        "age_band": _respondent(raw, "q105").map(wvs.map_age_band),
        "gender": _code(_respondent(raw, "q103"), _SEX),
        "education_level": _code(raw["q109b"], _EDUCATION),
        "region": nuts1.map(wvs.NUTS1_ALPHA_TO_REGION),
        "nuts1": nuts1,
        "settlement_type": _code(raw["urbanity"], _SETTLEMENT),
        "marital_status": _code(raw["q107b"], _MARITAL),
        "employment_status": employed,
        "household_size": raw["q1"].astype("Int64"),
        "tenure": _code(raw["q209"], TENURE),
        "sector": _code(raw["q319"], SECTOR).where(working),
        "informal": (raw["q3153"] == 2).where(working & raw["q3153"].isin([1, 2])),
    })
    return out.reset_index(drop=True)[list(COLUMNS)]
