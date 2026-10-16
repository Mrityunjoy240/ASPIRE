# tests/test_intervention_plan_reason_codes.py
# Static model<->migration agreement for InterventionPlan.reason_codes: the
# ORM declaration must render the authoritative migration 009 column
# (reason_codes TEXT[] NOT NULL, no default). Live PostgreSQL round-trip:
# tests/test_intervention_plan_reason_codes_pg.py.

from pathlib import Path

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql import ARRAY

from app.models.intervention import InterventionPlan

MIGRATION_009 = (
    Path(__file__).resolve().parents[1] / "db" / "migrations" / "009_intervention.sql"
)


def _column():
    return InterventionPlan.__table__.c.reason_codes


def test_reason_codes_orm_type_renders_migration_text_array():
    col = _column()
    assert isinstance(col.type, ARRAY), "reason_codes must be a PostgreSQL ARRAY"
    assert col.type.compile(dialect=postgresql.dialect()) == "TEXT[]"
    assert col.nullable is False  # migration 009: NOT NULL
    assert col.default is None
    assert col.server_default is None  # migration 009: no DEFAULT


def test_reason_codes_matches_migration_009_declaration():
    line = next(
        ln.strip()
        for ln in MIGRATION_009.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("reason_codes")
    )
    assert line == "reason_codes TEXT[] NOT NULL,"


def test_reason_codes_sqlite_variant_keeps_in_memory_query_tests():
    # The F-01 real-query regression test builds these tables on SQLite,
    # where a PostgreSQL ARRAY type cannot compile DDL.
    assert _column().type.compile(dialect=sqlite.dialect()) == "JSON"
