"""sources/lits.py on a tiny hand-made Stata file (the real LiTS file is never committed)."""

import pandas as pd
import pytest

from src.personas.sources import lits


@pytest.fixture
def dta(tmp_path):
    rows = [
        # Türkiye, respondent is roster member 2 (female, 70), retired, owner
        dict(hhid=1, country=35, weight_trt=1.5, rand_resp_code=2, q1031=1, q1051=72, q1032=2, q1052=70,
             q109b=2, region="Ege", urbanity=1, q107b=3, q304=2, q304b=5, q1=2, q209=1, q319=None, q3153=None),
        # Türkiye, respondent is member 1 (male, 30), working in construction without social security, tenant
        dict(hhid=2, country=35, weight_trt=0.5, rand_resp_code=1, q1031=1, q1051=30, q1032=None, q1052=None,
             q109b=7, region="İstanbul", urbanity=1, q107b=1, q304=1, q304b=None, q1=1, q209=2, q319=3, q3153=2),
        # another country: must be dropped
        dict(hhid=3, country=34, weight_trt=1.0, rand_resp_code=1, q1031=2, q1051=40, q1032=None, q1052=None,
             q109b=4, region="X", urbanity=2, q107b=2, q304=1, q304b=None, q1=3, q209=1, q319=9, q3153=1),
    ]
    path = tmp_path / "lits.dta"
    pd.DataFrame(rows).to_stata(path, write_index=False, version=118)
    return path


def test_maps_turkiye_respondents_to_schema(dta):
    f = lits.load(dta)
    assert list(f.columns) == list(lits.COLUMNS) and len(f) == 2
    old, young = f.iloc[0], f.iloc[1]
    assert (old.gender, old.age_band, old.education_level, old.marital_status) == ("female", "65+", "primary", "widowed")
    assert (old.employment_status, old.tenure, old.region, old.nuts1) == ("retired", "owner", "Ege", "TR3")
    assert pd.isna(old.sector) and pd.isna(old.informal)  # work questions only for workers
    assert (young.gender, young.age_band, young.education_level, young.region) == ("male", "25-34", "bachelor", "Marmara")
    assert (young.employment_status, young.sector, young.informal, young.tenure) == ("employed", "construction", True, "tenant")
    assert young.household_size == 1 and young.weight == 0.5
