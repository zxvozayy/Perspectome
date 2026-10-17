"""Three-round simulation engine.

Round 1 — independent stance (LLM query per archetype cell).
Round 2 — Friedkin-Johnsen numerical update in code (no LLM calls).
Round 3 — settle: sample final choice from updated distributions.
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

    Returns {cell_id: {option: probability}}.
    """
    distributions: dict[str, dict[str, float]] = {}
    for entry in prompts:
        cell_id = entry["cell_id"]
        options = entry["options_order"]
        dist = model.query(entry["prompt"], options, n_repeats, seed)
        # Normalise keys back to canonical option names (in case of reversal
        # the model returns probabilities keyed by the displayed order, but
        # we always store in canonical order).
        distributions[cell_id] = dist
    return distributions


def assign_personas_round_1(
    personas: pd.DataFrame,
    cell_distributions: dict[str, dict[str, float]],
    options: list[str],
    seed: int,
) -> pd.DataFrame:
    """Sample a concrete choice for each persona from their cell's distribution."""
    rng = np.random.default_rng(seed)
    df = personas.copy()
    choices = []
    for _, row in df.iterrows():
        dist = cell_distributions[row["cell_id"]]
        probs = np.array([dist.get(opt, 0.0) for opt in options])
        probs = probs / probs.sum()  # safety normalise
        choice = rng.choice(options, p=probs)
        choices.append(choice)
    df["round_1_choice"] = choices
    return df


# ---------------------------------------------------------------------------
# Round 2 — Friedkin-Johnsen update
# ---------------------------------------------------------------------------

def _age_band_index(band: str) -> int:
    return AGE_BANDS.index(band)


def _are_adjacent(band_a: str, band_b: str) -> bool:
    return abs(_age_band_index(band_a) - _age_band_index(band_b)) <= 1


def _choice_to_soft_vector(choice: str, options: list[str], epsilon: float = 0.02) -> np.ndarray:
    """Convert a discrete choice to a softened probability vector."""
    k = len(options)
    vec = np.full(k, epsilon)
    idx = options.index(choice)
    vec[idx] = 1.0 - epsilon * (k - 1)
    return vec


def run_round_2_fj(
    personas: pd.DataFrame,
    options: list[str],
    stubbornness: float = 0.6,
    seed: int = 42,
) -> pd.DataFrame:
    """Friedkin-Johnsen numerical update.

    Each persona's opinion is a probability vector over options.
    Neighbours share the same region and have adjacent age bands.
    Update: x_new = s * x_initial + (1 - s) * mean(neighbours).
    Clamped so no option exceeds the range of initial opinions in the
    neighbourhood.
    """
    df = personas.copy()

    # Build initial position vectors.
    positions = np.array([
        _choice_to_soft_vector(row["round_1_choice"], options)
        for _, row in df.iterrows()
    ])

    initial_positions = positions.copy()
    n = len(df)

    # Precompute neighbourhood indices.
    regions = df["region"].values
    age_bands = df["age_band"].values
    neighbours: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j and regions[i] == regions[j] and _are_adjacent(age_bands[i], age_bands[j]):
                neighbours[i].append(j)

    # Single FJ update step.
    updated = np.empty_like(positions)
    for i in range(n):
        if neighbours[i]:
            neighbour_mean = initial_positions[neighbours[i]].mean(axis=0)
            updated[i] = stubbornness * initial_positions[i] + (1 - stubbornness) * neighbour_mean
        else:
            # Singleton — no neighbours, stays at initial position.
            updated[i] = initial_positions[i]

    # Clamp to convex hull of neighbourhood initial opinions.
    for i in range(n):
        if neighbours[i]:
            all_in_neighbourhood = np.vstack([
                initial_positions[neighbours[i]],
                initial_positions[i:i+1],
            ])
            lo = all_in_neighbourhood.min(axis=0)
            hi = all_in_neighbourhood.max(axis=0)
            updated[i] = np.clip(updated[i], lo, hi)

    # Re-normalise to valid probability distributions.
    row_sums = updated.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    updated = updated / row_sums

    df["round_2_distribution"] = [
        {opt: float(updated[i, j]) for j, opt in enumerate(options)}
        for i in range(n)
    ]

    return df


# ---------------------------------------------------------------------------
# Round 3 — settle
# ---------------------------------------------------------------------------

def run_round_3_settle(
    personas: pd.DataFrame,
    options: list[str],
    seed: int,
) -> pd.DataFrame:
    """Sample each persona's final choice from their round-2 distribution."""
    rng = np.random.default_rng(seed + 1)  # offset to avoid reusing R1 seed
    df = personas.copy()
    choices = []
    for _, row in df.iterrows():
        dist = row["round_2_distribution"]
        probs = np.array([dist[opt] for opt in options])
        probs = probs / probs.sum()
        choice = rng.choice(options, p=probs)
        choices.append(choice)
    df["final_choice"] = choices
    return df
