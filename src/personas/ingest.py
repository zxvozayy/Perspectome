"""Ingest and clean WVS Wave 7 Turkey -> mapped persona / held-out frames.

Pipeline (issue #6, Sprint 2):

    raw = load_raw("data/raw/WVS_Wave7_Turkey.csv")   # git-ignored, never committed
    raw = recode_missing(raw)                          # -1/-2/-3/-4/-5 -> null
    personas, heldout = to_personas_and_heldout(raw)   # two SEPARATE frames

``personas`` and ``heldout`` share only ``persona_id`` and are never joined
back together outside Track C -- that held-out discipline is the one rule in
this track that can't bend (persona README). Post-stratification weights and
the frozen population come later (issues #10 / #14); this step only ingests,
cleans and maps.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import schema
from src.personas import wvs

log = logging.getLogger(__name__)

# Output column order. Mirrors the frozen contract header (persona README).
# ``weight`` is deliberately absent here -- it is produced by the
# post-stratification generator (issue #10), not by ingest.
PERSONA_COLUMNS = [
    "persona_id",
    "cell_id",
    "age_band",
    "gender",
    "education_level",
    "region",
    "settlement_type",
    "marital_status",
    "employment_status",
    "income_decile",
]
HELDOUT_COLUMNS = ["persona_id", *schema.HELDOUT_FIELDS]

# demographic field -> (source column key in wvs.SRC, mapper)
_CONDITIONING = {
    "age_band": ("age", wvs.map_age_band),
    "gender": ("gender", wvs.map_gender),
    "education_level": ("education", wvs.map_education),
    "region": ("region", wvs.map_region),
    "settlement_type": ("settlement", wvs.map_settlement),
    "marital_status": ("marital", wvs.map_marital),
    "employment_status": ("employment", wvs.map_employment),
    "income_decile": ("income", wvs.map_income_decile),
}

# held-out field -> (raw WVS column, mapper). One field per column, no
# aggregation (Track C sign-off). Trust/religious_identity are categorical;
# the rest keep their raw survey scale via wvs.keep_scale.
HELDOUT_SRC = {
    "trust_government": ("Q71", wvs.map_confidence),
    "trust_courts": ("Q70", wvs.map_confidence),
    "trust_police": ("Q69", wvs.map_confidence),
    "trust_parliament": ("Q73", wvs.map_confidence),
    "religiosity": ("Q164", wvs.keep_scale),
    "religious_identity": ("Q173", wvs.map_religious_identity),
    "happiness": ("Q46", wvs.keep_scale),
    "life_satisfaction": ("Q49", wvs.keep_scale),
    "income_equality": ("Q106", wvs.keep_scale),
    "competition": ("Q109", wvs.keep_scale),
    "political_leaning": ("Q240", wvs.keep_scale),
    "financial_satisfaction": ("Q50", wvs.keep_scale),
}


def load_raw(path) -> pd.DataFrame:
    """Load a raw WVS-7 export (.csv or Stata .dta) from the git-ignored data/ dir.

    Raw survey files are never committed -- this reads whatever the user has
    placed under ``data/`` locally.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".dta":
        return pd.read_stata(path, convert_categoricals=False)
    if suffix == ".sav":
        # SPSS format (WVS also ships .sav); needs the optional pyreadstat dep.
        return pd.read_spss(path, convert_categoricals=False)
    return pd.read_csv(path)


def recode_missing(df: pd.DataFrame, columns=None) -> pd.DataFrame:
    """Recode WVS sentinel missing codes (-1/-2/-3/-4/-5) to NaN.

    Runs before any mapping, on a copy. ``columns`` defaults to every numeric
    column; string columns (e.g. region ISO codes) are left untouched.
    """
    out = df.copy()
    if columns is None:
        columns = out.select_dtypes(include="number").columns
    for col in columns:
        if col in out.columns:
            out[col] = out[col].where(~out[col].isin(wvs.MISSING_CODES), other=np.nan)
    return out


def _persona_ids(df: pd.DataFrame, id_col) -> pd.Series:
    """Stable persona_id per row. Uses id_col if present, else a zero-padded index."""
    if id_col is not None and id_col in df.columns:
        return df[id_col].astype(str).map(lambda s: f"p{s}")
    width = max(2, len(str(len(df))))
    return pd.Series([f"p{i:0{width}d}" for i in range(1, len(df) + 1)], index=df.index)


def _warn_inconsistencies(personas: pd.DataFrame) -> None:
    """Log consistency warnings. Never drops rows (persona README: warn, never drop)."""
    students_old = personas[(personas["employment_status"] == "student")
                            & (personas["age_band"].isin(["55-64", "65+"]))]
    for pid in students_old["persona_id"]:
        log.warning("consistency: persona %s is a student aged 55+", pid)

    retired_young = personas[(personas["employment_status"] == "retired")
                             & (personas["age_band"] == "18-24")]
    for pid in retired_young["persona_id"]:
        log.warning("consistency: persona %s is retired aged 18-24", pid)


def to_personas_and_heldout(df: pd.DataFrame, id_col: str | None = "D_INTERVIEW"):
    """Map a recoded WVS frame to (personas, heldout) -- two separate frames.

    Returns
    -------
    (personas, heldout) : tuple[pd.DataFrame, pd.DataFrame]
        ``personas`` holds conditioning fields only (+ cell_id archetype);
        ``heldout`` holds attitude fields only. They share persona_id and
        nothing else, and must never be joined outside Track C.
    """
    pid = _persona_ids(df, id_col)

    personas = pd.DataFrame({"persona_id": pid.values})
    for field, (src_key, mapper) in _CONDITIONING.items():
        src_col = wvs.SRC[src_key]
        if src_col in df.columns:
            personas[field] = df[src_col].map(mapper).values
        else:
            log.warning("source column %s (%s) missing from raw file", src_col, field)
            personas[field] = None

    # cell_id = post-stratification archetype = age|gender|education (matches
    # the fixture). Null in any component -> null cell_id.
    def _cell(row):
        parts = [row["age_band"], row["gender"], row["education_level"]]
        return "|".join(parts) if all(p is not None and pd.notna(p) for p in parts) else None
    personas["cell_id"] = personas.apply(_cell, axis=1)
    personas = personas.reindex(columns=PERSONA_COLUMNS)

    heldout = pd.DataFrame({"persona_id": pid.values})
    for field, (src_col, mapper) in HELDOUT_SRC.items():
        if src_col in df.columns:
            heldout[field] = df[src_col].map(mapper).values
        else:
            log.warning("source column %s (%s) missing from raw file", src_col, field)
            heldout[field] = None
    heldout = heldout.reindex(columns=HELDOUT_COLUMNS)

    _warn_inconsistencies(personas)
    return personas, heldout
