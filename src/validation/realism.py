"""Is the synthetic persona set realistic? Checks against the real core (Track C).

    python -m src.validation.realism        # writes reports/realism.json

- structural zeros: share of synthetic personas with a pair of values that no
  real respondent has (e.g. a combination the core never shows);
- SRMSE on every 2- and 3-way table of the conditioning fields, weighted;
- C2ST: a classifier trained to tell real from synthetic personas (cross-fitted);
  AUC 0.5 = indistinguishable, 1.0 = trivially separable;
- consistency rules (src/personas/rules.yaml): hard violations and soft-rule
  shares, synthetic vs real;
- ``check_text``: does a persona's free text contradict its own fields?

Pass thresholds are pre-registered in docs/findings.md (F-4).
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import combinations
from typing import Optional

import numpy as np
import pandas as pd

from src.common import paths, schema
from src.common.labels import answer_label
from src.personas import rules
from src.validation import baselines, metrics

FIELDS = tuple(f for f in schema.CONDITIONING_FIELDS if f != "persona_id")
REPORT = paths.REPO / "reports" / "realism.json"
C2ST_SIZE = 2000  # draws per side; both sides are resampled by weight, so they represent the population


def _labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Fields as comparable labels: 4, 4.0 and "4" are the same income decile."""
    out = frame[list(FIELDS)].apply(lambda c: c.map(answer_label)).fillna("NA")
    out["weight"] = frame["weight"].astype(float).to_numpy()
    return out


def _table(frame: pd.DataFrame, fields: tuple) -> pd.Series:
    return frame.groupby(list(fields))["weight"].sum() / frame["weight"].sum()


def _srmse(p: pd.Series, q: pd.Series) -> float:
    cells = p.index.union(q.index)
    p, q = p.reindex(cells, fill_value=0.0), q.reindex(cells, fill_value=0.0)
    return float(np.sqrt(((p - q) ** 2).mean()) / q.mean())


def srmse(synthetic: pd.DataFrame, real: pd.DataFrame, fields: tuple) -> float:
    """Standardized RMSE between the weighted joint tables of ``fields`` (0 = identical).

    SRMSE = sqrt(mean_cells (p - q)^2) / mean_cells q, over every cell seen in either set.
    """
    return _srmse(_table(_labels(synthetic), fields), _table(_labels(real), fields))


def srmse_summary(synthetic: pd.DataFrame, real: pd.DataFrame, ways: int) -> dict:
    synthetic, real = _labels(synthetic), _labels(real)
    values = {"|".join(f): _srmse(_table(synthetic, f), _table(real, f)) for f in combinations(FIELDS, ways)}
    worst = max(values, key=values.get)
    return {"mean": float(np.mean(list(values.values()))), "max": values[worst], "worst": worst}


def structural_zero_rate(synthetic: pd.DataFrame, real: pd.DataFrame) -> dict:
    """Share of synthetic personas with at least one pair of values absent from the real core."""
    synthetic, real = _labels(synthetic), _labels(real)
    bad = np.zeros(len(synthetic), dtype=bool)
    worst, worst_n = None, 0
    for pair in combinations(FIELDS, 2):
        seen = pd.MultiIndex.from_frame(real[list(pair)]).unique()
        missing = (synthetic[list(pair)] == "NA").any(axis=1).to_numpy()
        unseen = ~pd.MultiIndex.from_frame(synthetic[list(pair)]).isin(seen) & ~missing
        bad |= unseen
        if unseen.sum() > worst_n:
            worst, worst_n = "|".join(pair), int(unseen.sum())
    return {"rate": float(bad.mean()), "worst_pair": worst, "worst_pair_n": worst_n}


def c2st_auc(synthetic: pd.DataFrame, real: pd.DataFrame, seed: int = 0, n: int = C2ST_SIZE,
             folds: int = 5) -> float:
    """Cross-fitted AUC of a softmax classifier telling real (1) from synthetic (0) personas."""
    rng = np.random.default_rng(seed)

    def draw(frame):
        p = frame["weight"].to_numpy(float)
        return frame.iloc[rng.choice(len(frame), size=n, p=p / p.sum())]

    both = pd.concat([draw(real).assign(_real=1), draw(synthetic).assign(_real=0)], ignore_index=True)
    X = baselines._design_matrix(both)
    y = both["_real"].to_numpy()
    fold = rng.permutation(len(both)) % folds
    scores = np.zeros(len(both))
    for f in range(folds):
        W = baselines.fit_softmax(X[fold != f], y[fold != f], 2, np.ones((fold != f).sum()))
        scores[fold == f] = baselines.predict_proba(X[fold == f], W)[:, 1]
    return float(metrics.auc(scores, y))


