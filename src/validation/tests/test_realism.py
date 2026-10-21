"""realism.py against hand-computed values."""

import math

import numpy as np
import pandas as pd
import pytest

from src.common import schema
from src.validation import realism


def _people(rows, weight=1.0):
    base = {"age_band": "35-44", "gender": "female", "education_level": "secondary", "region": "Ege",
            "settlement_type": "urban", "marital_status": "married", "employment_status": "employed",
            "income_decile": 5, "religiosity_band": "high", "political_leaning_band": "centre"}
    frame = pd.DataFrame([{**base, **r} for r in rows])
    frame["weight"] = weight
    frame["cell_id"] = frame[list(schema.CELL_FIELDS)].agg("|".join, axis=1)
    frame.insert(0, "persona_id", [f"p{i}" for i in range(len(frame))])
    return frame


def test_srmse_hand_computed():
    real = _people([{"gender": "male"}, {"gender": "female"}])            # 0.5 / 0.5
    synth = _people([{"gender": "male"}] * 3 + [{"gender": "female"}])    # 0.75 / 0.25
    # cells 2, errors .25 each: sqrt(mean(.0625, .0625)) / mean(.5, .5) = .25 / .5
    assert realism.srmse(synth, real, ("gender",)) == pytest.approx(0.5)
    assert realism.srmse(real, real, ("gender",)) == 0.0


def test_float_and_int_income_are_the_same_category():
    real = _people([{"income_decile": 4.0}])
    synth = _people([{"income_decile": 4}])
    assert realism.srmse(synth, real, ("income_decile",)) == 0.0
    assert realism.structural_zero_rate(synth, real)["rate"] == 0.0


def test_structural_zeros_count_people_with_an_unseen_pair():
    # real has students (18-24) and people aged 65+, but no student aged 65+
    real = _people([{"employment_status": "student", "age_band": "18-24"}, {"age_band": "65+"}, {}])
    synth = _people([{"employment_status": "student", "age_band": "18-24"},
                     {"employment_status": "student", "age_band": "65+"},   # pair never seen in real
                     {}, {}])
    out = realism.structural_zero_rate(synth, real)
    assert out["rate"] == pytest.approx(0.25)
    assert out["worst_pair"] == "age_band|employment_status" and out["worst_pair_n"] == 1


def test_c2st_cannot_separate_identical_sets_but_separates_disjoint_ones():
    rng = np.random.default_rng(0)
    rows = [{"gender": g, "region": r} for g, r in zip(rng.choice(schema.GENDERS, 400), rng.choice(schema.REGIONS, 400))]
    same = realism.c2st_auc(_people(rows), _people(rows), n=400)
    assert abs(same - 0.5) < 0.08
    disjoint = realism.c2st_auc(_people([{"gender": "male"}] * 200), _people([{"gender": "female"}] * 200), n=200)
    assert disjoint > 0.95


def test_independent_baseline_keeps_marginals_and_breaks_structure():
    real = _people([{"employment_status": "student", "age_band": "18-24"}] * 50
                   + [{"employment_status": "retired", "age_band": "65+"}] * 50)
    naive = realism.independent_baseline(real, 4000, seed=0)
    assert naive["age_band"].value_counts(normalize=True)["65+"] == pytest.approx(0.5, abs=0.03)
    mixed = ((naive.employment_status == "student") & (naive.age_band == "65+")).mean()
    assert mixed == pytest.approx(0.25, abs=0.03)   # independence invents 65+ students


def test_report_has_both_sets_and_rules():
    real = _people([{}] * 30)
    out = realism.report(_people([{}] * 30), real)
    assert out["rules"]["hard_violations"] == 0
    assert set(out["independent_baseline"]) == {"structural_zeros", "srmse_2way", "srmse_3way", "c2st_auc"}
    assert math.isclose(out["srmse_2way"]["mean"], 0.0)
