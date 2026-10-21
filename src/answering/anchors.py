"""Anchor items (anchors.yaml): WVS-7 answers that may reach the simulation.

Anchors are neither held-out items nor conditioning fields, so the answering
layer may learn from them and quote a cell's typical answers in a prompt. When
a probe targets a held-out item, its near-duplicate anchors (``exclude``) are
dropped first.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

from src.personas.sources import wvs

ANCHORS_YAML = Path(__file__).with_name("anchors.yaml")


@lru_cache(maxsize=1)
def _spec() -> dict:
    with open(ANCHORS_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def items(target: str | None = None) -> list[dict]:
    """Anchor items usable when ``target`` (a held-out field, or None) is the question."""
    banned = set(_spec()["exclude"].get(target, ()))
    return [it for it in _spec()["items"] if it["code"] not in banned]


def from_raw(raw: pd.DataFrame, persona_ids) -> pd.DataFrame:
    """The anchors' answers per respondent (raw codes; missing or off-scale -> empty)."""
    out = pd.DataFrame({"persona_id": list(persona_ids)})
    for it in items():
        valid = set(it["options"])
        column = raw[it["code"]] if it["code"] in raw.columns else pd.Series([None] * len(raw))
        out[it["name"]] = column.map(lambda v: v if (v := wvs.keep_scale(v)) in valid else None).astype("Int64").values
    return out
