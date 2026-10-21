"""Post-stratified persona generator (issue #10).

Takes the ingested WVS-7 Turkey respondents and reweights them to the Turkey
population margins (sources/eurostat.py) by raking / iterative proportional fitting, so
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
import sys
import logging
from pathlib import Path

import pandas as pd

from src.common import paths, schema, stats
from src.answering import anchors
from src.common.hashing import file_hash
from src.personas import attach, ingest, synth
from src.personas.sources import eurostat, lits, wvs

log = logging.getLogger(__name__)

RAKING_DIMS = ("age_band", "gender", "region", "edu3")
PROCESSED_DIR = paths.PROCESSED


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
        shares = stats.weighted_share(complete[dim], w, list(targets[dim]))
        for cat, target in targets[dim].items():
            rows.append({"dim": dim, "category": cat, "target": target,
                         "weighted": shares[cat], "abs_error": abs(shares[cat] - target)})
    return pd.DataFrame(rows)


def weight_diagnostics(weights: pd.Series, frame: pd.DataFrame) -> dict:
    """How much the post-stratification weights cost: Kish n_eff and the extremes."""
    w = weights.astype(float)
    n_eff = stats.kish_n_eff(w)
    by_age = frame.assign(w=w.values).groupby("age_band")["w"].agg(["size", "mean", "max"])
    return {
        "n_eff": n_eff,
        "max_weight": float(w.max()),
        "min_weight": float(w.min()),
        "by_age_band": {band: {"n": int(r["size"]), "mean_weight": round(float(r["mean"]), 3),
                               "max_weight": round(float(r["max"]), 3)} for band, r in by_age.iterrows()},
    }


def _joint_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Composite keys so the two joint target tables can be raked like one-way margins."""
    return pd.DataFrame({
        "region_age_sex": frame["region"] + "|" + frame["age_band"] + "|" + frame["gender"],
        "age_sex_edu": frame["age_band"] + "|" + frame["gender"] + "|" + frame["edu3"],
    }, index=frame.index)


def _joint_targets(year: int) -> dict:
    j = eurostat.joint_targets(year)
    ras, ase = j["region_age_sex"], j["age_sex_edu"]
    return {
        "region_age_sex": dict(zip(ras["region"] + "|" + ras["age_band"] + "|" + ras["gender"], ras["share"])),
        "age_sex_edu": dict(zip(ase["age_band"] + "|" + ase["gender"] + "|" + ase["edu3"], ase["share"])),
    }


def synthesize(core: pd.DataFrame, raw: pd.DataFrame, n: int, seed: int, year: int) -> tuple[pd.DataFrame, dict]:
    """``n`` synthetic personas raked to the joint targets, with every attached field."""
    core = core.assign(edu3=raw[wvs.SRC["education"]].map(wvs.edu3_from_isced).values)
    syn = synth.synthesize(core, n, seed=seed)
    joint = _joint_frame(syn)
    targets = _joint_targets(year)
    weights = rake(joint, targets, dims=tuple(targets))
    syn["weight"] = weights.round(4).values
    syn = attach.attach(syn, lits.load(), seed=seed)
    fit = marginal_fit(joint, weights, targets, dims=tuple(targets))
    columns = [*schema.PERSONA_COLUMNS, *schema.SYNTHETIC_FIELDS]
    return syn[columns], {"max_calibration_error": float(fit["abs_error"].max()),
                          "weights": weight_diagnostics(weights, syn), "assumptions": list(attach.ASSUMPTIONS)}


