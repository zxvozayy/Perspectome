"""Secrets from the environment, else from the repo's git-ignored .env file. Never print them."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from src.common import paths

ENV_FILE = paths.REPO / ".env"


def get(name: str, env_file: Path = ENV_FILE) -> Optional[str]:
    value = os.environ.get(name)
    if not value and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().removeprefix("export ").strip()
            if line.startswith(f"{name}="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                break
    return value or None
