"""Put the repo root on sys.path so `import src.common` / `src.personas` work
regardless of where pytest is invoked from."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../src/validation/tests -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
