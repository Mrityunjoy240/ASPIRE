# tests/test_scheduler_pg.py
# R4 scheduler integration evidence (11_ROADMAP R4): real PostgreSQL
# evaluation of TASK_OVERDUE with durable occurrence claims (migration 015)
# — emission exactly-once across repeated cycles and session ("restart")
# boundaries, crash recovery of unconfirmed claims, and zero business-state
# mutation (DM-SS02). Covers 08_EVALS SCH-01..07 and 09 EC-SCH-01..06.
# Skips when ASPIRE_TEST_PG_DSN is unset (same safety guard as conftest).

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventBus
from app.models.enums import TaskSourceType, TaskStatus
from app.models.scheduler import SchedulerOccurrence
from app.models.tasks import StudentTask
from app.services.scheduler import (
    EVENT_TASK_OVERDUE,
    CycleReport,
    cancel_scheduler_task,
    run_cycle,
    scheduler_loop,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def sched_env(pg_engine, pg_seed):
    return SimpleNamespace(
        engine=pg_engine,
        student_id=pg_seed.student_profile_id,
        created_by=pg_seed.student_user_id,
    )


async def _add_task(env, *, status: TaskStatus, deadline: datetime | None, title: str):
    now = datetime.now(UTC)
    task = StudentTask(
        id=uuid.uuid4(),
        student_id=env.student_id,
        source_type=TaskSourceType.MENTOR,
        source_id=uuid.uuid4(),
        created_by=env.created_by,
        title=title,
        deadline=deadline,
        status=status,
        created_at=now,
        updated_at=now,
    )
    async with AsyncSession(env.engine, expire_on_commit=False) as session:
        session.add(task)
        await session.commit()
    return task


def _session(engine) -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False)


def _recording_bus() -> tuple[EventBus, list]:
    bus = EventBus()
    received: list = []

    async def _record(event):
        received.append(event)

    bus.subscribe(EVENT_TASK_OVERDUE, _record)
    return bus, received


async def _occurrence(engine, task) -> SchedulerOccurrence | None:
    async with _session(engine) as session:
        return await session.get(
            SchedulerOccurrence,
            {
                "event_type": EVENT_TASK_OVERDUE,
                "source_id": task.id,
                "trigger_value": task.deadline,
            },
        )


async def _fresh_task(engine, task_id) -> StudentTask:
    async with _session(engine) as session:
        return await session.get(StudentTask, task_id)


async def test_sch04_sch07_emits_once_and_never_mutates_task(sched_env):
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env,
        status=TaskStatus.PENDING,
        deadline=now - timedelta(hours=2),
        title="Submit lab record",
    )
    bus, received = _recording_bus()

    async with _session(sched_env.engine) as session:
        report = await run_cycle(session, bus, now)

    assert report == CycleReport(evaluated_at=now, candidates=1, emitted=1)
    assert len(received) == 1
    event = received[0]
    assert event.event_type == EVENT_TASK_OVERDUE
    assert event.student_id == task.student_id
    assert event.source_id == task.id
    assert event.payload["task_id"] == str(task.id)
    assert event.payload["title"] == "Submit lab record"
    assert datetime.fromisoformat(event.payload["deadline"]) == task.deadline

    occurrence = await _occurrence(sched_env.engine, task)
    assert occurrence is not None
    assert occurrence.state == "EMITTED"
    assert occurrence.claimed_at == now
    assert occurrence.emitted_at == now
    assert occurrence.student_id == task.student_id

    # SCH-07 / DM-SS02: business state untouched — PENDING stays PENDING.
    fresh = await _fresh_task(sched_env.engine, task.id)
    assert fresh.status == TaskStatus.PENDING
    assert fresh.deadline == task.deadline
    assert fresh.updated_at == task.updated_at


async def test_sch02_ec_sch01_repeated_cycles_and_restart_emit_no_duplicates(sched_env):
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    bus, received = _recording_bus()

    async with _session(sched_env.engine) as session:
        first = await run_cycle(session, bus, now)
        second = await run_cycle(session, bus, now)
    # EC-SCH-01 "restart": a fresh session re-evaluates from DB state.
    async with _session(sched_env.engine) as session:
        restarted = await run_cycle(session, bus, now)

    assert first.emitted == 1
    assert second == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    assert restarted == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    assert len(received) == 1
    assert (await _occurrence(sched_env.engine, task)).state == "EMITTED"


