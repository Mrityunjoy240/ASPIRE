# tests/test_follow_up_pg.py
# Follow-up persistence + scheduler/consumer contract on real PostgreSQL
# (ADR-004, 05 §9, migration 016). Unit behavior without a DB lives in
# tests/test_follow_up.py.

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.events import EventBus
from app.models.academic import Course, CourseRun, Semester
from app.models.attendance import AttendanceDerivedState
from app.models.audit import AuditLog
from app.models.enums import FollowUpStatus, FollowUpTriggerType, InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionFollowUp
from app.models.student import StudentProfile
from app.services.follow_up_service import (
    FollowUpConsumer,
    handle_followup_due_event,
    schedule_followup,
)
from app.services.scheduler import run_cycle

pytestmark = pytest.mark.integration


# ---- helpers ----------------------------------------------------------------


async def _set_case_status(pg_engine, case_id, status: InterventionCaseStatus):
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(InterventionCase).where(InterventionCase.id == case_id).with_for_update()
        )
        case = result.scalar_one()
        case.status = status
        await session.commit()


async def _load_case(pg_engine, case_id) -> InterventionCase | None:
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(InterventionCase).where(InterventionCase.id == case_id)
        )
        return result.scalar_one_or_none()


async def _load_follow_up(pg_engine, follow_up_id) -> InterventionFollowUp | None:
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(InterventionFollowUp).where(InterventionFollowUp.id == follow_up_id)
        )
        return result.scalar_one_or_none()


async def _audit_count(pg_engine, entity_id, action_type: str) -> int:
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == entity_id,
                AuditLog.action_type == action_type,
            )
        )
        return len(list(result.scalars().all()))


async def _schedule(
    pg_engine,
    *,
    case_id: uuid.UUID,
    mentor_id: uuid.UUID,
    trigger_type: str,
    due_at: datetime | None = None,
):
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        result = await session.execute(
            select(InterventionCase).where(InterventionCase.id == case_id).with_for_update()
        )
        case = result.scalar_one()
        follow_up = await schedule_followup(
            session,
            case=case,
            trigger_type=trigger_type,
            due_at=due_at,
            actor_id=mentor_id,
        )
        await session.commit()
        return follow_up


async def _backdate_due(pg_engine, follow_up_id, when: datetime):
    """CUSTOM_DATE rows are scheduled with a future due_at (service rule);
    tests simulate elapsed time by rewriting the timestamp directly."""
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionFollowUp)
                .where(InterventionFollowUp.id == follow_up_id)
                .with_for_update()
            )
        ).scalar_one()
        row.due_at = when
        await session.commit()


async def _mark_fulfilled_with_ended_window(pg_engine, follow_up_id):
    """Simulate a fulfilled follow-up whose evaluation window already ended
    (for EXPIRY-path tests)."""
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionFollowUp)
                .where(InterventionFollowUp.id == follow_up_id)
                .with_for_update()
            )
        ).scalar_one()
        row.status = FollowUpStatus.FULFILLED.value
        row.triggered_at = datetime.now(UTC) - timedelta(days=9)
        row.due_at = datetime.now(UTC) - timedelta(days=10)
        row.evaluation_window_ends_at = datetime.now(UTC) - timedelta(minutes=5)
        await session.commit()


async def _schedule_past_due(
    pg_engine,
    *,
    case_id: uuid.UUID,
    mentor_id: uuid.UUID,
):
    """Schedule a CUSTOM_DATE follow-up, then backdate it so the scheduler's
    DUE condition fires on the next cycle."""
    follow_up = await _schedule(
        pg_engine,
        case_id=case_id,
        mentor_id=mentor_id,
        trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
        due_at=datetime.now(UTC) + timedelta(days=30),
    )
    await _backdate_due(pg_engine, follow_up.follow_up_id, datetime.now(UTC) - timedelta(minutes=1))
    return follow_up


def _session_maker(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)


async def _seed_attendance_above_threshold(pg_engine, pg_seed, *, percent="90.00"):
    """One course run + an above-threshold derived state for the seeded student."""
    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase).where(InterventionCase.id == pg_seed.case_id)
            )
        ).scalar_one()
        profile = (
            await session.execute(
                select(StudentProfile).where(
                    StudentProfile.id == pg_seed.student_profile_id
                )
            )
        ).scalar_one()
        semester = Semester(
            id=uuid.uuid4(),
            batch_id=profile.batch_id,
            semester_number=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 5, 31),
            status="ONGOING",
            created_at=now,
            updated_at=now,
        )
        course = Course(
            id=uuid.uuid4(),
            institution_id=pg_seed.institution_id,
            name="Remedial",
            code=f"RM-{uuid.uuid4().hex[:6]}",
            created_at=now,
            updated_at=now,
        )
        run = CourseRun(
            id=uuid.uuid4(),
            course_id=course.id,
            semester_id=semester.id,
            batch_id=profile.batch_id,
            faculty_id=case.mentor_id,
            total_classes=100,
            created_at=now,
            updated_at=now,
        )
        session.add_all([semester, course, run])
        await session.flush()
        attended = int(Decimal(percent))
        state = AttendanceDerivedState(
            id=uuid.uuid4(),
            student_id=pg_seed.student_profile_id,
            course_run_id=run.id,
            classes_conducted=100,
            classes_attended=attended,
            attendance_percentage=Decimal(percent),
            risk_band="SAFE",
            required_to_recover=0,
            computed_at=now,
        )
        session.add(state)
        await session.commit()


