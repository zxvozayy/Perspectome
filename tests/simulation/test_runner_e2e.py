"""End-to-end tests (DoD #6).

Runs the full pipeline against fixture personas and all three scenario YAMLs.
"""

import json
import tempfile
from pathlib import Path

from src.simulation.runner import run_simulation

FIXTURE_PERSONAS = Path("src/personas/fixtures/personas.sample.csv")
SCENARIOS_DIR = Path("src/simulation/scenarios")


def _run_and_validate(scenario_path: str | Path, expected_run_type: str):
    """Helper: run simulation and validate the output JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_simulation(
            personas_path=FIXTURE_PERSONAS,
            scenario_path=scenario_path,
            output_dir=tmpdir,
            seed=42,
        )

        # Check top-level keys.
        assert "run_id" in result
        assert result["run_type"] == expected_run_type
        assert "scenario_id" in result
        assert "options" in result
        assert result["n_personas"] == 15
        assert "arms" in result
        assert "metadata" in result

        # Check metadata.
        meta = result["metadata"]
        assert meta["model"] == "mock"
        assert meta["seed"] == 42
        assert meta["n_rounds"] == 3
        assert meta["persona_set_hash"].startswith("sha256:")
        assert meta["option_order"] == "reversed_half"
        # Timestamp is valid ISO 8601.
        from datetime import datetime
        datetime.fromisoformat(meta["timestamp"])

        # Check arms.
        arms = result["arms"]
        assert "treatment" in arms
        assert "vanilla" in arms

        # Treatment arm has full structure.
        treatment = arms["treatment"]
        assert "response_distribution" in treatment
        assert "option_usage" in treatment
        assert "by_subgroup" in treatment

        # Distributions sum to ~1.0.
        for arm_name in ["treatment", "vanilla"]:
            arm_data = arms[arm_name]
            if arm_data is not None:
                total = sum(arm_data["response_distribution"].values())
                assert abs(total - 1.0) < 0.02, (
                    f"{arm_name} distribution sums to {total}"
                )

        # Vanilla has no subgroups.
        assert "by_subgroup" not in arms["vanilla"]

        # Check that a file was written.
        files = list(Path(tmpdir).glob("*.json"))
        assert len(files) == 1
        with open(files[0]) as f:
            written = json.load(f)
        assert written["run_id"] == result["run_id"]

    return result


class TestScenarioEndToEnd:
    def test_unemployment_shock(self):
        result = _run_and_validate(
            SCENARIOS_DIR / "unemployment_shock_v1.yaml", "scenario"
        )
        assert result["arms"]["placebo"] is not None
        placebo = result["arms"]["placebo"]
        assert "response_distribution" in placebo

    def test_ai_adoption(self):
        result = _run_and_validate(
            SCENARIOS_DIR / "ai_adoption_v1.yaml", "scenario"
        )
        assert result["arms"]["placebo"] is not None


class TestProbeEndToEnd:
    def test_trust_institutions(self):
        result = _run_and_validate(
            SCENARIOS_DIR / "probe_trust_institutions.yaml", "probe"
        )
        assert result["target_item"] == "trust_institutions"
        # Probes have placebo = null.
        assert result["arms"]["placebo"] is None
        # Options are 1-5.
        assert result["options"] == ["1", "2", "3", "4", "5"]
