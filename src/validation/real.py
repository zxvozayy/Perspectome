"""Real (held-out) answer distributions, weighted by Track A's persona weights.

This is the only place in the repo that joins ``heldout.csv`` back onto
``personas.csv`` (methodology invariant: only Track C reads held-out data).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from src.common import schema
from src.validation import metrics

PERSONAS_FIXTURE = Path("src/personas/fixtures/personas.sample.csv")
HELDOUT_FIXTURE = Path("src/personas/fixtures/heldout.sample.csv")

# Held-out items whose options have a natural order (Wasserstein applies).
# religious_identity (religious / not / atheist) is nominal.
NOMINAL_ITEMS = ("religious_identity",)


def is_ordinal(item: str) -> bool:
    return item in schema.HELDOUT_FIELDS and item not in NOMINAL_ITEMS


def load(personas_path=PERSONAS_FIXTURE, heldout_path=HELDOUT_FIXTURE) -> pd.DataFrame:
    """personas (conditioning + weight) joined with held-out answers on persona_id."""
    personas = pd.read_csv(personas_path, dtype={"persona_id": str})
    heldout = pd.read_csv(heldout_path, dtype={"persona_id": str})
    if "weight" not in personas.columns:
        personas["weight"] = 1.0
    return personas.merge(heldout, on="persona_id", how="inner", validate="one_to_one")


def answer_labels(series: pd.Series) -> pd.Series:
    """Held-out values as option labels: 7.0 -> "7", "quite_a_lot" stays."""
    def label(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        if isinstance(v, (int, np.integer)) or (isinstance(v, float) and float(v).is_integer()):
            return str(int(v))
        return str(v)
    return series.map(label)


def distribution(frame: pd.DataFrame, item: str, options: Sequence[str]) -> dict:
    """Weighted share of each option among respondents who answered ``item``.

    Answers outside ``options`` are dropped (and counted in ``coverage``).
    """
    stats = distribution_stats(frame, item, options)
    return stats["distribution"]


def distribution_stats(frame: pd.DataFrame, item: str, options: Sequence[str]) -> dict:
    """Distribution plus n, Kish n_eff and option coverage for ``item``."""
    labels = answer_labels(frame[item])
    answered = labels.notna()
    in_options = labels.isin(list(options))
    sub = frame[in_options]
    w = sub["weight"].astype(float)
    total = w.sum()
    dist = {o: float(w[labels[in_options] == o].sum() / total) if total > 0 else 0.0
            for o in options}
    return {
        "distribution": dist,
        "n": int(in_options.sum()),
        "n_eff": metrics.kish_n_eff(w),
        "coverage": float(in_options.sum() / answered.sum()) if answered.sum() else 0.0,
    }


def subgroup_distribution(frame: pd.DataFrame, item: str, options: Sequence[str],
                          field: str) -> dict:
    """{group value: {"n": int, "distribution": {...}}} for one conditioning field."""
    out = {}
    for value, group in frame.groupby(field):
        stats = distribution_stats(group, item, options)
        out[str(value)] = {"n": stats["n"], "distribution": stats["distribution"]}
    return out


def role(item: str) -> Optional[str]:
    """"fit" or "test" from schema.HELDOUT_ROLE (None for unknown items)."""
    return getattr(schema, "HELDOUT_ROLE", {}).get(item)
