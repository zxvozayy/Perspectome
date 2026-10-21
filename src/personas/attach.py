"""Features attached to synthetic personas after generation (schema.SYNTHETIC_FIELDS).

L1 household and work — hot-deck from a LiTS IV respondent in the same cell:
   household_size and tenure from a donor matching age_band, gender,
   education_level and region (falling back to coarser matches); sector and
   informal only for employed personas, from an employed donor.
L3 lifestyle — drawn from published tables given gender (and age_band for
   generative-AI use).
L4 concern — the person's "most important problem", from the national table.

Anything not observed jointly with the persona's other fields is drawn as if
independent of them given the conditioning keys; ``ASSUMPTIONS`` lists this
and goes into the generation summary.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import schema
from src.personas.sources import tables

DONOR_KEYS = (
    ("age_band", "gender", "education_level", "region"),
    ("age_band", "gender", "education_level"),
    ("age_band", "gender"),
    ("age_band",),
)

ASSUMPTIONS = (
    "household_size, tenure: LiTS IV 2022-23 donor with the same age_band, gender, education_level, region "
    "(coarser match if none); LiTS levels differ from TÜİK (owners 68.7% vs 57.1%), not re-weighted.",
    "sector, informal: employed LiTS IV donor, same keys; informal = no social security in the main job.",
    "smoker, drinks_alcohol, obese, internet_user: published shares by gender only (TÜİK 2025-26, "
    "news-reported, unverified); independent of every other field given gender.",
    "genai_user: TÜİK 2026 shares by age_band and gender (news-reported, unverified).",
    "concern: TÜİK Yaşam Memnuniyeti 2025 national shares (top three published, rest 'other'); same for everyone.",
)


def _key(k) -> tuple:
    return k if isinstance(k, tuple) else (k,)


def _hot_deck(personas: pd.DataFrame, donors: pd.DataFrame, columns: list[str],
              rng: np.random.Generator) -> pd.DataFrame:
    """For every persona, copy ``columns`` from one donor drawn by weight within the best-matching cell."""
    out = pd.DataFrame(index=personas.index, columns=columns, dtype=object)
    todo = personas.index
    for keys in DONOR_KEYS:
        if todo.empty:
            break
        pool = donors.dropna(subset=list(keys) + columns)
        groups = {_key(k): g for k, g in pool.groupby(list(keys))}
        for k, sub in personas.loc[todo].groupby(list(keys)):
            idx = sub.index
            g = groups.get(_key(k))
            if g is None:
                continue
            p = g["weight"].to_numpy(float)
            pick = rng.choice(len(g), size=len(idx), p=p / p.sum())
            out.loc[idx, columns] = g[columns].to_numpy()[pick]
        todo = out.index[out[columns[0]].isna()]
    return out


def _bernoulli(probs: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return rng.random(len(probs)) < probs


def attach(personas: pd.DataFrame, lits: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Personas plus every schema.SYNTHETIC_FIELDS column."""
    rng = np.random.default_rng(seed)
    out = personas.copy()

    home = _hot_deck(out, lits, ["household_size", "tenure"], rng)
    out["household_size"] = home["household_size"].astype("Int64")
    out["tenure"] = home["tenure"]

    employed = out["employment_status"] == "employed"
    work = _hot_deck(out[employed], lits[lits["employment_status"] == "employed"], ["sector", "informal"], rng)
    out["sector"] = work["sector"].reindex(out.index)
    out["informal"] = work["informal"].reindex(out.index).astype("boolean")

    gender = out["gender"].to_numpy()
    for field, table_id in (("smoker", "daily_smoking_by_sex"), ("drinks_alcohol", "alcohol_last_year_by_sex"),
                            ("obese", "obesity_by_sex"), ("internet_user", "internet_use_by_sex")):
        values = tables.get(table_id)["values"]
        yes = next(k for k in values[schema.GENDERS[0]] if k in ("yes", "daily"))
        out[field] = _bernoulli(np.array([values[g][yes] for g in gender]), rng)

    genai = tables.get("genai_use_by_age_sex")["values"]
    out["genai_user"] = _bernoulli(np.array([genai[a][g]["yes"] for a, g in zip(out["age_band"], gender)]), rng)

    concern = tables.get("top_problem")["values"]
    out["concern"] = rng.choice(list(concern), size=len(out), p=np.array(list(concern.values())))
    return out
