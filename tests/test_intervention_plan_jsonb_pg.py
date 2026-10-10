# tests/test_intervention_plan_jsonb_pg.py
# Live PostgreSQL round-trip for the JSONB columns corrected in this task:
# InterventionPlan.plan_actions / evidence and InterventionCase.trigger_events.
# ORM insert (seed) -> separate-session read-back -> full replacement ->
# fresh-session read with structure preserved; empty vs SQL NULL for the
# nullable trigger_events; pg_catalog reports jsonb with migration 009's
# nullability contract. DSN guard + throwaway schema: tests/conftest.py.

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention import InterventionCase, InterventionPlan

pytestmark = pytest.mark.integration


async def _read_plan(engine, plan_id) -> InterventionPlan:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                select(InterventionPlan).where(InterventionPlan.id == plan_id)
            )
        ).scalar_one()


async def _read_case(engine, case_id) -> InterventionCase:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                select(InterventionCase).where(InterventionCase.id == case_id)
            )
        ).scalar_one()


async def test_plan_actions_and_evidence_round_trip(pg_engine, pg_seed):
    """Insert (via the ORM seed) -> separate-session read-back -> replace the
    whole JSON values -> fresh-session read. Nested structures must survive
    without silent reshaping (engine-realistic action shapes, nested dict and
    list evidence)."""
    original_actions = [{"type": "ATTEND_CLASS", "subject": "DBMS"}]
    row = await _read_plan(pg_engine, pg_seed.plan_id)
    assert row.plan_actions == original_actions
    assert row.evidence == {}

    new_actions = [
        {"type": "ATTEND_CLASS", "subject": "DBMS", "target_classes": 4},
        {"type": "STUDY_BLOCK", "topic": "Weak areas in DBMS", "duration_min": 60},
    ]
    new_evidence = {
        "attendance": 72.5,
        "thresholds": {"required": 80, "recover_in": 3},
        "notes": ["Attendance: 72.5%", "Threshold: 76%"],
    }
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionPlan).where(
                    InterventionPlan.id == pg_seed.plan_id
                )
            )
        ).scalar_one()
        row.plan_actions = new_actions  # whole-value replacement (tracked)
        row.evidence = new_evidence
        row.updated_at = datetime.now(UTC)
        await session.commit()

    row = await _read_plan(pg_engine, pg_seed.plan_id)
    assert row.plan_actions == new_actions
    assert row.evidence == new_evidence
    # shape preserved, not silently reshaped
    assert row.evidence["thresholds"] == {"required": 80, "recover_in": 3}
    assert row.evidence["notes"][0] == "Attendance: 72.5%"
    assert row.plan_actions[1]["type"] == "STUDY_BLOCK"


async def test_trigger_events_round_trip_null_vs_empty(pg_engine, pg_seed):
    """trigger_events is JSONB and nullable (migration 009): None must read
    back as None (SQL NULL), [] must persist as '{}' and stay distinct from
    NULL, and a populated list must round-trip in order."""
    case = await _read_case(pg_engine, pg_seed.case_id)
    assert case.trigger_events is None  # seed did not set it

    async with AsyncSession(pg_engine) as session:
        is_null = (
            await session.execute(
                text(
                    "SELECT trigger_events IS NULL FROM intervention_cases "
                    "WHERE id = :cid"
                ),
                {"cid": pg_seed.case_id},
            )
        ).scalar_one()
    assert is_null is True

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionCase).where(
                    InterventionCase.id == pg_seed.case_id
                )
            )
        ).scalar_one()
        row.trigger_events = ["EVT-ATTENDANCE-RISK", "EVT-EXAM-APPROACHING"]
        await session.commit()

    row = await _read_case(pg_engine, pg_seed.case_id)
    assert row.trigger_events == ["EVT-ATTENDANCE-RISK", "EVT-EXAM-APPROACHING"]

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionCase).where(
                    InterventionCase.id == pg_seed.case_id
                )
            )
        ).scalar_one()
        row.trigger_events = []
        await session.commit()

    row = await _read_case(pg_engine, pg_seed.case_id)
    assert row.trigger_events == []
    async with AsyncSession(pg_engine) as session:
        is_null = (
            await session.execute(
                text(
                    "SELECT trigger_events IS NULL FROM intervention_cases "
                    "WHERE id = :cid"
                ),
                {"cid": pg_seed.case_id},
            )
        ).scalar_one()
    assert is_null is False  # [] stored as '{}', not NULL

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionCase).where(
                    InterventionCase.id == pg_seed.case_id
                )
            )
        ).scalar_one()
        row.trigger_events = None
        await session.commit()

    row = await _read_case(pg_engine, pg_seed.case_id)
    assert row.trigger_events is None  # SQL NULL again


async def test_jsonb_catalog_matches_migration(pg_engine):
    """pg_catalog reports jsonb for all three columns with migration 009's
    nullability and no defaults."""
    expected = [
        ("trigger_events", False),
        ("plan_actions", True),
        ("evidence", True),
    ]
    async with AsyncSession(pg_engine) as session:
        for column, expect_not_null in expected:
            row = (
                await session.execute(
                    text(
                        "SELECT format_type(a.atttypid, a.atttypmod), "
                        "a.attnotnull, a.atthasdef "
                        "FROM pg_attribute a "
                        "WHERE a.attrelid = CAST(:rel AS regclass) "
                        "AND a.attname = :col AND a.attnum > 0"
                    ),
                    {
                        "rel": (
                            "intervention_cases"
                            if column == "trigger_events"
                            else "intervention_plans"
                        ),
                        "col": column,
                    },
                )
            ).one()
            assert row[0] == "jsonb", f"{column}: catalog type must be jsonb"
            assert row[1] is expect_not_null, (
                f"{column}: attnotnull must be {expect_not_null} (migration 009)"
            )
            assert row[2] is False, f"{column}: no DEFAULT in migration 009"
