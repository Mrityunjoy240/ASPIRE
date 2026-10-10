# tests/test_concurrent_student_decisions_pg.py
# Genuine two-connection PostgreSQL concurrency test for the student decision
# path (close-out of OQ-A02: "implementation verified, concurrency test
# pending"). Two independent sessions race on the same case/plan through the
# real FOR UPDATE lock, plan selection, audit write and event emission.
#
# Run (never against a production database):
#   docker run --rm -d --name aspire-it-pg -p 55432:5432 \
#       -e POSTGRES_PASSWORD=aspire -e POSTGRES_DB=aspire_test pgvector/pgvector:pg16
#   set ASPIRE_TEST_PG_DSN=postgresql+psycopg://postgres:aspire@127.0.0.1:55432/aspire_test
#   pytest -m integration tests/test_concurrent_student_decisions_pg.py -q
#
# Safety: the test refuses any DSN whose database name does not end in
# "_test", applies db/migrations/*.sql inside a unique throwaway schema, and
# drops only that schema afterwards. It is SKIPPED when ASPIRE_TEST_PG_DSN is
# unset (default local and CI runs — the unit suite must never need a DB).

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import String, literal, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.academic import Batch, Programme
from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.institutions import Institution
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile
from app.models.users import User

pytestmark = pytest.mark.integration

DSN_ENV = "ASPIRE_TEST_PG_DSN"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"
# Windows + psycopg async: the default ProactorEventLoop cannot be used.
# pytest-asyncio builds loops from the policy, so switch before any loop for
# this module's tests is created. Applied only when the test can actually run.
if sys.platform == "win32" and os.environ.get(DSN_ENV):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _require_dsn() -> str:
    dsn = os.environ.get(DSN_ENV)
    if not dsn:
        pytest.skip(f"{DSN_ENV} not set — PostgreSQL integration test not executed")
    database = dsn.rsplit("/", 1)[-1].split("?")[0]
    if not database.endswith("_test"):
        pytest.fail(
            f"refusing to run against database '{database}': {DSN_ENV} must point "
            "at a disposable database whose name ends in '_test'"
        )
    return dsn


@pytest.fixture
async def pg_engine():
    """Fresh throwaway schema + full migration chain per test, dropped after."""
    dsn = _require_dsn()
    schema = f"aspire_it_{uuid.uuid4().hex[:10]}"
    engine = create_async_engine(
        dsn,
        poolclass=NullPool,  # every checkout = a fresh independent connection
        future=True,
        # All DDL lands in the throwaway schema (first existing entry);
        # `public` stays on the path so CREATE EXTENSION's vector type from
        # migration 001 resolves (extension objects must live outside the
        # throwaway schema, or the teardown drop would remove them).
        connect_args={"options": f"-c search_path={schema},public"},
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            async with engine.begin() as conn:
                await conn.execute(text(path.read_text(encoding="utf-8")))
        yield engine
    finally:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            await engine.dispose()


@pytest.fixture
async def pg_seed(pg_engine):
    """A minimal PLAN_PROPOSED case with one PROPOSED plan, via the ORM."""
    now = datetime.now(UTC)
    tok = uuid.uuid4().hex[:8]
    inst = Institution(
        id=uuid.uuid4(), name=f"Integration {tok}", slug=f"it-{tok}", status="ACTIVE"
    )
    prog = Programme(
        id=uuid.uuid4(), institution_id=inst.id, name="BCA", code=f"BCA-{tok}",
        total_semesters=6, created_at=now, updated_at=now,
    )
    batch = Batch(
        id=uuid.uuid4(), institution_id=inst.id, programme_id=prog.id,
        name=f"Batch {tok}", start_year=2024, end_year=2028, status="ACTIVE",
        created_at=now, updated_at=now,
    )
    student_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"student-{tok}@example.test",
        full_name="Integration Student", status="ACTIVE", created_at=now, updated_at=now,
    )
    mentor_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"mentor-{tok}@example.test",
        full_name="Integration Mentor", status="ACTIVE", created_at=now, updated_at=now,
    )
    profile = StudentProfile(
        id=uuid.uuid4(), user_id=student_user.id, batch_id=batch.id,
        roll_number=f"IT-{tok}", enrollment_year=2024, created_at=now, updated_at=now,
    )
    case = InterventionCase(
        id=uuid.uuid4(), student_id=profile.id, mentor_id=mentor_user.id,
        status=InterventionCaseStatus.PLAN_PROPOSED, urgency_band="URGENT",
        opened_at=now, created_at=now, updated_at=now,
    )
    plan = InterventionPlan(
        id=uuid.uuid4(), case_id=case.id, created_by="SYSTEM_AGENT",
        status="PROPOSED",
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
        evidence={},
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add_all([inst, prog, batch, student_user, mentor_user, profile, case])
        # reason_codes is TEXT[] in migration 009 (the schema authority) while
        # the ORM model declares JSON — insert via a typed ARRAY literal so the
        # seed matches the real schema. (Model/migration mismatch is reported,
        # not fixed here — models are not the schema authority.)
        await session.execute(
            InterventionPlan.__table__.insert().values(
                id=plan.id,
                case_id=case.id,
                created_by="SYSTEM_AGENT",
                status="PROPOSED",
                plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
                reason_codes=literal(["LOW_ATTENDANCE"], ARRAY(String)),
                evidence={},
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return SimpleNamespace(
        case_id=case.id,
        plan_id=plan.id,
        student_user_id=student_user.id,
        student_profile_id=profile.id,
    )


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