def rule_comparison(synthetic: pd.DataFrame, real: pd.DataFrame) -> dict:
    s = rules.summary(synthetic).set_index("id")
    r = rules.summary(real).set_index("id")
    return {
        "hard_violations": int(s.loc[s.kind == "hard", "n"].sum()),
        "soft": {i: {"synthetic": float(s.loc[i, "share"]), "real": float(r.loc[i, "share"])}
                 for i in s.index[s.kind == "soft"]},
    }


def _scores(synthetic: pd.DataFrame, real: pd.DataFrame, seed: int) -> dict:
    return {
        "structural_zeros": structural_zero_rate(synthetic, real),
        "srmse_2way": srmse_summary(synthetic, real, 2),
        "srmse_3way": srmse_summary(synthetic, real, 3),
        "c2st_auc": c2st_auc(synthetic, real, seed=seed),
    }


def report(synthetic: pd.DataFrame, real: pd.DataFrame, seed: int = 0) -> dict:
    """Realism of ``synthetic`` and of the independent-fields baseline, both against ``real``."""
    return {
        "n_synthetic": len(synthetic),
        "n_real": len(real),
        **_scores(synthetic, real, seed),
        "rules": rule_comparison(synthetic, real),
        "independent_baseline": _scores(independent_baseline(real, len(synthetic), seed), real, seed),
    }


def independent_baseline(real: pd.DataFrame, n: int, seed: int = 0) -> pd.DataFrame:
    """Naive comparison: every field drawn on its own from its weighted marginal in the core."""
    rng = np.random.default_rng(seed)
    w = real["weight"].astype(float)
    out = {}
    for f in FIELDS:
        shares = w.groupby(real[f]).sum()
        out[f] = rng.choice(shares.index.to_numpy(), size=n, p=(shares / shares.sum()).to_numpy())
    frame = pd.DataFrame(out)
    frame["weight"] = 1.0
    frame["cell_id"] = frame[list(schema.CELL_FIELDS)].astype(str).agg("|".join, axis=1)
    frame.insert(0, "persona_id", [f"i{i}" for i in range(n)])
    return frame


# --- free text vs the persona's own fields -------------------------------------------

_AGE = re.compile(r"\b(\d{2})\s*yaşında", re.IGNORECASE)
# (pattern in the text, field, values that are consistent with it)
TEXT_RULES = (
    (re.compile(r"\bemekliyim\b|\bemekli oldum\b", re.IGNORECASE), "employment_status", {"retired"}),
    (re.compile(r"\böğrenciyim\b|\bdersim(e|den)?\b|\bfinallerim\b", re.IGNORECASE), "employment_status", {"student"}),
    (re.compile(r"\bişsizim\b|\biş arıyorum\b", re.IGNORECASE), "employment_status", {"unemployed"}),
    (re.compile(r"\b(eşim|karım|kocam)\b", re.IGNORECASE), "marital_status", {"married"}),
    (re.compile(r"\bbekarım\b|\bbekârım\b", re.IGNORECASE), "marital_status", {"single", "divorced", "widowed"}),
)


def check_text(text: str, persona: dict) -> list[str]:
    """Contradictions between a persona's free text and its fields (empty list = consistent)."""
    problems = []
    for pattern, field, allowed in TEXT_RULES:
        value = persona.get(field)
        if value is not None and pattern.search(text) and value not in allowed:
            problems.append(f"text implies {field} in {sorted(allowed)}, persona has {value!r}")
    for match in _AGE.finditer(text):
        years = int(match.group(1))
        band = next((b for b, lo in zip(reversed(schema.AGE_BANDS), reversed(schema.AGE_EDGES)) if years >= lo), None)
        if band and persona.get("age_band") and band != persona["age_band"]:
            problems.append(f"text says {years} years old, persona is {persona['age_band']}")
    return problems


def main(argv: Optional[list] = None):
    ap = argparse.ArgumentParser(description="Realism of the synthetic persona set vs the real core.")
    ap.add_argument("--synthetic", default=str(paths.PERSONAS_SYNTHETIC_CSV))
    ap.add_argument("--real", default=str(paths.PERSONAS_CSV))
    ap.add_argument("--out", default=str(REPORT))
    args = ap.parse_args(argv)
    out = report(pd.read_csv(args.synthetic), pd.read_csv(args.real))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    for name, s in (("synthetic", out), ("independent baseline", out["independent_baseline"])):
        print(f"{name:21} structural zeros {s['structural_zeros']['rate']:.4f} | SRMSE 2-way {s['srmse_2way']['mean']:.3f} "
              f"| 3-way {s['srmse_3way']['mean']:.3f} | C2ST AUC {s['c2st_auc']:.3f}")
    print(f"hard violations {out['rules']['hard_violations']} -> {args.out}")
    return out


if __name__ == "__main__":
    main()
