"""Consistency rules for personas (rules.yaml): which rows break which rule.

Real respondents are never dropped (warn only); the synthesizer resamples rows
that break a hard rule; Track C compares soft-rule shares with the real ones.
``check_text`` holds a persona's free text (a simulated comment) to the same
fields: a comment that contradicts its persona is dropped.
"""

from __future__ import annotations

import logging
import re
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


# --- free text vs the persona's own fields -------------------------------------------

_AGE = re.compile(r"\b(\d{2})\s*yaşında", re.IGNORECASE)
# (pattern in the text, field, values that are consistent with it)
TEXT_RULES = (
    (re.compile(r"\bemekliyim\b|\bemekli oldum\b|\bemekli olduğum\b|\bemekli maaşım", re.IGNORECASE),
     "employment_status", {"retired"}),
    (re.compile(r"\böğrenciyim\b|\bdersim(e|den)?\b|\bfinallerim\b", re.IGNORECASE), "employment_status", {"student"}),
    (re.compile(r"\bişsizim\b|\biş arıyorum\b", re.IGNORECASE), "employment_status", {"unemployed"}),
    (re.compile(r"\b(eşim|karım|kocam)(ın|in|la|le|a|e|ı|i)?\b", re.IGNORECASE), "marital_status", {"married"}),
    (re.compile(r"\bbekarım\b|\bbekârım\b", re.IGNORECASE), "marital_status", {"single", "divorced", "widowed"}),
    # "ev sahibim(iz)" is "my landlord"; "ev sahibiyim" (I own) is left alone
    (re.compile(r"\bkiradayım\b|\bkirada oturuyoruz\b|\bkirada oturuyorum\b|\bkira ödüyorum\b|\bkiracıyım\b"
                r"|\bev sahibim(iz)?\b", re.IGNORECASE), "tenure", {"tenant"}),
    (re.compile(r"\bkendi evim(de|iz)?\b|\bevimiz kendimizin\b|\bev(im)? (benim|bizim)\b", re.IGNORECASE),
     "tenure", {"owner"}),
    (re.compile(r"\bsigortasız çalış", re.IGNORECASE), "informal", {True}),
)


def check_text(text: str, persona: dict) -> list[str]:
    """Contradictions between a persona's free text and its fields (empty list = consistent)."""
    problems = []
    for pattern, field, allowed in TEXT_RULES:
        value = persona.get(field)
        if value is not None and pattern.search(text) and value not in allowed:
            problems.append(f"text implies {field} in {sorted(allowed)}, persona has {value!r}")
    for match in _AGE.finditer(text):
        years = int(match.group(1))
        band = next((b for b, lo in zip(reversed(schema.AGE_BANDS), reversed(schema.AGE_EDGES)) if years >= lo), None)
        if band and persona.get("age_band") and band != persona["age_band"]:
            problems.append(f"text says {years} years old, persona is {persona['age_band']}")
    return problems
