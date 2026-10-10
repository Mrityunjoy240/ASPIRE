# tests/test_jsonb_audit_rules_conflicts_pg.py
# Live PostgreSQL round-trip for the JSONB columns corrected in this task:
# audit_log.previous_state / new_state (007), data_conflicts existing_value /
# incoming_value / resolution (011), institution_rules.value (012).
# ORM insert -> separate-session read-back -> whole-value replacement ->
# fresh-session read with structure preserved; NULL behavior per migration;
# pg_catalog confirms jsonb + nullability + no defaults. DSN guard and
# throwaway schema: tests/conftest.py (pg_engine / pg_seed).

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.conflicts import DataConflict
from app.models.rules import InstitutionRule

pytestmark = pytest.mark.integration


async def _read(engine, model, row_id):
    async with AsyncSession(engine) as session:
        return (
            await session.execute(select(model).where(model.id == row_id))
        ).scalar_one()


async def test_audit_log_states_round_trip(pg_engine, pg_seed):
    """previous_state/new_state insert (mirroring deps.log_audit), read in a
    separate session, whole-value replacement, fresh read; then NULL stays
    NULL (migration 007: both columns nullable)."""
    now = datetime.now(UTC)
    log = AuditLog(
        actor_id=pg_seed.student_user_id,
        actor_type="USER",
        action_type="PLAN_DECIDED",
        entity_table="intervention_cases",
        entity_id=pg_seed.case_id,
        previous_state={"case_status": "PLAN_PROPOSED", "plan_status": "PROPOSED"},
        new_state={"case_status": "PENDING_APPROVAL", "student_decision": "ACCEPTED"},
        source_system="STUDENT_APP",
        created_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(log)
        await session.commit()
    log_id = log.id

    row = await _read(pg_engine, AuditLog, log_id)
    assert row.previous_state == {
        "case_status": "PLAN_PROPOSED",
        "plan_status": "PROPOSED",
    }
    assert row.new_state == {
        "case_status": "PENDING_APPROVAL",
        "student_decision": "ACCEPTED",
    }

    new_previous = {"case_status": "PENDING_APPROVAL", "plan_status": "PROPOSED"}
    new_state = {
        "case_status": "ACTIVE",
        "student_decision": "ACCEPTED",
        "facts": ["Attendance: 72.5%", "Threshold: 76%"],
    }
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(select(AuditLog).where(AuditLog.id == log_id))
        ).scalar_one()
        row.previous_state = new_previous
        row.new_state = new_state
        await session.commit()

    row = await _read(pg_engine, AuditLog, log_id)
    assert row.previous_state == new_previous
    assert row.new_state == new_state  # nested list preserved
    assert row.new_state["facts"][0] == "Attendance: 72.5%"

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(select(AuditLog).where(AuditLog.id == log_id))
        ).scalar_one()
        row.previous_state = None
        await session.commit()

    row = await _read(pg_engine, AuditLog, log_id)
    assert row.previous_state is None  # SQL NULL, not '{}'
    async with AsyncSession(pg_engine) as session:
        is_null = (
            await session.execute(
                text(
                    "SELECT previous_state IS NULL FROM audit_log WHERE id = :rid"
                ),
                {"rid": log_id},
            )
        ).scalar_one()
    assert is_null is True


async def test_data_conflict_values_round_trip(pg_engine, pg_seed):
    """existing_value/incoming_value insert (NOT NULL per 011), read back;
    resolution starts NULL, then whole-value replacement; empty vs NULL
    distinction for the nullable resolution column."""
    conflict = DataConflict(
        id=uuid.uuid4(),  # explicit id still supported (DEC-03 added server_default)
        entity_table="attendance_records",
        entity_id=uuid.uuid4(),
        existing_value={"attendance_percentage": 72.5, "source_row": 118},
        incoming_value={"attendance_percentage": 81.25, "source_row": 118},
        source_a="MANUAL_ENTRY",
        source_b="CSV_IMPORT",
        status="OPEN",
        resolver_id=None,
        resolution=None,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(conflict)
        await session.commit()
    cid = conflict.id

    row = await _read(pg_engine, DataConflict, cid)
    assert row.existing_value == {"attendance_percentage": 72.5, "source_row": 118}
    assert row.incoming_value == {"attendance_percentage": 81.25, "source_row": 118}
    assert row.resolution is None

    new_resolution = {
        "action": "ACCEPT_INCOMING",
        "resolver_note": "CSV import matches class register",
        "facts": ["existing: 72.5%", "incoming: 81.25%"],
    }
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(select(DataConflict).where(DataConflict.id == cid))
        ).scalar_one()
        row.resolution = new_resolution
        row.status = "RESOLVED"
        await session.commit()

    row = await _read(pg_engine, DataConflict, cid)
    assert row.resolution == new_resolution
    assert row.resolution["facts"][1] == "incoming: 81.25%"

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(select(DataConflict).where(DataConflict.id == cid))
        ).scalar_one()
        row.resolution = None
        await session.commit()

    row = await _read(pg_engine, DataConflict, cid)
    assert row.resolution is None
    async with AsyncSession(pg_engine) as session:
        is_null = (
            await session.execute(
                text("SELECT resolution IS NULL FROM data_conflicts WHERE id = :cid"),
                {"cid": cid},
            )
        ).scalar_one()
    assert is_null is True


