"""CLI entry point for the simulation engine.

Usage (dry-run, mock model — the default):
    python -m src.simulation.runner \
        --personas src/personas/fixtures/personas.sample.csv \
        --scenario src/simulation/scenarios/unemployment_shock_v1.yaml

Add --live --model <snapshot> to use a real API (costs money).

Cells: by default the archetype cells of personas.csv (age x gender x
education). ``cell_fields: auto`` in the scenario (or --cells auto) lets
src/answering pick the fields that matter for this question and quote the
cell's answers to related anchor items; a list of fields fixes them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.answering import cells, importance
from src.simulation.aggregator import aggregate_arm, build_result
from src.simulation.loader import (
    group_by_cell,
    load_personas,
    load_scenario,
)
from src.simulation.model import AnthropicModel, MockModel, OpenAIModel
from src.common import paths
from src.common.hashing import file_hash
from src.common.schema import ARMS, CELL_FIELDS
from src.simulation.prompt import build_prompts_for_arm
from src.simulation.rounds import initial_vectors, run_fj, run_round_1


def _cell_representatives(cell_groups: dict) -> dict[str, dict]:
    """The fields that define each cell (identical for every member).

    Other fields (region, income, ...) differ inside a cell, so taking one
    member's value would describe that member, not the cell.
    """
    return {cell_id: {f: sub_df.iloc[0][f] for f in CELL_FIELDS} for cell_id, sub_df in cell_groups.items()}


def _question_cells(personas, scenario: dict, spec, core_path, anchors_path):
    """Cells on question-specific fields (src/answering): personas with a new
    cell_id, each cell's fields, prompt context per cell, and run metadata."""
    if spec == "auto":
        imp = importance.table(core_path, anchors_path)
        chosen = cells.choose(scenario["question"], imp, target=scenario.get("target_item"))
    else:
        chosen = {"fields": list(spec), "anchors": []}
    cell_id, reps = cells.assign(personas, chosen["fields"])
    contexts = {}
    if chosen["anchors"]:
        core = pd.read_csv(core_path).merge(pd.read_csv(anchors_path), on="persona_id")
        contexts = {c: cells.context(rep, core, chosen["anchors"]) for c, rep in reps.items()}
    return personas.assign(cell_id=cell_id), reps, contexts, {"mode": spec if spec == "auto" else "fixed",
                                                             **chosen, "n_cells": len(reps)}


def _run_arm(
    arm: str,
    scenario: dict,
    personas,
    cell_reps: dict[str, dict],
    contexts: dict[str, str],
    model,
    seed: int,
    n_repeats: int,
    stubbornness: float,
    n_rounds: int,
    refusals: dict,
) -> dict | None:
    """Round 1 per cell, then Friedkin–Johnsen for rounds 2..n_rounds.

    Personas in cells the model refused to answer are left out of the arm and
    recorded in ``refusals``; an arm with no answered cell is None.
    """
    options = scenario["options"]
    prompts = build_prompts_for_arm(
        arm=arm,
        scenario=scenario,
        cell_representatives=cell_reps if arm != "vanilla" else {"__vanilla__": {}},
        reverse_half=True,
        contexts=contexts,
    )
    cell_dists = run_round_1(model, prompts, n_repeats, seed)
    refused = sorted(p["cell_id"] for p in prompts if p["cell_id"] not in cell_dists)
    if refused:
        cells_of = personas["cell_id"] if arm != "vanilla" else personas["cell_id"].map(lambda _: "__vanilla__")
        refusals[arm] = {"cells": refused, "n_personas": int(cells_of.isin(refused).sum())}
    if not cell_dists:
        return None

    if arm == "vanilla":
        # The model's own prior: one answer for everyone, no persona, no deliberation.
        x = initial_vectors(personas.assign(cell_id="__vanilla__"), cell_dists, options)
        return aggregate_arm(personas, x, options, include_subgroups=False)

    personas = personas[personas["cell_id"].isin(cell_dists)].reset_index(drop=True)
    x0 = initial_vectors(personas, cell_dists, options)
    x = run_fj(personas, x0, stubbornness, steps=n_rounds - 1)
    return aggregate_arm(personas, x, options, include_subgroups=True)


