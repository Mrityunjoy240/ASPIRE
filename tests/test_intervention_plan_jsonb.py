# tests/test_intervention_plan_jsonb.py
# Static model<->migration agreement for the three in-scope JSONB columns:
# InterventionCase.trigger_events, InterventionPlan.plan_actions and
# InterventionPlan.evidence must render JSONB with the exact nullability of
# migration 009 (the schema authority). Live round-trip evidence:
# tests/test_intervention_plan_jsonb_pg.py.

from pathlib import Path

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql import JSONB

from app.models.intervention import InterventionCase, InterventionPlan

MIGRATION_009 = (
    Path(__file__).resolve().parents[1] / "db" / "migrations" / "009_intervention.sql"
)


def _migration_line(prefix: str) -> str:
    return next(
        ln.strip()
        for ln in MIGRATION_009.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith(prefix)
    )


_CASE = InterventionCase.__table__
_PLAN = InterventionPlan.__table__


def test_trigger_events_renders_jsonb_and_stays_nullable():
    col = _CASE.c.trigger_events
    assert isinstance(col.type, JSONB)
    assert col.type.compile(dialect=postgresql.dialect()) == "JSONB"
    assert col.nullable is True
    assert col.default is None and col.server_default is None
    line = _migration_line("trigger_events")
    assert line.startswith("trigger_events JSONB,")
    assert "NOT NULL" not in line


def test_plan_actions_renders_jsonb_not_null():
    col = _PLAN.c.plan_actions
    assert isinstance(col.type, JSONB)
    assert col.type.compile(dialect=postgresql.dialect()) == "JSONB"
    assert col.nullable is False
    assert col.default is None and col.server_default is None
    line = _migration_line("plan_actions")
    assert line.startswith("plan_actions JSONB NOT NULL,")
    assert "NOT NULL" in line


def test_evidence_renders_jsonb_not_null():
    col = _PLAN.c.evidence
    assert isinstance(col.type, JSONB)
    assert col.type.compile(dialect=postgresql.dialect()) == "JSONB"
    assert col.nullable is False
    assert col.default is None and col.server_default is None
    line = _migration_line("evidence")
    assert line.startswith("evidence JSONB NOT NULL,")
    assert "NOT NULL" in line


def test_sqlite_variants_keep_in_memory_query_test_working():
    # The F-01 real-query regression test builds these tables on SQLite,
    # where a PostgreSQL JSONB type cannot compile DDL (same pattern as the
    # reason_codes ARRAY variant).
    for col in (_CASE.c.trigger_events, _PLAN.c.plan_actions, _PLAN.c.evidence):
        assert col.type.compile(dialect=sqlite.dialect()) == "JSON"
