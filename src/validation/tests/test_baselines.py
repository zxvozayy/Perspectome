"""ML and equation baselines."""

import math

import numpy as np
import pandas as pd
import pytest

from src.validation import baselines

OPTS = ["support", "oppose", "uncertain"]


def _frame(n=200, seed=0):
    """Synthetic people whose answer depends on gender only (women 80% 'a')."""
    rng = np.random.default_rng(seed)
    gender = rng.choice(["female", "male"], size=n)
    p_a = np.where(gender == "female", 0.8, 0.2)
    answer = np.where(rng.random(n) < p_a, "a", "b")
    return pd.DataFrame({
        "persona_id": [f"p{i}" for i in range(n)],
        "weight": 1.0,
        "age_band": rng.choice(["18-24", "65+"], size=n),
        "gender": gender,
        "income_decile": rng.integers(1, 11, size=n),
        "item": answer,
    })


def test_equation_effect_matches_closed_form():
    # scale = .1 * (1 - e^-1) = .0632121 ; effect = scale * (e_support - p0)
    eff = baselines.equation_effect({"support": .33, "oppose": .60, "uncertain": .07},
                                    OPTS, "support", intensity=0.1, rate=1.0, rounds=1)
    scale = 0.1 * (1 - math.exp(-1))
    assert eff["support"] == pytest.approx(scale * 0.67)
    assert eff["oppose"] == pytest.approx(-scale * 0.60)
    assert eff["uncertain"] == pytest.approx(-scale * 0.07)
    assert sum(eff.values()) == pytest.approx(0.0, abs=1e-12)


def test_equation_effect_grows_with_rounds_and_saturates_at_intensity():
    p0 = {"support": .5, "oppose": .5, "uncertain": 0}
    one = baselines.equation_effect(p0, OPTS, "support", 0.2, rounds=1)["support"]
    many = baselines.equation_effect(p0, OPTS, "support", 0.2, rounds=50)["support"]
    assert one < many == pytest.approx(0.2 * 0.5)


def test_equation_effect_rejects_unknown_option():
    with pytest.raises(ValueError):
        baselines.equation_effect({"support": 1}, OPTS, "maybe", 0.1)


def test_registered_params_cover_the_example_scenarios():
    params = baselines.load_equation_params()
    for sid in ("unemployment_shock_v1", "ai_adoption_v1"):
        assert params[sid]["target_option"] in OPTS
        assert 0 < params[sid]["intensity"] <= 1
        assert params[sid]["rationale"].strip()


def test_scenario_without_params_has_no_equation_baseline():
    assert baselines.scenario_equation_effect("unknown", {"support": 1}, OPTS, 1, {}) is None


def test_ml_baseline_recovers_population_distribution():
    frame = _frame()
    out = baselines.ml_baseline(frame, "item", ["a", "b"])
    real_a = (frame["item"] == "a").mean()
    assert out["distribution"]["a"] == pytest.approx(real_a, abs=0.05)
    assert sum(out["distribution"].values()) == pytest.approx(1.0)
    assert out["n"] == len(frame)


def test_ml_baseline_learns_the_demographic_signal():
    # A model fit on gender should predict women answer 'a' far more often.
    frame = _frame()
    X = baselines._design_matrix(frame)
    y = (frame["item"] == "b").astype(int).to_numpy()
    W = baselines.fit_softmax(X, y, 2, np.ones(len(frame)))
    proba_a = baselines.predict_proba(X, W)[:, 0]
    women = frame["gender"].to_numpy() == "female"
    assert proba_a[women].mean() > 0.65 > 0.35 > proba_a[~women].mean()


def test_ml_baseline_folds_are_deterministic():
    frame = _frame()
    a = baselines.ml_baseline(frame, "item", ["a", "b"])
    b = baselines.ml_baseline(frame.sample(frac=1, random_state=3), "item", ["a", "b"])
    assert a["distribution"]["a"] == pytest.approx(b["distribution"]["a"], abs=1e-9)


def test_ml_baseline_skips_unanswered_and_out_of_option_rows():
    frame = _frame(50)
    frame.loc[:4, "item"] = None
    frame.loc[5:9, "item"] = "dont_know"
    assert baselines.ml_baseline(frame, "item", ["a", "b"])["n"] == 40
