"""Fetch Turkey population margins from the Eurostat REST API (no registration).

These are post-stratification *marginal* targets for issue #10. Eurostat is a
programmatic, registration-free source and reports Turkey at NUTS-1, the same
region level as the WVS variable N_REG_NUTS1 -- so region cells line up.

IMPORTANT (methodology): the project's designated authoritative margin source
is TÜİK (docs/data-sources.md). Eurostat re-publishes TÜİK's demographic
aggregates, so it is a close, usable stand-in, but the choice to use it must be
verified against TÜİK's own tables before any calibration claim. Not a silent
swap -- recorded in src/personas/NOTES.md.

Output: tidy CSVs under the git-ignored data/raw/eurostat/.

    python -m src.personas.fetch_eurostat_margins
"""

from __future__ import annotations

import json
import urllib.request
from itertools import product
from pathlib import Path

import pandas as pd

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OUT_DIR = Path("data/raw/eurostat")

# Turkey NUTS-1 regions (İBBS Düzey-1) -- matches WVS N_REG_NUTS1 cells.
TR_NUTS1 = ["TR1", "TR2", "TR3", "TR4", "TR5", "TR6", "TR7", "TR8", "TR9", "TRA", "TRB", "TRC"]


def _fetch(dataset: str, params: dict) -> dict:
    query = []
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            query.extend(f"{key}={v}" for v in value)
        else:
            query.append(f"{key}={value}")
    url = f"{BASE}/{dataset}?{'&'.join(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read())


def _to_tidy(js: dict) -> pd.DataFrame:
    """Expand a JSON-stat 2.0 response into one row per cell."""
    dims = js["id"]
    # ordered category keys per dimension
    cats = []
    for d in dims:
        idx = js["dimension"][d]["category"]["index"]
        cats.append([k for k, _ in sorted(idx.items(), key=lambda kv: kv[1])])
    labels = {d: js["dimension"][d]["category"]["label"] for d in dims}
    values = js["value"]

    rows = []
    for flat, combo in enumerate(product(*cats)):
        v = values.get(str(flat))
        if v is None:
            continue
        row = {}
        for d, code in zip(dims, combo):
            row[d] = code
            row[f"{d}_label"] = labels[d].get(code, code)
        row["value"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_population_by_age_sex_region(time: str = "2024") -> pd.DataFrame:
    """demo_r_pjangrp3: population by 5-year age group, sex, NUTS region."""
    js = _fetch("demo_r_pjangrp3", {
        "format": "JSON", "sex": ["M", "F"], "geo": TR_NUTS1, "time": time,
    })
    return _to_tidy(js)


def fetch_education_by_sex_age(time: str = "2024") -> pd.DataFrame:
    """edat_lfse_03: population by educational attainment, sex and age (%)."""
    js = _fetch("edat_lfse_03", {
        "format": "JSON", "geo": "TR", "sex": ["M", "F"], "time": time,
    })
    return _to_tidy(js)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Try the most recent year, fall back one year if empty.
    for year in ("2024", "2023"):
        pop = fetch_population_by_age_sex_region(year)
        if not pop.empty:
            break
    pop.to_csv(OUT_DIR / "tr_population_age_sex_nuts1.csv", index=False)
    print(f"population: {len(pop)} rows ({year}) -> {OUT_DIR / 'tr_population_age_sex_nuts1.csv'}")

    for year in ("2024", "2023"):
        edu = fetch_education_by_sex_age(year)
        if not edu.empty:
            break
    edu.to_csv(OUT_DIR / "tr_education_sex_age.csv", index=False)
    print(f"education:  {len(edu)} rows ({year}) -> {OUT_DIR / 'tr_education_sex_age.csv'}")


if __name__ == "__main__":
    main()
