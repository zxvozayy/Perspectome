"""End-to-end demo: personas -> simulation -> validation report -> dashboard.

    python -m src.demo            # mock model, no API key, no cost
    python -m src.ui.server       # then open http://localhost:8501

Uses Track A's real persona files if they exist under data/processed/,
otherwise the fabricated fixtures. Every scenario and probe runs at two seeds
so the noise floor is measured, then Track C's report is written to
reports/comparison.json, where Track D's site picks it up.
"""

from __future__ import annotations

import contextlib
import json
import io
from pathlib import Path

from src.simulation import runner
from src.validation import real, report

SCENARIOS = Path("src/simulation/scenarios")
RESULTS = Path("results")
REPORT = Path("reports/comparison.json")
SEEDS = (1, 2)


def main():
    personas = Path("data/processed/personas.csv")
    heldout = Path("data/processed/heldout.csv")
    fixtures = not (personas.exists() and heldout.exists())
    if fixtures:
        personas, heldout = real.PERSONAS_FIXTURE, real.HELDOUT_FIXTURE

    RESULTS.mkdir(exist_ok=True)
    for old in RESULTS.glob("*.json"):
        old.unlink()
    files = sorted(SCENARIOS.glob("*.yaml"))
    for path in files:
        for seed in SEEDS:
            with contextlib.redirect_stdout(io.StringIO()):
                runner.run_simulation(personas, path, output_dir=RESULTS, seed=seed)

    rep = report.build(report.load_runs(sorted(RESULTS.glob("*.json"))),
                       real.load(personas, heldout), fixtures=fixtures)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"personas : {personas} ({'fixtures' if fixtures else 'real'})")
    print(f"runs     : {len(files)} scenario/probe files x {len(SEEDS)} seeds -> {RESULTS}/")
    print(f"report   : {REPORT}  (noise floor {rep['noise_floor_tvd']}, "
          f"{len(rep['probes'])} probe, {len(rep['scenarios'])} scenarios)")
    for sc in rep["scenarios"]:
        print(f"  {sc['scenario_id']:24} effect TVD {sc['effect_tvd']}  "
              f"measurable={sc['measurable']}  MDD={sc['minimum_detectable_difference']}")
    print("next     : python -m src.ui.server  ->  http://localhost:8501")


if __name__ == "__main__":
    main()
