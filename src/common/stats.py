"""Small numeric helpers shared by every track (numpy only)."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


def normalize_vec(v) -> np.ndarray:
    """Rescale to sum 1; an all-zero vector becomes uniform. Works row-wise on 2-D input."""
    v = np.asarray(v, dtype=float)
    total = v.sum(axis=-1, keepdims=True)
    k = v.shape[-1]
    return np.where(total > 0, v / np.where(total > 0, total, 1.0), 1.0 / k)


def weighted_share(labels: Sequence, weights: Sequence[float], options: Sequence) -> dict:
    """Weighted share of each option among ``labels`` (labels outside ``options`` are ignored)."""
    labels = np.asarray(list(labels), dtype=object)
    w = np.asarray(list(weights), dtype=float)
    keep = np.isin(labels, np.asarray(list(options), dtype=object))
    total = w[keep].sum()
    return {o: float(w[labels == o].sum() / total) if total > 0 else 0.0 for o in options}


def kish_n_eff(weights: Iterable[float]) -> float:
    """Kish effective sample size: (sum w)^2 / sum w^2."""
    w = np.asarray(list(weights), dtype=float)
    if w.size == 0 or (w ** 2).sum() == 0:
        return 0.0
    return float(w.sum() ** 2 / (w ** 2).sum())


def weighted_mean_rows(vectors, weights) -> np.ndarray:
    """Weight-weighted mean of the rows of ``vectors`` (n, k); unweighted if weights sum to 0."""
    x = np.asarray(vectors, dtype=float)
    w = np.asarray(weights, dtype=float)
    total = w.sum()
    return (x * w[:, None]).sum(axis=0) / total if total > 0 else x.mean(axis=0)
