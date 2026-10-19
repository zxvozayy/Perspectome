"""Statistics core vs. hand-computed reference values (worked out on paper)."""

import math

import pytest

from src.validation import metrics

AB = ["a", "b"]
ABC = ["a", "b", "c"]


def test_tvd_two_options():
    # 0.5 * (|.5-.2| + |.5-.8|) = 0.3
    assert metrics.tvd({"a": .5, "b": .5}, {"a": .2, "b": .8}, AB) == pytest.approx(0.3)


def test_tvd_three_options_and_missing_key_is_zero():
    # 0.5 * (.1 + .3 + .2) = 0.3
    p, q = {"a": .2, "b": .3, "c": .5}, {"a": .1, "b": .6, "c": .3}
    assert metrics.tvd(p, q, ABC) == pytest.approx(0.3)
    assert metrics.tvd({"a": 1.0}, {"b": 1.0}, AB) == pytest.approx(1.0)


def test_tvd_identical_is_zero():
    p = {"a": .2, "b": .3, "c": .5}
    assert metrics.tvd(p, p, ABC) == 0.0


def test_calibration_error_is_mean_abs_gap():
    # (.1 + .3 + .2) / 3 = 0.2
    p, q = {"a": .2, "b": .3, "c": .5}, {"a": .1, "b": .6, "c": .3}
    assert metrics.calibration_error(p, q, ABC) == pytest.approx(0.2)


def test_wasserstein_end_to_end_is_one_adjacent_is_half():
    # CDF gaps [1, 1] -> 2 / (3-1) = 1 ;  [1, 0] -> 1 / 2 = 0.5
    assert metrics.wasserstein_ordinal({"a": 1}, {"c": 1}, ABC) == pytest.approx(1.0)
    assert metrics.wasserstein_ordinal({"a": 1}, {"b": 1}, ABC) == pytest.approx(0.5)


def test_wasserstein_separates_near_and_far_misses_where_tvd_cannot():
    near = metrics.wasserstein_ordinal({"a": 1}, {"b": 1}, ABC)
    far = metrics.wasserstein_ordinal({"a": 1}, {"c": 1}, ABC)
    assert metrics.tvd({"a": 1}, {"b": 1}, ABC) == metrics.tvd({"a": 1}, {"c": 1}, ABC)
    assert far > near


def test_expected_position():
    assert metrics.expected_position({"c": 1}, ABC) == pytest.approx(1.0)
    assert metrics.expected_position({"a": .5, "c": .5}, ABC) == pytest.approx(0.5)


@pytest.mark.parametrize("x, y, expected", [
    ([1, 2, 3], [1, 2, 3], 1.0),
    ([1, 2, 3], [3, 2, 1], -1.0),
    ([1, 2, 3, 4], [1, 3, 2, 4], 4 / 6),          # 5 concordant, 1 discordant
    ([1, 1, 2], [1, 2, 3], 2 / math.sqrt(3 * 2)),  # tie in x: tau-b = 0.8165
])
def test_kendall_tau_b(x, y, expected):
    assert metrics.kendall_tau_b(x, y) == pytest.approx(expected)


def test_kendall_undefined_cases():
    assert metrics.kendall_tau_b([1], [1]) is None
    assert metrics.kendall_tau_b([1, 1], [2, 2]) is None


def test_kish_n_eff():
    assert metrics.kish_n_eff([1, 1, 1, 1]) == pytest.approx(4.0)
    assert metrics.kish_n_eff([1, 3]) == pytest.approx(16 / 10)


@pytest.mark.parametrize("p, expected", [
    # thresholds for m=4: .0125 .025 .0375 .05 -> only the smallest passes
    ([0.01, 0.04, 0.03, 0.2], [True, False, False, False]),
    ([0.01, 0.02, 0.03, 0.04], [True, True, True, True]),
    # step-up: .02 misses its own threshold (.0167) but rank 2 (.024 <= .0333) passes
    ([0.02, 0.024, 0.5], [True, True, False]),
    ([], []),
])
def test_benjamini_hochberg(p, expected):
    assert metrics.benjamini_hochberg(p) == expected


def test_two_proportion_p_value():
    # pooled .5, se = sqrt(.25 * .02) = .070711, z = 2.8284 -> p = .004678
    assert metrics.two_proportion_p_value(.6, 100, .4, 100) == pytest.approx(0.004678, abs=1e-5)
    assert metrics.two_proportion_p_value(.5, 100, .5, 100) == pytest.approx(1.0)


def test_minimum_detectable_difference():
    # (1.96 + 0.8416) * sqrt(.25 * (1/100 + 1/100)) = 0.19810
    assert metrics.minimum_detectable_difference(.5, 100, 100) == pytest.approx(0.19810, abs=1e-4)
    assert metrics.minimum_detectable_difference(.5, 400, 400) < 0.1


@pytest.mark.parametrize("share, saturated", [(.05, True), (.10, False), (.5, False), (.95, True)])
def test_saturation(share, saturated):
    assert metrics.is_saturated(share) is saturated