def run_simulation(
    personas_path: str | Path,
    scenario_path: str | Path,
    output_dir: str | Path = paths.RESULTS_DIR,
    seed: int = 42,
    live: bool = False,
    model_snapshot: str = "mock-0",
    max_calls: int = 200,
    n_repeats: int = 5,
    stubbornness: float = 0.6,
    n_rounds: int = 3,
    cell_fields=None,
    core_path: str | Path = paths.PERSONAS_CSV,
    anchors_path: str | Path = paths.ANCHORS_CSV,
) -> dict:
    """Run the full simulation and return the result dict.

    ``cell_fields`` ("auto" or a list) overrides the scenario's own setting;
    ``core_path``/``anchors_path`` are the real core and its anchor answers,
    used only for question-specific cells. Also writes the result JSON to output_dir.
    """
    # Load data.
    personas = load_personas(personas_path)
    scenario = load_scenario(scenario_path)
    p_hash = file_hash(personas_path)

    # A persona without a cell (a cell-defining field missing) can't be queried.
    no_cell = personas["cell_id"].isna()
    n_excluded = int(no_cell.sum())
    personas = personas[~no_cell].reset_index(drop=True)

    # Select model.
    if live:
        if model_snapshot.startswith("claude"):
            model = AnthropicModel(model_snapshot=model_snapshot, max_calls=max_calls)
            model_name = f"anthropic/{model_snapshot}"
        else:
            model = OpenAIModel(model_snapshot=model_snapshot, max_calls=max_calls)
            model_name = f"openai/{model_snapshot}"
    else:
        model = MockModel(seed=seed)
        model_name = "mock"
        model_snapshot = "mock-0"

    spec = cell_fields if cell_fields is not None else scenario.get("cell_fields")
    if spec is None:
        cell_reps, contexts = _cell_representatives(group_by_cell(personas)), {}
        cell_meta = {"mode": "default", "fields": list(CELL_FIELDS), "n_cells": len(cell_reps)}
    else:
        personas, cell_reps, contexts, cell_meta = _question_cells(personas, scenario, spec, core_path, anchors_path)

    # Probes have no placebo arm (placebo = null in the output).
    arms_to_run = [a for a in ARMS if scenario["run_type"] == "scenario" or a != "placebo"]

    arms_output: dict[str, dict | None] = {}
    refusals: dict[str, dict] = {}
    for arm in arms_to_run:
        arms_output[arm] = _run_arm(
            arm=arm,
            scenario=scenario,
            personas=personas,
            cell_reps=cell_reps,
            contexts=contexts,
            model=model,
            seed=seed,
            n_repeats=n_repeats,
            stubbornness=stubbornness,
            n_rounds=n_rounds,
            refusals=refusals,
        )

    # Probes have placebo = null.
    if "placebo" not in arms_output:
        arms_output["placebo"] = None

    run_id = f"{scenario['scenario_id']}__{model_snapshot}__seed{seed}"  # one file per model and seed
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
        n_rounds=n_rounds,
        extra_metadata={"n_excluded_no_cell": n_excluded, "model_stats": model.summary(), "cells": cell_meta,
                        "refusals": refusals},
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
    parser.add_argument("--output-dir", default=str(paths.RESULTS_DIR), help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--live", action="store_true", help="Use real API (costs money)")
    parser.add_argument("--model", default="mock-0", help="Model snapshot string")
    parser.add_argument("--max-calls", type=int, default=200, help="Hard call cap")
    parser.add_argument("--n-repeats", type=int, default=5, help="Repeats per cell query")
    parser.add_argument("--stubbornness", type=float, default=0.6, help="FJ stubbornness")
    parser.add_argument("--cells", default=None, help="'auto', or comma-separated fields (default: the scenario's)")
    parser.add_argument("--core", default=str(paths.PERSONAS_CSV), help="real core personas (for --cells)")
    parser.add_argument("--anchors", default=str(paths.ANCHORS_CSV), help="the core's anchor answers")
    args = parser.parse_args()
    spec = args.cells if args.cells in (None, "auto") else args.cells.split(",")

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
        cell_fields=spec,
        core_path=args.core,
        anchors_path=args.anchors,
    )


if __name__ == "__main__":
    main()
