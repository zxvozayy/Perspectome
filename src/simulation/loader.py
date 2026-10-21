"""Load and validate personas and scenario definitions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.common.schema import CATEGORIES, HELDOUT_FIELDS, PERSONA_COLUMNS, RUN_TYPES


def load_personas(path: str | Path) -> pd.DataFrame:
    """Read personas.csv and validate against the shared schema."""
    df = pd.read_csv(path)

    missing = set(PERSONA_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in personas CSV: {sorted(missing)}")

    # Track A keeps respondents with missing fields (warn, never drop), so
    # every field except the id and weight may be missing.
    df["income_decile"] = pd.to_numeric(df["income_decile"], errors="coerce").astype("Int64")
    df["weight"] = df["weight"].astype(float)

    for col, valid in CATEGORIES.items():
        invalid = set(df[col].dropna().unique()) - set(valid)
        if invalid:
            raise ValueError(f"Invalid values in '{col}': {sorted(invalid)}")

    return df


def load_scenario(path: str | Path) -> dict:
    """Read a scenario/probe YAML and validate its structure."""
    with open(path, "r", encoding="utf-8") as f:
        scenario = yaml.safe_load(f)

    if scenario.get("run_type") not in RUN_TYPES:
        raise ValueError(
            f"Invalid run_type '{scenario.get('run_type')}'; "
            f"must be one of {RUN_TYPES}"
        )

    if not scenario.get("options"):
        raise ValueError("Scenario must have a non-empty 'options' list")

    target = scenario.get("target_item")
    if target is not None and target not in HELDOUT_FIELDS:
        raise ValueError(
            f"target_item '{target}' not in HELDOUT_FIELDS: {HELDOUT_FIELDS}"
        )

    if scenario["run_type"] == "scenario":
        if not scenario.get("treatment_text"):
            raise ValueError("Scenarios must have non-null treatment_text")
        if not scenario.get("placebo_text"):
            raise ValueError("Scenarios must have non-null placebo_text")

    return scenario


def group_by_cell(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Group personas by cell_id. Returns {cell_id: sub_df}."""
    return {cell_id: group for cell_id, group in df.groupby("cell_id")}
