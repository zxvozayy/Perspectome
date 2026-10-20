"""Three-round simulation engine.

Round 1 — independent stance: the LLM is queried once per archetype cell and
          every persona starts from its cell's answer distribution.
Rounds 2..n — Friedkin–Johnsen update in code (no LLM calls), on probability
          vectors: x(t+1) = s * x(0) + (1 - s) * mean(neighbours' x(t)).

Opinions stay probability vectors throughout; nothing is sampled. The
population result is the weighted mean of the final vectors (aggregator.py),
which is less noisy than counting one sampled choice per persona.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.schema import AGE_BANDS


# ---------------------------------------------------------------------------
# Round 1
# ---------------------------------------------------------------------------

def run_round_1(
    model,
    prompts: list[dict],
    n_repeats: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    """Query the model once per cell_id.

    Returns {cell_id: {option: probability}}. The model returns probabilities
    keyed by option name, so the displayed (possibly reversed) order doesn't
    matter here.
    """
    distributions: dict[str, dict[str, float]] = {}
    for entry in prompts:
        distributions[entry["cell_id"]] = model.query(entry["prompt"], entry["options_order"], n_repeats, seed)
    return distributions


def initial_vectors(
    personas: pd.DataFrame,
    cell_distributions: dict[str, dict[str, float]],
    options: list[str],
) -> np.ndarray:
    """Each persona's round-1 opinion: its cell's distribution, shape (n, k)."""
    out = np.empty((len(personas), len(options)))
    for i, cell in enumerate(personas["cell_id"].to_numpy()):
        dist = cell_distributions[cell]
        v = np.array([dist.get(opt, 0.0) for opt in options], dtype=float)
        out[i] = v / v.sum() if v.sum() > 0 else 1.0 / len(options)
    return out


# ---------------------------------------------------------------------------
# Rounds 2..n — Friedkin–Johnsen update
# ---------------------------------------------------------------------------

def _neighbour_groups(personas: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Group index per persona (region x age band) and each group's band index."""
    regions = personas["region"].astype("string").fillna("__unknown__").to_numpy()
    bands = personas["age_band"].map(lambda b: AGE_BANDS.index(b) if b in AGE_BANDS else -10).to_numpy()
    keys = pd.Series(list(zip(regions, bands)))
    codes, uniques = pd.factorize(keys)
    return codes, uniques


def run_fj(
    personas: pd.DataFrame,
    x0: np.ndarray,
    stubbornness: float = 0.6,
    steps: int = 1,
) -> np.ndarray:
    """Friedkin–Johnsen update on probability vectors, vectorized.

    Neighbours share the same region and an adjacent (or the same) age band.
    Each step: x(t+1) = s * x0 + (1 - s) * mean of neighbours' x(t), the
    persona itself excluded. A persona with no neighbours keeps x0. Results
    are clipped to the range of initial opinions in the neighbourhood and
    re-normalised, so updates never invent opinions nobody held.
    """
    n, k = x0.shape
    codes, uniques = _neighbour_groups(personas)
    g = len(uniques)
    # members of group a are neighbours of group b when same region and |band diff| <= 1
    adj = np.zeros((g, g), dtype=bool)
    for a, (ra, ba) in enumerate(uniques):
        for b, (rb, bb) in enumerate(uniques):
            adj[a, b] = ra == rb and abs(ba - bb) <= 1 and ba >= 0 and bb >= 0
    member = np.zeros((g, n))
    member[codes, np.arange(n)] = 1.0
    hood = adj.astype(float) @ member            # (g, n): 1 if persona j is in group a's neighbourhood
    hood_size = hood.sum(axis=1)[codes] - 1.0      # neighbours per persona, self excluded

    # neighbourhood range of initial opinions (self included)
    lo = np.empty((g, k))
    hi = np.empty((g, k))
    for a in range(g):
        mask = hood[a] > 0
        if mask.any():
            lo[a], hi[a] = x0[mask].min(axis=0), x0[mask].max(axis=0)
        else:  # unknown age band: no neighbourhood, nothing to clip against
            lo[a], hi[a] = 0.0, 1.0
    lo, hi = lo[codes], hi[codes]

    x = x0.copy()
    has_nb = hood_size > 0
    for _ in range(max(steps, 0)):
        sums = (hood @ x)[codes] - x               # neighbours' sum, self excluded
        mean = np.where(has_nb[:, None], sums / np.maximum(hood_size, 1)[:, None], x0)
        x = stubbornness * x0 + (1 - stubbornness) * mean
        x = np.clip(x, lo, hi)
        x = x / x.sum(axis=1, keepdims=True)
    return x
