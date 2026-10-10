# tests/test_intervention_plan_reason_codes_pg.py
# Live PostgreSQL round-trip for InterventionPlan.reason_codes: ORM
# insert / read-back in a separate session / update against the migrated
# TEXT[] column, empty-array vs SQL NULL semantics, and pg_catalog agreement
# with migration 009. DSN guard + throwaway schema: tests/conftest.py.

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention import InterventionPlan

pytestmark = pytest.mark.integration

MIGRATION_009 = (
    Path(__file__).resolve().parents[1] / "db" / "migrations" / "009_intervention.sql"
)


async def _read_plan(engine, plan_id) -> InterventionPlan:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                select(InterventionPlan).where(InterventionPlan.id == plan_id)
            )
        ).scalar_one()


async def test_reason_codes_insert_read_update_round_trip(pg_engine, pg_seed):
    """ORM insert -> separate-session read-back (values + order preserved) ->
    update in another session -> fresh read-back. Exercises the corrected
    ARRAY(Text) declaration against the real TEXT[] column end to end."""
    now = datetime.now(UTC)
    original = ["LOW_ATTENDANCE", "EXAM_APPROACHING", "DECLINING_PERFORMANCE"]
    plan_id = uuid.uuid4()
    plan = InterventionPlan(
        id=plan_id, case_id=pg_seed.case_id, created_by="SYSTEM_AGENT",
        status="PROPOSED",
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
        reason_codes=original,
        evidence={},
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(plan)
        await session.commit()

    row = await _read_plan(pg_engine, plan_id)
    assert row.reason_codes == original
    assert isinstance(row.reason_codes, list)
    assert all(isinstance(code, str) for code in row.reason_codes)

    replacement = ["EXAM_APPROACHING", "LOW_ATTENDANCE"]
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionPlan).where(InterventionPlan.id == plan_id)
            )
        ).scalar_one()
        row.reason_codes = replacement  # whole-collection replace, like JSON
        row.updated_at = datetime.now(UTC)
        await session.commit()

    row = await _read_plan(pg_engine, plan_id)
    assert row.reason_codes == replacement  # replaced in order, not merged
    assert len(row.reason_codes) == 2


async def test_reason_codes_empty_array_is_not_null_and_null_is_refused(
    pg_engine, pg_seed
):
    """Migration 009 contract: NOT NULL with no default. An empty array is a
    legitimate distinct value; SQL NULL must be rejected by the database."""
    now = datetime.now(UTC)
    empty_id = uuid.uuid4()
    empty_plan = InterventionPlan(
        id=empty_id, case_id=pg_seed.case_id, created_by="SYSTEM_AGENT",
        status="SUPERSEDED",
        plan_actions=[],
        reason_codes=[],
        evidence={},
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(empty_plan)
        await session.commit()

    row = await _read_plan(pg_engine, empty_id)
    assert row.reason_codes == []
    async with AsyncSession(pg_engine) as session:
        is_null = (
            await session.execute(
                text(
                    "SELECT reason_codes IS NULL FROM intervention_plans "
                    "WHERE id = :pid"
                ),
                {"pid": empty_id},
            )
        ).scalar_one()
    assert is_null is False  # empty array persisted as '{}', not NULL

    null_id = uuid.uuid4()
    null_plan = InterventionPlan(
        id=null_id, case_id=pg_seed.case_id, created_by="SYSTEM_AGENT",
        status="SUPERSEDED",
        plan_actions=[],
        reason_codes=None,  # violates migration 009 NOT NULL
        evidence={},
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(null_plan)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_reason_codes_pg_catalog_matches_migration(pg_engine):
    """pg_catalog agrees with the migration text: text[] / NOT NULL / no
    default — the schema the ORM now writes into."""
    line = next(
        ln.strip()
        for ln in MIGRATION_009.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("reason_codes")
    )
    assert line == "reason_codes TEXT[] NOT NULL,"

    async with AsyncSession(pg_engine) as session:
        row = (
            await session.execute(
                text(
                    "SELECT format_type(a.atttypid, a.atttypmod), "
                    "a.attnotnull, a.atthasdef "
                    "FROM pg_attribute a "
                    "WHERE a.attrelid = 'intervention_plans'::regclass "
                    "AND a.attname = 'reason_codes' AND a.attnum > 0"
                )
            )
        ).one()
    assert row[0] == "text[]", "catalog type must be text[] (migration 009)"
    assert row[1] is True, "column must be NOT NULL"
    assert row[2] is False, "column must have no DEFAULT"
