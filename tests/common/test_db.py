"""src/common/db.py: everything that can be checked without a live database."""

from pathlib import Path

import pytest

from src.common import db, schema

PERSONAS = Path("src/personas/fixtures/personas.sample.csv")
HELDOUT = Path("src/personas/fixtures/heldout.sample.csv")
ADMIN = "postgresql://postgres.abcdref:s3cret@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"


def test_normalize_hash_unifies_track_a_and_b_forms():
    hexd = "a" * 64
    assert db.normalize_hash(hexd) == f"sha256:{hexd}"
    assert db.normalize_hash(f"sha256:{hexd}") == f"sha256:{hexd}"
    assert db.normalize_hash("SHA256:" + hexd.upper()) == f"sha256:{hexd}"


def test_file_hash_matches_track_b_loader():
    from src.simulation.loader import persona_set_hash
    assert db.file_hash(PERSONAS.read_bytes()) == persona_set_hash(PERSONAS)


def test_fixture_personas_pass_validation():
    rows = db.read_csv_rows(PERSONAS.read_bytes())
    assert db.validate_personas(rows) == []
    held = db.read_csv_rows(HELDOUT.read_bytes())
    assert db.validate_heldout(held, {r["persona_id"] for r in rows}) == []


def test_validation_blocks_leaked_heldout_field():
    rows = db.read_csv_rows(PERSONAS.read_bytes())
    for r in rows:
        r["political_leaning"] = "5"
    assert any("held-out" in p for p in db.validate_personas(rows))


def test_validation_blocks_unknown_category_and_duplicates():
    rows = db.read_csv_rows(PERSONAS.read_bytes())
    rows[0]["age_band"] = "17-19"
    rows[1]["persona_id"] = rows[2]["persona_id"]
    problems = " ".join(db.validate_personas(rows))
    assert "age_band" in problems and "duplicate" in problems


def test_heldout_unknown_column_and_orphans():
    held = [{"persona_id": "x1", "trust_police": "none", "mystery": "1"}]
    problems = " ".join(db.validate_heldout(held, {"p01"}))
    assert "mystery" in problems and "no persona" in problems


def test_heldout_long_keeps_only_schema_items_and_nulls_blanks():
    rows = [{"persona_id": "p1", "trust_police": "none", "religiosity": "", "extra": "x"}]
    out = db.heldout_long(rows)
    assert ("p1", "trust_police", "none") in out
    assert ("p1", "religiosity", None) in out
    assert all(item in schema.HELDOUT_FIELDS for _, item, _ in out)


def test_user_url_swaps_login_and_keeps_host():
    url = db.user_url(ADMIN, "hasan", "abc123")
    assert url == "postgresql://hasan.abcdref:abc123@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"


def test_clean_url_drops_prisma_params_only():
    url = ADMIN.replace(":5432", ":6543") + "?pgbouncer=true&sslmode=require"
    assert db.clean_url(url) == ADMIN.replace(":5432", ":6543") + "?sslmode=require"
    assert db.clean_url(ADMIN) == ADMIN


def test_redact_hides_password():
    assert "s3cret" not in db.redact(ADMIN) and "***" in db.redact(ADMIN)


def test_database_url_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env = tmp_path / ".env"
    env.write_text('# comment\nDATABASE_URL="postgresql://u:p@h:5432/d"\n', encoding="utf-8")
    assert db.database_url(env) == "postgresql://u:p@h:5432/d"
    with pytest.raises(RuntimeError):
        db.database_url(tmp_path / "missing.env")


def test_people_map_to_existing_track_roles():
    sql = (db.MIGRATIONS / "001_init.sql").read_text(encoding="utf-8")
    for role in set(db.PEOPLE.values()):
        assert f"create role {role} nologin" in sql


def test_heldout_schema_is_closed_to_tracks_b_and_d():
    sql = (db.MIGRATIONS / "001_init.sql").read_text(encoding="utf-8")
    grants = [l for l in sql.splitlines() if l.startswith("grant") and "heldout" in l]
    assert grants and all("track_b" not in g and "track_d" not in g for g in grants)
