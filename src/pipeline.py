"""Full run on real data: personas -> live model -> validation report -> site.

    python -m src.pipeline --model claude-haiku-4-5-20251001
    python -m src.pipeline --model claude-haiku-5-5            # a second model into the same results/
    python -m src.pipeline --model ... --cells auto --results-dir results/auto
    python -m src.pipeline --model ... --synthetic             # simulate the 20,000 synthetic personas
    python -m src.ui.server                                    # then open http://localhost:8501

Every scenario and probe runs at two seeds (the noise floor) on the real core
under data/processed/, and the report is written to reports/comparison.json,
which the site reads. Costs money: every run is capped by --max-calls. Runs
already in the results folder are kept and not repeated, so an interrupted
pipeline resumes and a second model adds to the first.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path

import pandas as pd

from src.common import paths
from src.simulation import runner
from src.validation import real, realism, report

SEEDS = (1, 2)


def main():
    ap = argparse.ArgumentParser(description="Live run on the real persona set, then the validation report.")
    ap.add_argument("--model", required=True, help="model snapshot, e.g. claude-haiku-4-5-20251001")
    ap.add_argument("--synthetic", action="store_true", help="simulate data/processed/personas_synthetic.csv")
    ap.add_argument("--cells", choices=("auto",), help="question-specific cells instead of age x gender x education")
    ap.add_argument("--n-repeats", type=int, default=10, help="answers sampled per cell")
    ap.add_argument("--max-calls", type=int, default=3000, help="hard call cap per run")
    ap.add_argument("--results-dir", default=str(paths.RESULTS_DIR))
    ap.add_argument("--out", default=str(paths.COMPARISON_JSON))
    args = ap.parse_args()

    personas, heldout = paths.PERSONAS_CSV, paths.HELDOUT_CSV
    simulated = paths.PERSONAS_SYNTHETIC_CSV if args.synthetic else personas
    for f in (personas, heldout, simulated):
        if not f.exists():
            raise SystemExit(f"{f} not found (python -m src.personas.generator, or pull it from the database).")

    results = Path(args.results_dir)
    results.mkdir(parents=True, exist_ok=True)
    for path in sorted(paths.SCENARIOS_DIR.glob("*.yaml")):
        for seed in SEEDS:
            if (results / f"{path.stem}__{args.model}__seed{seed}.json").exists():
                continue
            with contextlib.redirect_stdout(io.StringIO()):
                run = runner.run_simulation(simulated, path, output_dir=results, seed=seed, live=True,
                                            model_snapshot=args.model, max_calls=args.max_calls,
                                            n_repeats=args.n_repeats, cell_fields=args.cells)
            st = run["metadata"]["model_stats"]
            print(f"{path.stem:32} seed {seed}: {st['calls']} calls, {st['parse_failures']} unreadable", flush=True)

    persona_realism = realism.report(pd.read_csv(simulated), pd.read_csv(personas)) if args.synthetic else None
    rep = report.build(report.load_runs(sorted(results.glob("*.json"))), real.load(personas, heldout),
                       persona_realism=persona_realism)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report -> {out}  (noise floor {rep['noise_floor_tvd']}, {len(rep['probes'])} probes, "
          f"{len(rep['scenarios'])} scenarios)")
    print("next: python -m src.ui.server  ->  http://localhost:8501")


if __name__ == "__main__":
    main()