async def _seed_course_run_and_state(pg_engine, pg_seed, *, percent="10.00"):
    await _seed_attendance_above_threshold(pg_engine, pg_seed, percent=percent)


# ---- persistence ------------------------------------------------------------


async def test_schedule_persists_row_and_audit(pg_engine, pg_seed):
    """schedule_followup writes the follow-up row + FOLLOW_UP_SCHEDULED
    audit on a committed ACTIVE case."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    due = datetime.now(UTC) + timedelta(days=2)

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == pg_seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        follow_up = await schedule_followup(
            session,
            case=case,
            trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
            due_at=due,
            actor_id=case.mentor_id,
        )
        follow_up_id = follow_up.follow_up_id
        await session.commit()

    persisted = await _load_follow_up(pg_engine, follow_up_id)
    assert persisted is not None
    assert persisted.status == FollowUpStatus.SCHEDULED.value
    assert persisted.trigger_type == FollowUpTriggerType.CUSTOM_DATE.value
    assert persisted.due_at is not None
    assert persisted.evaluation_window_ends_at is None  # set at fulfilment
    assert await _audit_count(pg_engine, follow_up_id, "FOLLOW_UP_SCHEDULED") == 1


async def test_schedule_rejects_non_active_case(pg_engine, pg_seed):
    """PLAN_PROPOSED (the seed default) must not accept follow-ups."""
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == pg_seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        with pytest.raises(Exception) as exc_info:
            await schedule_followup(
                session,
                case=case,
                trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
                due_at=datetime.now(UTC) + timedelta(days=1),
                actor_id=case.mentor_id,
            )
        assert "ILLEGAL_TRANSITION" in str(exc_info.value) or "ACTIVE" in str(exc_info.value)
        await session.rollback()


# ---- scheduler → consumer happy path ---------------------------------------


async def test_due_emission_and_consumer_fulfil(pg_engine, pg_seed):
    """run_cycle emits MENTOR_FOLLOWUP_DUE (DUE); the consumer flips
    SCHEDULED→FULFILLED and ACTIVE→MONITORING, writes CASE_FOLLOWUP_DUE."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    follow_up = await _schedule_past_due(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=(await _load_case(pg_engine, pg_seed.case_id)).mentor_id,
    )

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        report = await run_cycle(session, bus, now)

    assert report.emitted >= 1

    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.FULFILLED.value
    assert persisted.triggered_at is not None
    assert persisted.evaluation_window_ends_at is not None
    assert persisted.outcome is None

    case = await _load_case(pg_engine, pg_seed.case_id)
    assert case.status == InterventionCaseStatus.MONITORING
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_FOLLOWUP_DUE") == 1


async def test_duplicate_due_dispatch_is_noop(pg_engine, pg_seed):
    """Second DUE dispatch after fulfilment: window still open → noop,
    no state drift, no extra audit rows."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule_past_due(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
    )

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        await run_cycle(session, bus, now)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        report = await run_cycle(session, bus, now)  # occurrence already EMITTED

    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.FULFILLED.value
    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.MONITORING
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_FOLLOWUP_DUE") == 1
    assert report.emitted == 0  # occurrence idempotency suppresses re-publish


async def test_expiry_emission_and_consumer_replan(pg_engine, pg_seed):
    """FULFILLED follow-up past its window: EXPIRY emission drives
    MONITORING → REPLAN_REQUIRED (no attendance data → not improved)."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
        trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
        due_at=datetime.now(UTC) + timedelta(days=30),
    )
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.MONITORING)
    await _mark_fulfilled_with_ended_window(pg_engine, follow_up.follow_up_id)

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        report = await run_cycle(session, bus, now)

    assert report.emitted >= 1
    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.EVALUATED.value
    assert persisted.outcome == InterventionCaseStatus.REPLAN_REQUIRED.value
    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_FOLLOWUP_EXPIRED") == 1


