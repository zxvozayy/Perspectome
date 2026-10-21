"""Unit tests for the post-stratified generator (issue #10).

Raking and fit tests run on small in-memory frames. The end-to-end lineage
(hash reproducibility) test runs only when the real WVS Turkey file is present
locally, and is skipped otherwise (the raw file is never committed).

Run:  python -m pytest src/personas/tests -q
"""


import pandas as pd
import pytest

from src.common import paths, schema
from src.personas import generator, wvs

TURKEY_CSV = paths.DATA_RAW / "wvs7_turkey.csv"

TWO_DIMS = ("age_band", "gender")
TARGETS = {
    "age_band": {"A": 0.5, "B": 0.5},
    "gender": {"male": 0.5, "female": 0.5},
}


@pytest.fixture
def skewed_frame():
    # 70% band A, 30% B; 80% male, 20% female -- both far from the 50/50 targets.
    rows = ([{"age_band": "A", "gender": "male"}] * 56
            + [{"age_band": "A", "gender": "female"}] * 14
            + [{"age_band": "B", "gender": "male"}] * 24
            + [{"age_band": "B", "gender": "female"}] * 6)
    return pd.DataFrame(rows)


# --- raking ----------------------------------------------------------------

def test_rake_matches_targets(skewed_frame):
    w = generator.rake(skewed_frame, TARGETS, dims=TWO_DIMS)
    fit = generator.marginal_fit(skewed_frame, w, TARGETS, dims=TWO_DIMS)
    assert fit["abs_error"].max() < 1e-6


def test_rake_normalizes_to_count(skewed_frame):
    w = generator.rake(skewed_frame, TARGETS, dims=TWO_DIMS)
    assert w.sum() == pytest.approx(len(skewed_frame))


def test_rake_is_deterministic(skewed_frame):
    w1 = generator.rake(skewed_frame, TARGETS, dims=TWO_DIMS)
    w2 = generator.rake(skewed_frame, TARGETS, dims=TWO_DIMS)
    pd.testing.assert_series_equal(w1, w2)


def test_rake_keeps_incomplete_rows_with_weight_one(skewed_frame):
    frame = pd.concat([skewed_frame,
                       pd.DataFrame([{"age_band": None, "gender": "male"}])],
                      ignore_index=True)
    w = generator.rake(frame, TARGETS, dims=TWO_DIMS)
    assert len(w) == len(frame)            # not dropped
    assert w.iloc[-1] == 1.0               # incomplete -> neutral weight


# --- edu3 helper (calibration-only axis) ------------------------------------

@pytest.mark.parametrize("isced,expected", [
    (0, "low"), (1, "low"), (2, "low"), (3, "mid"), (4, "mid"),
    (6, "high"), (8, "high"), (-2, None),
])
def test_edu3_from_isced(isced, expected):
    assert wvs.edu3_from_isced(isced) == expected


# --- hash / lineage ---------------------------------------------------------

@pytest.mark.skipif(not TURKEY_CSV.exists(),
                    reason="real WVS Turkey file not present (never committed)")
def test_generate_lineage_hash_stable(tmp_path):
    # Lineage: same raw file + seed -> identical persona_set_hash.
    s1 = generator.generate(out_dir=tmp_path / "run1", seed=0)
    s2 = generator.generate(out_dir=tmp_path / "run2", seed=0)
    assert s1["persona_set_hash"] == s2["persona_set_hash"]
    assert s1["max_calibration_error"] < 1e-6


@pytest.mark.skipif(not TURKEY_CSV.exists(),
                    reason="real WVS Turkey file not present (never committed)")
def test_generated_output_keeps_heldout_separate(tmp_path):
    generator.generate(out_dir=tmp_path, seed=0)
    personas = pd.read_csv(tmp_path / "personas.csv")
    heldout = pd.read_csv(tmp_path / "heldout.csv")
    assert "weight" in personas.columns
    assert not (set(schema.HELDOUT_FIELDS) & set(personas.columns))  # no leakage
    assert set(personas.columns) & set(heldout.columns) == {"persona_id"}