def generate(turkey_csv=paths.DATA_RAW / "wvs7_turkey.csv", out_dir=PROCESSED_DIR,
             seed: int = 0, synthetic: int = 20000, year: int = eurostat.DEFAULT_YEAR) -> dict:
    """ingest -> rake the real core -> (optionally) synthesize; write the frozen sets.

    personas.csv / heldout.csv are the real WVS-7 respondents (deterministic, no
    sampling); anchors.csv is their answers to the anchor items (src/answering),
    which, unlike heldout.csv, may reach the simulation. personas_synthetic.csv holds ``synthetic`` personas drawn from
    the core (seeded); ``synthetic=0`` writes the core only.
    """
    raw = ingest.recode_missing(ingest.load_raw(turkey_csv))
    personas, heldout = ingest.to_personas_and_heldout(raw)

    frame = _raking_frame(personas, raw)
    targets = eurostat.target_margins(year)
    weights = rake(frame, targets)

    personas = personas.copy()
    personas["weight"] = weights.round(4).values
    personas = personas.reindex(columns=list(schema.PERSONA_COLUMNS))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    personas_path = out_dir / paths.PERSONAS_CSV.name
    heldout_path = out_dir / paths.HELDOUT_CSV.name
    anchors_path = out_dir / paths.ANCHORS_CSV.name
    personas.to_csv(personas_path, index=False)
    heldout.to_csv(heldout_path, index=False)
    anchors.from_raw(raw, personas["persona_id"]).to_csv(anchors_path, index=False)

    fit = marginal_fit(frame, weights, targets)
    summary = {
        "n_personas": len(personas),
        "personas_path": str(personas_path),
        "heldout_path": str(heldout_path),
        "anchors_path": str(anchors_path),
        "persona_set_hash": file_hash(personas_path),
        "seed": seed,
        "targets_year": year,
        "max_calibration_error": float(fit["abs_error"].max()),
        "weights": weight_diagnostics(weights, frame),
        "fit": fit,
        "synthetic": None,
    }
    if synthetic:
        syn, info = synthesize(personas, raw, synthetic, seed, year)
        syn_path = out_dir / paths.PERSONAS_SYNTHETIC_CSV.name
        syn.to_csv(syn_path, index=False)
        summary["synthetic"] = {"n": len(syn), "path": str(syn_path), "persona_set_hash": file_hash(syn_path),
                                "core_set_hash": summary["persona_set_hash"], **info}
    return summary


def main():
    """Documented, reproducible generation command (issue #14).

        python -m src.personas.generator                  # real core + 20,000 synthetic, seed 0
        python -m src.personas.generator --synthetic 0    # real core only
    """
    ap = argparse.ArgumentParser(description="Generate the frozen persona set.")
    ap.add_argument("--turkey-csv", default=str(paths.DATA_RAW / "wvs7_turkey.csv"))
    ap.add_argument("--out-dir", default=str(PROCESSED_DIR))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--synthetic", type=int, default=20000, help="synthetic personas (0 = real core only)")
    ap.add_argument("--year", type=int, default=eurostat.DEFAULT_YEAR, help="Eurostat target year")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # TÜİK, İstanbul on a cp1252 console

    s = generate(args.turkey_csv, args.out_dir, args.seed, args.synthetic, args.year)
    print(f"n_personas        : {s['n_personas']}")
    print(f"seed              : {s['seed']}")
    print(f"max_calib_error   : {s['max_calibration_error']*100:.4f} pp")
    wd = s["weights"]
    print(f"Kish n_eff        : {wd['n_eff']:.0f} of {s['n_personas']} "
          f"(weights {wd['min_weight']:.2f}..{wd['max_weight']:.2f})")
    for band, r in wd["by_age_band"].items():
        print(f"  {band:6} n={r['n']:4}  mean weight {r['mean_weight']:.2f}  max {r['max_weight']:.2f}")
    print(f"personas          : {s['personas_path']}")
    print(f"heldout           : {s['heldout_path']}")
    print(f"anchors           : {s['anchors_path']}")
    print(f"persona_set_hash  : {s['persona_set_hash']}  (real core, targets {s['targets_year']})")
    if s["synthetic"]:
        syn = s["synthetic"]
        print(f"synthetic         : {syn['n']} -> {syn['path']}")
        print(f"  joint calib err : {syn['max_calibration_error']*100:.4f} pp; "
              f"Kish n_eff {syn['weights']['n_eff']:.0f} of {syn['n']}")
        print(f"  persona_set_hash: {syn['persona_set_hash']}")
        for line in syn["assumptions"]:
            print(f"  assumption      : {line}")
    print("Track B pins the persona_set_hash it ran on; regenerating is a PR.")


if __name__ == "__main__":
    main()
