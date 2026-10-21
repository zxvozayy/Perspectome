"""rules.yaml / rules.py: every rule can fire, and the real data matches its reference."""

import pandas as pd
import pytest

from src.common import paths
from src.personas import rules

ALL = rules.load_rules()


def _persona(**fields):
    row = {"persona_id": "p1", "cell_id": "35-44|female|secondary", "weight": 1.0, "age_band": "35-44",
           "gender": "female", "education_level": "secondary", "region": "Ege", "settlement_type": "urban",
           "marital_status": "married", "employment_status": "employed", "income_decile": 5}
    row.update(fields)
    return pd.DataFrame([row])


# One row per rule that breaks exactly that rule (rule 28: prove each rule can fire).
BREAKERS = {
    "cell_id_matches_fields": {"cell_id": "18-24|male|primary"},
    "weight_positive": {"weight": 0.0},
    "retired_under_35": {"employment_status": "retired", "age_band": "25-34", "cell_id": "25-34|female|secondary"},
    "student_55_plus": {"employment_status": "student", "marital_status": "widowed", "age_band": "65+", "cell_id": "65+|female|secondary"},
    "widowed_under_25": {"marital_status": "widowed", "age_band": "18-24", "cell_id": "18-24|female|secondary"},
    "divorced_under_25": {"marital_status": "divorced", "age_band": "18-24", "cell_id": "18-24|female|secondary"},
    "graduate_under_25": {"education_level": "graduate", "age_band": "18-24", "cell_id": "18-24|female|graduate"},
    "male_homemaker": {"employment_status": "homemaker", "gender": "male", "cell_id": "35-44|male|secondary"},
    "unemployed_top_income": {"employment_status": "unemployed", "income_decile": 10},
    "married_student": {"employment_status": "student"},
}


def test_every_rule_has_a_breaking_example():
    assert set(BREAKERS) == {r.id for r in ALL}


@pytest.mark.parametrize("rule_id", sorted(BREAKERS))
def test_rule_fires_on_its_breaking_row_only(rule_id):
    hits = rules.violations(_persona(**BREAKERS[rule_id]))
    assert set(hits) == {rule_id}


def test_clean_persona_breaks_nothing():
    assert rules.violations(_persona()) == {}


def test_missing_columns_skip_rules_instead_of_failing():
    assert rules.violations(_persona().drop(columns=["weight"])) == {}


def test_fixture_has_no_hard_violations():
    s = rules.summary(pd.read_csv(paths.PERSONAS_FIXTURE))
    assert s.loc[s.kind == "hard", "n"].sum() == 0


@pytest.mark.skipif(not paths.PERSONAS_CSV.exists(), reason="real persona set not present")
def test_real_shares_match_the_recorded_reference():
    s = rules.summary(pd.read_csv(paths.PERSONAS_CSV))
    assert s.loc[s.kind == "hard", "n"].sum() == 0
    soft = s[s.kind == "soft"]
    assert (soft["share"] - soft["real_share"]).abs().max() < 0.0001
