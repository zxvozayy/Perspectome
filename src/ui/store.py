"""Past conversations, one local file per account, so they survive a restart."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DIR = Path(__file__).parent / ".cache" / "chats"


def _path(user: str) -> Path:
    # Hash the name so no user input ever becomes part of a file path.
    return DIR / f"{hashlib.sha256(user.encode()).hexdigest()[:24]}.json"


def load(user: str) -> list[dict]:
    try:
        chats = json.loads(_path(user).read_text(encoding="utf-8"))
        return chats if isinstance(chats, list) else []
    except (OSError, ValueError):
        return []


def save(user: str, chats: list[dict]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    _path(user).write_text(json.dumps(chats, ensure_ascii=False, indent=1), encoding="utf-8")
