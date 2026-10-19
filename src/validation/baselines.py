"""Baselines the engine is compared against (issue #12).

ML baseline (probes)
    Multinomial logistic regression on the conditioning fields, trained on the
    real held-out answers. Cross-fitted: personas are split into K folds by a
    hash of persona_id, each fold is predicted by a model that never saw it, and
    the out-of-fold probabilities are averaged with the persona weights. So the
    population distribution it reports is a genuine held-out prediction, and it
    covers the same people as the real distribution. It is *supervised* (it sees
    real answers to the same item), which the engine never does -- treat it as
    "how far demographics alone get you", not as a fair fight.

Equation baseline (scenarios)
    A no-agent system-dynamics model. The population share vector relaxes
    toward a shocked equilibrium:

        dp/dt = lambda * (pi - p),   pi = (1 - s) * p0 + s * e_target

    with p0 = the placebo distribution (status quo), e_target = all mass on the
    option the shock pushes toward, s = shock intensity, lambda = adjustment
    rate. After T rounds:

        effect = p(T) - p0 = s * (1 - exp(-lambda * T)) * (e_target - p0)

    s, lambda and the target option are written down per scenario in
    ``equation_params.yaml`` *before* any run (rule 9) -- they are priors, not
    fitted. A probe has no shock, so there is no equation baseline for probes.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import yaml

from src.common import schema
from src.validation import real

EQUATION_PARAMS = Path(__file__).parent / "equation_params.yaml"

# Conditioning fields used as ML features (persona_id is an identifier).
FEATURES = tuple(f for f in schema.CONDITIONING_FIELDS if f != "persona_id")
NUMERIC_FEATURES = ("income_decile",)


# --- ML baseline ---------------------------------------------------------------

def _design_matrix(frame: pd.DataFrame) -> np.ndarray:
    """One-hot categorical fields + standardized numeric fields with a missing flag."""
    cols = []
    for f in FEATURES:
        if f not in frame.columns:
            continue
        if f in NUMERIC_FEATURES:
            x = pd.to_numeric(frame[f], errors="coerce")
            missing = x.isna().astype(float)
            mu, sd = x.mean(), x.std(ddof=0)
            x = ((x - mu) / sd if sd and sd > 0 else x * 0).fillna(0.0)
            cols += [x.to_numpy(float), missing.to_numpy()]
        else:
            dummies = pd.get_dummies(frame[f].astype("string"), dtype=float)
            cols += [dummies[c].to_numpy() for c in sorted(dummies.columns)]
    cols.append(np.ones(len(frame)))  # intercept
    return np.column_stack(cols)


def fit_softmax(X: np.ndarray, y: np.ndarray, k: int, sample_weight: np.ndarray,
                l2: float = 1.0, iters: int = 400, lr: float = 0.5) -> np.ndarray:
    """Weighted multinomial logistic regression by gradient descent (deterministic).

    ``y`` holds class indices 0..k-1. Returns coefficients of shape (features, k).
    The intercept (last column) is not penalized.
    """
    n, d = X.shape
    W = np.zeros((d, k))
    Y = np.zeros((n, k))
    Y[np.arange(n), y] = 1.0
    sw = sample_weight / sample_weight.sum()
    penalty = np.ones((d, 1))
    penalty[-1] = 0.0
    for _ in range(iters):
        P = predict_proba(X, W)
        grad = X.T @ ((P - Y) * sw[:, None]) + l2 * penalty * W / n
        W -= lr * grad
    return W


def predict_proba(X: np.ndarray, W: np.ndarray) -> np.ndarray:
    Z = X @ W
    Z -= Z.max(axis=1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(axis=1, keepdims=True)


def _fold(persona_id: str, k: int) -> int:
    return int(hashlib.sha256(str(persona_id).encode()).hexdigest()[:16], 16) % k


def ml_baseline(frame: pd.DataFrame, item: str, options: Sequence[str],
                n_folds: int = 5) -> dict:
    """Cross-fitted population distribution for ``item`` from demographics alone.

    Returns {"distribution": {...}, "n": int, "n_folds": int}. Only personas who
    answered the item are predicted, so it lines up with real.distribution().
    """
    labels = real.answer_labels(frame[item])
    keep = labels.isin(list(options)).to_numpy()
    sub = frame[keep].reset_index(drop=True)
    y = np.array([list(options).index(v) for v in labels[keep]])
    w = sub["weight"].astype(float).to_numpy()
    X = _design_matrix(sub)
    k = len(options)
    folds = np.array([_fold(pid, n_folds) for pid in sub["persona_id"]])

    proba = np.zeros((len(sub), k))
    for f in range(n_folds):
        test = folds == f
        train = ~test
        if not test.any():
            continue
        if not train.any():  # degenerate tiny input: fall back to the prior
            proba[test] = 1.0 / k
            continue
        W = fit_softmax(X[train], y[train], k, w[train])
        proba[test] = predict_proba(X[test], W)

    dist = (proba * w[:, None]).sum(axis=0) / w.sum()
    return {"distribution": {o: float(p) for o, p in zip(options, dist)},
            "n": int(len(sub)), "n_folds": n_folds}


# --- Equation baseline ------------------------------------------------------------

def load_equation_params(path=EQUATION_PARAMS) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def equation_effect(placebo: dict, options: Sequence[str], target_option: str,
                    intensity: float, rate: float = 1.0, rounds: int = 1) -> dict:
    """Closed-form ODE effect p(T) - p0 per option (sums to 0)."""
    if target_option not in options:
        raise ValueError(f"target_option {target_option!r} not in options {list(options)}")
    p0 = np.array([float(placebo.get(o, 0.0)) for o in options])
    p0 = p0 / p0.sum() if p0.sum() > 0 else np.full(len(options), 1.0 / len(options))
    e = np.array([1.0 if o == target_option else 0.0 for o in options])
    scale = intensity * (1.0 - math.exp(-rate * rounds))
    return {o: float(d) for o, d in zip(options, scale * (e - p0))}


def scenario_equation_effect(scenario_id: str, placebo: dict, options: Sequence[str],
                             rounds: int, params: Optional[dict] = None) -> Optional[dict]:
    """Equation baseline for one scenario, or None if no parameters were registered."""
    params = load_equation_params() if params is None else params
    cfg = params.get(scenario_id)
    if not cfg:
        return None
    return equation_effect(placebo, options, cfg["target_option"], float(cfg["intensity"]),
                           float(cfg.get("rate", 1.0)), int(rounds or 1))
