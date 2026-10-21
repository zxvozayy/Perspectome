"""Which persona fields predict each anchor item? Learned on the real core.

    python -m src.answering.importance      # fit (or load) and print the top fields per anchor

Per anchor: a gradient-boosted classifier on the conditioning fields, then
permutation importance on a held-back 30% of respondents (weighted log-loss
increase when one field is shuffled). Rows are normalised to sum to 1, so an
anchor's row says how much of what the fields explain each field carries.

Uses only conditioning fields and anchor answers; held-out items never enter.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.common import paths, schema
from src.common.hashing import file_hash
from src.common.labels import answer_label

FIELDS = tuple(f for f in schema.CONDITIONING_FIELDS if f != "persona_id")
ORDINAL = {"age_band", "education_level", "income_decile", "religiosity_band", "political_leaning_band"}
CACHE = paths.PROCESSED / "importance.json"
TEST_SHARE = 0.3
REPEATS = 5
_MEMO: dict = {}  # tables fitted in this process, by key


def encode(personas: pd.DataFrame) -> np.ndarray:
    """Fields as category indices (schema order); missing -> NaN."""
    cols = []
    for f in FIELDS:
        index = {answer_label(v): i for i, v in enumerate(schema.CATEGORIES[f])}
        cols.append(personas[f].map(lambda v: index.get(answer_label(v), np.nan)).astype(float).to_numpy())
    return np.column_stack(cols)


def _log_loss(model, X, y, w) -> float:
    proba = model.predict_proba(X)
    col = np.searchsorted(model.classes_, y)
    return float(np.average(-np.log(np.clip(proba[np.arange(len(y)), col], 1e-12, None)), weights=w))


def fit_item(X: np.ndarray, y: np.ndarray, w: np.ndarray, seed: int = 0) -> np.ndarray:
    """Normalised permutation importance of each field for one anchor's answers."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    rng = np.random.default_rng(seed)
    test = rng.random(len(y)) < TEST_SHARE
    test &= np.isin(y, np.unique(y[~test]))  # score only answers the model has seen
    model = HistGradientBoostingClassifier(max_iter=100, learning_rate=0.05, max_depth=3,
                                           categorical_features=[f not in ORDINAL for f in FIELDS],
                                           random_state=seed)
    model.fit(X[~test], y[~test], sample_weight=w[~test])
    base = _log_loss(model, X[test], y[test], w[test])
    drop = np.zeros(len(FIELDS))
    for j in range(len(FIELDS)):
        for _ in range(REPEATS):
            Xp = X[test].copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            drop[j] += _log_loss(model, Xp, y[test], w[test]) - base
    drop = np.clip(drop / REPEATS, 0.0, None)
    return drop / drop.sum() if drop.sum() > 0 else np.full(len(FIELDS), 1.0 / len(FIELDS))


def fit(personas: pd.DataFrame, answers: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Importance table: one row per anchor column of ``answers``, one column per field."""
    frame = personas.merge(answers, on="persona_id", how="inner")
    X, w = encode(frame), frame["weight"].astype(float).to_numpy()
    rows = {}
    for name in answers.columns.drop("persona_id"):
        y = pd.to_numeric(frame[name], errors="coerce").to_numpy(float)
        ok = ~np.isnan(y)
        rows[name] = fit_item(X[ok], y[ok].astype(int), w[ok], seed)
    return pd.DataFrame.from_dict(rows, orient="index", columns=list(FIELDS))


def table(personas_path=paths.PERSONAS_CSV, anchors_path=paths.ANCHORS_CSV, seed: int = 0) -> pd.DataFrame:
    """``fit`` on the given files, kept per process. For the real core's anchors the
    table is also cached under data/processed, keyed by both files' hashes (refit
    when either changes)."""
    key = {"personas": file_hash(personas_path), "anchors": file_hash(anchors_path), "seed": seed}
    memo = tuple(key.values())
    if memo in _MEMO:
        return _MEMO[memo]
    cache = CACHE if Path(anchors_path).resolve() == paths.ANCHORS_CSV.resolve() else None
    if cache and cache.exists():
        stored = json.loads(cache.read_text(encoding="utf-8"))
        if stored["key"] == key:
            _MEMO[memo] = pd.DataFrame(stored["table"]).T[list(FIELDS)]
            return _MEMO[memo]
    out = _MEMO[memo] = fit(pd.read_csv(personas_path), pd.read_csv(anchors_path), seed)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "table": out.T.to_dict()}, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Per-anchor field importance on the real core.")
    ap.add_argument("--personas", default=str(paths.PERSONAS_CSV))
    ap.add_argument("--anchors", default=str(paths.ANCHORS_CSV))
    args = ap.parse_args()
    imp = table(args.personas, args.anchors)
    for name, row in imp.iterrows():
        top = row.sort_values(ascending=False).head(3)
        print(f"{name:34} " + "  ".join(f"{f} {v:.2f}" for f, v in top.items()))
    print("mean over anchors: " + "  ".join(f"{f} {v:.2f}" for f, v in imp.mean().sort_values(ascending=False).items()))


if __name__ == "__main__":
    main()
