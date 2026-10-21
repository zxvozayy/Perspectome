"""sources/tables.yaml: every published table is well-formed and carries its provenance."""

import pytest

from src.personas.sources import tables

ALL = tables.load()


@pytest.mark.parametrize("table_id", sorted(ALL))
def test_every_distribution_sums_to_one(table_id):
    for dist in tables.distributions(ALL[table_id]):
        assert all(0 <= v <= 1 for v in dist.values())
        assert sum(dist.values()) == pytest.approx(1.0, abs=0.002)


@pytest.mark.parametrize("table_id", sorted(ALL))
def test_provenance_is_complete(table_id):
    entry = ALL[table_id]
    assert entry["url"].startswith("https://") and 2018 <= entry["year"] <= 2026
    assert isinstance(entry["verified"], bool) and entry["publisher"]


def test_unverified_tables_are_refused_as_targets():
    unverified = next(t for t, e in ALL.items() if not e["verified"])
    with pytest.raises(ValueError, match="not verified"):
        tables.get(unverified, verified_only=True)
    assert tables.get(unverified)["id"] == unverified
