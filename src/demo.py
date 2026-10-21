"""End-to-end demo: personas -> simulation -> validation report -> dashboard.

    python -m src.demo            # fixtures, mock model, no API key, no cost
    python -m src.demo --real     # Track A's real core personas under data/processed/
    python -m src.demo --synthetic  # simulate the 20,000 synthetic personas, validate on the real core
    python -m src.ui.server       # then open http://localhost:8501

Runs on the fabricated fixtures unless --real is given. Every scenario and probe runs at two seeds
so the noise floor is measured, then Track C's report is written to
reports/comparison.json, where Track D's site picks it up.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import io

import pandas as pd

from src.common import paths
from src.simulation import runner
from src.validation import real, realism, report

SCENARIOS = paths.SCENARIOS_DIR
RESULTS = paths.RESULTS_DIR
REPORT = paths.COMPARISON_JSON
SEEDS = (1, 2)


def main():
    ap = argparse.ArgumentParser(description="End-to-end demo on fixtures (default) or real personas.")
    ap.add_argument("--real", action="store_true", help="use data/processed/personas.csv and heldout.csv")
    ap.add_argument("--synthetic", action="store_true", help="simulate data/processed/personas_synthetic.csv")
    args = ap.parse_args()

    personas, heldout = real.PERSONAS_FIXTURE, real.HELDOUT_FIXTURE
    fixtures = True
    if args.real or args.synthetic:
        personas, heldout = paths.PERSONAS_CSV, paths.HELDOUT_CSV
        if not (personas.exists() and heldout.exists()):
            raise SystemExit("No real persona files under data/processed/ (pull them: python -m src.common.db pull-personas).")
        fixtures = False
    # held-out answers belong to real respondents, so validation always joins on the core
    simulated = paths.PERSONAS_SYNTHETIC_CSV if args.synthetic else personas
    if not simulated.exists():
        raise SystemExit(f"{simulated} not found (python -m src.personas.generator).")

    RESULTS.mkdir(exist_ok=True)
    for old in RESULTS.glob("*.json"):
        old.unlink()
    files = sorted(SCENARIOS.glob("*.yaml"))
    for path in files:
        for seed in SEEDS:
            with contextlib.redirect_stdout(io.StringIO()):
                runner.run_simulation(simulated, path, output_dir=RESULTS, seed=seed)

    persona_realism = None
    if args.synthetic:
        persona_realism = realism.report(pd.read_csv(simulated), pd.read_csv(personas))
    rep = report.build(report.load_runs(sorted(RESULTS.glob("*.json"))),
                       real.load(personas, heldout), fixtures=fixtures, persona_realism=persona_realism)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"personas : {simulated} ({'fixtures' if fixtures else 'synthetic' if args.synthetic else 'real core'})")
    print(f"runs     : {len(files)} scenario/probe files x {len(SEEDS)} seeds -> {RESULTS}/")
    print(f"report   : {REPORT}  (noise floor {rep['noise_floor_tvd']}, "
          f"{len(rep['probes'])} probe, {len(rep['scenarios'])} scenarios)")
    for sc in rep["scenarios"]:
        print(f"  {sc['scenario_id']:24} effect TVD {sc['effect_tvd']}  "
              f"measurable={sc['measurable']}  MDD={sc['minimum_detectable_difference']}")
    print("next     : python -m src.ui.server  ->  http://localhost:8501")


if __name__ == "__main__":
    main()
