"""WVS Wave 7 (Turkey) -> frozen schema mapping.

This module is the one place that knows how raw World Values Survey codes map
onto the categories in ``src/common/schema.py``. A mislabelled item silently
poisons everything downstream (persona README), so every mapping here carries
the WVS item it comes from and, where the exact code could not be confirmed
against the official codebook, a ``VERIFY`` note.

Codes confirmed against the WVS Wave 7 Variables Report / GESIS codebook and
verified by value-range check against the real Turkey file (n=2415):
  conditioning:
    Q260  sex          1 Male, 2 Female
    Q262  age          age in years (numeric)
    Q275  education    ISCED 2011 level (Turkey populates only 0,1,2,3,6)
    Q273  marital      1-6
    Q279  employment   1-8
    Q288  income       self-placed income group, 1 (lowest) .. 10 (highest)
    H_URBRURAL         1 Urban, 2 Rural
    N_REG_NUTS1        region, İBBS Düzey-1 / NUTS-1, coded 792NN
                       (N_REGION_ISO is all -5 for Turkey -- do not use it)
  held-out attitudes (DEFAULTS, pending Track C sign-off):
    Q240  left-right self-placement 1-10
    Q164  importance of God 1-10
    Q50   satisfaction with household finances 1-10 (economic-optimism proxy)
    Q47   Schwartz 'adventure/risk important to me' 1-6 (reversed)
    Q69/Q70/Q71/Q73  confidence in police/courts/government/parliament 1-4

Missing-value sentinels are negative across WVS (-1 don't know, -2 no answer,
-3 not applicable, -4 not asked, -5 missing). They are recoded to null in
``ingest.recode_missing`` BEFORE any mapping here runs, so the functions below
assume their input is either a valid code or NaN.

WVS Turkey is from 2018 -- time drift is not corrected here; note it wherever
results are presented (persona README). See src/personas/NOTES.md for the
real-data findings behind these mappings.
"""

from __future__ import annotations

import math
from typing import Optional

from src.common import schema

# Every WVS missing/sentinel code. Recoded to null before mapping. The persona
# README names -1/-2/-4/-5; -3 (not applicable) is included because it is a
# missing-type code too. Treating every negative value as missing is the
# standard WVS convention.
MISSING_CODES = (-1, -2, -3, -4, -5)


def is_missing(value) -> bool:
    """True for NaN/None or any WVS negative sentinel code."""
    if value is None:
        return True
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
    except TypeError:
        pass
    try:
        return int(value) in MISSING_CODES
    except (TypeError, ValueError):
        return False


# --- source column names in the raw WVS-7 file -----------------------------
# The raw export uses these column names. Kept together so a codebook revision
# is a one-line change.
SRC = {
    "age": "Q262",
    "gender": "Q260",
    "education": "Q275",
    "marital": "Q273",
    "employment": "Q279",
    "income": "Q288",
    "settlement": "H_URBRURAL",
    # N_REGION_ISO is entirely missing (-5) for Turkey in WVS-7; the region is
    # carried in N_REG_NUTS1 (İBBS Düzey-1 / NUTS-1, 12 regions), coded 792NN.
    "region": "N_REG_NUTS1",
    # held-out attitudes (see HELDOUT_SRC below for the per-field detail)
    "political_leaning": "Q240",
    "religiosity": "Q164",
    "economic_optimism": "Q50",
    "risk_tolerance": "Q47",
}

# Confidence battery items averaged into the single trust_institutions score.
# WVS confidence is 1 "a great deal" .. 4 "none at all" (reversed below so
# higher = more trust). VERIFY the item set with Track C before it is used on
# real data -- which institutions belong in the index is a design choice.
TRUST_INSTITUTION_ITEMS = ("Q71", "Q73", "Q70", "Q69")  # govt, parliament, courts, police


# --- conditioning (personas.csv) mappings ----------------------------------

def map_age_band(age) -> Optional[str]:
    """Numeric age (Q262) -> age_band. Returns None if missing or out of range."""
    if is_missing(age):
        return None
    try:
        years = int(age)
    except (TypeError, ValueError):
        return None
    if years < 18:
        return None  # WVS is 18+; anything below is a coding error, drop/warn
    if years <= 24:
        return "18-24"
    if years <= 34:
        return "25-34"
    if years <= 44:
        return "35-44"
    if years <= 54:
        return "45-54"
    if years <= 64:
        return "55-64"
    return "65+"


_GENDER = {1: "male", 2: "female"}


def map_gender(code) -> Optional[str]:
    """Q260 -> gender."""
    if is_missing(code):
        return None
    return _GENDER.get(int(code))


# ISCED 2011 level (Q275, 0-8) -> our five levels. Documented, defensible
# collapse of the 9-point ISCED scale.
_EDUCATION = {
    0: "primary",      # early childhood / less than primary
    1: "primary",      # primary
    2: "secondary",    # lower secondary
    3: "secondary",    # upper secondary
    4: "vocational",   # post-secondary non-tertiary
    5: "vocational",   # short-cycle tertiary
    6: "bachelor",     # bachelor or equivalent
    7: "graduate",     # master or equivalent
    8: "graduate",     # doctoral or equivalent
}


def map_education(code) -> Optional[str]:
    """Q275 (ISCED 2011) -> education_level."""
    if is_missing(code):
        return None
    return _EDUCATION.get(int(code))


