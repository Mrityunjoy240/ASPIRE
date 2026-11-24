# tests/test_uuid_server_default.py
# DEC-03 static agreement: ORM id declarations mirror migrations 011/012
# (DEFAULT gen_random_uuid()) so real-PostgreSQL inserts that omit id work.
# Review F6 extends the same agreement to intervention_follow_ups via
# migration 017 (ALTER COLUMN ... SET DEFAULT, the additive form).
# Live verification: tests/test_uuid_server_default_pg.py. CI has no
# PostgreSQL service, so this static pair is what the CI job executes.

from pathlib import Path

from sqlalchemy.sql.elements import TextClause

from app.models.conflicts import DataConflict
from app.models.intervention import InterventionFollowUp
from app.models.rules import InstitutionRule

MIGRATIONS = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _migration_has_id_default(filename: str) -> bool:
    lines = (MIGRATIONS / filename).read_text(encoding="utf-8").splitlines()
    id_lines = [ln.strip() for ln in lines if ln.strip().startswith("id UUID")]
    assert len(id_lines) == 1, f"{filename}: expected exactly one id line"
    return "DEFAULT gen_random_uuid()" in id_lines[0]


def _migration_has_alter_id_default(filename: str) -> bool:
    """Additive form (migration 017): no id line — the default arrives as
    `ALTER TABLE ... ALTER COLUMN id SET DEFAULT gen_random_uuid()`."""
    content = (MIGRATIONS / filename).read_text(encoding="utf-8")
    return "ALTER COLUMN id SET DEFAULT gen_random_uuid()" in " ".join(
        content.split()
    )


def _server_default_sql(col) -> str:
    arg = col.server_default.arg
    return arg.text if isinstance(arg, TextClause) else str(arg)


def test_data_conflict_id_server_default_matches_migration():
    col = DataConflict.__table__.c.id
    assert col.primary_key
    assert col.server_default is not None
    assert "gen_random_uuid()" in _server_default_sql(col)
    assert _migration_has_id_default("011_data_conflicts.sql")


def test_institution_rule_id_server_default_matches_migration():
    col = InstitutionRule.__table__.c.id
    assert col.primary_key
    assert col.server_default is not None
    assert "gen_random_uuid()" in _server_default_sql(col)
    assert _migration_has_id_default("012_institution_rules.sql")


def test_intervention_follow_up_id_server_default_matches_migration():
    """F6: the follow-up ORM id mirrors migration 017 (ADR-004 Amendment 1
    — 016 shipped without the server-side default the 05 §9 contract and
    DEC-03 pattern require)."""
    col = InterventionFollowUp.__table__.c.id
    assert col.primary_key
    assert col.server_default is not None
    assert "gen_random_uuid()" in _server_default_sql(col)
    assert _migration_has_alter_id_default("017_followup_contract_alignment.sql")
