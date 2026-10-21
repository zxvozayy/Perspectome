"""Published figures (tables.yaml) as lookup tables, with their provenance.

    from src.personas.sources import tables
    tables.get("daily_smoking_by_sex")["values"]["male"]["daily"]   # 0.429
    tables.get("religiosity_self_description", verified_only=True)  # raises: not verified yet
"""

from __future__ import annotations

from pathlib import Path

import yaml

FILE = Path(__file__).with_name("tables.yaml")
REQUIRED = ("id", "title", "publisher", "year", "url", "verified", "dims", "values")


def load(path=FILE) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    out = {}
    for e in entries:
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            raise ValueError(f"table {e.get('id')!r} is missing {missing}")
        if e["id"] in out:
            raise ValueError(f"duplicate table id {e['id']!r}")
        out[e["id"]] = e
    return out


def get(table_id: str, verified_only: bool = False, path=FILE) -> dict:
    """One table; with ``verified_only`` an unverified table raises instead of being used."""
    entry = load(path)[table_id]
    if verified_only and not entry["verified"]:
        raise ValueError(f"table {table_id!r} is not verified against its primary source")
    return entry


def distributions(entry: dict) -> list[dict]:
    """Every leaf distribution of a table: category -> share mappings, at any nesting depth."""
    def leaves(node):
        if all(isinstance(v, (int, float)) for v in node.values()):
            return [node]
        return [leaf for v in node.values() for leaf in leaves(v)]
    return leaves(entry["values"])