async def test_immediate_improvement_resolves(pg_engine, pg_seed):
    """Above-threshold attendance + no pending plan tasks: DUE fulfilment
    verifies improvement and closes MONITORING→RESOLVED in one transaction."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    await _seed_attendance_above_threshold(pg_engine, pg_seed, percent="90.00")
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule_past_due(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
    )

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        await run_cycle(session, bus, now)

    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.EVALUATED.value
    assert persisted.outcome == InterventionCaseStatus.RESOLVED.value
    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.RESOLVED
    assert refreshed.resolved_at is not None
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_FOLLOWUP_DUE") == 1
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_IMPROVEMENT_VERIFIED") == 1


async def test_expiry_improved_resolves(pg_engine, pg_seed):
    """MONITORING + ended window + improved attendance → RESOLVED."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    await _seed_attendance_above_threshold(pg_engine, pg_seed, percent="88.00")
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
        trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
        due_at=datetime.now(UTC) + timedelta(days=30),
    )
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.MONITORING)
    await _mark_fulfilled_with_ended_window(pg_engine, follow_up.follow_up_id)

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        await run_cycle(session, bus, now)

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.RESOLVED
    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.EVALUATED.value
    assert persisted.outcome == InterventionCaseStatus.RESOLVED.value
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_IMPROVEMENT_VERIFIED") == 1


async def test_below_threshold_expiry_stays_monitoring_then_replans(pg_engine, pg_seed):
    """DUE fulfilment with no improvement → MONITORING (window open);
    then a forced EXPIRY emission after the window ends → REPLAN_REQUIRED."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    await _seed_course_run_and_state(pg_engine, pg_seed, percent="10.00")
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule_past_due(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
    )

    maker = _session_maker(pg_engine)
    consumer = FollowUpConsumer(maker)
    bus = EventBus()
    consumer.ensure_subscribed(bus)

    now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        await run_cycle(session, bus, now)

    mid = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert mid.status == FollowUpStatus.FULFILLED.value
    assert (
        await _load_case(pg_engine, pg_seed.case_id)
    ).status == InterventionCaseStatus.MONITORING

    # Close the evaluation window, then emit EXPIRY.
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        row = (
            await session.execute(
                select(InterventionFollowUp)
                .where(InterventionFollowUp.id == follow_up.follow_up_id)
                .with_for_update()
            )
        ).scalar_one()
        row.evaluation_window_ends_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    event_now = datetime.now(UTC)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        await run_cycle(session, bus, event_now)

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.REPLAN_REQUIRED
    persisted = await _load_follow_up(pg_engine, follow_up.follow_up_id)
    assert persisted.status == FollowUpStatus.EVALUATED.value
    assert persisted.outcome == InterventionCaseStatus.REPLAN_REQUIRED.value


# ---- concurrency (lead option A: status under FOR UPDATE) -------------------


async def test_concurrent_due_single_winner(pg_engine, pg_seed):
    """Two concurrent DUE consumers: the row lock serialises them — winner
    fulfils, loser re-reads FULFILLED and no-ops (no double MONITORING)."""
    await _set_case_status(pg_engine, pg_seed.case_id, InterventionCaseStatus.ACTIVE)
    case = await _load_case(pg_engine, pg_seed.case_id)
    follow_up = await _schedule_past_due(
        pg_engine,
        case_id=pg_seed.case_id,
        mentor_id=case.mentor_id,
    )

    from app.core.events import DomainEvent

    event = DomainEvent(
        event_type="MENTOR_FOLLOWUP_DUE",
        student_id=case.student_id,
        source_id=follow_up.follow_up_id,
        payload={
            "case_id": str(follow_up.case_id),
            "follow_up_id": str(follow_up.follow_up_id),
            "trigger_type": follow_up.trigger_type,
            "phase": "DUE",
        },
    )

    first_locked = asyncio.Event()
    release = asyncio.Event()
    results: dict[str, str] = {}

    async def winner():
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            locked = await session.execute(
                select(InterventionFollowUp)
                .where(InterventionFollowUp.id == follow_up.follow_up_id)
                .with_for_update()
            )
            assert locked.scalar_one() is not None
            first_locked.set()
            await asyncio.wait_for(release.wait(), timeout=5)
            outcome = await handle_followup_due_event(session, event)
            results["winner"] = outcome.action
        finally:
            await session.close()

    async def loser():
        await asyncio.wait_for(first_locked.wait(), timeout=5)
        session = AsyncSession(pg_engine, expire_on_commit=False)
        try:
            outcome = await handle_followup_due_event(session, event)
            results["loser"] = outcome.action
        finally:
            await session.close()

    winner_task = asyncio.create_task(winner())
    loser_task = asyncio.create_task(loser())
    await asyncio.wait_for(first_locked.wait(), timeout=5)
    release.set()
    await asyncio.gather(winner_task, loser_task)

    assert results["winner"] == "fulfilled"
    assert results["loser"] == "noop"

    refreshed = await _load_case(pg_engine, pg_seed.case_id)
    assert refreshed.status == InterventionCaseStatus.MONITORING
    assert await _audit_count(pg_engine, pg_seed.case_id, "CASE_FOLLOWUP_DUE") == 1
