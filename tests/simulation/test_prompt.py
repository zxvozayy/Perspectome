"""Prompt-payload tests (DoD #5).

Captures what is actually sent and checks the persona block
and exact question wording are in it.
"""

from pathlib import Path

import pytest

from src.common.schema import HELDOUT_FIELDS
from src.simulation.loader import load_personas, load_scenario, group_by_cell
from src.simulation.prompt import (
    build_persona_block,
    build_prompt,
    build_prompts_for_arm,
)

FIXTURE_PERSONAS = Path("src/personas/fixtures/personas.sample.csv")
FIXTURE_SCENARIO = Path("src/simulation/scenarios/unemployment_shock_v1.yaml")
FIXTURE_PROBE = Path("src/simulation/scenarios/probe_trust_police.yaml")


class TestBuildPersonaBlock:
    def test_includes_conditioning_fields(self):
        fields = {
            "age_band": "25-34",
            "gender": "female",
            "education_level": "bachelor",
            "region": "Marmara",
            "settlement_type": "urban",
            "marital_status": "single",
            "employment_status": "student",
            "income_decile": 4,
        }
        block = build_persona_block(fields)
        assert "25-34" in block
        assert "female" in block
        assert "bachelor" in block
        assert "Marmara" in block
        assert "urban" in block
        assert "single" in block
        assert "student" in block
        assert "4" in block

    def test_excludes_heldout_fields(self):
        fields = {
            "age_band": "25-34",
            "gender": "female",
            "education_level": "bachelor",
            "region": "Marmara",
            "settlement_type": "urban",
            "marital_status": "single",
            "employment_status": "student",
            "income_decile": 4,
        }
        block = build_persona_block(fields)
        for field in HELDOUT_FIELDS:
            assert field not in block.lower()


class TestBuildPrompt:
    def test_treatment_includes_scenario_and_question(self):
        prompt = build_prompt(
            persona_block="You are a 25-34 year old female.",
            scenario_text="Unemployment rose sharply.",
            question="Should the government act?",
            options=["support", "oppose"],
            reverse_options=False,
        )
        assert "Unemployment rose sharply." in prompt
        assert "Should the government act?" in prompt
        assert "support" in prompt
        assert "oppose" in prompt
        assert "You are a 25-34 year old female." in prompt

    def test_vanilla_has_no_persona_or_scenario(self):
        prompt = build_prompt(
            persona_block=None,
            scenario_text=None,
            question="Should the government act?",
            options=["support", "oppose"],
            reverse_options=False,
        )
        assert "Should the government act?" in prompt
        # No persona or scenario text.
        assert "You are" not in prompt

    def test_option_reversal(self):
        prompt_normal = build_prompt(
            persona_block=None,
            scenario_text=None,
            question="Q?",
            options=["support", "oppose"],
            reverse_options=False,
        )
        prompt_reversed = build_prompt(
            persona_block=None,
            scenario_text=None,
            question="Q?",
            options=["support", "oppose"],
            reverse_options=True,
        )
        assert "A) support\nB) oppose" in prompt_normal
        assert "A) oppose\nB) support" in prompt_reversed

    def test_every_option_gets_a_single_letter(self):
        """Rule 25: no option silently loses its label."""
        options = [str(i) for i in range(1, 11)]
        prompt = build_prompt(None, None, "Q?", options, reverse_options=False)
        assert "J) 10" in prompt and "letter of exactly one option" in prompt
        with pytest.raises(ValueError):
            build_prompt(None, None, "Q?", [str(i) for i in range(27)], reverse_options=False)

    def test_persona_block_skips_missing_fields(self):
        block = build_persona_block({"age_band": "65+", "gender": "male", "education_level": "primary",
                                     "income_decile": float("nan"), "region": None})
        assert "nan" not in block and "None" not in block and "65+" in block

    def test_no_rationale_request(self):
        """Rule 19: don't ask for a rationale alongside the choice."""
        prompt = build_prompt(
            persona_block="Persona.",
            scenario_text="Scenario.",
            question="Question?",
            options=["a", "b"],
            reverse_options=False,
        )
        assert "explain" not in prompt.lower()
        assert "rationale" not in prompt.lower()
        assert "why" not in prompt.lower()
        assert "reason" not in prompt.lower()


class TestBuildPromptsForArm:
    """Capture tests using real fixture data (rule 27)."""

    def test_treatment_prompts_contain_persona_and_question(self):
        scenario = load_scenario(FIXTURE_SCENARIO)
        df = load_personas(FIXTURE_PERSONAS)
        cells = group_by_cell(df)
        cell_reps = {
            cid: sub.iloc[0].to_dict() for cid, sub in cells.items()
        }

        prompts = build_prompts_for_arm("treatment", scenario, cell_reps)
        for entry in prompts:
            # Exact question wording from the YAML is in the prompt.
            assert "unemployment rate" in entry["prompt"].lower()
            # Persona conditioning is in the prompt.
            assert "you are" in entry["prompt"].lower()

    def test_placebo_does_not_contain_treatment_text(self):
        scenario = load_scenario(FIXTURE_SCENARIO)
        df = load_personas(FIXTURE_PERSONAS)
        cells = group_by_cell(df)
        cell_reps = {
            cid: sub.iloc[0].to_dict() for cid, sub in cells.items()
        }

        prompts = build_prompts_for_arm("placebo", scenario, cell_reps)
        for entry in prompts:
            # Placebo text is present, treatment text is not.
            assert "energy consumption" in entry["prompt"].lower()
            assert "unemployment rate has risen sharply" not in entry["prompt"].lower()

    def test_vanilla_has_no_persona_block(self):
        scenario = load_scenario(FIXTURE_SCENARIO)
        prompts = build_prompts_for_arm(
            "vanilla", scenario, {"__vanilla__": {}}
        )
        for entry in prompts:
            assert "you are" not in entry["prompt"].lower()

    def test_heldout_fields_never_in_prompt(self):
        scenario = load_scenario(FIXTURE_SCENARIO)
        df = load_personas(FIXTURE_PERSONAS)
        cells = group_by_cell(df)
        cell_reps = {
            cid: sub.iloc[0].to_dict() for cid, sub in cells.items()
        }

        for arm in ["treatment", "placebo"]:
            prompts = build_prompts_for_arm(arm, scenario, cell_reps)
            for entry in prompts:
                for field in HELDOUT_FIELDS:
                    assert field not in entry["prompt"].lower()

    def test_half_are_reversed(self):
        scenario = load_scenario(FIXTURE_SCENARIO)
        df = load_personas(FIXTURE_PERSONAS)
        cells = group_by_cell(df)
        cell_reps = {
            cid: sub.iloc[0].to_dict() for cid, sub in cells.items()
        }

        prompts = build_prompts_for_arm(
            "treatment", scenario, cell_reps, reverse_half=True
        )
        reversed_count = sum(1 for p in prompts if p["reversed"])
        not_reversed = sum(1 for p in prompts if not p["reversed"])
        assert reversed_count > 0
        assert not_reversed > 0
