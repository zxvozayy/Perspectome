"""synth.py and attach.py on a hand-made core (no real data needed)."""

import numpy as np
import pandas as pd
import pytest

from src.common import schema
from src.personas import attach, rules, synth


@pytest.fixture(scope="module")
def core():
    """600 people: every student is single and aged 18-24; every retiree is 55+."""
    rng = np.random.default_rng(1)
    n = 600
    age = rng.choice(schema.AGE_BANDS, n)
    young = age == "18-24"
    old = np.isin(age, ["55-64", "65+"])
    employment = np.where(young, "student", np.where(old, "retired", rng.choice(["employed", "homemaker"], n)))
    marital = np.where(young, "single", rng.choice(["married", "divorced", "widowed"], n))
    education = rng.choice(schema.EDUCATION_LEVELS, n)
    frame = pd.DataFrame({
        "age_band": age, "gender": rng.choice(schema.GENDERS, n), "region": rng.choice(schema.REGIONS, n),
        "education_level": education, "edu3": np.where(education == "primary", "low", "mid"),
        "settlement_type": rng.choice(schema.SETTLEMENT_TYPES, n), "marital_status": marital,
        "employment_status": employment, "income_decile": rng.integers(1, 11, n),
        "religiosity_band": rng.choice(schema.RELIGIOSITY_BANDS, n),
        "political_leaning_band": rng.choice(schema.POLITICAL_BANDS, n), "weight": 1.0,
    })
    return frame


@pytest.fixture(scope="module")
def synthetic(core):
    return synth.synthesize(core, 3000, seed=0)


def test_same_seed_same_people(core, synthetic):
    assert synth.synthesize(core, 3000, seed=0).equals(synthetic)
    assert not synth.synthesize(core, 3000, seed=1).equals(synthetic)


def test_every_value_is_a_schema_category(synthetic):
    for field, allowed in schema.CATEGORIES.items():
        assert set(synthetic[field]) <= set(allowed), field
    assert synthetic["persona_id"].is_unique


def test_no_hard_rule_is_broken(synthetic):
    s = rules.summary(synthetic.assign(weight=1.0))
    assert s.loc[s.kind == "hard", "n"].sum() == 0


def test_joint_structure_survives(synthetic):
    """Students stay young and single, retirees stay old: combinations aren't drawn independently."""
    students = synthetic[synthetic.employment_status == "student"]
    assert (students.age_band == "18-24").mean() > 0.95
    assert (students.marital_status == "single").mean() > 0.95
    retired = synthetic[synthetic.employment_status == "retired"]
    assert retired.age_band.isin(["55-64", "65+"]).mean() > 0.95


def test_marginals_follow_the_core(core, synthetic):
    for field in ("age_band", "region", "religiosity_band"):
        a = core[field].value_counts(normalize=True)
        b = synthetic[field].value_counts(normalize=True)
        assert (a - b).abs().max() < 0.04, field


def test_attach_fills_every_synthetic_field(synthetic):
    lits = pd.DataFrame({
        "age_band": schema.AGE_BANDS * 4, "gender": list(schema.GENDERS) * 12,
        "education_level": [schema.EDUCATION_LEVELS[i % 5] for i in range(24)],
        "region": [schema.REGIONS[i % 7] for i in range(24)], "weight": 1.0,
        "employment_status": ["employed"] * 24, "household_size": [i % 5 + 1 for i in range(24)],
        "tenure": [schema.TENURES[i % 3] for i in range(24)], "sector": [schema.SECTORS[i % 5] for i in range(24)],
        "informal": [i % 2 == 0 for i in range(24)],
    })
    out = attach.attach(synthetic, lits, seed=0)
    assert set(schema.SYNTHETIC_FIELDS) <= set(out.columns)
    assert out["household_size"].notna().all() and set(out["tenure"]) <= set(schema.TENURES)
    employed = out.employment_status == "employed"
    assert out.loc[employed, "sector"].notna().all() and out.loc[~employed, "sector"].isna().all()
    assert set(out["concern"]) <= {"cost_of_living", "poverty", "education", "other"}
    # smoking follows the published shares by sex (42.9% of men, 17.5% of women), within sampling error
    men = out[out.gender == "male"]
    assert abs(men["smoker"].mean() - 0.429) < 0.05


SCRIPT = """
import hashlib, numpy as np, pandas as pd
from src.common import schema
from src.personas import synth
rng = np.random.default_rng(5); n = 300
edu = rng.choice(schema.EDUCATION_LEVELS, n)
core = pd.DataFrame({f: rng.choice(v, n) for f, v in schema.CATEGORIES.items()})
core["education_level"] = edu
core["edu3"] = np.where(edu == "primary", "low", "mid")
core["weight"] = 1.0
print(hashlib.sha256(synth.synthesize(core, 500, seed=3).to_csv(index=False).encode()).hexdigest())
"""


def test_same_seed_same_people_across_processes():
    """Python randomizes set/dict hashing per process; the draw must not depend on it."""
    import os
    import subprocess
    import sys
    out = []
    for hash_seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        out.append(subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True,
                                  env=env, check=True).stdout.strip())
    assert out[0] == out[1] and len(out[0]) == 64
