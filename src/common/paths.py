"""Repository paths shared by every track. Absolute, so commands work from any directory."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DATA_RAW = REPO / "data" / "raw"
PROCESSED = REPO / "data" / "processed"
PERSONAS_CSV = PROCESSED / "personas.csv"
HELDOUT_CSV = PROCESSED / "heldout.csv"

RESULTS_DIR = REPO / "results"
COMPARISON_JSON = REPO / "reports" / "comparison.json"
SCENARIOS_DIR = REPO / "src" / "simulation" / "scenarios"

PERSONAS_FIXTURE = REPO / "src" / "personas" / "fixtures" / "personas.sample.csv"
HELDOUT_FIXTURE = REPO / "src" / "personas" / "fixtures" / "heldout.sample.csv"
RESULTS_FIXTURES = (
    REPO / "src" / "simulation" / "fixtures" / "results.sample.json",
    REPO / "src" / "simulation" / "fixtures" / "results.probe.sample.json",
)
COMPARISON_FIXTURE = REPO / "src" / "validation" / "fixtures" / "comparison.sample.json"