async def test_data_conflict_not_null_enforced(pg_engine):
    """Migration 011 existing_value/incoming_value are NOT NULL: a NULL insert
    must be rejected by the database (jsonb NOT NULL contract)."""
    bad = DataConflict(
        id=uuid.uuid4(),
        entity_table="attendance_records",
        entity_id=uuid.uuid4(),
        existing_value=None,  # violates 011 NOT NULL
        incoming_value={"attendance_percentage": 81.25},
        source_a="MANUAL_ENTRY",
        source_b="CSV_IMPORT",
        status="OPEN",
    )
    async with AsyncSession(pg_engine) as session:
        session.add(bad)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_institution_rule_value_round_trip(pg_engine, pg_seed):
    """value insert (NOT NULL per 012), read back, whole-value replacement,
    and the attendance-router-shaped select of just InstitutionRule.value."""
    rule = InstitutionRule(
        id=uuid.uuid4(),  # explicit id still supported (DEC-03 added server_default)
        institution_id=pg_seed.institution_id,
        rule_id="attendance_threshold",
        scope_level="INSTITUTION",
        scope_id=None,
        value={"threshold": 76.0, "grace_days": 3, "retake_allowed": True},
        effective_from=datetime.now(UTC),
        version=1,
        status="ACTIVE",
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(rule)
        await session.commit()
    rid = rule.id

    row = await _read(pg_engine, InstitutionRule, rid)
    assert row.value == {"threshold": 76.0, "grace_days": 3, "retake_allowed": True}

    new_value = {"threshold": 80.0, "grace_days": 0, "retake_allowed": False}
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InstitutionRule).where(InstitutionRule.id == rid)
            )
        ).scalar_one()
        row.value = new_value
        row.version = 2
        await session.commit()

    row = await _read(pg_engine, InstitutionRule, rid)
    assert row.value == new_value

    # exact query shape used by app/api/routers/attendance.py
    async with AsyncSession(pg_engine) as session:
        selected = (
            await session.execute(
                select(InstitutionRule.value).where(
                    InstitutionRule.id == rid,
                    InstitutionRule.status == "ACTIVE",
                )
            )
        ).scalar_one()
    assert selected == new_value


async def test_jsonb_catalog_matches_migration(pg_engine):
    """pg_catalog reports jsonb for all six columns with migration 007/011/012
    nullability and no defaults."""
    expected = [
        ("audit_log", "previous_state", False),
        ("audit_log", "new_state", False),
        ("data_conflicts", "existing_value", True),
        ("data_conflicts", "incoming_value", True),
        ("data_conflicts", "resolution", False),
        ("institution_rules", "value", True),
    ]
    async with AsyncSession(pg_engine) as session:
        for table, column, expect_not_null in expected:
            row = (
                await session.execute(
                    text(
                        "SELECT format_type(a.atttypid, a.atttypmod), "
                        "a.attnotnull, a.atthasdef "
                        "FROM pg_attribute a "
                        "WHERE a.attrelid = CAST(:rel AS regclass) "
                        "AND a.attname = :col AND a.attnum > 0"
                    ),
                    {"rel": table, "col": column},
                )
            ).one()
            assert row[0] == "jsonb", f"{table}.{column}: catalog type must be jsonb"
            assert row[1] is expect_not_null, (
                f"{table}.{column}: attnotnull must be {expect_not_null} "
                "per migrations 007/011/012"
            )
            assert row[2] is False, f"{table}.{column}: no DEFAULT in migration"
