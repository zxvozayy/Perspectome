"""Tests for src.simulation.loader."""

import tempfile

import pandas as pd
import pytest
import yaml

from src.common import paths
from src.common.schema import PERSONA_COLUMNS
from src.simulation.loader import (
    group_by_cell,
    load_personas,
    load_scenario,
)

FIXTURE_PERSONAS = paths.PERSONAS_FIXTURE
FIXTURE_SCENARIO = paths.SCENARIOS_DIR / "unemployment_shock_v1.yaml"
FIXTURE_PROBE = paths.SCENARIOS_DIR / "probe_trust_police.yaml"


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
            f.write(",".join(PERSONA_COLUMNS) + "\n")
            f.write("p01,cell1,1.0,0-17,male,bachelor,Marmara,urban,single,student,4,high,centre\n")
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
        assert s["target_item"] == "trust_police"

    def test_rejects_invalid_run_type(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("scenario_id: bad\nrun_type: invalid\noptions: [a]\n")
            f.flush()
            with pytest.raises(ValueError, match="Invalid run_type"):
                load_scenario(f.name)


class TestGroupByCell:
    def test_groups_fixture(self):
        df = load_personas(FIXTURE_PERSONAS)
        groups = group_by_cell(df)
        # In the fixture each persona has a unique cell_id.
        assert len(groups) == 15


class TestMissingValues:
    def test_missing_fields_are_allowed(self, tmp_path):
        """Track A keeps respondents with missing fields; the loader must accept them."""
        df = pd.read_csv(FIXTURE_PERSONAS)
        df.loc[0, "income_decile"] = None
        df.loc[1, "employment_status"] = None
        df.loc[2, "cell_id"] = None
        path = tmp_path / "p.csv"
        df.to_csv(path, index=False)
        out = load_personas(path)
        assert out["income_decile"].isna().sum() == 1 and str(out["income_decile"].dtype) == "Int64"
        assert out["employment_status"].isna().sum() == 1


@pytest.mark.parametrize("cells", ["auto", ["gender", "region"]])
def test_scenario_cell_fields_accepted(tmp_path, cells):
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump({"scenario_id": "x", "run_type": "probe", "question": "q",
                                    "options": ["a", "b"], "cell_fields": cells}), encoding="utf-8")
    assert load_scenario(path)["cell_fields"] == cells


@pytest.mark.parametrize("cells", ["all", ["trust_police"], "gender"])
def test_scenario_cell_fields_rejected(tmp_path, cells):
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump({"scenario_id": "x", "run_type": "probe", "question": "q",
                                    "options": ["a", "b"], "cell_fields": cells}), encoding="utf-8")
    with pytest.raises(ValueError, match="cell_fields"):
        load_scenario(path)


def test_option_labels_need_one_per_option(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump({"scenario_id": "x", "run_type": "probe", "question": "q",
                                    "options": ["1", "2"], "option_labels": ["low"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="option_labels"):
        load_scenario(path)


def test_every_heldout_item_has_a_probe():
    from src.common.schema import HELDOUT_FIELDS
    probes = {load_scenario(p)["target_item"] for p in paths.SCENARIOS_DIR.glob("probe_*.yaml")}
    assert probes == set(HELDOUT_FIELDS)
