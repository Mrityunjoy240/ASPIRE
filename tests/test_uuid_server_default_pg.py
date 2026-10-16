# tests/test_uuid_server_default_pg.py
# DEC-03 (approved): the database owns UUID generation for data_conflicts.id
# and institution_rules.id. Migrations 011:6 / 012:7 already declare
# DEFAULT gen_random_uuid(); the ORM now mirrors that with server_default
# (project convention, 05_DATA_API_CONTRACTS general rules; precedent:
# app/models/audit.py). Verified against real PostgreSQL: insert without id
# -> persisted generated UUID -> reload by that id -> distinct second id ->
# explicit id still accepted. DSN guard: tests/conftest.py.
# Review F6 (16 Oct 2026) extends the same live verification to
# intervention_follow_ups.id (migration 017 additive ALTER default).

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conflicts import DataConflict
from app.models.intervention import InterventionFollowUp
from app.models.rules import InstitutionRule

pytestmark = pytest.mark.integration


def _new_conflict(**overrides) -> DataConflict:
    payload = dict(
        entity_table="attendance_records",
        entity_id=uuid.uuid4(),
        existing_value={"attendance_percentage": 72.5},
        incoming_value={"attendance_percentage": 81.25},
        source_a="MANUAL_ENTRY",
        source_b="CSV_IMPORT",
        status="OPEN",
    )
    payload.update(overrides)
    return DataConflict(**payload)


def _new_rule(institution_id: uuid.UUID, **overrides) -> InstitutionRule:
    payload = dict(
        institution_id=institution_id,
        rule_id="attendance_threshold",
        scope_level="INSTITUTION",
        scope_id=None,
        value={"threshold": 75.0},
        effective_from=datetime.now(UTC),
        version=1,
        status="ACTIVE",
    )
    payload.update(overrides)
    return InstitutionRule(**payload)


def _new_follow_up(case_id: uuid.UUID, **overrides) -> InterventionFollowUp:
    payload = dict(
        case_id=case_id,
        trigger_type="ATTENDANCE_INTERVENTION",  # event-driven: due_at NULL
        created_by="SYSTEM",
        created_at=datetime.now(UTC),
    )
    payload.update(overrides)
    return InterventionFollowUp(**payload)


async def _read(engine, model, row_id):
    async with AsyncSession(engine) as session:
        return (
            await session.execute(select(model).where(model.id == row_id))
        ).scalar_one()


async def test_data_conflict_id_generated_by_database(pg_engine):
    # 1) insert through the ORM without supplying an id
    conflict = _new_conflict()
    assert conflict.id is None  # never set client-side
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(conflict)
        await session.flush()  # RETURNING restores the identity
        generated = conflict.id
        await session.commit()
    assert isinstance(generated, UUID)
    assert generated is not None

    # 2) reload using the generated id
    row = await _read(pg_engine, DataConflict, generated)
    assert row.id == generated
    assert row.existing_value == {"attendance_percentage": 72.5}

    # 3) another insert gets a distinct UUID
    second = _new_conflict()
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(second)
        await session.commit()
    assert second.id is not None
    assert second.id != generated

    # 4) explicit id remains compatible
    explicit = uuid.uuid4()
    third = _new_conflict(id=explicit)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(third)
        await session.commit()
    row = await _read(pg_engine, DataConflict, explicit)
    assert row.id == explicit


async def test_institution_rule_id_generated_by_database(pg_engine, pg_seed):
    # 1) insert through the ORM without supplying an id
    rule = _new_rule(pg_seed.institution_id)
    assert rule.id is None
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(rule)
        await session.flush()
        generated = rule.id
        await session.commit()
    assert isinstance(generated, UUID)
    assert generated is not None

    # 2) reload using the generated id
    row = await _read(pg_engine, InstitutionRule, generated)
    assert row.id == generated
    assert row.value == {"threshold": 75.0}

    # 3) another insert gets a distinct UUID
    second = _new_rule(
        pg_seed.institution_id,
        rule_id="assessment_scheme",
        version=1,
        value={"ca_weight": 40},
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(second)
        await session.commit()
    assert second.id is not None
    assert second.id != generated

    # 4) explicit id remains compatible
    explicit = uuid.uuid4()
    third = _new_rule(
        pg_seed.institution_id,
        rule_id="grace_days",
        version=1,
        value={"days": 3},
        id=explicit,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(third)
        await session.commit()
    row = await _read(pg_engine, InstitutionRule, explicit)
    assert row.id == explicit


async def test_intervention_follow_up_id_generated_by_database(pg_engine, pg_seed):
    # 1) insert through the ORM without supplying an id
    follow_up = _new_follow_up(pg_seed.case_id)
    assert follow_up.id is None  # never set client-side
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(follow_up)
        await session.flush()  # RETURNING restores the identity
        generated = follow_up.id
        await session.commit()
    assert isinstance(generated, UUID)
    assert generated is not None

    # 2) reload using the generated id
    row = await _read(pg_engine, InterventionFollowUp, generated)
    assert row.id == generated
    assert row.status == "SCHEDULED"
    assert row.trigger_type == "ATTENDANCE_INTERVENTION"
    assert row.due_at is None

    # 3) another insert gets a distinct UUID
    second = _new_follow_up(pg_seed.case_id)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(second)
        await session.commit()
    assert second.id is not None
    assert second.id != generated

    # 4) explicit id remains compatible
    explicit = uuid.uuid4()
    third = _new_follow_up(pg_seed.case_id, id=explicit)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(third)
        await session.commit()
    row = await _read(pg_engine, InterventionFollowUp, explicit)
    assert row.id == explicit