# Q273 marital status (WVS-7): 1 married, 2 living together, 3 divorced,
# 4 separated, 5 widowed, 6 single/never married.
_MARITAL = {
    1: "married",
    2: "married",    # living together as married
    3: "divorced",
    4: "divorced",   # separated -> divorced bucket
    5: "widowed",
    6: "single",
}


def map_marital(code) -> Optional[str]:
    """Q273 -> marital_status."""
    if is_missing(code):
        return None
    return _MARITAL.get(int(code))


# Q279 employment (WVS-7): 1 full-time, 2 part-time, 3 self-employed,
# 4 retired, 5 housewife, 6 student, 7 unemployed, 8 other.
_EMPLOYMENT = {
    1: "employed",
    2: "employed",
    3: "employed",
    4: "retired",
    5: "homemaker",
    6: "student",
    7: "unemployed",
    8: None,         # "other" has no schema bucket -> null (warn upstream)
}


def map_employment(code) -> Optional[str]:
    """Q279 -> employment_status."""
    if is_missing(code):
        return None
    return _EMPLOYMENT.get(int(code))


_SETTLEMENT = {1: "urban", 2: "rural"}


def map_settlement(code) -> Optional[str]:
    """H_URBRURAL -> settlement_type."""
    if is_missing(code):
        return None
    return _SETTLEMENT.get(int(code))


def map_income_decile(code) -> Optional[int]:
    """Q288 self-placed income group (1-10) -> income_decile.

    Note: Q288 is a self-reported income *group*, not a true decile, and the
    harmonized income variable is known to be incomplete for Turkey in WVS7
    (GESIS). Flagged for the post-stratification step (issue #10).
    """
    if is_missing(code):
        return None
    value = int(code)
    return value if value in schema.INCOME_DECILES else None


# Region: N_REG_NUTS1 (İBBS Düzey-1, 12 regions, coded 792NN) -> the 7 classic
# Turkish geographic regions used in the schema. Resolved against the actual
# WVS-7 Turkey file: N_REGION_ISO is all -5, so N_REG_NUTS1 is the live
# region variable. The 792NN -> NUTS-1 order below is the standard İBBS Düzey-1
# numbering, corroborated by the response counts (79201 = İstanbul is the
# largest cell). Double-check against the WVS region annex if a count looks off.
REGION_MAP = {
    79201: "Marmara",            # TR1 İstanbul
    79202: "Marmara",            # TR2 Batı Marmara
    79203: "Ege",                # TR3 Ege
    79204: "Marmara",            # TR4 Doğu Marmara
    79205: "Ic Anadolu",         # TR5 Batı Anadolu (Ankara/Konya)
    79206: "Akdeniz",            # TR6 Akdeniz
    79207: "Ic Anadolu",         # TR7 Orta Anadolu
    79208: "Karadeniz",          # TR8 Batı Karadeniz
    79209: "Karadeniz",          # TR9 Doğu Karadeniz
    79210: "Dogu Anadolu",       # TRA Kuzeydoğu Anadolu
    79211: "Dogu Anadolu",       # TRB Ortadoğu Anadolu
    79212: "Guneydogu Anadolu",  # TRC Güneydoğu Anadolu
}


def map_region(code) -> Optional[str]:
    """N_REG_NUTS1 (792NN) -> one of the 7 geographic regions in the schema."""
    if is_missing(code):
        return None
    try:
        return REGION_MAP.get(int(float(code)))
    except (TypeError, ValueError):
        return None


# --- held-out (heldout.csv) attitude mappings -------------------------------
# Each held-out field is a 1-5 score in the schema. The source WVS item and
# rescaling below are DEFAULTS and need Track C sign-off (persona README's
# "first decision"): which value items condition vs. are held out is a
# decision we do not get to make silently.

def _rescale(value, src_lo: int, src_hi: int, *, reverse: bool = False) -> Optional[int]:
    """Linearly map a value on [src_lo, src_hi] onto the 1-5 schema scale.

    reverse=True flips the source scale first (for items where a low raw code
    means "more" of the construct).
    """
    if is_missing(value):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not (src_lo <= v <= src_hi):
        return None
    if reverse:
        v = src_hi - (v - src_lo)
    frac = (v - src_lo) / (src_hi - src_lo)
    return int(round(1 + frac * 4))  # -> 1..5


def map_political_leaning(code) -> Optional[int]:
    """Q240 left-right self-placement (1-10) -> 1-5 (1 left .. 5 right)."""
    return _rescale(code, 1, 10)


def map_religiosity(code) -> Optional[int]:
    """Q164 importance of God (1-10) -> 1-5."""
    return _rescale(code, 1, 10)


def map_economic_optimism(code) -> Optional[int]:
    """Q50 satisfaction with household financial situation (1-10) -> 1-5.

    VERIFY: this is a *current satisfaction* proxy, not a forward-looking
    optimism item; confirm with Track C or substitute a better item.
    """
    return _rescale(code, 1, 10)


def map_risk_tolerance(code) -> Optional[int]:
    """Q47 Schwartz 'adventure/taking risks is important to me' (1-6) -> 1-5.

    WVS codes 1 'very much like me' .. 6 'not at all like me', so reverse:
    higher output = more risk-tolerant.
    """
    return _rescale(code, 1, 6, reverse=True)
