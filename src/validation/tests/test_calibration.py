"""calibration.py: temperature and stacking fitted on fit items only."""

import copy

import pytest

from src.validation import calibration, report

OPTS = ["a", "b", "c", "d"]


def _probe(item, role, engine, real, ml=None, options=OPTS):
    ml = ml or {o: 1 / len(options) for o in options}
    return {"item": item, "role": role, "options": options, "ordinal": True, "real": real,
            "methods": {"engine": {"distribution": engine}, "ml_baseline": {"distribution": ml}}}


def test_temper_hand_computed():
    out = calibration.temper({"a": 0.8, "b": 0.2}, ["a", "b"], 2.0)   # sqrt: .894, .447 -> 2/3, 1/3
    assert out["a"] == pytest.approx(2 / 3) and out["b"] == pytest.approx(1 / 3)
    assert calibration.temper({"a": 0.8, "b": 0.2}, ["a", "b"], 1.0)["a"] == pytest.approx(0.8)


def _too_sharp(item, role, engine):
    return _probe(item, role, engine, calibration.temper(engine, OPTS, 2.0))


FIT = [_too_sharp("f1", "fit", {"a": .7, "b": .2, "c": .07, "d": .03}),
       _too_sharp("f2", "fit", {"a": .05, "b": .15, "c": .6, "d": .2})]


def test_fit_recovers_an_overconfident_engine():
    params = calibration.fit(FIT, "m1")
    assert params["by_scale_size"][4]["temperature"] == pytest.approx(2.0)
    assert params["by_scale_size"][4]["fitted_on"] == ["f1", "f2"]
    assert params["by_scale_size"][4]["stack_weight"] == 1.0   # engine is perfect once tempered


def test_stack_weight_goes_to_the_ml_baseline_when_it_is_exact():
    real = {"a": .4, "b": .3, "c": .2, "d": .1}
    probes = [_probe("f", "fit", {"a": .1, "b": .2, "c": .3, "d": .4}, real, ml=real)]
    assert calibration.fit(probes, "m")["default"]["stack_weight"] == 0.0


def test_test_items_never_move_the_parameters():
    test = _probe("t1", "test", {"a": .25, "b": .25, "c": .25, "d": .25}, {"a": 1, "b": 0, "c": 0, "d": 0})
    shuffled = copy.deepcopy(test)
    shuffled["real"] = {"a": 0, "b": 0, "c": 0, "d": 1}
    a = calibration.fit(FIT + [test], "m")
    b = calibration.fit(FIT + [shuffled], "m")
    assert a == b


def test_fit_needs_fit_items():
    with pytest.raises(ValueError):
        calibration.fit([_too_sharp("t", "test", {"a": .7, "b": .1, "c": .1, "d": .1})], "m")


def test_report_applies_only_to_the_fitted_model():
    params = calibration.fit(FIT, "m1")
    probes, warnings = copy.deepcopy(FIT), []
    report.add_calibrated(probes, params, "m1", warnings)
    assert probes[0]["methods"]["engine_calibrated"]["tvd"] == pytest.approx(0.0, abs=1e-3)
    assert "stacked" in probes[0]["methods"]
    other, warnings = copy.deepcopy(FIT), []
    report.add_calibrated(other, params, "m2", warnings)
    assert "engine_calibrated" not in other[0]["methods"] and "not applied" in warnings[0]
