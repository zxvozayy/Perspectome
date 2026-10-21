"""Load Track B's results/*.json and Track C's comparison.json.

Pure consumer: nothing here imports pipeline code. Real files are picked up
from `results/` and `reports/comparison.json` at the repo root (or from the
PERSPECTOME_RESULTS_DIR / PERSPECTOME_COMPARISON environment variables). With
no real runs the bundle is empty: the site never shows fabricated numbers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from src.common import paths


@dataclass
class Bundle:
    results: dict[str, dict] = field(default_factory=dict)  # run_id -> results.json
    comparison: dict | None = None

    def runs(self, run_type: str) -> list[dict]:
        return [r for r in self.results.values() if r.get("run_type") == run_type]

    def scored(self, scenario_id: str) -> dict | None:
        """Track C's entry for a scenario, or None if it hasn't scored it."""
        for s in (self.comparison or {}).get("scenarios", []):
            if s.get("scenario_id") == scenario_id:
                return s
        return None

    @property
    def warnings(self) -> list[str]:
        return list((self.comparison or {}).get("warnings", []))


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load(results_dir: Path | None = None, comparison_path: Path | None = None) -> Bundle:
    results_dir = results_dir or Path(os.environ.get("PERSPECTOME_RESULTS_DIR", paths.RESULTS_DIR))
    comparison_path = comparison_path or Path(
        os.environ.get("PERSPECTOME_COMPARISON", paths.COMPARISON_JSON)
    )

    bundle = Bundle()
    for f in sorted(results_dir.glob("*.json")) if results_dir.is_dir() else []:
        run = _read(f)
        if run and "run_id" in run and "arms" in run:
            bundle.results[run["run_id"]] = run
    if comparison_path.is_file():
        bundle.comparison = _read(comparison_path)
    return bundle
