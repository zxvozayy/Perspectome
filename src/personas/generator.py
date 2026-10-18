"""Post-stratified persona generator (issue #10).

Takes the ingested WVS-7 Turkey respondents and reweights them to the Turkey
population margins (margins.py) by raking / iterative proportional fitting, so
the weighted persona set matches the real age / gender / region / education
distribution. Each respondent becomes a persona carrying a post-stratification
`weight` and its archetype `cell_id`; the held-out attitudes stay in a separate
file. The persona set is deterministic (no sampling) -> reproducible hash.

Raking calibrates four marginals: age_band, gender, region, edu3. edu3 (a
coarse ISCED grouping) is used only for calibration, never written out.

    from src.personas import generator
    summary = generator.generate(seed=0)   # writes data/processed/*.csv
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.personas import ingest, margins as margins_mod, wvs

log = logging.getLogger(__name__)

RAKING_DIMS = ("age_band", "gender", "region", "edu3")
PROCESSED_DIR = Path("data/processed")

# personas.csv column order (contract): weight sits after cell_id.
GEN_PERSONA_COLUMNS = [
    "persona_id", "cell_id", "weight", "age_band", "gender", "education_level",
    "region", "settlement_type", "marital_status", "employment_status", "income_decile",
]


def _raking_frame(personas: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Raking variables per persona: age_band/gender/region (+ edu3 from raw ISCED)."""
    frame = personas[["persona_id", "age_band", "gender", "region"]].copy()
    frame["edu3"] = raw[wvs.SRC["education"]].map(wvs.edu3_from_isced).values
    return frame


def rake(frame: pd.DataFrame, targets: dict, dims=RAKING_DIMS,
         max_iter: int = 50, tol: float = 1e-6) -> pd.Series:
    """Iterative proportional fitting -> post-stratification weights.

    Weights are computed on rows complete in every raking dimension and
    normalized to sum to that complete-case count (mean weight ~ 1). Rows
    missing any raking variable keep weight 1.0 (warned, never dropped).
    """
    complete = frame.dropna(subset=list(dims))
    n = len(complete)
    w = pd.Series(1.0, index=complete.index)

    for _ in range(max_iter):
        max_delta = 0.0
        for dim in dims:
            cats = complete[dim]
            wsum = w.groupby(cats).sum()
            for cat, target in targets[dim].items():
                current = wsum.get(cat, 0.0)
                if current > 0:
                    factor = (target * n) / current
                    w.loc[cats == cat] *= factor
                    max_delta = max(max_delta, abs(factor - 1.0))
        if max_delta < tol:
            break

    w *= n / w.sum()  # renormalize: mean weight = 1

    weights = pd.Series(1.0, index=frame.index)
    weights.loc[w.index] = w
    n_incomplete = len(frame) - n
    if n_incomplete:
        log.warning("%d persona(s) missing a raking variable -> weight 1.0 (kept)",
                    n_incomplete)
    return weights


def marginal_fit(frame: pd.DataFrame, weights: pd.Series, targets: dict,
                 dims=RAKING_DIMS) -> pd.DataFrame:
    """Calibration error: weighted share vs target per category."""
    complete = frame.dropna(subset=list(dims))
    w = weights.loc[complete.index]
    rows = []
    for dim in dims:
        wsum = w.groupby(complete[dim]).sum()
        total = wsum.sum()
        for cat, target in targets[dim].items():
            got = wsum.get(cat, 0.0) / total
            rows.append({"dim": dim, "category": cat, "target": target,
                         "weighted": got, "abs_error": abs(got - target)})
    return pd.DataFrame(rows)


def persona_set_hash(path) -> str:
    """SHA-256 of a file's bytes (the frozen persona_set_hash Track B records)."""
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def generate(turkey_csv="data/raw/wvs7_turkey.csv", out_dir=PROCESSED_DIR,
             seed: int = 0) -> dict:
    """Full pipeline: ingest -> rake -> write frozen personas.csv / heldout.csv.

    Deterministic: no sampling, so the same raw file + seed yield an identical
    persona_set_hash. ``seed`` is recorded for lineage and reserved for an
    optional future resample step.
    """
    np.random.seed(seed)
    raw = ingest.recode_missing(ingest.load_raw(turkey_csv))
    personas, heldout = ingest.to_personas_and_heldout(raw)

    frame = _raking_frame(personas, raw)
    targets = margins_mod.target_margins()
    weights = rake(frame, targets)

    personas = personas.copy()
    personas["weight"] = weights.round(4).values
    personas = personas.reindex(columns=GEN_PERSONA_COLUMNS)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    personas_path = out_dir / "personas.csv"
    heldout_path = out_dir / "heldout.csv"
    personas.to_csv(personas_path, index=False)
    heldout.to_csv(heldout_path, index=False)

    fit = marginal_fit(frame, weights, targets)
    return {
        "n_personas": len(personas),
        "personas_path": str(personas_path),
        "heldout_path": str(heldout_path),
        "persona_set_hash": persona_set_hash(personas_path),
        "seed": seed,
        "max_calibration_error": float(fit["abs_error"].max()),
        "fit": fit,
    }


def main():
    """Documented, reproducible generation command (issue #14).

        python -m src.personas.generator            # default seed 0
        python -m src.personas.generator --seed 0
    """
    ap = argparse.ArgumentParser(description="Generate the frozen persona set.")
    ap.add_argument("--turkey-csv", default="data/raw/wvs7_turkey.csv")
    ap.add_argument("--out-dir", default=str(PROCESSED_DIR))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    s = generate(args.turkey_csv, args.out_dir, args.seed)
    print(f"n_personas        : {s['n_personas']}")
    print(f"seed              : {s['seed']}")
    print(f"max_calib_error   : {s['max_calibration_error']*100:.4f} pp")
    print(f"personas          : {s['personas_path']}")
    print(f"heldout           : {s['heldout_path']}")
    print(f"persona_set_hash  : {s['persona_set_hash']}")
    print("Track B pins this persona_set_hash on every run; regenerating is a PR.")


if __name__ == "__main__":
    main()
