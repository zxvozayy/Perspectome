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
  held-out attitudes (Track C sign-off; two items per topic, fit vs. test):
    Q71/Q70  confidence in government/courts 1-4 categorical   (fit)
    Q69/Q73  confidence in police/parliament 1-4 categorical   (test)
    Q164  importance of God 1-10                               (fit)
    Q173  religious person / not / atheist 1-3 categorical     (test)
    Q46   feeling of happiness 1-4                             (fit)
    Q49   life satisfaction 1-10                               (test)
    Q106  incomes more equal .. larger differences 1-10        (fit)
    Q109  competition good .. harmful 1-10                     (test)
    Q240  left-right self-placement 1-10                       (test)
    Q50   satisfaction with household finances 1-10            (test)
  (Q47 is self-reported health, not a risk item -- no WVS-7 risk item exists,
   so risk_tolerance was dropped. Held-out values keep their raw survey scale;
   trust and religious_identity are stored as categorical labels.)

Missing-value sentinels are negative across WVS (-1 don't know, -2 no answer,
-3 not applicable, -4 not asked, -5 missing). They are recoded to null in
``ingest.recode_missing`` BEFORE any mapping here runs, so the functions below
assume their input is either a valid code or NaN.

WVS Turkey is from 2018 -- time drift is not corrected here; note it wherever
results are presented (persona README). See src/personas/NOTES.md for the
real-data findings behind these mappings.
"""

from __future__ import annotations

import bisect

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
# Conditioning (personas.csv) source columns. Kept together so a codebook
# revision is a one-line change. Held-out source columns live in
# ingest.HELDOUT_SRC (one field per column, no aggregation).
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
}


# --- conditioning (personas.csv) mappings ----------------------------------

def map_age_band(age) -> Optional[str]:
    """Numeric age (Q262) -> age_band (schema.AGE_EDGES). None if missing or under 18."""
    if is_missing(age):
        return None
    try:
        years = int(age)
    except (TypeError, ValueError):
        return None
    i = bisect.bisect_right(schema.AGE_EDGES, years) - 1
    return schema.AGE_BANDS[i] if i >= 0 else None


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
# (WVS code, Eurostat alpha code, Turkish NUTS-1 name, schema region) for the 12 NUTS-1 regions.
_NUTS1 = (
    (79201, "TR1", "İstanbul", "Marmara"),
    (79202, "TR2", "Batı Marmara", "Marmara"),
    (79203, "TR3", "Ege", "Ege"),
    (79204, "TR4", "Doğu Marmara", "Marmara"),
    (79205, "TR5", "Batı Anadolu", "Ic Anadolu"),          # Ankara/Konya
    (79206, "TR6", "Akdeniz", "Akdeniz"),
    (79207, "TR7", "Orta Anadolu", "Ic Anadolu"),
    (79208, "TR8", "Batı Karadeniz", "Karadeniz"),
    (79209, "TR9", "Doğu Karadeniz", "Karadeniz"),
    (79210, "TRA", "Kuzeydoğu Anadolu", "Dogu Anadolu"),
    (79211, "TRB", "Ortadoğu Anadolu", "Dogu Anadolu"),
    (79212, "TRC", "Güneydoğu Anadolu", "Guneydogu Anadolu"),
)
assert {r for *_, r in _NUTS1} == set(schema.REGIONS)
REGION_MAP = {code: region for code, _, _, region in _NUTS1}
NUTS1_ALPHA_TO_REGION = {alpha: region for _, alpha, _, region in _NUTS1}
NUTS1_NAME_TO_ALPHA = {name: alpha for _, alpha, name, _ in _NUTS1}


def map_region(code) -> Optional[str]:
    """N_REG_NUTS1 (792NN) -> one of the 7 geographic regions in the schema."""
    if is_missing(code):
        return None
    try:
        return REGION_MAP.get(int(float(code)))
    except (TypeError, ValueError):
        return None


# Coarse 3-level education axis (ISCED 0-2 / 3-4 / 5-8) used only for
# post-stratification (issue #10). Both the personas (via raw Q275) and the
# Eurostat education margins (ED0-2 / ED3_4 / ED5-8) collapse to it, so the two
# sides share a grouping even though the schema's 5 education_level categories
# don't line up with the Eurostat ISCED aggregates. Not an output field.
def edu3_from_isced(code) -> Optional[str]:
    """Raw Q275 ISCED level -> 'low' (0-2) / 'mid' (3-4) / 'high' (5-8)."""
    if is_missing(code):
        return None
    level = int(code)
    if level <= 2:
        return "low"
    if level <= 4:
        return "mid"
    if level <= 8:
        return "high"
    return None


# --- held-out (heldout.csv) attitude mappings -------------------------------
# Per Track C sign-off: held-out values keep their RAW survey scale (no
# rescaling -- Track C validates against the original scale). Trust and
# religious_identity are stored as categorical labels. Nothing is averaged and
# nothing is reverse-coded, so the scale direction is whatever the codebook says
# (documented per field in schema.HELDOUT_FIELDS).

def keep_scale(code) -> Optional[int]:
    """Keep a numeric held-out item at its raw survey value; missing -> None."""
    if is_missing(code):
        return None
    try:
        return int(code)
    except (TypeError, ValueError):
        return None


# WVS confidence battery (Q69-Q73): 1 a great deal .. 4 none at all.
_CONFIDENCE = {1: "a_great_deal", 2: "quite_a_lot", 3: "not_very_much", 4: "none"}


def map_confidence(code) -> Optional[str]:
    """Confidence item (Q69/Q70/Q71/Q73) -> categorical label. Missing -> None."""
    if is_missing(code):
        return None
    return _CONFIDENCE.get(int(code))


# Q173: 1 a religious person, 2 not a religious person, 3 a convinced atheist.
_RELIGIOUS_IDENTITY = {1: "religious", 2: "not_religious", 3: "atheist"}


def map_religious_identity(code) -> Optional[str]:
    """Q173 religious self-identification -> categorical label. Missing -> None."""
    if is_missing(code):
        return None
    return _RELIGIOUS_IDENTITY.get(int(code))
