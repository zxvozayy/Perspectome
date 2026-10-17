"""Load and validate personas and scenario definitions."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

from src.common.schema import (
    AGE_BANDS,
    EDUCATION_LEVELS,
    EMPLOYMENT_STATUSES,
    GENDERS,
    HELDOUT_FIELDS,
    INCOME_DECILES,
    MARITAL_STATUSES,
    RUN_TYPES,
    SETTLEMENT_TYPES,
)

REQUIRED_PERSONA_COLUMNS = (
    "persona_id", "cell_id", "weight",
    "age_band", "gender", "education_level", "region",
    "settlement_type", "marital_status", "employment_status", "income_decile",
)

_ENUM_VALIDATORS = {
    "age_band": set(AGE_BANDS),
    "gender": set(GENDERS),
    "education_level": set(EDUCATION_LEVELS),
    "settlement_type": set(SETTLEMENT_TYPES),
    "marital_status": set(MARITAL_STATUSES),
    "employment_status": set(EMPLOYMENT_STATUSES),
    "income_decile": set(INCOME_DECILES),
}


def load_personas(path: str | Path) -> pd.DataFrame:
    """Read personas.csv and validate against the shared schema."""
    df = pd.read_csv(path)

    missing = set(REQUIRED_PERSONA_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in personas CSV: {sorted(missing)}")

    df["income_decile"] = df["income_decile"].astype(int)
    df["weight"] = df["weight"].astype(float)

    for col, valid in _ENUM_VALIDATORS.items():
        invalid = set(df[col].unique()) - valid
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


def persona_set_hash(path: str | Path) -> str:
    """SHA-256 hex digest of the raw file bytes, prefixed with 'sha256:'."""
    raw = Path(path).read_bytes()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def group_by_cell(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Group personas by cell_id. Returns {cell_id: sub_df}."""
    return {cell_id: group for cell_id, group in df.groupby("cell_id")}
