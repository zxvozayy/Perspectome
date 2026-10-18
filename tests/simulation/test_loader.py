"""Tests for src.simulation.loader."""

import tempfile
from pathlib import Path

import pytest

from src.simulation.loader import (
    group_by_cell,
    load_personas,
    load_scenario,
    persona_set_hash,
)

FIXTURE_PERSONAS = Path("src/personas/fixtures/personas.sample.csv")
FIXTURE_SCENARIO = Path("src/simulation/scenarios/unemployment_shock_v1.yaml")
FIXTURE_PROBE = Path("src/simulation/scenarios/probe_trust_institutions.yaml")


class TestLoadPersonas:
    def test_reads_fixture_correctly(self):
        df = load_personas(FIXTURE_PERSONAS)
        assert len(df) == 15
        assert "persona_id" in df.columns
        assert "cell_id" in df.columns
        assert "weight" in df.columns

    def test_correct_types(self):
        df = load_personas(FIXTURE_PERSONAS)
        assert df["income_decile"].dtype.kind == "i"  # integer
        assert df["weight"].dtype.kind == "f"  # float

    def test_rejects_missing_column(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("persona_id,cell_id,weight\n")
            f.write("p01,cell1,1.0\n")
            f.flush()
            with pytest.raises(ValueError, match="Missing columns"):
                load_personas(f.name)

    def test_rejects_invalid_enum(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "persona_id,cell_id,weight,age_band,gender,education_level,"
                "region,settlement_type,marital_status,employment_status,income_decile\n"
            )
            f.write("p01,cell1,1.0,0-17,male,bachelor,Marmara,urban,single,student,4\n")
            f.flush()
            with pytest.raises(ValueError, match="Invalid values in 'age_band'"):
                load_personas(f.name)


class TestLoadScenario:
    def test_reads_scenario(self):
        s = load_scenario(FIXTURE_SCENARIO)
        assert s["run_type"] == "scenario"
        assert s["scenario_id"] == "unemployment_shock_v1"
        assert len(s["options"]) == 3

    def test_reads_probe(self):
        s = load_scenario(FIXTURE_PROBE)
        assert s["run_type"] == "probe"
        assert s["target_item"] == "trust_institutions"

    def test_rejects_invalid_run_type(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("scenario_id: bad\nrun_type: invalid\noptions: [a]\n")
            f.flush()
            with pytest.raises(ValueError, match="Invalid run_type"):
                load_scenario(f.name)


class TestPersonaSetHash:
    def test_deterministic(self):
        h1 = persona_set_hash(FIXTURE_PERSONAS)
        h2 = persona_set_hash(FIXTURE_PERSONAS)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_is_hex(self):
        h = persona_set_hash(FIXTURE_PERSONAS)
        hex_part = h.split(":")[1]
        assert len(hex_part) == 64
        int(hex_part, 16)  # should not raise


class TestGroupByCell:
    def test_groups_fixture(self):
        df = load_personas(FIXTURE_PERSONAS)
        groups = group_by_cell(df)
        # In the fixture each persona has a unique cell_id.
        assert len(groups) == 15
