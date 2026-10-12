# app/services/scheduler.py
# Time-based scheduler (DM-AG03 / OQ-AG03 — FROZEN hybrid trigger model).
# Contract: docs/03_SYSTEM_SPEC.md §8.3, §8.2; docs/11_ROADMAP.md R4.
#
# One evaluation at application startup, then every 5 minutes. Each cycle
# evaluates time conditions from current database state and emits domain
# events only. The scheduler:
#   - never mutates business state (DM-SS02: OVERDUE is never persisted),
#   - never calls agents or LLMs (downstream event-driven processing does),
#   - never emits events outside the canonical catalog (03 §8.1).
#
# Idempotency (EC-SCH-01..03 / SCH-02..03): one logical occurrence =
# (event_type, source_id, trigger_value) persists one scheduler_occurrences
# row (migration 015, 05 §7): CLAIMED and committed BEFORE publish, EMITTED
# after publish. Already-EMITTED occurrences are skipped (duplicate-tick
# no-op). A CLAIMED leftover (crash between claim and publish-mark) is
# re-emitted once on the next cycle — outstanding events are recovered,
# never lost. Honest delivery boundary (R4 crash-window review): if the
# crash happened AFTER the handlers ran, that recovery is a DUPLICATE bus
# dispatch — dispatch is at-least-once, not exactly-once (tests:
# window B in tests/test_scheduler_pg.py). Duplicate *business effects* are
# a consumer concern: EMITTED means publish() completed with handlers
# awaited, NOT that handlers succeeded (handler failure is terminal —
# window D), and the only current TASK_OVERDUE consumer (Supervisor
# route-only) writes nothing.

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.events import DomainEvent, EventBus
from app.models.enums import TaskStatus
from app.models.scheduler import SchedulerOccurrence
from app.models.tasks import StudentTask

logger = logging.getLogger(__name__)

# 03 §8.3: one evaluation at startup, then every 5 minutes.
SCHEDULER_INTERVAL_SECONDS = 300

# Producer-side constant (case_service precedent): the canonical catalog
# name from 03 §8.1; tests assert it matches the Supervisor's constant.
EVENT_TASK_OVERDUE = "TASK_OVERDUE"

# 05 §7 scheduler_occurrences.state vocabulary.
STATE_CLAIMED = "CLAIMED"
STATE_EMITTED = "EMITTED"

# Conditions R4 deferred at the contract gate (documented blockers — do not
# silently evaluate them without their approved sources):
#   EXAM_APPROACHING   — no calendar/exam persistence exists (03 §9 Calendar
#                        Engine); exam_approaching_days has no seed row and
#                        rule precedence/effective dating is open in ADR-003
#                        §6.4 (lead-held).
#   MENTOR_FOLLOWUP_DUE — no persisted follow-up due-date; schedule_followup
#                        (06 §4) is unimplemented and the approved follow-up
#                        policy (06 §4, 02 Step 6) is event-driven, not
#                        time-based.
DEFERRED_CONDITIONS: dict[str, str] = {
    "EXAM_APPROACHING": (
        "no calendar/exam persistence (03 §9); threshold seed and ADR-003 §6.4 "
        "rule precedence unresolved — deferred at the R4 contract gate"
    ),
    "MENTOR_FOLLOWUP_DUE": (
        "no persisted follow-up due-date; schedule_followup (06 §4) "
        "unimplemented; approved policy is event-driven — deferred at the R4 "
        "contract gate"
    ),
}


@dataclass(frozen=True, slots=True)
class TimeTrigger:
    """One true time condition awaiting emission."""

    event_type: str
    student_id: UUID
    source_id: UUID
    trigger_value: datetime
    payload: dict[str, str]


class TimeCondition(Protocol):
    """A time-based condition the scheduler knows how to evaluate."""

    event_type: str

    async def candidates(self, session: AsyncSession, now: datetime) -> Sequence[TimeTrigger]:
        """Occurrences whose condition is true at `now`, deterministic order."""
        ...


class TaskOverdueCondition:
    """DM-SS02 (03 §5.1 / §8.2): status = PENDING AND deadline < now.

    NULL deadlines never fire; OVERDUE is never persisted — the task row is
    left exactly as it was.
    """

    event_type = EVENT_TASK_OVERDUE

    async def candidates(self, session: AsyncSession, now: datetime) -> Sequence[TimeTrigger]:
        result = await session.execute(
            select(StudentTask)
            .where(
                StudentTask.status == TaskStatus.PENDING,
                StudentTask.deadline.is_not(None),
                StudentTask.deadline < now,
            )
            .order_by(StudentTask.deadline, StudentTask.id)
        )
        triggers: list[TimeTrigger] = []
        for task in result.scalars():
            deadline = task.deadline
            if deadline is None:  # never fires (DM-SS02); kept for type narrowing
                continue
            triggers.append(
                TimeTrigger(
                    event_type=EVENT_TASK_OVERDUE,
                    student_id=task.student_id,
                    source_id=task.id,
                    trigger_value=deadline,
                    payload={
                        "task_id": str(task.id),
                        "deadline": deadline.isoformat(),
                        "title": task.title,
                    },
                )
            )
        return triggers


