"""Collapse persona-level opinions into the contract-shaped output."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.common.schema import CELL_FIELDS
from src.common.stats import weighted_mean_rows


def _weighted_mean(vectors: np.ndarray, weights: np.ndarray, options: list[str]) -> dict[str, float]:
    return {opt: round(float(p), 4) for opt, p in zip(options, weighted_mean_rows(vectors, weights))}


def aggregate_arm(
    personas: pd.DataFrame,
    vectors: np.ndarray,
    options: list[str],
    # Breakdowns by the cell-defining fields: other fields (region, income) would only
    # reflect which cells their members fall into, not anything the model said.
    subgroup_fields: tuple[str, ...] = CELL_FIELDS,
    include_subgroups: bool = True,
) -> dict:
    """response_distribution, option_usage and by_subgroup for one arm.

    ``vectors`` holds each persona's final probability vector (n, k).
    response_distribution is their weight-weighted mean. option_usage is the
    expected number of personas choosing each option (unweighted sum of
    probabilities, rounded) — an option nobody ever picks shows as 0 (rule 21).
    """
    weights = personas["weight"].to_numpy(dtype=float)
    result: dict = {
        "response_distribution": _weighted_mean(vectors, weights, options),
        "option_usage": {opt: int(round(float(c))) for opt, c in zip(options, vectors.sum(axis=0))},
    }

    if include_subgroups:
        by_subgroup: dict[str, dict] = {}
        for field in subgroup_fields:
            if field not in personas.columns:
                continue
            groups: dict[str, dict] = {}
            values = personas[field].to_numpy()
            for value in pd.unique(personas[field].dropna()):
                mask = values == value
                groups[str(value)] = {
                    "n": int(mask.sum()),
                    "distribution": _weighted_mean(vectors[mask], weights[mask], options),
                }
            by_subgroup[field] = groups
        result["by_subgroup"] = by_subgroup

    return result


def build_result(
    run_id: str,
    scenario: dict,
    arms: dict[str, dict | None],
    n_personas: int,
    model_name: str,
    model_snapshot: str,
    seed: int,
    persona_set_hash: str,
    option_order: str,
    n_rounds: int,
    extra_metadata: dict | None = None,
) -> dict:
    """Assemble the full results.json dict matching the contract."""
    metadata = {
        "model": model_name,
        "model_snapshot": model_snapshot,
        "seed": seed,
        "persona_set_hash": persona_set_hash,
        "option_order": option_order,
        "n_rounds": n_rounds,
        "aggregation": "weighted_mean_probability",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metadata.update(extra_metadata or {})
    return {
        "run_id": run_id,
        "run_type": scenario["run_type"],
        "scenario_id": scenario["scenario_id"],
        "target_item": scenario.get("target_item"),
        "options": scenario["options"],
        "n_personas": n_personas,
        "arms": arms,
        "metadata": metadata,
    }
