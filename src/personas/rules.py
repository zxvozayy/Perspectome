"""Consistency rules for personas (rules.yaml): which rows break which rule.

Real respondents are never dropped (warn only); the synthesizer resamples rows
that break a hard rule; Track C compares soft-rule shares with the real ones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from src.common import schema

log = logging.getLogger(__name__)

RULES_FILE = Path(__file__).with_name("rules.yaml")


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    when: str
    rationale: str
    source: str
    real_share: Optional[float] = None


def load_rules(path=RULES_FILE) -> list[Rule]:
    with open(path, encoding="utf-8") as f:
        rules = [Rule(**r) for r in yaml.safe_load(f)]
    bad = [r.id for r in rules if r.kind not in ("hard", "soft")]
    if bad:
        raise ValueError(f"rules with unknown kind: {bad}")
    return rules


def _frame(personas: pd.DataFrame) -> pd.DataFrame:
    """Personas plus the helper columns rule queries may use."""
    out = personas.copy()
    cells = out[list(schema.CELL_FIELDS)]
    out["expected_cell_id"] = cells.astype("string").fillna("").agg("|".join, axis=1).where(cells.notna().all(axis=1))
    return out


def violations(personas: pd.DataFrame, rules: Optional[list[Rule]] = None) -> dict[str, pd.Index]:
    """{rule id: index of the rows that break it} for every rule with at least one row.

    Rules whose columns are absent from ``personas`` are skipped.
    """
    rules = load_rules() if rules is None else rules
    frame = _frame(personas)
    out = {}
    for rule in rules:
        try:
            hit = frame.query(rule.when, engine="python").index
        except NameError:  # a column the rule needs isn't there yet (e.g. weight before raking)
            continue
        if len(hit):
            out[rule.id] = hit
    return out


def summary(personas: pd.DataFrame, rules: Optional[list[Rule]] = None) -> pd.DataFrame:
    """One row per rule: kind, rows breaking it, their share, and the real reference share."""
    rules = load_rules() if rules is None else rules
    hits = violations(personas, rules)
    n = max(len(personas), 1)
    return pd.DataFrame([{
        "id": r.id, "kind": r.kind, "n": len(hits.get(r.id, ())),
        "share": len(hits.get(r.id, ())) / n, "real_share": r.real_share,
    } for r in rules])


def warn(personas: pd.DataFrame, rules: Optional[list[Rule]] = None) -> dict[str, pd.Index]:
    """Log every violation (real respondents: warn, never drop) and return them."""
    hits = violations(personas, rules)
    for rule_id, idx in hits.items():
        ids = personas.loc[idx, "persona_id"].tolist() if "persona_id" in personas else list(idx)
        log.warning("rule %s: %d persona(s), e.g. %s", rule_id, len(idx), ids[:5])
    return hits
