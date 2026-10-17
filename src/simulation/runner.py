"""CLI entry point for the simulation engine.

Usage (dry-run, mock model — the default):
    python -m src.simulation.runner \
        --personas src/personas/fixtures/personas.sample.csv \
        --scenario src/simulation/scenarios/unemployment_shock_v1.yaml

Add --live --model <snapshot> to use a real API (costs money).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.simulation.aggregator import aggregate_arm, build_result
from src.simulation.loader import (
    group_by_cell,
    load_personas,
    load_scenario,
    persona_set_hash,
)
from src.simulation.model import MockModel, OpenAIModel
from src.simulation.prompt import build_prompts_for_arm
from src.simulation.rounds import (
    assign_personas_round_1,
    run_round_1,
    run_round_2_fj,
    run_round_3_settle,
)


def _cell_representatives(cell_groups: dict) -> dict[str, dict]:
    """Extract one representative row (as dict) per cell for prompt building."""
    reps = {}
    for cell_id, sub_df in cell_groups.items():
        row = sub_df.iloc[0]
        reps[cell_id] = {
            "age_band": row["age_band"],
            "gender": row["gender"],
            "education_level": row["education_level"],
            "region": row["region"],
            "settlement_type": row["settlement_type"],
            "marital_status": row["marital_status"],
            "employment_status": row["employment_status"],
            "income_decile": row["income_decile"],
        }
    return reps


def _run_arm(
    arm: str,
    scenario: dict,
    personas,
    cell_reps: dict[str, dict],
    model,
    seed: int,
    n_repeats: int,
    stubbornness: float,
) -> dict:
    """Run the full three-round pipeline for one arm."""
    options = scenario["options"]

    # Build prompts for this arm.
    prompts = build_prompts_for_arm(
        arm=arm,
        scenario=scenario,
        cell_representatives=cell_reps if arm != "vanilla" else {"__vanilla__": {}},
        reverse_half=True,
    )

    # For vanilla: all personas map to the single vanilla cell.
    if arm == "vanilla":
        cell_dists = run_round_1(model, prompts, n_repeats, seed)
        # All personas get the vanilla distribution.
        vanilla_dist = cell_dists["__vanilla__"]
        cell_dists_mapped = {cid: vanilla_dist for cid in personas["cell_id"].unique()}

        df = assign_personas_round_1(personas, cell_dists_mapped, options, seed)
        df = run_round_2_fj(df, options, stubbornness, seed)
        df = run_round_3_settle(df, options, seed)
        return aggregate_arm(df, options, include_subgroups=False)

    # Treatment / placebo.
    cell_dists = run_round_1(model, prompts, n_repeats, seed)
    df = assign_personas_round_1(personas, cell_dists, options, seed)
    df = run_round_2_fj(df, options, stubbornness, seed)
    df = run_round_3_settle(df, options, seed)
    return aggregate_arm(df, options, include_subgroups=True)


def run_simulation(
    personas_path: str | Path,
    scenario_path: str | Path,
    output_dir: str | Path = "results",
    seed: int = 42,
    live: bool = False,
    model_snapshot: str = "mock-0",
    max_calls: int = 200,
    n_repeats: int = 5,
    stubbornness: float = 0.6,
) -> dict:
    """Run the full simulation and return the result dict.

    Also writes the result JSON to output_dir.
    """
    # Load data.
    personas = load_personas(personas_path)
    scenario = load_scenario(scenario_path)
    p_hash = persona_set_hash(personas_path)

    # Select model.
    if live:
        model = OpenAIModel(model_snapshot=model_snapshot, max_calls=max_calls)
        model_name = f"openai/{model_snapshot}"
    else:
        model = MockModel(seed=seed)
        model_name = "mock"
        model_snapshot = "mock-0"

    cell_groups = group_by_cell(personas)
    cell_reps = _cell_representatives(cell_groups)

    # Determine which arms to run.
    arms_to_run = ["treatment", "vanilla"]
    if scenario["run_type"] == "scenario":
        arms_to_run.insert(1, "placebo")

    arms_output: dict[str, dict | None] = {}
    for arm in arms_to_run:
        arms_output[arm] = _run_arm(
            arm=arm,
            scenario=scenario,
            personas=personas,
            cell_reps=cell_reps,
            model=model,
            seed=seed,
            n_repeats=n_repeats,
            stubbornness=stubbornness,
        )

    # Probes have placebo = null.
    if "placebo" not in arms_output:
        arms_output["placebo"] = None

    run_id = f"{scenario['scenario_id']}__seed{seed}"
    result = build_result(
        run_id=run_id,
        scenario=scenario,
        arms=arms_output,
        n_personas=len(personas),
        model_name=model_name,
        model_snapshot=model_snapshot,
        seed=seed,
        persona_set_hash=p_hash,
        option_order="reversed_half",
        n_rounds=3,
    )

    # Write output.
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Written: {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Perspectome simulation runner")
    parser.add_argument("--personas", required=True, help="Path to personas.csv")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--live", action="store_true", help="Use real API (costs money)")
    parser.add_argument("--model", default="mock-0", help="Model snapshot string")
    parser.add_argument("--max-calls", type=int, default=200, help="Hard call cap")
    parser.add_argument("--n-repeats", type=int, default=5, help="Repeats per cell query")
    parser.add_argument("--stubbornness", type=float, default=0.6, help="FJ stubbornness")
    args = parser.parse_args()

    run_simulation(
        personas_path=args.personas,
        scenario_path=args.scenario,
        output_dir=args.output_dir,
        seed=args.seed,
        live=args.live,
        model_snapshot=args.model,
        max_calls=args.max_calls,
        n_repeats=args.n_repeats,
        stubbornness=args.stubbornness,
    )


if __name__ == "__main__":
    main()
