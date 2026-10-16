# tests/test_jsonb_audit_rules_conflicts.py
# Static model<->migration agreement for the six JSONB columns corrected in
# this task: audit_log.previous_state / new_state (007), data_conflicts
# existing_value / incoming_value / resolution (011), institution_rules.value
# (012) must render JSONB with the migration's exact nullability. Live
# round-trip evidence: tests/test_jsonb_audit_rules_conflicts_pg.py.

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from app.models.audit import AuditLog
from app.models.conflicts import DataConflict
from app.models.rules import InstitutionRule

MIGRATIONS = Path(__file__).resolve().parents[1] / "db" / "migrations"
_AUDIT = AuditLog.__table__
_CONFLICTS = DataConflict.__table__
_RULES = InstitutionRule.__table__


def _migration_line(migration: str, prefix: str) -> str:
    return next(
        ln.strip()
        for ln in (MIGRATIONS / migration).read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith(prefix)
    )


def _assert_jsonb(col, migration: str, prefix: str, *, not_null: bool) -> None:
    assert isinstance(col.type, JSONB)
    assert col.type.compile(dialect=postgresql.dialect()) == "JSONB"
    assert col.nullable is (not not_null)
    assert col.default is None and col.server_default is None
    line = _migration_line(migration, prefix)
    if not_null:
        assert line.startswith(f"{prefix} JSONB NOT NULL,")
    else:
        assert line.startswith(f"{prefix} JSONB,")
        assert "NOT NULL" not in line


def test_audit_log_states_render_jsonb_nullable():
    # migration 007: previous_state JSONB, / new_state JSONB, — nullable
    _assert_jsonb(_AUDIT.c.previous_state, "007_audit_log.sql", "previous_state", not_null=False)
    _assert_jsonb(_AUDIT.c.new_state, "007_audit_log.sql", "new_state", not_null=False)


def test_data_conflict_values_render_jsonb():
    # migration 011: existing_value/incoming_value NOT NULL, resolution nullable
    _assert_jsonb(
        _CONFLICTS.c.existing_value, "011_data_conflicts.sql", "existing_value",
        not_null=True,
    )
    _assert_jsonb(
        _CONFLICTS.c.incoming_value, "011_data_conflicts.sql", "incoming_value",
        not_null=True,
    )
    _assert_jsonb(
        _CONFLICTS.c.resolution, "011_data_conflicts.sql", "resolution",
        not_null=False,
    )


def test_institution_rule_value_renders_jsonb_not_null():
    # migration 012: value JSONB NOT NULL,
    _assert_jsonb(_RULES.c.value, "012_institution_rules.sql", "value", not_null=True)