async def test_ec_sch02_unconfirmed_claim_is_recovered_exactly_once(sched_env):
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    # Crash simulation: the claim committed but the process died before
    # publish — the occurrence is outstanding (EC-SCH-02: not lost).
    async with _session(sched_env.engine) as session:
        session.add(
            SchedulerOccurrence(
                event_type=EVENT_TASK_OVERDUE,
                source_id=task.id,
                trigger_value=task.deadline,
                student_id=task.student_id,
                state="CLAIMED",
                claimed_at=now - timedelta(minutes=5),
            )
        )
        await session.commit()

    bus, received = _recording_bus()
    async with _session(sched_env.engine) as session:
        recovered = await run_cycle(session, bus, now)
        again = await run_cycle(session, bus, now)

    assert recovered == CycleReport(evaluated_at=now, candidates=1, recovered=1)
    assert again == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    assert len(received) == 1
    occurrence = await _occurrence(sched_env.engine, task)
    assert occurrence.state == "EMITTED"
    assert occurrence.emitted_at == now


async def test_sch05_sch06_completed_and_null_deadline_never_emit(sched_env):
    now = datetime.now(UTC)
    completed = await _add_task(
        sched_env, status=TaskStatus.COMPLETED, deadline=now - timedelta(hours=3), title="Done"
    )
    no_deadline = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=None, title="No date"
    )
    bus, received = _recording_bus()

    async with _session(sched_env.engine) as session:
        report = await run_cycle(session, bus, now)

    assert report == CycleReport(evaluated_at=now)
    assert received == []
    assert await _occurrence(sched_env.engine, completed) is None
    assert await _occurrence(sched_env.engine, no_deadline) is None


async def test_ec_sch04_deadline_crosses_between_cycles(sched_env):
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env,
        status=TaskStatus.PENDING,
        deadline=now + timedelta(minutes=4),
        title="Due soon",
    )
    bus, received = _recording_bus()

    async with _session(sched_env.engine) as session:
        before = await run_cycle(session, bus, now)
    assert before == CycleReport(evaluated_at=now)
    assert received == []

    later = now + timedelta(minutes=6)  # next 5-minute cycle crosses it
    async with _session(sched_env.engine) as session:
        after = await run_cycle(session, bus, later)
    assert after == CycleReport(evaluated_at=later, candidates=1, emitted=1)
    assert len(received) == 1
    assert received[0].source_id == task.id


async def test_claim_is_committed_before_publish(sched_env):
    """EC-SCH-01 ordering: subscribers observe the durable CLAIMED claim;
    only afterwards does the row become EMITTED."""
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    bus, received = _recording_bus()
    observed: list[tuple[str, datetime | None]] = []

    async def _spy(event):
        occurrence = await _occurrence(sched_env.engine, task)
        observed.append((occurrence.state, occurrence.emitted_at))

    bus.subscribe(EVENT_TASK_OVERDUE, _spy)

    async with _session(sched_env.engine) as session:
        await run_cycle(session, bus, now)

    assert observed == [("CLAIMED", None)]
    assert len(received) == 1
    assert (await _occurrence(sched_env.engine, task)).state == "EMITTED"


# --- Crash-window fault injection -------------------------------------------
# The windows below are traced separately (EC-SCH-01..03 semantics):
#   A/C — claim durable, publish never reached a handler: no delivery, the
#         occurrence is CLAIMED and recovered next cycle → exactly once.
#   B   — publish reached the handlers, process died before the EMITTED
#         mark: the row stays CLAIMED → recovery RE-DISPATCHES. This is
#         at-least-once: duplicate bus delivery of one logical occurrence
#         is possible (distinct event_id, identical logical identity).
#   D   — a handler receives the event and fails: EventBus isolates the
#         failure, publish returns, the row becomes EMITTED → the failure
#         is terminal (at-most-once processing, no retry). EMITTED means
#         "publish completed / handlers awaited", NOT "handler succeeded".


async def test_crash_before_publish_recovers_with_exactly_one_delivery(sched_env):
    """Windows A and C: the claim committed but no handler ever ran (process
    died before publish, or the publish attempt failed before the bus).
    Nothing was delivered; the CLAIMED row is recovered exactly once —
    no loss, no duplicate from this window."""
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )

    class _PublishNeverReachesBus(EventBus):
        async def publish(self, event):  # fails before any handler runs
            raise RuntimeError("simulated crash before publish reaches handlers")

    async with _session(sched_env.engine) as session:
        first = await run_cycle(session, _PublishNeverReachesBus(), now)

    assert first == CycleReport(evaluated_at=now, candidates=1, errors=1)
    assert (await _occurrence(sched_env.engine, task)).state == "CLAIMED"

    bus, received = _recording_bus()  # restart: fresh session + subscribers
    async with _session(sched_env.engine) as session:
        recovered = await run_cycle(session, bus, now)
    async with _session(sched_env.engine) as session:
        again = await run_cycle(session, bus, now)

    assert recovered == CycleReport(evaluated_at=now, candidates=1, recovered=1)
    assert again == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    assert len(received) == 1  # delivered exactly once across both attempts
    assert (await _occurrence(sched_env.engine, task)).state == "EMITTED"


