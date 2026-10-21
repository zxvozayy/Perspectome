"""Statistics core for Track C. Pure functions over plain dicts / arrays.

Every function here has a hand-computed reference test in
``src/validation/tests/test_metrics.py`` (README: "test the statistics core
against hand-computed reference values").

Distributions are dicts ``{option: share}`` in the option order the caller
passes; missing options count as 0.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

from src.common.schema import SATURATION
from src.common.stats import normalize_vec


def _vec(dist: dict, options: Sequence[str]) -> np.ndarray:
    return np.array([float(dist.get(o, 0.0) or 0.0) for o in options])


def normalize(dist: dict, options: Sequence[str]) -> dict:
    """Rescale to sum 1 over ``options`` (rounded inputs rarely sum exactly)."""
    return dict(zip(options, normalize_vec(_vec(dist, options)).tolist()))


def tvd(p: dict, q: dict, options: Sequence[str]) -> float:
    """Total variation distance: half the L1 gap. 0 = identical, 1 = disjoint."""
    return float(0.5 * np.abs(_vec(p, options) - _vec(q, options)).sum())


def calibration_error(p: dict, q: dict, options: Sequence[str]) -> float:
    """Mean absolute share error per option (in proportion points).

    Unlike TVD it does not grow with the option count's mass shuffling between
    two options only, so it reads as "off by X points per option on average".
    """
    return float(np.abs(_vec(p, options) - _vec(q, options)).mean())


def wasserstein_ordinal(p: dict, q: dict, options: Sequence[str]) -> float:
    """Earth mover's distance on an ordered scale, normalized to [0, 1].

    ``options`` must be in scale order. Distance between adjacent options is
    1/(k-1), so moving all mass from one end to the other costs 1. Penalizes
    a 1-vs-10 miss more than a 5-vs-6 miss, which TVD can't.
    """
    k = len(options)
    if k < 2:
        return 0.0
    cdf_gap = np.cumsum(_vec(p, options) - _vec(q, options))[:-1]
    return float(np.abs(cdf_gap).sum() / (k - 1))


def expected_position(dist: dict, options: Sequence[str]) -> float:
    """Mean scale position in [0, 1] (first option = 0, last = 1)."""
    k = len(options)
    v = _vec(dist, options)
    if k < 2 or v.sum() <= 0:
        return float("nan")
    return float((v / v.sum()) @ np.linspace(0.0, 1.0, k))


def kendall_tau_b(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Kendall's tau-b (tie-corrected). None if fewer than 2 items or no variance."""
    x, y = list(x), list(y)
    n = len(x)
    if n < 2 or n != len(y):
        return None
    concordant = discordant = ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = np.sign(x[i] - x[j])
            dy = np.sign(y[i] - y[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx == dy:
                concordant += 1
            else:
                discordant += 1
    denom = math.sqrt((concordant + discordant + ties_x) * (concordant + discordant + ties_y))
    if denom == 0:
        return None
    return float((concordant - discordant) / denom)


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """BH step-up procedure. Returns, per input p-value, whether it is rejected."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    max_k = 0
    for rank, i in enumerate(order, start=1):
        if p_values[i] <= alpha * rank / m:
            max_k = rank
    rejected = [False] * m
    for rank, i in enumerate(order, start=1):
        if rank <= max_k:
            rejected[i] = True
    return rejected


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_proportion_p_value(p1: float, n1: float, p2: float, n2: float) -> float:
    """Two-sided p-value of a pooled two-proportion z-test."""
    if n1 <= 0 or n2 <= 0:
        return 1.0
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0 if p1 == p2 else 0.0
    z = abs(p1 - p2) / se
    return float(2 * (1 - _norm_cdf(z)))


# z for two-sided alpha = 0.05 and power = 0.80.
Z_ALPHA_2 = 1.959964
Z_POWER_80 = 0.841621


def minimum_detectable_difference(p: float, n1: float, n2: float) -> float:
    """Smallest share difference detectable at alpha=.05 (two-sided), power=.80.

    ``p`` is the baseline (placebo) share; ``n1``/``n2`` are effective sizes.
    """
    if n1 <= 0 or n2 <= 0:
        return float("inf")
    p = min(max(p, 0.0), 1.0)
    return float((Z_ALPHA_2 + Z_POWER_80) * math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)))


def is_saturated(share: float, low: float = SATURATION[0], high: float = SATURATION[1]) -> bool:
    """Rule 7: a placebo share outside 10-90% leaves no room to show an effect."""
    return share < low or share > high


def auc(scores: Sequence[float], labels: Sequence[int]) -> Optional[float]:
    """Area under the ROC curve (Mann-Whitney, ties count half). None without both classes."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return None
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))
