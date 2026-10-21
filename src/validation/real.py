"""Real (held-out) answer distributions, weighted by Track A's persona weights.

This is the only place in the repo that joins ``heldout.csv`` back onto
``personas.csv`` (methodology invariant: only Track C reads held-out data).
"""

from __future__ import annotations

from typing import Optional, Sequence

import pandas as pd

from src.common import paths, schema, stats
from src.common.labels import answer_label

PERSONAS_FIXTURE = paths.PERSONAS_FIXTURE
HELDOUT_FIXTURE = paths.HELDOUT_FIXTURE

# Held-out items without a natural option order (Wasserstein doesn't apply).
# Every current held-out item is ordinal.
NOMINAL_ITEMS: tuple = ()


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
    return series.map(answer_label)


def distribution(frame: pd.DataFrame, item: str, options: Sequence[str]) -> dict:
    """Weighted share of each option among respondents who answered ``item``.

    Answers outside ``options`` are dropped (and counted in ``coverage``).
    """
    return distribution_stats(frame, item, options)["distribution"]


def distribution_stats(frame: pd.DataFrame, item: str, options: Sequence[str]) -> dict:
    """Distribution plus n, Kish n_eff and option coverage for ``item``."""
    labels = answer_labels(frame[item])
    answered = labels.notna()
    in_options = labels.isin(list(options))
    w = frame["weight"].astype(float)
    return {
        "distribution": stats.weighted_share(labels, w, options),
        "n": int(in_options.sum()),
        "n_eff": stats.kish_n_eff(w[in_options]),
        "coverage": float(in_options.sum() / answered.sum()) if answered.sum() else 0.0,
    }


def role(item: str) -> Optional[str]:
    """"fit" or "test" from schema.HELDOUT_ROLE (None for unknown items)."""
    return schema.HELDOUT_ROLE.get(item)
