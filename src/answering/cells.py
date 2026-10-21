"""Question-specific cells: which persona fields matter for this question?

For a new question: the anchor items worded most like it (qembed), their field
importances (importance) weighted by similarity, and the top fields define the
cells. A cell smaller than MIN_CELL_N falls back to fewer fields, dropping the
weakest first. The prompt then carries the cell's most common answers to those
anchors among real respondents, so the model sees what people like the persona
said on related questions, never on the question itself.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.answering import anchors, qembed
from src.common.labels import answer_label
from src.common.schema import MIN_CELL_N

N_ANCHORS = 3
N_FIELDS = 3
MIN_SIMILARITY = 0.1


def choose(question: str, importance: pd.DataFrame, target: str | None = None,
           k: int = N_ANCHORS, n_fields: int = N_FIELDS) -> dict:
    """Fields for this question's cells and the anchors they were learned from.

    Anchors below MIN_SIMILARITY share too few words with the question to say
    anything; with none left, fields are ranked by importance averaged over
    every anchor, and the prompt gets no anchor answers.
    """
    usable = [it for it in anchors.items(target) if it["name"] in importance.index]
    near = [(it, s) for it, s in qembed.nearest(question, usable, k) if s >= MIN_SIMILARITY]
    if near:
        sims = np.array([s for _, s in near])
        score = sum(w * importance.loc[it["name"]] for (it, _), w in zip(near, sims / sims.sum()))
    else:
        score = importance.loc[[it["name"] for it in usable]].mean()
    fields = list(score.sort_values(ascending=False, kind="stable").index[:n_fields])
    return {"fields": fields, "anchors": [it["name"] for it, _ in near],
            "similarity": [round(s, 3) for _, s in near], "field_score": {f: round(float(score[f]), 3) for f in fields}}


def _key(frame: pd.DataFrame, fields: list[str]) -> pd.Series:
    if not fields:
        return pd.Series("all", index=frame.index)
    return frame[fields].apply(lambda c: c.map(answer_label)).fillna("unknown").agg("|".join, axis=1)


def assign(personas: pd.DataFrame, fields: list[str], min_n: int = MIN_CELL_N) -> tuple[pd.Series, dict]:
    """cell_id per persona and each cell's defining fields.

    Personas first get a cell on every field; those whose cell has fewer than
    ``min_n`` members move to a cell on one field fewer, down to a single
    "all" cell, so every cell holds at least ``min_n`` personas (except "all").
    """
    cell = pd.Series(None, index=personas.index, dtype=object)
    reps = {}
    for depth in range(len(fields), -1, -1):
        todo = personas[cell.isna()]
        key = _key(todo, fields[:depth])
        big = key.map(key.value_counts()) >= min_n if depth else pd.Series(True, index=key.index)
        cell[key.index[big]] = key[big]
        for cell_id, members in todo[big].groupby(key[big]):
            first = members.iloc[0]
            reps[cell_id] = {f: (first[f] if pd.notna(first[f]) else None) for f in fields[:depth]}
    return cell, reps


def answer_text(options: dict, code: int) -> str:
    """An option's label; on a numbered scale, the number with the scale's end labels."""
    if not any(str(v).isdigit() for v in options.values()):
        return str(options[code])
    lo, hi = min(options), max(options)
    return f"{code} on a scale from {lo} ({options[lo]}) to {hi} ({options[hi]})"


def context(rep: dict, core: pd.DataFrame, names: list[str], min_n: int = MIN_CELL_N) -> str:
    """The cell's most common answer to each anchor in ``names``, among real respondents.

    ``core`` is the real core joined with its anchor answers. Respondents match
    the cell on its fields; with fewer than ``min_n`` matches the weakest field is
    dropped. Empty string when there is nothing to say.
    """
    fields = [f for f, v in rep.items() if v is not None]
    while True:
        match = np.ones(len(core), dtype=bool)
        for f in fields:
            match &= (core[f].map(answer_label) == answer_label(rep[f])).to_numpy()
        if match.sum() >= min_n or not fields:
            break
        fields.pop()
    group, items = core[match], {it["name"]: it for it in anchors.items()}
    lines = []
    for name in names:
        shares = group.groupby(name)["weight"].sum()
        if shares.empty:
            continue
        top = shares.idxmax()
        lines.append(f"- {items[name]['title']}: {answer_text(items[name]['options'], int(top))} "
                     f"({shares[top] / shares.sum():.0%})")
    if not lines:
        return ""
    return "In a national survey, the most common answers of people like you to related questions were:\n" + "\n".join(lines)
