"""Unit tests for the WVS-7 ingest/clean/map step (issue #6).

Runs entirely on a small *synthetic* WVS-shaped sample (fixtures/
wvs_raw.sample.csv) -- fabricated numbers, not real respondents. No raw survey
data is committed or required.

Run:  python -m pytest src/personas/tests -q
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.common import schema
from src.personas import ingest, wvs

FIXTURE = Path(__file__).parent / "fixtures" / "wvs_raw.sample.csv"


@pytest.fixture
def raw():
    return ingest.load_raw(FIXTURE)


@pytest.fixture
def recoded(raw):
    return ingest.recode_missing(raw)


@pytest.fixture
def mapped(recoded):
    return ingest.to_personas_and_heldout(recoded)


# --- recoding ---------------------------------------------------------------

def test_recode_turns_sentinels_into_nan(raw, recoded):
    # raw has -2 (income row 1005), -1 (age row 1006), -4 (religiosity row 1006),
    # -5 (trust battery row 1008); all must become NaN.
    assert (raw["Q288"] < 0).any()
    assert not (recoded["Q288"] < 0).any()
    assert recoded["Q262"].isna().sum() == 1   # the -1 age
    assert recoded["Q164"].isna().sum() == 1   # the -4 religiosity
    assert recoded["Q71"].isna().sum() == 1    # the -5 trust item


def test_recode_leaves_valid_values_untouched(raw, recoded):
    assert recoded.loc[0, "Q262"] == 22
    assert recoded.loc[0, "Q288"] == 4


# --- demographic (conditioning) mapping -------------------------------------

def test_first_persona_demographics(mapped):
    personas, _ = mapped
    row = personas.iloc[0]
    assert row["persona_id"] == "p1001"
    assert row["age_band"] == "18-24"
    assert row["gender"] == "female"
    assert row["education_level"] == "bachelor"
    assert row["marital_status"] == "single"
    assert row["employment_status"] == "student"
    assert row["settlement_type"] == "urban"
    assert row["region"] == "Marmara"
    assert row["income_decile"] == 4


def test_cell_id_matches_archetype_format(mapped):
    personas, _ = mapped
    assert personas.iloc[0]["cell_id"] == "18-24|female|bachelor"


def test_missing_component_yields_null_cell_id(mapped):
    personas, _ = mapped
    # row 1006 had age -1 (now null) -> no age_band -> no cell_id
    p1006 = personas[personas["persona_id"] == "p1006"].iloc[0]
    assert p1006["age_band"] is None or pd.isna(p1006["age_band"])
    assert p1006["cell_id"] is None or pd.isna(p1006["cell_id"])


def test_missing_income_is_null_not_a_sentinel(mapped):
    personas, _ = mapped
    p1005 = personas[personas["persona_id"] == "p1005"].iloc[0]
    assert pd.isna(p1005["income_decile"])


def test_every_mapped_category_is_in_schema(mapped):
    personas, _ = mapped
    checks = {
        "age_band": schema.AGE_BANDS,
        "gender": schema.GENDERS,
        "education_level": schema.EDUCATION_LEVELS,
        "settlement_type": schema.SETTLEMENT_TYPES,
        "marital_status": schema.MARITAL_STATUSES,
        "employment_status": schema.EMPLOYMENT_STATUSES,
    }
    for field, allowed in checks.items():
        values = personas[field].dropna().unique()
        assert set(values) <= set(allowed), f"{field} has out-of-schema values: {values}"


# --- held-out (attitude) mapping --------------------------------------------

def test_numeric_heldout_keeps_raw_scale(mapped):
    _, heldout = mapped
    # political_leaning keeps the raw Q240 1-10 scale (no rescaling).
    assert heldout.iloc[0]["political_leaning"] == 2     # Q240 = 2
    assert heldout.iloc[3]["political_leaning"] == 10    # Q240 = 10
    assert heldout.iloc[0]["religiosity"] == 3           # Q164 = 3
    assert heldout.iloc[3]["life_satisfaction"] == 8     # Q49 = 8


def test_trust_is_categorical_per_item(mapped):
    _, heldout = mapped
    # each institution is its own categorical field, nothing averaged.
    assert heldout.iloc[0]["trust_government"] == "quite_a_lot"   # Q71 = 2
    assert heldout.iloc[3]["trust_government"] == "a_great_deal"  # Q71 = 1
    p1008 = heldout[heldout["persona_id"] == "p1008"].iloc[0]
    for f in ("trust_government", "trust_courts", "trust_police", "trust_parliament"):
        assert pd.isna(p1008[f])                          # all four were -5


def test_religious_identity_is_categorical(mapped):
    _, heldout = mapped
    assert heldout.iloc[0]["religious_identity"] == "religious"   # Q173 = 1
    p1008 = heldout[heldout["persona_id"] == "p1008"].iloc[0]
    assert p1008["religious_identity"] == "atheist"              # Q173 = 3


def test_missing_heldout_becomes_null(mapped):
    _, heldout = mapped
    p1006 = heldout[heldout["persona_id"] == "p1006"].iloc[0]
    assert pd.isna(p1006["religiosity"])                  # Q164 was -4


# --- held-out discipline / leakage (the rule that can't bend) ---------------

def test_personas_frame_has_no_attitude_columns(mapped):
    personas, _ = mapped
    leaked = set(schema.HELDOUT_FIELDS) & set(personas.columns)
    assert not leaked, f"held-out fields leaked into personas.csv: {leaked}"


def test_frames_share_only_persona_id(mapped):
    personas, heldout = mapped
    shared = set(personas.columns) & set(heldout.columns)
    assert shared == {"persona_id"}


def test_distinctive_heldout_value_never_appears_in_personas(recoded):
    # Leakage sentinel: inject a unique marker as a held-out source value and
    # assert it cannot surface anywhere in personas.csv.
    marked = recoded.copy()
    marker = 999999
    marked.loc[0, ingest.HELDOUT_SRC["political_leaning"][0]] = marker  # Q240
    personas, _ = ingest.to_personas_and_heldout(marked)
    assert not personas.astype(str).apply(lambda c: c.str.contains(str(marker))).any().any()


# --- warn, never drop -------------------------------------------------------

def test_no_rows_dropped(raw, mapped):
    personas, heldout = mapped
    assert len(personas) == len(raw)
    assert len(heldout) == len(raw)


def test_inconsistency_warns_but_keeps_row(recoded, caplog):
    with caplog.at_level(logging.WARNING):
        personas, _ = ingest.to_personas_and_heldout(recoded)
    # row 1008: retired at age 23 -> warned, but still present
    assert any("retired aged 18-24" in r.message for r in caplog.records)
    assert "p1008" in set(personas["persona_id"])


# --- prove a test can fail (rule 28): a mislabelled/out-of-range code must
#     map to null, never silently pass through as a bogus category -----------

def test_unknown_codes_map_to_null_not_passthrough():
    assert wvs.map_gender(9) is None            # 9 is not a valid WVS sex code
    assert wvs.map_education(42) is None         # outside ISCED 0-8
    assert wvs.map_age_band(10) is None          # below WVS 18+ floor
    assert wvs.map_confidence(9) is None         # outside the 1-4 confidence scale
    assert wvs.map_religious_identity(7) is None  # outside the 1-3 Q173 scale


def test_can_fail_sanity():
    # A deliberately broken expectation: confirms the suite actually asserts.
    # (rule 28 -- flip the `==` to prove red.)
    assert wvs.map_gender(1) == "male"