async def test_crash_after_publish_before_emitted_mark_redispatches(sched_env):
    """Window B: publish succeeded (handlers awaited), then the process
    died before the EMITTED mark. The CLAIMED row survives, so the next
    cycle re-dispatches — proving at-least-once delivery with a possible
    duplicate: two bus deliveries, one logical occurrence."""
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    deliveries: list = []

    async def _record(event):
        deliveries.append(event)

    class _CrashAfterPublish(EventBus):
        async def publish(self, event):
            await super().publish(event)  # handlers run — delivery happens
            raise RuntimeError("simulated crash after publish, before EMITTED mark")

    crashing = _CrashAfterPublish()
    crashing.subscribe(EVENT_TASK_OVERDUE, _record)
    async with _session(sched_env.engine) as session:
        first = await run_cycle(session, crashing, now)

    assert first == CycleReport(evaluated_at=now, candidates=1, errors=1)
    assert len(deliveries) == 1  # delivered, but the mark was lost
    assert (await _occurrence(sched_env.engine, task)).state == "CLAIMED"

    restarted = EventBus()  # restart: fresh session + subscribers
    restarted.subscribe(EVENT_TASK_OVERDUE, _record)
    async with _session(sched_env.engine) as session:
        recovered = await run_cycle(session, restarted, now)
    async with _session(sched_env.engine) as session:
        again = await run_cycle(session, restarted, now)

    assert recovered == CycleReport(evaluated_at=now, candidates=1, recovered=1)
    assert again == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    # Duplicate dispatch: ONE logical occurrence, TWO bus deliveries.
    assert len(deliveries) == 2
    first_delivery, second_delivery = deliveries
    assert first_delivery.event_id != second_delivery.event_id  # wire ids differ
    assert (  # logical identity + payload are stable across re-dispatch
        first_delivery.event_type,
        first_delivery.source_id,
        first_delivery.payload,
    ) == (
        second_delivery.event_type,
        second_delivery.source_id,
        second_delivery.payload,
    )
    occurrence = await _occurrence(sched_env.engine, task)
    assert occurrence.state == "EMITTED"
    assert occurrence.emitted_at is not None


async def test_handler_failure_is_terminal_emitted_without_retry(sched_env):
    """Window D: the handler receives the event and fails. EventBus isolates
    the failure, publish returns normally, and the occurrence is marked
    EMITTED — so the failure is terminal: no re-delivery on later cycles
    (at-most-once processing; EMITTED ≠ handler success)."""
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    received: list = []

    async def _failing_handler(event):
        received.append(event)
        raise RuntimeError("handler failed after receiving the event")

    bus = EventBus()
    bus.subscribe(EVENT_TASK_OVERDUE, _failing_handler)

    async with _session(sched_env.engine) as session:
        first = await run_cycle(session, bus, now)
    async with _session(sched_env.engine) as session:
        second = await run_cycle(session, bus, now)

    assert first == CycleReport(evaluated_at=now, candidates=1, emitted=1)
    assert second == CycleReport(evaluated_at=now, candidates=1, skipped=1)
    assert len(received) == 1  # no redelivery after the handler failure
    occurrence = await _occurrence(sched_env.engine, task)
    assert occurrence.state == "EMITTED"
    assert occurrence.emitted_at is not None


async def test_scheduler_loop_evaluates_at_startup_then_idles(sched_env):
    """03 §8.3 lifecycle: one evaluation at startup; the loop is cancellable
    (lifespan shutdown) without emitting anything else."""
    now = datetime.now(UTC)
    task = await _add_task(
        sched_env, status=TaskStatus.PENDING, deadline=now - timedelta(hours=1), title="T"
    )
    bus, received = _recording_bus()

    @asynccontextmanager
    async def maker():
        async with _session(sched_env.engine) as session:
            yield session

    started = asyncio.Event()

    async def _on_event(event):
        started.set()

    bus.subscribe(EVENT_TASK_OVERDUE, _on_event)

    loop_task = asyncio.create_task(
        scheduler_loop(bus, session_maker=maker, interval=3600, clock=lambda: now)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        # The handler fires mid-publish; wait for the cycle's EMITTED mark
        # so shutdown cancellation cannot land inside the mark commit.
        for _ in range(200):
            occurrence = await _occurrence(sched_env.engine, task)
            if occurrence is not None and occurrence.state == "EMITTED":
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("startup cycle never marked the occurrence EMITTED")
    finally:
        await cancel_scheduler_task(loop_task)

    assert loop_task.cancelled()
    assert len(received) == 1
    assert (await _occurrence(sched_env.engine, task)).state == "EMITTED"
    assert (await _fresh_task(sched_env.engine, task.id)).status == TaskStatus.PENDING
