"""src/common/stats.py, labels.py and schema.py — the shared single sources."""

import numpy as np
import pandas as pd
import pytest

from src.common import paths, schema
from src.common.labels import answer_label
from src.common.stats import kish_n_eff, normalize_vec, weighted_mean_rows, weighted_share


def test_kish_n_eff():
    assert kish_n_eff([1, 1, 1, 1]) == pytest.approx(4.0)
    assert kish_n_eff([1, 3]) == pytest.approx(16 / 10)
    assert kish_n_eff([]) == 0.0


def test_normalize_vec_rows_and_zero_vector():
    assert np.allclose(normalize_vec([1, 3]), [0.25, 0.75])
    assert np.allclose(normalize_vec([0, 0, 0]), [1 / 3] * 3)
    assert np.allclose(normalize_vec([[1, 1], [0, 2]]), [[0.5, 0.5], [0, 1]])


def test_weighted_share_ignores_labels_outside_options():
    labels = ["a", "b", None, "x"]
    assert weighted_share(labels, [3, 1, 5, 5], ["a", "b"]) == {"a": 0.75, "b": 0.25}
    assert weighted_share([], [], ["a"]) == {"a": 0.0}


def test_weighted_mean_rows():
    x = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert np.allclose(weighted_mean_rows(x, [3, 1]), [0.75, 0.25])
    assert np.allclose(weighted_mean_rows(x, [0, 0]), [0.5, 0.5])


@pytest.mark.parametrize("value, label", [
    (7.0, "7"), (7, "7"), ("7", "7"), ("7.0", "7"), (np.int64(3), "3"), (np.float64(2.0), "2"),
    (float("nan"), None), ("", None), (None, None), ("quite_a_lot", "quite_a_lot"), (" none ", "none"),
])
def test_answer_label(value, label):
    assert answer_label(value) == label


def test_schema_tables_agree():
    assert list(schema.CATEGORIES) == list(schema.CONDITIONING_FIELDS[1:])
    assert set(schema.CELL_FIELDS) <= set(schema.CATEGORIES)
    assert len(schema.AGE_EDGES) == len(schema.AGE_BANDS)
    assert set(schema.HELDOUT_ROLE) == set(schema.HELDOUT_FIELDS)


def test_fixture_header_is_the_contract():
    assert tuple(pd.read_csv(paths.PERSONAS_FIXTURE, nrows=0).columns) == schema.PERSONA_COLUMNS
