"""Tests for src.simulation.aggregator."""

import numpy as np
import pandas as pd

from src.simulation.aggregator import aggregate_arm, build_result


ONE_HOT = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])


def _df(weights=(1.0, 2.0, 1.0)):
    return pd.DataFrame({
        "persona_id": ["p1", "p2", "p3"],
        "weight": list(weights),
        "age_band": ["18-24", "18-24", "25-34"],
        "gender": ["female", "male", "female"],
    })


class TestAggregateArm:
    def test_weighted_distribution(self):
        result = aggregate_arm(_df(), ONE_HOT, ["a", "b"])
        # Weighted: a = 1/4 = 0.25, b = 3/4 = 0.75
        assert abs(result["response_distribution"]["a"] - 0.25) < 0.01
        assert abs(result["response_distribution"]["b"] - 0.75) < 0.01

    def test_soft_vectors_are_averaged_not_counted(self):
        x = np.array([[0.6, 0.4], [0.6, 0.4], [0.6, 0.4]])
        result = aggregate_arm(_df((1.0, 1.0, 1.0)), x, ["a", "b"])
        assert result["response_distribution"] == {"a": 0.6, "b": 0.4}

    def test_option_usage_is_expected_count(self):
        result = aggregate_arm(_df(), ONE_HOT, ["a", "b"])
        assert result["option_usage"] == {"a": 1, "b": 2}

    def test_subgroup_breakdown_by_cell_fields(self):
        result = aggregate_arm(_df((1.0, 1.0, 1.0)), ONE_HOT, ["a", "b"])
        assert result["by_subgroup"]["age_band"]["18-24"]["n"] == 2
        assert result["by_subgroup"]["age_band"]["25-34"]["n"] == 1
        assert result["by_subgroup"]["gender"]["female"]["distribution"] == {"a": 0.5, "b": 0.5}
        assert "education_level" not in result["by_subgroup"]  # column absent -> skipped

    def test_no_subgroups_when_disabled(self):
        result = aggregate_arm(_df(), ONE_HOT, ["a", "b"], include_subgroups=False)
        assert "by_subgroup" not in result


class TestBuildResult:
    def test_has_all_required_keys(self):
        scenario = {
            "scenario_id": "test",
            "run_type": "scenario",
            "options": ["a", "b"],
            "target_item": None,
        }
        arms = {
            "treatment": {"response_distribution": {"a": 0.5, "b": 0.5}},
            "placebo": {"response_distribution": {"a": 0.5, "b": 0.5}},
            "vanilla": {"response_distribution": {"a": 0.5, "b": 0.5}},
        }
        result = build_result(
            run_id="test__seed42",
            scenario=scenario,
            arms=arms,
            n_personas=10,
            model_name="mock",
            model_snapshot="mock-0",
            seed=42,
            persona_set_hash="sha256:abc",
            option_order="reversed_half",
            n_rounds=3,
        )
        assert result["run_id"] == "test__seed42"
        assert result["run_type"] == "scenario"
        assert "metadata" in result
        assert result["metadata"]["model"] == "mock"
        assert result["metadata"]["seed"] == 42
        assert result["metadata"]["n_rounds"] == 3

    def test_distributions_sum_to_one(self):
        scenario = {"scenario_id": "t", "run_type": "scenario", "options": ["a", "b"]}
        arms = {
            "treatment": {"response_distribution": {"a": 0.6, "b": 0.4}},
            "placebo": None,
            "vanilla": {"response_distribution": {"a": 0.5, "b": 0.5}},
        }
        result = build_result(
            run_id="t", scenario=scenario, arms=arms, n_personas=5,
            model_name="mock", model_snapshot="mock-0", seed=1,
            persona_set_hash="sha256:x", option_order="fixed", n_rounds=3,
        )
        for arm_name, arm_data in result["arms"].items():
            if arm_data is not None:
                total = sum(arm_data["response_distribution"].values())
                assert abs(total - 1.0) < 0.01
