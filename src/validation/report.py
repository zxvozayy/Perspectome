"""Build ``reports/comparison.json`` -- the contract Track D renders.

    python -m src.validation.report                      # real inputs if present, else fixtures
    python -m src.validation.report --fixtures           # force the fixture inputs
    python -m src.validation.report --results-dir results --personas data/processed/personas.csv \
        --heldout data/processed/heldout.csv --out reports/comparison.json

Probes are scored against the real held-out answers (TVD, calibration error,
Wasserstein for ordinal items) next to vanilla and the ML baseline. Scenarios
report effects only (treatment - placebo), gated by the noise floor, the
saturation screen and the minimum detectable difference.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from src.common import schema
from src.validation import baselines, metrics, real

RESULTS_FIXTURES = (
    Path("src/simulation/fixtures/results.sample.json"),
    Path("src/simulation/fixtures/results.probe.sample.json"),
)
REAL_PERSONAS = Path("data/processed/personas.csv")
REAL_HELDOUT = Path("data/processed/heldout.csv")
DEFAULT_OUT = Path("reports/comparison.json")
MIN_RANK_ITEMS = 3


# --- loading -------------------------------------------------------------------

def load_runs(paths: Sequence[Path]) -> list[dict]:
    runs = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            runs.append(json.load(f))
    return runs


def _snapshot(run: dict) -> str:
    return str(run.get("metadata", {}).get("model_snapshot") or "unknown")


def _seed(run: dict):
    return run.get("metadata", {}).get("seed")


def _mean_dist(dists: list[dict], options: Sequence[str]) -> dict:
    v = np.mean([[float(d.get(o, 0.0)) for o in options] for d in dists], axis=0)
    return metrics.normalize({o: float(x) for o, x in zip(options, v)}, options)


def _arm_dist(run: dict, arm: str, options: Sequence[str]) -> Optional[dict]:
    a = (run.get("arms") or {}).get(arm)
    if not a or not a.get("response_distribution"):
        return None
    return metrics.normalize(a["response_distribution"], options)


def _primary_model(runs: list[dict]) -> str:
    """The model snapshot with the most runs (ties: alphabetical)."""
    counts = defaultdict(int)
    for r in runs:
        counts[_snapshot(r)] += 1
    return sorted(counts, key=lambda m: (-counts[m], m))[0]


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _rdist(d: dict, nd=4) -> dict:
    return {k: _r(v, nd) for k, v in d.items()}


# --- noise floor ------------------------------------------------------------------

def noise_floor(runs: list[dict]) -> Optional[float]:
    """Largest treatment-arm TVD between two seeds of the same config (rule 6).

    Config = (run_type, scenario_id, model snapshot). None if no config was run
    with more than one seed -- then nothing can be called measurable.
    """
    groups = defaultdict(list)
    for r in runs:
        groups[(r.get("run_type"), r.get("scenario_id"), _snapshot(r))].append(r)
    gaps = []
    for group in groups.values():
        by_seed = {}
        for r in group:
            by_seed.setdefault(_seed(r), r)
        seeds = list(by_seed.values())
        for i in range(len(seeds)):
            for j in range(i + 1, len(seeds)):
                options = seeds[i]["options"]
                a, b = _arm_dist(seeds[i], "treatment", options), _arm_dist(seeds[j], "treatment", options)
                if a and b:
                    gaps.append(metrics.tvd(a, b, options))
    return max(gaps) if gaps else None


# --- probes -----------------------------------------------------------------------

def _scores(dist: dict, real_dist: dict, options: Sequence[str], ordinal: bool) -> dict:
    out = {"distribution": _rdist(dist),
           "tvd": _r(metrics.tvd(dist, real_dist, options)),
           "calibration_error": _r(metrics.calibration_error(dist, real_dist, options))}
    if ordinal:
        out["wasserstein"] = _r(metrics.wasserstein_ordinal(dist, real_dist, options))
    return out


def score_probes(runs: list[dict], frame: pd.DataFrame, warnings: list[str]) -> list[dict]:
    by_item = defaultdict(list)
    for r in runs:
        if r.get("run_type") == "probe" and r.get("target_item"):
            by_item[r["target_item"]].append(r)

    probes = []
    for item in sorted(by_item):
        item_runs = by_item[item]
        if item not in frame.columns:
            warnings.append(f"Probe '{item}' has no held-out column; not scored.")
            continue
        options = list(item_runs[0]["options"])
        ordinal = real.is_ordinal(item)
        stats = real.distribution_stats(frame, item, options)
        real_dist = stats["distribution"]
        if stats["coverage"] < 0.95:
            warnings.append(f"Probe '{item}': {1 - stats['coverage']:.0%} of real answers fall "
                            "outside the probe's options and were dropped.")

        primary = _primary_model(item_runs)
        primary_runs = [r for r in item_runs if _snapshot(r) == primary]
        methods = {}
        engine = [d for r in primary_runs if (d := _arm_dist(r, "treatment", options))]
        if engine:
            methods["engine"] = _scores(_mean_dist(engine, options), real_dist, options, ordinal)
        vanilla = [d for r in primary_runs if (d := _arm_dist(r, "vanilla", options))]
        if vanilla:
            methods["vanilla"] = _scores(_mean_dist(vanilla, options), real_dist, options, ordinal)
        ml = baselines.ml_baseline(frame, item, options)
        methods["ml_baseline"] = _scores(ml["distribution"], real_dist, options, ordinal)

        models = {}
        for snap in sorted({_snapshot(r) for r in item_runs}):
            ds = [d for r in item_runs if _snapshot(r) == snap and (d := _arm_dist(r, "treatment", options))]
            if ds:
                models[snap] = {"tvd": _r(metrics.tvd(_mean_dist(ds, options), real_dist, options))}

        probes.append({
            "item": item,
            "role": real.role(item),
            "options": options,
            "ordinal": ordinal,
            "real": _rdist(real_dist),
            "n_real": stats["n"],
            "n_eff_real": _r(stats["n_eff"], 1),
            "methods": methods,
            "models": models,
        })
    return probes


def rank_agreement(probes: list[dict], warnings: list[str]) -> dict:
    """Kendall tau-b between real and method orderings of ordinal probe items.

    Measured on "test" items only (rule 10) once there are enough of them;
    until then on every ordinal item, with a warning.
    """
    ordinal = [p for p in probes if p.get("ordinal")]
    test = [p for p in ordinal if p.get("role") == "test"]
    if len(test) >= MIN_RANK_ITEMS:
        ordinal = test
    elif ordinal:
        warnings.append("Rank agreement uses fit items too (fewer than "
                        f"{MIN_RANK_ITEMS} test items were probed); treat it as a development check.")
    out = {"metric": "kendall_tau", "n_items": len(ordinal),
           "items": [p["item"] for p in ordinal], "methods": {}}
    if len(ordinal) < MIN_RANK_ITEMS:
        warnings.append(f"Rank agreement needs at least {MIN_RANK_ITEMS} ordinal probe items; "
                        f"have {len(ordinal)}. Not computed.")
        return out
    real_pos = [metrics.expected_position(p["real"], p["options"]) for p in ordinal]
    names = sorted({m for p in ordinal for m in p["methods"]})
    for name in names:
        if not all(name in p["methods"] for p in ordinal):
            continue
        pos = [metrics.expected_position(p["methods"][name]["distribution"], p["options"]) for p in ordinal]
        tau = metrics.kendall_tau_b(real_pos, pos)
        if tau is not None:
            out["methods"][name] = _r(tau, 3)
    return out


# --- scenarios --------------------------------------------------------------------

def _subgroups(treat_run_arm: dict, placebo_arm: dict, option: str) -> tuple[dict, list[str]]:
    """Direction of the treatment-placebo gap per subgroup cell, BH-corrected.

    Cells with n < MIN_CELL_N in either arm are listed in small_cells, untested.
    """
    t_groups = (treat_run_arm or {}).get("by_subgroup") or {}
    p_groups = (placebo_arm or {}).get("by_subgroup") or {}
    tested, small = [], []
    for field, cells in t_groups.items():
        for value, t in cells.items():
            p = (p_groups.get(field) or {}).get(value)
            if not p:
                continue
            n_t, n_p = int(t.get("n", 0)), int(p.get("n", 0))
            if min(n_t, n_p) < schema.MIN_CELL_N:
                small.append(value)
                continue
            pt = float(t["distribution"].get(option, 0.0))
            pp = float(p["distribution"].get(option, 0.0))
            tested.append((field, value, pt - pp, metrics.two_proportion_p_value(pt, n_t, pp, n_p)))

    rejected = metrics.benjamini_hochberg([t[3] for t in tested])
    directions = defaultdict(dict)
    for (field, value, gap, _), rej in zip(tested, rejected):
        directions[field][value] = ("+" if gap > 0 else "-") if rej else "0"
    return dict(directions), small


def score_scenarios(runs: list[dict], noise: Optional[float], n_eff_ratio: float,
                    warnings: list[str], params: Optional[dict] = None) -> list[dict]:
    params = baselines.load_equation_params() if params is None else params
    by_id = defaultdict(list)
    for r in runs:
        if r.get("run_type") == "scenario":
            by_id[r["scenario_id"]].append(r)

    out = []
    for sid in sorted(by_id):
        sruns = by_id[sid]
        options = list(sruns[0]["options"])
        primary = _primary_model(sruns)
        prim = [r for r in sruns if _snapshot(r) == primary]
        treat = [d for r in prim if (d := _arm_dist(r, "treatment", options))]
        plac = [d for r in prim if (d := _arm_dist(r, "placebo", options))]
        if not treat or not plac:
            warnings.append(f"Scenario '{sid}' lacks a treatment or placebo arm; not scored.")
            continue
        t, p = _mean_dist(treat, options), _mean_dist(plac, options)
        effect = {o: t[o] - p[o] for o in options}
        effect_tvd = metrics.tvd(t, p, options)

        cfg = params.get(sid) or {}
        option = cfg.get("target_option") if cfg.get("target_option") in options else \
            max(options, key=lambda o: abs(effect[o]))
        saturated = metrics.is_saturated(p[option])
        n = float(prim[0].get("n_personas") or 0) * n_eff_ratio
        mdd = metrics.minimum_detectable_difference(p[option], n, n)
        measurable = (noise is not None and effect_tvd > noise and not saturated
                      and abs(effect[option]) >= mdd)

        directions, small = _subgroups((prim[0]["arms"] or {}).get("treatment"),
                                       (prim[0]["arms"] or {}).get("placebo"), option)

        models_agree = None
        snaps = sorted({_snapshot(r) for r in sruns})
        if len(snaps) > 1:
            signs = set()
            for snap in snaps:
                rs = [r for r in sruns if _snapshot(r) == snap]
                tt = [d for r in rs if (d := _arm_dist(r, "treatment", options))]
                pp = [d for r in rs if (d := _arm_dist(r, "placebo", options))]
                if tt and pp:
                    signs.add(np.sign(_mean_dist(tt, options)[option] - _mean_dist(pp, options)[option]))
            models_agree = len(signs) == 1

        eq = baselines.scenario_equation_effect(
            sid, p, options, prim[0].get("metadata", {}).get("n_rounds") or 1, params)
        if eq is None:
            warnings.append(f"Scenario '{sid}' has no registered equation-baseline parameters.")

        out.append({
            "scenario_id": sid,
            "effect_vs_placebo": _rdist(effect),
            "effect_tvd": _r(effect_tvd),
            "measurable": bool(measurable),
            "saturated": bool(saturated),
            "option_of_interest": option,
            "minimum_detectable_difference": _r(mdd),
            "equation_baseline_effect": _rdist(eq) if eq else None,
            "subgroup_direction": directions,
            "small_cells": small,
            "models_agree": models_agree,
        })
    return out


# --- top level --------------------------------------------------------------------

def build(runs: list[dict], frame: pd.DataFrame, fixtures: bool = False,
          params: Optional[dict] = None) -> dict:
    warnings: list[str] = []
    if fixtures:
        warnings.append("Built from fixture data: every number here is fabricated for development.")

    hashes = {r.get("metadata", {}).get("persona_set_hash") for r in runs}
    if len(hashes) > 1:
        warnings.append("Runs come from different persona sets; they are not comparable.")
    persona_hash = sorted(h for h in hashes if h)[0] if any(hashes) else None

    noise = noise_floor(runs)
    if noise is None:
        warnings.append("Noise floor unknown: no configuration was run with two seeds, "
                        "so no scenario effect is reported as measurable.")
    if len({_snapshot(r) for r in runs}) < 2:
        warnings.append("Only one model was run. Results may reflect that model's prior "
                        "rather than the population (rule 14: at least two models).")

    n_eff_ratio = metrics.kish_n_eff(frame["weight"]) / len(frame) if len(frame) else 1.0
    probes = score_probes(runs, frame, warnings)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "persona_set_hash": persona_hash,
        "noise_floor_tvd": _r(noise),
        "probes": probes,
        "rank_agreement": rank_agreement(probes, warnings),
        "scenarios": score_scenarios(runs, noise, n_eff_ratio, warnings, params),
        "warnings": warnings,
    }
    report["warnings"] += [
        "Scenario results are effects (treatment minus placebo), never population shares.",
        "Personas query the model per archetype cell, which flattens variation inside a cell.",
        "The real data is WVS Wave 7 Turkey (fieldwork 2018); drift since then is not measured.",
        "The ML baseline is trained on real answers to the same item; the engine never sees them.",
    ]
    return report


def main():
    ap = argparse.ArgumentParser(description="Build reports/comparison.json")
    ap.add_argument("--results-dir", help="directory of results/*.json (default: results/ or fixtures)")
    ap.add_argument("--personas")
    ap.add_argument("--heldout")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--fixtures", action="store_true", help="force fixture inputs")
    args = ap.parse_args()

    results_dir = Path(args.results_dir) if args.results_dir else Path("results")
    result_files = sorted(results_dir.glob("*.json")) if results_dir.is_dir() else []
    use_fixtures = args.fixtures or not result_files
    if use_fixtures:
        result_files = list(RESULTS_FIXTURES)

    personas = Path(args.personas) if args.personas else (
        REAL_PERSONAS if REAL_PERSONAS.exists() and not use_fixtures else real.PERSONAS_FIXTURE)
    heldout = Path(args.heldout) if args.heldout else (
        REAL_HELDOUT if REAL_HELDOUT.exists() and not use_fixtures else real.HELDOUT_FIXTURE)

    report = build(load_runs(result_files), real.load(personas, heldout), fixtures=use_fixtures)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"probes: {len(report['probes'])}  scenarios: {len(report['scenarios'])}  "
          f"noise floor: {report['noise_floor_tvd']}  ->  {out}")


if __name__ == "__main__":
    main()
