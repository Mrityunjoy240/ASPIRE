# tests/test_case_lifecycle_pg.py
# Real-PostgreSQL persistence and two-connection concurrency for the
# remaining §10.2 mentor rows (R5): RESOLVED → CLOSED and the
# ESCALATION_REQUIRED self-transition. Shared DSN guard and throwaway-schema
# engine live in tests/conftest.py.

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase

pytestmark = pytest.mark.integration


async def _set_status(pg_engine, case_id, status: InterventionCaseStatus):
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = await session.get(InterventionCase, case_id)
        assert case is not None
        case.status = status
        if status == InterventionCaseStatus.RESOLVED:
            case.resolved_at = datetime.now(UTC)
        await session.commit()


async def _load_case(pg_engine, case_id, *, for_update: bool = False):
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        query = select(InterventionCase).where(InterventionCase.id == case_id)
        if for_update:
            query = query.with_for_update()
        result = await session.execute(query)
        return result.scalar_one()


async def _audit_count(pg_engine, case_id, action_type: str) -> int:
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.entity_id == case_id,
                AuditLog.action_type == action_type,
            )
        )
        return int(result.scalar_one())


async def test_close_persists_status_closed_at_and_audit(pg_engine, pg_seed):
    from app.api.routers.cases import _case_row_for_update
    from app.services.case_lifecycle_service import close_case

    await _set_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.RESOLVED)

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(_case_row_for_update(pg_seed.case_id))
        case = result.scalar_one()
        outcome = await close_case(
            session, case=case, actor_id=case.mentor_id
        )
        assert outcome.case_status == "CLOSED"

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.CLOSED
    assert refreshed.closed_at is not None
    assert refreshed.resolved_at is not None
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_CLOSED") == 1


async def test_escalate_persists_audit_and_keeps_status(pg_engine, pg_seed):
    from app.api.routers.cases import _case_row_for_update
    from app.services.case_lifecycle_service import escalate_case

    await _set_status(
        pg_engine, pg_seed.case_id, InterventionCaseStatus.ESCALATION_REQUIRED
    )

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(_case_row_for_update(pg_seed.case_id))
        case = result.scalar_one()
        outcome = await escalate_case(
            session,
            case=case,
            actor_id=case.mentor_id,
            target="HOD",
            note="Student not engaging with AI guidance",
        )
        assert outcome.escalated_to == "HOD"

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.ESCALATION_REQUIRED
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_ESCALATED") == 1


async def test_concurrent_close_single_winner(pg_engine, pg_seed):
    """Two independent connections race close_case on the same RESOLVED row
    through the real FOR UPDATE lock. Winner commits; loser re-reads CLOSED
    and is refused (ILLEGAL_TRANSITION → HTTP 409 at the router). Exactly
    one CASE_CLOSED audit row."""
    from app.api.routers.cases import _case_row_for_update
    from app.services.case_lifecycle_service import (
        CaseLifecycleError,
        close_case,
    )

    await _set_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.RESOLVED)

    a_holding = asyncio.Event()
    b_attempted = asyncio.Event()
    a_release = asyncio.Event()

    async def run_winner():
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            result = await session.execute(_case_row_for_update(pg_seed.case_id))
            case = result.scalar_one()
            a_holding.set()
            await b_attempted.wait()
            await a_release.wait()
            return await close_case(session, case=case, actor_id=case.mentor_id)
        finally:
            await session.close()

    async def run_loser():
        await a_holding.wait()
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            b_attempted.set()
            result = await session.execute(_case_row_for_update(pg_seed.case_id))
            case = result.scalar_one()
            return await close_case(session, case=case, actor_id=case.mentor_id)
        except CaseLifecycleError as exc:
            await session.rollback()
            return exc
        finally:
            await session.close()

    task_w = asyncio.create_task(run_winner())
    task_l = asyncio.create_task(run_loser())
    await a_holding.wait()
    await b_attempted.wait()
    done, _ = await asyncio.wait({task_l}, timeout=0.5)
    assert not done, "loser must block on the winner's FOR UPDATE row lock"
    a_release.set()
    winner, loser = await asyncio.gather(task_w, task_l)

    assert winner.case_status == "CLOSED"
    assert isinstance(loser, CaseLifecycleError)
    assert loser.code == "ILLEGAL_TRANSITION"

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.CLOSED
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_CLOSED") == 1


async def test_sequential_escalations_each_write_an_audit_row(pg_engine, pg_seed):
    """The self-transition is legal repeatedly (HOD, then CT): each action
    is its own CASE_ESCALATED audit row; status never moves."""
    from app.api.routers.cases import _case_row_for_update
    from app.services.case_lifecycle_service import escalate_case

    await _set_status(
        pg_engine, pg_seed.case_id, InterventionCaseStatus.ESCALATION_REQUIRED
    )

    for target in ("HOD", "CT"):
        async with AsyncSession(pg_engine, expire_on_commit=False) as session:
            result = await session.execute(_case_row_for_update(pg_seed.case_id))
            case = result.scalar_one()
            outcome = await escalate_case(
                session, case=case, actor_id=case.mentor_id, target=target
            )
            assert outcome.escalated_to == target

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.ESCALATION_REQUIRED
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_ESCALATED") == 2