DEFAULT_CONDITIONS: tuple[TimeCondition, ...] = (TaskOverdueCondition(),)


@dataclass(frozen=True, slots=True)
class CycleReport:
    """Per-cycle emission counters (logged + asserted in tests)."""

    evaluated_at: datetime
    candidates: int = 0
    emitted: int = 0
    recovered: int = 0
    skipped: int = 0
    errors: int = 0


async def _process_trigger(
    session: AsyncSession,
    bus: EventBus,
    trigger: TimeTrigger,
    now: datetime,
) -> str:
    """Claim → publish → mark one occurrence. Returns emitted|recovered|skipped."""
    key = {
        "event_type": trigger.event_type,
        "source_id": trigger.source_id,
        "trigger_value": trigger.trigger_value,
    }
    occurrence = await session.get(SchedulerOccurrence, key)
    if occurrence is None:
        occurrence = SchedulerOccurrence(
            event_type=trigger.event_type,
            source_id=trigger.source_id,
            trigger_value=trigger.trigger_value,
            student_id=trigger.student_id,
            state=STATE_CLAIMED,
            claimed_at=now,
        )
        session.add(occurrence)
        try:
            # Claim is durable BEFORE the event exists on the bus.
            await session.commit()
        except IntegrityError:
            # A concurrent claimant won the race; its occurrence stands.
            await session.rollback()
            return "skipped"
        action = "emitted"
    elif occurrence.state == STATE_EMITTED:
        return "skipped"
    else:
        # CLAIMED: prior cycle crashed between claim and publish-mark —
        # the occurrence was never confirmed emitted; recover it (EC-SCH-02).
        action = "recovered"

    await bus.publish(
        DomainEvent(
            event_type=trigger.event_type,
            student_id=trigger.student_id,
            source_id=trigger.source_id,
            payload=dict(trigger.payload),
        )
    )

    occurrence.state = STATE_EMITTED
    occurrence.emitted_at = now
    await session.commit()
    return action


async def run_cycle(
    session: AsyncSession,
    bus: EventBus,
    now: datetime,
    *,
    conditions: Sequence[TimeCondition] = DEFAULT_CONDITIONS,
) -> CycleReport:
    """One idempotent evaluation of all time conditions (03 §8.3).

    Reads candidates from current database state, claims each logical
    occurrence durably, publishes, then marks it EMITTED (suppressing all
    further publishes). One occurrence = one publish per successful attempt;
    an attempt that dies after publish but before the mark is re-published
    on recovery — dispatch is at-least-once, not exactly-once (see module
    header). Business rows are never written. The session must use
    expire_on_commit=False (async_session_maker default) so claim/emit
    identity-map state stays coherent across cycles sharing one session.
    """
    candidates: list[TimeTrigger] = []
    for condition in conditions:
        candidates.extend(await condition.candidates(session, now))

    emitted = recovered = skipped = errors = 0
    for trigger in candidates:
        try:
            outcome = await _process_trigger(session, bus, trigger, now)
        except Exception:
            # Fail closed for this occurrence: no unconfirmed emission is
            # treated as done — a committed CLAIMED row recovers next cycle.
            await session.rollback()
            logger.exception(
                "scheduler: occurrence failed event_type=%s source_id=%s",
                trigger.event_type,
                trigger.source_id,
            )
            errors += 1
            continue
        if outcome == "emitted":
            emitted += 1
        elif outcome == "recovered":
            recovered += 1
        else:
            skipped += 1

    return CycleReport(
        evaluated_at=now,
        candidates=len(candidates),
        emitted=emitted,
        recovered=recovered,
        skipped=skipped,
        errors=errors,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def scheduler_loop(
    bus: EventBus,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    interval: float = SCHEDULER_INTERVAL_SECONDS,
    clock=_utc_now,
) -> None:
    """Startup evaluation, then one cycle every `interval` seconds.

    A failing cycle is logged and never stops the loop; cancellation
    (lifespan shutdown) propagates out of the sleep or an awaited call.
    """
    maker = session_maker if session_maker is not None else async_session_maker
    logger.info(
        "scheduler: started interval=%ss deferred=%s",
        interval,
        ",".join(DEFERRED_CONDITIONS) or "none",
    )
    while True:
        try:
            async with maker() as session:
                report = await run_cycle(session, bus, clock())
            logger.info(
                "scheduler: cycle candidates=%d emitted=%d recovered=%d "
                "skipped=%d errors=%d",
                report.candidates,
                report.emitted,
                report.recovered,
                report.skipped,
                report.errors,
            )
        except Exception:
            logger.exception("scheduler: cycle failed; retrying next interval")
        await asyncio.sleep(interval)


def create_scheduler_task(bus: EventBus) -> asyncio.Task | None:
    """Start the scheduler loop unless it is disabled (tests/conftest.py)."""
    if not settings.scheduler_enabled:
        logger.info("scheduler: disabled (scheduler_enabled=false)")
        return None
    return asyncio.create_task(
        scheduler_loop(
            bus,
            interval=settings.scheduler_interval_seconds,
        ),
        name="aspire-scheduler",
    )


async def cancel_scheduler_task(task: asyncio.Task | None) -> None:
    """Stop the loop and wait for it (lifespan shutdown)."""
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
