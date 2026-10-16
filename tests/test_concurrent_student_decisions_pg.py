# tests/test_concurrent_student_decisions_pg.py
# Genuine two-connection PostgreSQL concurrency test for the student decision
# path (close-out of OQ-A02: "implementation verified, concurrency test
# pending"). Two independent sessions race on the same case/plan through the
# real FOR UPDATE lock, plan selection, audit write and event emission.
# Shared DSN guard and throwaway-schema engine live in tests/conftest.py.

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("winner_decision", "loser_decision"),
    [("ACCEPTED", "DECLINED"), ("DECLINED", "ACCEPTED")],
)
async def test_concurrent_conflicting_student_decisions_single_winner(
    pg_engine, pg_seed, winner_decision, loser_decision
):
    """Two conflicting decisions race on the same case and plan over two
    independent connections. Winner commits first; loser — blocked on the
    same FOR UPDATE row lock, then re-reading the committed state — must fail
    with the documented conflict (ILLEGAL_TRANSITION, mapped to HTTP 409 by
    the router). Exactly one transition, one audit row, one event; no
    contradictory audit/event records."""
    from app.api.routers.cases import _case_row_for_update, _plans_for_case_query
    from app.core.events import EventBus
    from app.services.student_action_service import (
        EVENT_PLAN_ACCEPTED,
        EVENT_PLAN_DECLINED,
        StudentActionError,
        decide_plan,
    )

    winner_reason = "Cannot do mornings" if winner_decision == "DECLINED" else None
    loser_reason = "Not feasible" if loser_decision == "DECLINED" else None
    a_holding = asyncio.Event()  # winner holds the FOR UPDATE row lock
    b_attempted = asyncio.Event()  # loser is about to issue its lock attempt
    a_release = asyncio.Event()  # main observed contention → let winner finish

    winner_events: list = []
    loser_events: list = []
    bus_w, bus_l = EventBus(), EventBus()

    async def record_w(event):
        winner_events.append(event)

    async def record_l(event):
        loser_events.append(event)

    bus_w.subscribe(EVENT_PLAN_ACCEPTED, record_w)
    bus_w.subscribe(EVENT_PLAN_DECLINED, record_w)
    bus_l.subscribe(EVENT_PLAN_ACCEPTED, record_l)
    bus_l.subscribe(EVENT_PLAN_DECLINED, record_l)

    async def run_winner():
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            result = await session.execute(_case_row_for_update(pg_seed.case_id))
            case = result.scalar_one()
            result = await session.execute(_plans_for_case_query(pg_seed.case_id))
            plans = list(result.scalars().all())
            a_holding.set()
            await b_attempted.wait()
            await a_release.wait()
            return await decide_plan(
                session, case=case, plans=plans, decision=winner_decision,
                plan_actions=None, reason=winner_reason,
                actor_id=pg_seed.student_user_id, event_bus=bus_w,
            )
        finally:
            await session.close()

    async def run_loser():
        await a_holding.wait()
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            b_attempted.set()
            # Independent connection: blocks on the winner's row lock.
            result = await session.execute(_case_row_for_update(pg_seed.case_id))
            case = result.scalar_one()
            # Lock-then-read (router order): post-commit state is visible here.
            result = await session.execute(_plans_for_case_query(pg_seed.case_id))
            plans = list(result.scalars().all())
            return await decide_plan(
                session, case=case, plans=plans, decision=loser_decision,
                plan_actions=None, reason=loser_reason,
                actor_id=pg_seed.student_user_id, event_bus=bus_l,
            )
        except StudentActionError as exc:
            await session.rollback()
            return exc
        finally:
            await session.close()

    task_w = asyncio.create_task(run_winner())
    task_l = asyncio.create_task(run_loser())
    await a_holding.wait()
    await b_attempted.wait()
    # Contention evidence (bounded observation only — outcome assertions below
    # do not depend on it): the loser must not finish while the winner holds
    # the row lock, i.e. the real FOR UPDATE serialization is exercised.
    done, _ = await asyncio.wait({task_l}, timeout=0.5)
    assert not done, (
        "loser completed while the winner still held the FOR UPDATE lock — "
        "row-lock contention was not exercised"
    )
    a_release.set()

    winner_result = await task_w
    loser_outcome = await task_l

    # Exactly one transition; the loser received the documented conflict.
    assert isinstance(loser_outcome, StudentActionError)
    assert loser_outcome.code == "ILLEGAL_TRANSITION"  # → HTTP 409 in router
    assert winner_result.student_decision == winner_decision
    assert winner_result.case_status == (
        "REPLAN_REQUIRED" if winner_decision == "DECLINED" else "PENDING_APPROVAL"
    )

    # Event behaviour: winner emitted exactly one, loser emitted none.
    expected_event = (
        EVENT_PLAN_DECLINED if winner_decision == "DECLINED" else EVENT_PLAN_ACCEPTED
    )
    assert [e.event_type for e in winner_events] == [expected_event]
    assert loser_events == []

    # Persisted state, fresh session, post-commit.
    async with AsyncSession(pg_engine) as verify:
        case = (
            await verify.execute(
                select(InterventionCase).where(InterventionCase.id == pg_seed.case_id)
            )
        ).scalar_one()
        plan = (
            await verify.execute(
                select(InterventionPlan).where(InterventionPlan.id == pg_seed.plan_id)
            )
        ).scalar_one()
        all_plans = (
            await verify.execute(
                select(InterventionPlan).where(
                    InterventionPlan.case_id == pg_seed.case_id
                )
            )
        ).scalars().all()
        audits = (
            await verify.execute(
                select(AuditLog).where(AuditLog.entity_id == pg_seed.plan_id)
            )
        ).scalars().all()

    assert case.status == InterventionCaseStatus(
        "REPLAN_REQUIRED" if winner_decision == "DECLINED" else "PENDING_APPROVAL"
    )
    assert plan.status == winner_decision
    assert plan.student_decision == winner_decision
    assert plan.decided_at is not None
    assert plan.student_reason == winner_reason
    assert len(all_plans) == 1  # no duplicate plan rows
    assert len(audits) == 1  # exactly one audit row — the loser wrote none

    audit = audits[0]
    expected_action = "PLAN_DECLINED" if winner_decision == "DECLINED" else "PLAN_ACCEPTED"
    assert audit.action_type == expected_action
    assert audit.actor_id == pg_seed.student_user_id
    assert audit.actor_type == "USER"
    assert audit.source_system == "STUDENT_APP"
    assert audit.entity_table == "intervention_plans"
    assert audit.entity_id == pg_seed.plan_id
    states = json.dumps(audit.previous_state) + json.dumps(audit.new_state)
    assert winner_reason not in states if winner_reason else True
    assert (loser_reason or "Not feasible") not in states
    for key in (*audit.previous_state.keys(), *audit.new_state.keys()):
        assert key not in ("email", "full_name", "name", "roll_number", "reason")
