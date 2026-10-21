"""sources/eurostat.py on a tiny hand-made table (no network)."""

import pandas as pd
import pytest

from src.common import schema
from src.personas.sources import eurostat

AGES = ["Y15-19", "Y20-24", "Y25-29", "Y30-34", "Y35-39", "Y40-44", "Y45-49", "Y50-54",
        "Y55-59", "Y60-64", "Y65-69", "Y70-74", "Y75-79", "Y80-84", "Y_GE85"]


@pytest.fixture
def tables(tmp_path, monkeypatch):
    monkeypatch.setattr(eurostat, "DIR", tmp_path)
    # 100 people in every 5-year band, sex and region; TR1 (Marmara) doubled.
    pop = [{"geo": g, "sex": s, "age": a, "value": 200 if g == "TR1" else 100}
           for g in eurostat.TR_NUTS1 for s in ("M", "F") for a in AGES]
    pd.DataFrame(pop).to_csv(eurostat.pop_file(2099), index=False)
    edu = []
    for s in ("M", "F"):
        for age in ("Y15-74", *eurostat.EDU_AGE_GROUPS.values()):
            edu += [{"sex": s, "age": age, "isced11": i, "value": v}
                    for i, v in (("ED0-2", 50), ("ED3_4", 30), ("ED5-8", 20))]
        # ages 55-74: 60/30/10; ages 55-64: 50/30/20  ->  65-74 must come out 70/30/0
        edu += [{"sex": s, "age": "Y55-74", "isced11": i, "value": v} for i, v in (("ED0-2", 60), ("ED3_4", 30), ("ED5-8", 10))]
    pd.DataFrame(edu).to_csv(eurostat.edu_file(2099), index=False)


def test_one_way_margins(tables):
    m = eurostat.target_margins(2099)
    assert all(sum(d.values()) == pytest.approx(1.0) for d in m.values())
    # 18-24 counts 0.4 of Y15-19 plus Y20-24: 1.4 bands vs 2 bands for 25-34
    assert m["age_band"]["18-24"] / m["age_band"]["25-34"] == pytest.approx(1.4 / 2)
    assert m["gender"] == {"male": pytest.approx(0.5), "female": pytest.approx(0.5)}
    assert m["edu3"] == {"low": pytest.approx(0.5), "mid": pytest.approx(0.3), "high": pytest.approx(0.2)}


def test_joint_targets_sum_to_one_and_cover_every_cell(tables):
    j = eurostat.joint_targets(2099)
    assert j["region_age_sex"]["share"].sum() == pytest.approx(1.0)
    assert j["age_sex_edu"]["share"].sum() == pytest.approx(1.0)
    assert len(j["age_sex_edu"]) == len(schema.AGE_BANDS) * len(schema.GENDERS) * 3
    # one row per schema region x age x sex, even though 12 NUTS-1 regions collapse onto 7
    keys = j["region_age_sex"][["region", "age_band", "gender"]]
    assert not keys.duplicated().any()
    assert len(keys) == len(schema.REGIONS) * len(schema.AGE_BANDS) * len(schema.GENDERS)


def test_65_plus_education_is_derived_from_55_74_minus_55_64(tables):
    j = eurostat.joint_targets(2099)["age_sex_edu"]
    old = j[(j.age_band == "65+") & (j.gender == "male")].set_index("edu3")["share"]
    # 55-64 and 65-74 are each 200 people per region-sex: (60*400 - 50*200) / 200 = 70, etc.
    assert (old / old.sum()).to_dict() == {"low": pytest.approx(0.7), "mid": pytest.approx(0.3),
                                           "high": pytest.approx(0.0)}
