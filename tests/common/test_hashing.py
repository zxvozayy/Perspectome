"""src/common/hashing.py: the one persona_set_hash."""

import hashlib

import pandas as pd

from src.common.hashing import file_hash, sha256_bytes


def test_same_bytes_same_hash(tmp_path):
    f1, f2 = tmp_path / "a.csv", tmp_path / "b.csv"
    df = pd.DataFrame({"persona_id": ["p1", "p2"], "weight": [1.0, 1.0]})
    df.to_csv(f1, index=False)
    df.to_csv(f2, index=False)
    assert file_hash(f1) == file_hash(f2)


def test_different_bytes_different_hash(tmp_path):
    f1, f2 = tmp_path / "a.csv", tmp_path / "b.csv"
    pd.DataFrame({"x": [1]}).to_csv(f1, index=False)
    pd.DataFrame({"x": [2]}).to_csv(f2, index=False)
    assert file_hash(f1) != file_hash(f2)


def test_format_is_prefixed_hex():
    h = sha256_bytes(b"abc")
    assert h == "sha256:" + hashlib.sha256(b"abc").hexdigest()
    assert len(h.split(":")[1]) == 64
