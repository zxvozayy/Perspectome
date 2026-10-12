"""Past conversations, kept in a local file so they survive a page reload."""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).parent / ".cache" / "chats.json"


def load() -> list[dict]:
    try:
        chats = json.loads(PATH.read_text(encoding="utf-8"))
        return chats if isinstance(chats, list) else []
    except (OSError, ValueError):
        return []


def save(chats: list[dict]) -> None:
    clean = [
        {**c, "messages": [{k: v for k, v in m.items() if k != "fresh"} for m in c["messages"]]}
        for c in chats
    ]
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
