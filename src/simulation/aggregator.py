"""Collapse persona-level outcomes into the contract-shaped output."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def aggregate_arm(
    personas: pd.DataFrame,
    options: list[str],
    subgroup_fields: tuple[str, ...] = ("age_band",),
    include_subgroups: bool = True,
) -> dict:
    """Compute response_distribution, option_usage, and by_subgroup.

    response_distribution uses weights; option_usage is raw counts.
    """
    weights = personas["weight"].values
    choices = personas["final_choice"].values

    # Weighted distribution.
    response_distribution: dict[str, float] = {}
    option_usage: dict[str, int] = {}
    for opt in options:
        mask = choices == opt
        option_usage[opt] = int(mask.sum())
        response_distribution[opt] = round(
            float(weights[mask].sum() / weights.sum()), 4
        )

    result: dict = {
        "response_distribution": response_distribution,
        "option_usage": option_usage,
    }

    if include_subgroups:
        by_subgroup: dict[str, dict] = {}
        for field in subgroup_fields:
            groups: dict[str, dict] = {}
            for value, group_df in personas.groupby(field):
                n = len(group_df)
                g_weights = group_df["weight"].values
                g_choices = group_df["final_choice"].values
                dist: dict[str, float] = {}
                for opt in options:
                    mask = g_choices == opt
                    dist[opt] = round(
                        float(g_weights[mask].sum() / g_weights.sum()), 4
                    )
                groups[str(value)] = {"n": n, "distribution": dist}
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
) -> dict:
    """Assemble the full results.json dict matching the contract."""
    return {
        "run_id": run_id,
        "run_type": scenario["run_type"],
        "scenario_id": scenario["scenario_id"],
        "target_item": scenario.get("target_item"),
        "options": scenario["options"],
        "n_personas": n_personas,
        "arms": arms,
        "metadata": {
            "model": model_name,
            "model_snapshot": model_snapshot,
            "seed": seed,
            "persona_set_hash": persona_set_hash,
            "option_order": option_order,
            "n_rounds": n_rounds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
