"""Türkiye population targets from the Eurostat REST API (registration-free).

Eurostat re-publishes TÜİK's register (ADNKS) and Labour Force Survey figures
at NUTS-1, the same region level as WVS ``N_REG_NUTS1``. Files are fetched
into git-ignored ``data/raw/eurostat/`` with the reference year in the name:

    python -m src.personas.sources.eurostat            # latest year available
    python -m src.personas.sources.eurostat --year 2025

Targets (each sums to 1, 18+ population):
- ``target_margins(year)``: one-way age_band, gender, region, edu3 — what the
  raking in generator.py uses today.
- ``joint_targets(year)``: region x age_band x gender (register) and
  age_band x gender x edu3 (LFS) for joint post-stratification.

Documented approximations:
- the schema's 18-24 band is Y20-24 + 0.4 x Y15-19 (ages 18-19 of 15-19);
- one-way education comes from the broad Y15-74 band, both sexes combined by
  their 18+ population share;
- joint education for 65+ uses Eurostat's Y55-74 minus Y55-64 (population
  weighted), so it describes ages 65-74 and is assumed for 75+ as well.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date
from itertools import product

import pandas as pd

from src.common import paths, schema, stats
from src.personas.sources import wvs

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
DIR = paths.DATA_RAW / "eurostat"
TR_NUTS1 = tuple(wvs.NUTS1_ALPHA_TO_REGION)

# Year of the targets behind the frozen persona set. Moving to a newer year
# re-weights every persona, so it changes persona_set_hash (a PR, not a rerun).
DEFAULT_YEAR = 2024

# schema age_band -> (eurostat age code, weight) components, 18+ only.
AGE_BAND_COMPONENTS = {
    "18-24": [("Y15-19", 0.4), ("Y20-24", 1.0)],
    "25-34": [("Y25-29", 1.0), ("Y30-34", 1.0)],
    "35-44": [("Y35-39", 1.0), ("Y40-44", 1.0)],
    "45-54": [("Y45-49", 1.0), ("Y50-54", 1.0)],
    "55-64": [("Y55-59", 1.0), ("Y60-64", 1.0)],
    "65+": [("Y65-69", 1.0), ("Y70-74", 1.0), ("Y75-79", 1.0), ("Y80-84", 1.0), ("Y_GE85", 1.0)],
}
assert set(AGE_BAND_COMPONENTS) == set(schema.AGE_BANDS)
# schema age_band -> Eurostat LFS education age group.
EDU_AGE_GROUPS = {"18-24": "Y18-24", "25-34": "Y25-34", "35-44": "Y35-44", "45-54": "Y45-54", "55-64": "Y55-64"}
EDU3 = {"ED0-2": "low", "ED3_4": "mid", "ED5-8": "high"}
SEX = {"M": schema.GENDERS[0], "F": schema.GENDERS[1]}
_EDU_ONE_WAY_AGE = "Y15-74"


# --- fetching ----------------------------------------------------------------------

def _fetch(dataset: str, params: dict) -> dict:
    query = []
    for key, value in params.items():
        values = value if isinstance(value, (list, tuple)) else [value]
        query.extend(f"{key}={v}" for v in values)
    req = urllib.request.Request(f"{BASE}/{dataset}?{'&'.join(query)}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read())


def _to_tidy(js: dict) -> pd.DataFrame:
    """Expand a JSON-stat 2.0 response into one row per cell."""
    dims = js["id"]
    cats = [[k for k, _ in sorted(js["dimension"][d]["category"]["index"].items(), key=lambda kv: kv[1])]
            for d in dims]
    labels = {d: js["dimension"][d]["category"]["label"] for d in dims}
    rows = []
    for flat, combo in enumerate(product(*cats)):
        v = js["value"].get(str(flat))
        if v is None:
            continue
        row = {d: code for d, code in zip(dims, combo)}
        row.update({f"{d}_label": labels[d].get(code, code) for d, code in zip(dims, combo)})
        row["value"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def pop_file(year: int):
    return DIR / f"tr_population_age_sex_nuts1_{year}.csv"


def edu_file(year: int):
    return DIR / f"tr_education_sex_age_{year}.csv"


def fetch(year: int | None = None) -> int:
    """Download population and education tables for ``year`` (default: latest with both)."""
    years = [year] if year else list(range(date.today().year, date.today().year - 4, -1))
    for y in years:
        pop = _to_tidy(_fetch("demo_r_pjangrp3", {"format": "JSON", "sex": ["M", "F"], "geo": TR_NUTS1, "time": y}))
        edu = _to_tidy(_fetch("edat_lfse_03", {"format": "JSON", "geo": "TR", "sex": ["M", "F"], "time": y}))
        if not pop.empty and not edu.empty:
            DIR.mkdir(parents=True, exist_ok=True)
            pop.to_csv(pop_file(y), index=False)
            edu.to_csv(edu_file(y), index=False)
            return y
    raise RuntimeError(f"No Eurostat population and education data for {years}")


# --- targets -----------------------------------------------------------------------

def _shares(counts: dict) -> dict:
    keys = list(counts)
    return dict(zip(keys, stats.normalize_vec([counts[k] for k in keys]).tolist()))


def population_cells(year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """18+ population as tidy rows: region, gender, age_band, count."""
    pop = pd.read_csv(pop_file(year))
    wide = pop.pivot_table(index=["geo", "sex"], columns="age", values="value", aggfunc="sum")
    rows = []
    for (geo, sex), r in wide.iterrows():
        region, gender = wvs.NUTS1_ALPHA_TO_REGION.get(geo), SEX.get(sex)
        if region is None or gender is None:
            continue
        for band, comps in AGE_BAND_COMPONENTS.items():
            rows.append({"region": region, "gender": gender, "age_band": band,
                         "count": sum(r.get(code, 0) * w for code, w in comps)})
    return pd.DataFrame(rows)


def _edu_pct(year: int) -> pd.DataFrame:
    edu = pd.read_csv(edu_file(year))
    return edu[edu["isced11"].isin(EDU3)]


def _education_one_way(cells: pd.DataFrame, year: int) -> dict:
    """National edu3 distribution (Y15-74), sexes combined by their 18+ population share."""
    edu = _edu_pct(year)
    edu = edu[edu["age"] == _EDU_ONE_WAY_AGE]
    sex_share = _shares(cells.groupby("gender")["count"].sum().to_dict())
    out = dict.fromkeys(EDU3.values(), 0.0)
    for code, gender in SEX.items():
        pct = _shares({EDU3[i]: v for i, v in zip(edu.loc[edu["sex"] == code, "isced11"],
                                                  edu.loc[edu["sex"] == code, "value"])})
        for level in out:
            out[level] += sex_share.get(gender, 0.0) * pct.get(level, 0.0)
    return _shares(out)


def target_margins(year: int = DEFAULT_YEAR) -> dict:
    """The four one-way target distributions the current raking uses."""
    cells = population_cells(year)
    return {
        "age_band": _shares(cells.groupby("age_band")["count"].sum().to_dict()),
        "gender": _shares(cells.groupby("gender")["count"].sum().to_dict()),
        "region": _shares(cells.groupby("region")["count"].sum().to_dict()),
        "edu3": _education_one_way(cells, year),
    }


def joint_targets(year: int = DEFAULT_YEAR) -> dict[str, pd.DataFrame]:
    """Joint 18+ targets: region x age_band x gender, and age_band x gender x edu3 (shares)."""
    cells = population_cells(year)
    region_age_sex = cells.assign(share=cells["count"] / cells["count"].sum()).drop(columns="count")

    edu = _edu_pct(year)
    by_band = cells.groupby(["age_band", "gender"])["count"].sum()
    raw = pd.read_csv(pop_file(year))
    raw = raw[raw["geo"].isin(TR_NUTS1)]
    rows = []
    for band in schema.AGE_BANDS:
        for code, gender in SEX.items():
            sub = edu[edu["sex"] == code].pivot_table(index="isced11", columns="age", values="value", aggfunc="sum")
            if band in EDU_AGE_GROUPS:
                pct = sub[EDU_AGE_GROUPS[band]].to_dict()
            else:  # 65+: Y55-74 minus Y55-64, weighted by their populations
                n_55_64 = by_band[("55-64", gender)]
                n_65_74 = float(raw.loc[(raw["sex"] == code) & raw["age"].isin(["Y65-69", "Y70-74"]), "value"].sum())
                pct = {i: max((sub.loc[i, "Y55-74"] * (n_55_64 + n_65_74) - sub.loc[i, "Y55-64"] * n_55_64) / n_65_74, 0.0)
                       for i in sub.index}
            for level, share in _shares({EDU3[i]: v for i, v in pct.items()}).items():
                rows.append({"age_band": band, "gender": gender, "edu3": level,
                             "share": share * by_band[(band, gender)] / by_band.sum()})
    return {"region_age_sex": region_age_sex, "age_sex_edu": pd.DataFrame(rows)}


def main():
    ap = argparse.ArgumentParser(description="Fetch Eurostat population and education tables for Türkiye.")
    ap.add_argument("--year", type=int, help="reference year (default: latest available)")
    year = fetch(ap.parse_args().year)
    print(f"Eurostat {year}: {pop_file(year)} and {edu_file(year)}")


if __name__ == "__main__":
    main()
