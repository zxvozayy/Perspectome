"""Synthetic personas from the real core: a small discrete Bayesian network.

Every conditioning field is drawn given its parents, in an order where the
parents come first, so combinations follow the real respondents' joint
structure instead of being drawn independently. Conditional tables are
fitted on the weighted core with light Dirichlet smoothing (``alpha``), so a
combination nobody in the core had keeps a small, non-zero chance instead of
being impossible. Rows that break a hard rule (rules.yaml) are redrawn.

The DAG and alpha were chosen by measuring soft-rule shares (rules.yaml)
against the real core (2026-10-21, 20,000 draws): with employment depending on
age and sex only and alpha 0.5, married students came out 0.87% vs 0.04% real;
with marital status as a third parent and alpha 0.05, 0.07%.

    from src.personas import synth
    frame = synth.synthesize(core, n=20000, seed=0)
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from src.common import schema
from src.personas import rules

EDU3 = ("low", "mid", "high")

# child -> parents. Roots first; every parent appears before its children.
DAG = {
    "age_band": (),
    "gender": (),
    "region": (),
    "education_level": ("age_band", "gender"),
    "edu3": ("education_level", "age_band"),
    "settlement_type": ("region",),
    "marital_status": ("age_band", "gender"),
    "employment_status": ("age_band", "gender", "marital_status"),
    "income_decile": ("education_level", "employment_status"),
    "religiosity_band": ("age_band", "education_level"),
    "political_leaning_band": ("religiosity_band", "region"),
}
FIELDS = tuple(DAG)
assert set(FIELDS) - {"edu3"} == set(schema.CATEGORIES)


def categories(field: str) -> tuple:
    return EDU3 if field == "edu3" else schema.CATEGORIES[field]


def _norm(values: pd.Series) -> pd.Series:
    """Compare as strings so 4, 4.0 and "4" are the same category."""
    return values.map(lambda v: None if pd.isna(v) else str(int(v)) if isinstance(v, float) else str(v))


def fit(core: pd.DataFrame, weights, alpha: float = 0.05) -> dict:
    """Conditional probability tables {field: {parent values: probabilities}}."""
    w = np.asarray(weights, dtype=float)
    cols = {f: _norm(core[f]) for f in FIELDS}
    model = {}
    for child, parents in DAG.items():
        cats = [str(c) for c in categories(child)]
        observed = cols[child].notna().to_numpy().copy()
        for p in parents:
            observed &= cols[p].notna().to_numpy()
        table = {}
        for combo in product(*[[str(c) for c in categories(p)] for p in parents]):
            rows = observed.copy()
            for p, value in zip(parents, combo):
                rows &= (cols[p] == value).to_numpy()
            counts = np.array([w[rows & (cols[child] == c).to_numpy()].sum() for c in cats])
            table[combo] = (counts + alpha) / (counts.sum() + alpha * len(cats))
        model[child] = table
    return model


def sample(model: dict, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Ancestral sampling of ``n`` rows (values as strings)."""
    out = pd.DataFrame(index=range(n))
    for child, parents in DAG.items():
        cats = np.array([str(c) for c in categories(child)], dtype=object)
        values = np.empty(n, dtype=object)
        keys = list(zip(*[out[p] for p in parents])) if parents else [()] * n
        for combo in sorted(set(keys)):  # fixed order: same seed, same people
            idx = np.array([i for i, k in enumerate(keys) if k == combo])
            values[idx] = rng.choice(cats, size=len(idx), p=model[child][combo])
        out[child] = values
    return out


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    """Back to schema types: income_decile as an integer, the rest as text."""
    frame = frame.copy()
    frame["income_decile"] = frame["income_decile"].astype(int)
    return frame


def synthesize(core: pd.DataFrame, n: int, seed: int = 0, weights=None, max_rounds: int = 20) -> pd.DataFrame:
    """``n`` synthetic personas with the core's joint structure and no hard-rule violation.

    ``core`` needs every DAG field (``edu3`` included); ``weights`` default to
    ``core["weight"]``. Returns persona_id, cell_id, the conditioning fields and edu3.
    """
    rng = np.random.default_rng(seed)
    model = fit(core, core["weight"] if weights is None else weights)
    frame = _typed(sample(model, n, rng))
    hard = [r for r in rules.load_rules() if r.kind == "hard"]
    for _ in range(max_rounds):
        frame["cell_id"] = frame[list(schema.CELL_FIELDS)].agg("|".join, axis=1)
        frame["weight"] = 1.0
        bad = sorted(set().union(*rules.violations(frame, hard).values())) if hard else []
        if not bad:
            break
        frame.loc[bad, list(FIELDS)] = _typed(sample(model, len(bad), rng)).set_index(pd.Index(bad))
    else:
        raise RuntimeError("could not draw personas free of hard-rule violations")
    width = len(str(n))
    frame.insert(0, "persona_id", [f"s{i:0{width}d}" for i in range(1, n + 1)])
    return frame.drop(columns="weight")
