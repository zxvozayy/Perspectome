"""Calibrate the engine on fit items, score the calibrated methods on test items (Track C).

    python -m src.validation.calibration     # fit on the probes in results/, write calibration_params.yaml

Two corrections, fitted on `fit`-role held-out items only (schema.HELDOUT_ROLE)
and applied to every probe by report.py:

- ``engine_calibrated``: a temperature per answer-scale size k, p_i^(1/T)
  renormalised. T > 1 flattens a distribution that is too sure of itself,
  T < 1 sharpens it.
- ``stacked``: w * engine_calibrated + (1 - w) * ml_baseline, w per scale size.
  The ML baseline is trained on the item's real answers, so ``stacked`` shows
  how much the engine adds to what demographics explain; it can't be used for
  a question that has no survey data.

Each parameter is the grid value with the lowest mean TVD over the fit items
of that scale size (over all fit items when a size has none). Test items never
enter: permuting their real answers leaves the parameters unchanged (test).
results.json stays raw; calibration exists only in comparison.json.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import yaml

from src.common import paths
from src.common.stats import normalize_vec
from src.validation import metrics

PARAMS = Path(__file__).with_name("calibration_params.yaml")
TEMPERATURES = tuple(float(t) for t in np.round(np.arange(0.5, 5.001, 0.1), 2))
WEIGHTS = tuple(float(w) for w in np.round(np.arange(0.0, 1.001, 0.05), 2))


def temper(dist: dict, options: Sequence[str], t: float) -> dict:
    p = np.clip([float(dist.get(o, 0.0)) for o in options], 1e-12, None) ** (1.0 / t)
    return dict(zip(options, normalize_vec(p)))


def blend(a: dict, b: dict, options: Sequence[str], w: float) -> dict:
    return {o: w * a[o] + (1 - w) * b[o] for o in options}


def calibrate(engine: dict, ml: dict, options: Sequence[str], cls: dict) -> tuple[dict, dict]:
    """(engine_calibrated, stacked) distributions for one probe."""
    cal = temper(engine, options, cls["temperature"])
    return cal, blend(cal, ml, options, cls["stack_weight"])


def _mean_tvd(probes: list[dict], predict) -> float:
    return float(np.mean([metrics.tvd(predict(p), p["real"], p["options"]) for p in probes]))


def _engine(p):
    return p["methods"]["engine"]["distribution"]


def _fit_class(group: list[dict]) -> dict:
    # ties: the value closest to "no correction" (T = 1, w = 1)
    t = min(TEMPERATURES, key=lambda t: (_mean_tvd(group, lambda p: temper(_engine(p), p["options"], t)), abs(t - 1)))
    w = min(WEIGHTS, key=lambda w: (_mean_tvd(group, lambda p: blend(
        temper(_engine(p), p["options"], t), p["methods"]["ml_baseline"]["distribution"], p["options"], w)), -w))
    return {"temperature": t, "stack_weight": w, "fitted_on": sorted(p["item"] for p in group)}


def fit(probes: list[dict], model_snapshot: str) -> dict:
    """Parameters from the fit-role probes (report.score_probes output) of one model."""
    usable = [p for p in probes if p["role"] == "fit" and "engine" in p["methods"]]
    if not usable:
        raise ValueError("No fit-role probe with an engine result; nothing to calibrate on.")
    sizes = sorted({len(p["options"]) for p in usable})
    return {
        "model_snapshot": model_snapshot,
        "default": _fit_class(usable),
        "by_scale_size": {k: _fit_class([p for p in usable if len(p["options"]) == k]) for k in sizes},
    }


def params_for(params: dict, options: Sequence[str]) -> dict:
    return params["by_scale_size"].get(len(options)) or params["default"]


def load(path=PARAMS) -> Optional[dict]:
    path = Path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: Optional[list] = None):
    from src.validation import real, report  # report imports this module

    ap = argparse.ArgumentParser(description="Fit calibration on fit-role probes.")
    ap.add_argument("--results-dir", default=str(paths.RESULTS_DIR))
    ap.add_argument("--personas", default=str(paths.PERSONAS_CSV))
    ap.add_argument("--heldout", default=str(paths.HELDOUT_CSV))
    ap.add_argument("--out", default=str(PARAMS))
    args = ap.parse_args(argv)

    runs = report.load_runs(sorted(Path(args.results_dir).glob("*.json")))
    probe_runs = [r for r in runs if r.get("run_type") == "probe"]
    if not probe_runs:
        raise SystemExit(f"No probe runs in {args.results_dir}.")
    snapshot = report._primary_model(probe_runs)
    probes = report.score_probes(probe_runs, real.load(args.personas, args.heldout), [])
    params = fit(probes, snapshot)
    params["fitted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    params["persona_set_hash"] = probe_runs[0].get("metadata", {}).get("persona_set_hash")
    Path(args.out).write_text("# Written by python -m src.validation.calibration; fit-role items only.\n"
                              + yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
    for k, cls in params["by_scale_size"].items():
        print(f"{k}-option items: T {cls['temperature']}, stack weight {cls['stack_weight']} "
              f"(fit on {', '.join(cls['fitted_on'])})")
    print(f"-> {args.out}")
    return params


if __name__ == "__main__":
    main()
