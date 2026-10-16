# app/services/follow_up_service.py
# Follow-up domain service + deterministic RULE_ENGINE consumer (ADR-004).
# Owns the three frozen follow-up rows of 03_SYSTEM_SPEC §10.2:
#   ACTIVE            → MONITORING  (follow-up due)
#   MONITORING        → RESOLVED    (improvement verified by engine)
#   MONITORING        → REPLAN_REQUIRED (no improvement, follow-up expires)
# Contract: docs/decisions/ADR-004_INTERVENTION_FOLLOWUP_MODEL.md; schema
# 05 §9 intervention_follow_ups (migration 016); trigger policies 06 §4 /
# 02 §2.1 Step 6; improvement predicate 02 §2.1 Step 7 (deterministic —
# engines calculate, never the LLM).
#
# Two fulfilment paths (ADR-004 §2.2), one frozen transition row:
#   - Time path: scheduler emits MENTOR_FOLLOWUP_DUE (DUE for due_at,
#     EXPIRY for the evaluation window) — 03 §8.3; handled here.
#   - Event path: policy trigger events (ATTENDANCE_UPDATED /
#     ASSESSMENT_GRADED / QUIZ_COMPLETED / TASK_OVERDUE) fulfil matching
#     SCHEDULED follow-ups (02 §2.1 Step 6).
# Follow-up row lifecycle additionally allows SCHEDULED → CANCELLED — the
# multiple-follow-up consumption rule (ADR-004 §2.1 Option B): a dispatch
# against a non-ACTIVE case cancels the stale row, and one fulfilment
# cancels its same-case siblings (audit FOLLOW_UP_SUPERSEDED, §2.8).
#
# Idempotency (lead option A, ADR-004 §2.3): the follow-up row IS the
# persisted logical identity. Every consumer path locks the row FOR UPDATE
# and flips SCHEDULED → FULFILLED (or FULFILLED → EVALUATED at expiry) in
# the same transaction as the case transition + audit row; a duplicate bus
# dispatch re-reads the committed status and no-ops. Window D (handler
# failure terminal, no automatic redelivery) is a documented exposure.

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import log_audit
from app.core.events import DomainEvent, EventBus
from app.models.attendance import AttendanceDerivedState
from app.models.enums import (
    FollowUpStatus,
    FollowUpTriggerType,
    InterventionCaseStatus,
    TaskSourceType,
    TaskStatus,
)
from app.models.intervention import InterventionCase, InterventionFollowUp, InterventionPlan
from app.models.tasks import StudentTask
from app.services.rules_reader import get_attendance_threshold, get_followup_evaluation_window_days

logger = logging.getLogger(__name__)

# 03 §8.2 catalog names (producer/consumer agreement — drift-guarded in tests).
EVENT_MENTOR_FOLLOWUP_DUE = "MENTOR_FOLLOWUP_DUE"
EVENT_ATTENDANCE_UPDATED = "ATTENDANCE_UPDATED"
EVENT_ASSESSMENT_GRADED = "ASSESSMENT_GRADED"
EVENT_QUIZ_COMPLETED = "QUIZ_COMPLETED"
EVENT_TASK_OVERDUE = "TASK_OVERDUE"

# 02 §2.1 Step 6 / 06 §4 trigger policies: catalog event → follow-up types
# fulfilled by that event.
EVENT_PATH_TRIGGER_TYPES: dict[str, tuple[str, ...]] = {
    EVENT_ATTENDANCE_UPDATED: (FollowUpTriggerType.ATTENDANCE_INTERVENTION.value,),
    EVENT_ASSESSMENT_GRADED: (FollowUpTriggerType.STUDY_INTERVENTION.value,),
    EVENT_QUIZ_COMPLETED: (FollowUpTriggerType.STUDY_INTERVENTION.value,),
    EVENT_TASK_OVERDUE: (FollowUpTriggerType.ASSIGNMENT_INTERVENTION.value,),
}

PHASE_DUE = "DUE"
PHASE_EXPIRY = "EXPIRY"

# 07 §4 is a mandatory minimum, not an exhaustive whitelist — these action
# names are added by ADR-004 §2.8.
AUDIT_FOLLOW_UP_SCHEDULED = "FOLLOW_UP_SCHEDULED"
AUDIT_FOLLOW_UP_SUPERSEDED = "FOLLOW_UP_SUPERSEDED"
AUDIT_CASE_FOLLOWUP_DUE = "CASE_FOLLOWUP_DUE"
AUDIT_CASE_IMPROVEMENT_VERIFIED = "CASE_IMPROVEMENT_VERIFIED"
AUDIT_CASE_FOLLOWUP_EXPIRED = "CASE_FOLLOWUP_EXPIRED"

_SOURCE_SYSTEM = "CORE_PLATFORM"
_APPROVED_MENTOR_DECISIONS = frozenset({"APPROVED", "EDITED"})
_CONFLICT_BAND = "DATA_CONFLICT"
# Attendance derived-state bands (attendance engine contract, ADR-004 §2.5):
# a student row still WARNING/CRITICAL means the original risk is NOT yet
# resolved — an aggregate percentage above threshold can mask a course run
# that is still at risk.
_RISK_BANDS = frozenset({"WARNING", "CRITICAL"})
# Reason vocabulary that this predicate can evaluate today (06 §4 trigger
# policies may fulfil follow-ups carrying other codes — those codes are
# deferred to their owning contract and fail closed here).
_REASON_LOW_ATTENDANCE = "LOW_ATTENDANCE"

_VALID_TRIGGER_TYPES = frozenset(t.value for t in FollowUpTriggerType)


class FollowUpError(Exception):
    """Domain error mapped to an HTTP status by the router layer."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FollowUpResult:
    follow_up_id: UUID
    case_id: UUID
    trigger_type: str
    status: str
    due_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ImprovementCheck:
    """Result of the deterministic improvement predicate (02 §2.1 Step 7).

    `verified` requires attendance_ok AND risk_cleared AND tasks_ok AND
    reasons_ok — every declared reason for the intervention must hold.
    """

    verified: bool
    attendance_ok: bool
    risk_cleared: bool
    tasks_ok: bool
    reasons_ok: bool
    attendance_percent: Decimal | None
    threshold: Decimal


@dataclass(frozen=True, slots=True)
class ConsumerOutcome:
    """One consumer processing result (asserted in unit/PG tests)."""

    action: str  # noop | fulfilled | resolved | replan | cancelled
    follow_up_id: UUID | None = None
    case_id: UUID | None = None
    case_status: str | None = None


async def schedule_followup(
    session: AsyncSession,
    *,
    case: InterventionCase,
    trigger_type: str,
    due_at: datetime | None,
    actor_id: UUID,
) -> FollowUpResult:
    """Mentor schedules a follow-up on an ACTIVE case (02 §2.1 Step 5-6,
    06 §4 schedule_followup). The caller MUST already hold SELECT ... FOR
    UPDATE on the case row (F-03 pattern, router-owned lock).

    CUSTOM_DATE requires a future due_at (mentor custom date); event-driven
    types forbid due_at (their trigger events fulfil them).
    """
    if trigger_type not in _VALID_TRIGGER_TYPES:
        raise FollowUpError(
            "INVALID_TRIGGER_TYPE",
            f"Unknown follow-up trigger type '{trigger_type}'",
        )

    case_status = _status_value(case.status)
    if case_status != InterventionCaseStatus.ACTIVE.value:
        raise FollowUpError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {case_status}; scheduling a follow-up "
                f"requires {InterventionCaseStatus.ACTIVE.value} "
                "(03_SYSTEM_SPEC §10.2, ADR-004 §2.7)"
            ),
        )

    now = datetime.now(UTC)
    if trigger_type == FollowUpTriggerType.CUSTOM_DATE.value:
        if due_at is None:
            raise FollowUpError(
                "INVALID_REQUEST",
                "CUSTOM_DATE follow-ups require due_at (02 §2.1 Step 6)",
            )
        if due_at <= now:
            raise FollowUpError(
                "INVALID_REQUEST",
                "due_at must be a future timestamp",
            )
    elif due_at is not None:
        raise FollowUpError(
            "INVALID_REQUEST",
            "due_at is only valid for CUSTOM_DATE follow-ups "
            "(event-driven types are fulfilled by their trigger events)",
        )

    follow_up = InterventionFollowUp(
        id=uuid4(),
        case_id=case.id,
        trigger_type=trigger_type,
        status=FollowUpStatus.SCHEDULED.value,
        due_at=due_at,
        created_by=str(actor_id),
        created_at=now,
    )

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type=AUDIT_FOLLOW_UP_SCHEDULED,
        entity_table="intervention_follow_ups",
        entity_id=follow_up.id,
        previous_state=None,
        new_state={
            "case_id": str(case.id),
            "follow_up_id": str(follow_up.id),
            "trigger_type": trigger_type,
            "status": FollowUpStatus.SCHEDULED.value,
        },
        source_system="MENTOR_WEB",
    )

    session.add(follow_up)
    await session.commit()

    return FollowUpResult(
        follow_up_id=follow_up.id,
        case_id=case.id,
        trigger_type=trigger_type,
        status=FollowUpStatus.SCHEDULED.value,
        due_at=due_at,
        created_at=now,
    )


async def check_improvement(
    session: AsyncSession, *, case: InterventionCase
) -> ImprovementCheck:
    """Deterministic improvement predicate (02 §2.1 Step 7; ADR-004 §2.5).

    Attendance — ONE query over the student's derived rows (no conflict
    pre-check + totals split):
      * any DATA_CONFLICT row        → fail (engine never trusts a conflicted
                                       aggregate; conflict is not a band to
                                       paper over)
      * aggregate attended/conducted → percentage requires conducted > 0;
                                       no data → not verified (fail-closed)
      * any row still WARNING/CRITICAL → risk_cleared False: the ORIGINAL
                                       risk must be resolved, not merely an
                                       aggregate above threshold
      * attendance_ok = no conflict AND percentage >= institution threshold

    Tasks — the case's APPROVED plan (mentor_decision APPROVED/EDITED) is
    required (PENDING_APPROVAL → ACTIVE is the approval, so an ACTIVE case
    always has one): every plan action must be materialized as a
    StudentTask row (source_type=AI_PLAN, source_id=plan.id) and none may
    be non-COMPLETED. Zero-materialized plans do NOT vacuously pass.
    No approved plan → not verified.

    Reasons — every approved-plan reason code must hold: LOW_ATTENDANCE
    requires attendance_ok AND risk_cleared; an unknown/unevaluable code
    fails closed. No approved plan → not verified.
    """
    threshold = await get_attendance_threshold(session, case.student_id)

    rows = await session.execute(
        select(
            AttendanceDerivedState.classes_attended,
            AttendanceDerivedState.classes_conducted,
            AttendanceDerivedState.risk_band,
        ).where(AttendanceDerivedState.student_id == case.student_id)
    )
    has_conflict = False
    risk_cleared = True
    attended_total = 0
    conducted_total = 0
    for attended, conducted, band in rows:
        if band == _CONFLICT_BAND:
            has_conflict = True
        if band in _RISK_BANDS:
            risk_cleared = False
        attended_total += int(attended or 0)
        conducted_total += int(conducted or 0)

    attendance_percent: Decimal | None = None
    if not has_conflict and conducted_total > 0:
        attendance_percent = (
            Decimal(attended_total) / Decimal(conducted_total)
        ) * Decimal(100)
    attendance_ok = attendance_percent is not None and attendance_percent >= threshold

    plans = await session.execute(
        select(InterventionPlan)
        .where(InterventionPlan.case_id == case.id)
        .order_by(InterventionPlan.created_at.desc())
    )
    approved = next(
        (
            p
            for p in plans.scalars()
            if p.mentor_decision in _APPROVED_MENTOR_DECISIONS
        ),
        None,
    )
    if approved is None:
        tasks_ok = False  # fail-closed — no approved plan, no verification
        reasons_ok = False
    else:
        statuses = await session.execute(
            select(StudentTask.status)
            .where(
                StudentTask.student_id == case.student_id,
                StudentTask.source_type == TaskSourceType.AI_PLAN,
                StudentTask.source_id == approved.id,
            )
        )
        materialized = list(statuses.scalars())
        planned = len(approved.plan_actions or [])
        tasks_ok = len(materialized) >= planned and all(
            _status_value(status) == TaskStatus.COMPLETED.value
            for status in materialized
        )
        reasons_ok = all(
            _reason_holds(
                code, attendance_ok=attendance_ok, risk_cleared=risk_cleared
            )
            for code in (approved.reason_codes or [])
        )

    return ImprovementCheck(
        verified=attendance_ok and risk_cleared and tasks_ok and reasons_ok,
        attendance_ok=attendance_ok,
        risk_cleared=risk_cleared,
        tasks_ok=tasks_ok,
        reasons_ok=reasons_ok,
        attendance_percent=attendance_percent,
        threshold=threshold,
    )


def _reason_holds(code: str, *, attendance_ok: bool, risk_cleared: bool) -> bool:
    """Predicate for one approved-plan reason code (ADR-004 §2.5). Unknown
    or not-yet-evaluable codes fail closed — verified means every declared
    reason is demonstrably resolved."""
    if code == _REASON_LOW_ATTENDANCE:
        return attendance_ok and risk_cleared
    return False


async def handle_followup_due_event(
    session: AsyncSession, event: DomainEvent, *, now: datetime | None = None
) -> ConsumerOutcome:
    """MENTOR_FOLLOWUP_DUE consumer entry (scheduler-emitted, 03 §8.3).

    Row status is authoritative (payload `phase` is advisory): SCHEDULED →
    due fulfilment (with stale-sibling supersession; or CANCELLED when the
    case is no longer ACTIVE — ADR-004 §2.1); FULFILLED → expiry re-check
    once the evaluation window has ended. Anything else (already EVALUATED,
    already CANCELLED, future CUSTOM_DATE, window not ended) is a no-op —
    duplicate/early dispatch safe.
    """
    now = now if now is not None else datetime.now(UTC)
    locked = await session.execute(
        select(InterventionFollowUp)
        .where(InterventionFollowUp.id == event.source_id)
        .with_for_update()
    )
    follow_up = locked.scalar_one_or_none()
    if follow_up is None:
        return ConsumerOutcome(action="noop")

    fu_status = _status_value(follow_up.status)
    if fu_status == FollowUpStatus.SCHEDULED.value:
        if (
            follow_up.due_at is not None
            and follow_up.due_at > now
        ):
            return ConsumerOutcome(action="noop")  # stray early DUE
        return await _fulfil_due(session, follow_up=follow_up, now=now)
    if fu_status == FollowUpStatus.FULFILLED.value:
        window_end = follow_up.evaluation_window_ends_at
        if window_end is None or window_end > now:
            return ConsumerOutcome(action="noop")  # window not ended
        return await _expire(session, follow_up=follow_up, now=now)
    return ConsumerOutcome(action="noop")


async def handle_policy_event(
    session: AsyncSession, event: DomainEvent, *, now: datetime | None = None
) -> list[ConsumerOutcome]:
    """Event-path fulfilment (02 §2.1 Step 6 / 06 §4 trigger policies).

    Finds SCHEDULED follow-ups whose trigger type matches this catalog
    event for the student's ACTIVE cases and fulfils each (one case
    transition per case — a second follow-up on the same case no-ops once
    the case has left ACTIVE).
    """
    now = now if now is not None else datetime.now(UTC)
    trigger_types = EVENT_PATH_TRIGGER_TYPES.get(event.event_type)
    if not trigger_types:
        return []

    result = await session.execute(
        select(InterventionFollowUp)
        .join(InterventionCase, InterventionCase.id == InterventionFollowUp.case_id)
        .where(
            InterventionFollowUp.status == FollowUpStatus.SCHEDULED.value,
            InterventionFollowUp.trigger_type.in_(trigger_types),
            InterventionCase.student_id == event.student_id,
            InterventionCase.status == InterventionCaseStatus.ACTIVE.value,
        )
        .order_by(InterventionFollowUp.created_at, InterventionFollowUp.id)
        .with_for_update(of=InterventionFollowUp)
    )
    follow_ups = list(result.scalars().all())

    outcomes: list[ConsumerOutcome] = []
    for follow_up in follow_ups:
        # Re-read under the lock in a fresh state — a concurrent dispatch
        # may have flipped the row between the scan and this iteration, and
        # _fulfil_due cancels same-case siblings (they appear here already
        # CANCELLED → noop).
        if _status_value(follow_up.status) != FollowUpStatus.SCHEDULED.value:
            outcomes.append(ConsumerOutcome(action="noop", follow_up_id=follow_up.id))
            continue
        outcome = await _fulfil_due(session, follow_up=follow_up, now=now)
        outcomes.append(outcome)
    return outcomes


async def _audit_superseded(
    session: AsyncSession,
    *,
    follow_up: InterventionFollowUp,
    reason: str,
    case_status: str | None = None,
) -> None:
    """FOLLOW_UP_SUPERSEDED audit row for a CANCELLED follow-up (ADR-004
    §2.8; 07 §4 — UUID/scalars-only state JSON)."""
    new_state = {
        "status": FollowUpStatus.CANCELLED.value,
        "follow_up_id": str(follow_up.id),
        "case_id": str(follow_up.case_id),
        "reason": reason,
    }
    if case_status is not None:
        new_state["case_status"] = case_status
    await log_audit(
        session,
        actor_id=None,
        actor_type="RULE_ENGINE",
        action_type=AUDIT_FOLLOW_UP_SUPERSEDED,
        entity_table="intervention_follow_ups",
        entity_id=follow_up.id,
        previous_state={
            "status": FollowUpStatus.SCHEDULED.value,
            "follow_up_id": str(follow_up.id),
        },
        new_state=new_state,
        source_system=_SOURCE_SYSTEM,
    )


async def _cancel_stale_siblings(
    session: AsyncSession, *, follow_up: InterventionFollowUp
) -> int:
    """Cancel every other SCHEDULED follow-up on this case (ADR-004 §2.1
    Option B): exactly one follow-up drives a case cycle. SKIP LOCKED keeps
    the lock order deadlock-safe against a concurrent txn holding a sibling
    while waiting on this case row."""
    stale = await session.execute(
        select(InterventionFollowUp)
        .where(
            InterventionFollowUp.case_id == follow_up.case_id,
            InterventionFollowUp.status == FollowUpStatus.SCHEDULED.value,
            InterventionFollowUp.id != follow_up.id,
        )
        .order_by(InterventionFollowUp.created_at, InterventionFollowUp.id)
        .with_for_update(skip_locked=True)
    )
    cancelled = 0
    for sibling in stale.scalars():
        sibling.status = FollowUpStatus.CANCELLED.value
        cancelled += 1
        await _audit_superseded(
            session, follow_up=sibling, reason="superseded_by_fulfilment"
        )
    return cancelled


async def _fulfil_due(
    session: AsyncSession, *, follow_up: InterventionFollowUp, now: datetime
) -> ConsumerOutcome:
    """SCHEDULED → FULFILLED + ACTIVE → MONITORING (+ immediate improvement
    check → maybe RESOLVED). One transaction: locks, transitions, audits,
    commit (ADR-004 §2.4).

    Multiple-follow-up lifecycle (ADR-004 §2.1 Option B consumption rule):
      * case no longer ACTIVE at dispatch → this SCHEDULED row can never
        fulfil (a peer/mentor already moved the case): it is CANCELLED
        (audit FOLLOW_UP_SUPERSEDED) instead of lingering SCHEDULED —
        fixes the EMITTED-then-stale defect (the DUE condition does not
        filter on case status, so every cycle would re-see it).
      * case ACTIVE → after the case lock, all other SCHEDULED sibling
        rows of this case are CANCELLED (SKIP LOCKED — the time path locks
        fu→case while a concurrent txn may hold sibling→case): exactly one
        follow-up drives a case cycle; stacked rows end terminal rather
        than stale. Audits: SUPERSEDED… then CASE_FOLLOWUP_DUE.
    """
    case_locked = await session.execute(
        select(InterventionCase)
        .where(InterventionCase.id == follow_up.case_id)
        .with_for_update()
    )
    case = case_locked.scalar_one_or_none()
    if case is None or _status_value(case.status) != InterventionCaseStatus.ACTIVE.value:
        if _status_value(follow_up.status) == FollowUpStatus.SCHEDULED.value:
            follow_up.status = FollowUpStatus.CANCELLED.value
            await _audit_superseded(
                session,
                follow_up=follow_up,
                reason="case_not_active",
                case_status=(
                    _status_value(case.status) if case is not None else None
                ),
            )
            await session.commit()
            return ConsumerOutcome(
                action="cancelled",
                follow_up_id=follow_up.id,
                case_id=follow_up.case_id,
                case_status=_status_value(case.status) if case is not None else None,
            )
        await session.rollback()
        return ConsumerOutcome(
            action="noop", follow_up_id=follow_up.id, case_id=follow_up.case_id
        )

    await _cancel_stale_siblings(session, follow_up=follow_up)

    window_days = await get_followup_evaluation_window_days(session, case.student_id)

    follow_up.status = FollowUpStatus.FULFILLED.value
    follow_up.triggered_at = now
    follow_up.evaluation_window_ends_at = now + timedelta(days=window_days)

    previous_status = _status_value(case.status)
    case.status = InterventionCaseStatus.MONITORING
    case.updated_at = now

    await log_audit(
        session,
        actor_id=None,
        actor_type="RULE_ENGINE",
        action_type=AUDIT_CASE_FOLLOWUP_DUE,
        entity_table="intervention_cases",
        entity_id=case.id,
        previous_state={"case_id": str(case.id), "case_status": previous_status},
        new_state={
            "case_id": str(case.id),
            "case_status": InterventionCaseStatus.MONITORING.value,
            "follow_up_id": str(follow_up.id),
            "trigger_type": follow_up.trigger_type,
        },
        source_system=_SOURCE_SYSTEM,
    )

    improvement = await check_improvement(session, case=case)
    if improvement.verified:
        case.status = InterventionCaseStatus.RESOLVED
        case.resolved_at = now
        case.updated_at = now
        follow_up.status = FollowUpStatus.EVALUATED.value
        follow_up.outcome = InterventionCaseStatus.RESOLVED.value
        follow_up.evaluated_at = now
        await log_audit(
            session,
            actor_id=None,
            actor_type="RULE_ENGINE",
            action_type=AUDIT_CASE_IMPROVEMENT_VERIFIED,
            entity_table="intervention_cases",
            entity_id=case.id,
            previous_state={
                "case_id": str(case.id),
                "case_status": InterventionCaseStatus.MONITORING.value,
            },
            new_state={
                "case_id": str(case.id),
                "case_status": InterventionCaseStatus.RESOLVED.value,
                "follow_up_id": str(follow_up.id),
            },
            source_system=_SOURCE_SYSTEM,
        )
        await session.commit()
        return ConsumerOutcome(
            action="resolved",
            follow_up_id=follow_up.id,
            case_id=case.id,
            case_status=InterventionCaseStatus.RESOLVED.value,
        )

    await session.commit()
    return ConsumerOutcome(
        action="fulfilled",
        follow_up_id=follow_up.id,
        case_id=case.id,
        case_status=InterventionCaseStatus.MONITORING.value,
    )


async def _expire(
    session: AsyncSession, *, follow_up: InterventionFollowUp, now: datetime
) -> ConsumerOutcome:
    """FULFILLED → EVALUATED at window end: improvement re-check →
    MONITORING → RESOLVED or MONITORING → REPLAN_REQUIRED (ADR-004 §2.4)."""
    case_locked = await session.execute(
        select(InterventionCase)
        .where(InterventionCase.id == follow_up.case_id)
        .with_for_update()
    )
    case = case_locked.scalar_one_or_none()
    if case is None or _status_value(case.status) != InterventionCaseStatus.MONITORING.value:
        await session.rollback()
        return ConsumerOutcome(
            action="noop", follow_up_id=follow_up.id, case_id=follow_up.case_id
        )

    improvement = await check_improvement(session, case=case)
    follow_up.status = FollowUpStatus.EVALUATED.value
    follow_up.evaluated_at = now

    previous_state = {
        "case_id": str(case.id),
        "case_status": InterventionCaseStatus.MONITORING.value,
    }
    if improvement.verified:
        case.status = InterventionCaseStatus.RESOLVED
        case.resolved_at = now
        case.updated_at = now
        follow_up.outcome = InterventionCaseStatus.RESOLVED.value
        action_type = AUDIT_CASE_IMPROVEMENT_VERIFIED
        next_status = InterventionCaseStatus.RESOLVED.value
        action = "resolved"
    else:
        case.status = InterventionCaseStatus.REPLAN_REQUIRED
        case.updated_at = now
        follow_up.outcome = InterventionCaseStatus.REPLAN_REQUIRED.value
        action_type = AUDIT_CASE_FOLLOWUP_EXPIRED
        next_status = InterventionCaseStatus.REPLAN_REQUIRED.value
        action = "replan"

    await log_audit(
        session,
        actor_id=None,
        actor_type="RULE_ENGINE",
        action_type=action_type,
        entity_table="intervention_cases",
        entity_id=case.id,
        previous_state=previous_state,
        new_state={
            "case_id": str(case.id),
            "case_status": next_status,
            "follow_up_id": str(follow_up.id),
        },
        source_system=_SOURCE_SYSTEM,
    )
    await session.commit()
    return ConsumerOutcome(
        action=action,
        follow_up_id=follow_up.id,
        case_id=case.id,
        case_status=next_status,
    )


class FollowUpConsumer:
    """Deterministic RULE_ENGINE bus subscriber (03 §10.2 scheduler note).

    Owns no LLM calls and no agent routing — it is a pure event consumer
    that validates and performs the frozen follow-up transitions. Session
    lifecycle is consumer-owned (mirrors the scheduler's session usage);
    a failing handler rolls back and raises (window D — terminal, logged
    by the bus).
    """

    SUBSCRIBED_EVENTS: Sequence[str] = (
        EVENT_MENTOR_FOLLOWUP_DUE,
        EVENT_ATTENDANCE_UPDATED,
        EVENT_ASSESSMENT_GRADED,
        EVENT_QUIZ_COMPLETED,
        EVENT_TASK_OVERDUE,
    )

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker
        self._subscribed_buses: set[int] = set()

    def ensure_subscribed(self, bus: EventBus) -> None:
        """Idempotent per bus (lifespan/TestClient restarts never double-subscribe)."""
        if id(bus) in self._subscribed_buses:
            return
        for event_type in self.SUBSCRIBED_EVENTS:
            bus.subscribe(event_type, self._on_event)
        self._subscribed_buses.add(id(bus))

    async def _on_event(self, event: DomainEvent) -> None:
        async with self._session_maker() as session:
            try:
                if event.event_type == EVENT_MENTOR_FOLLOWUP_DUE:
                    outcome = await handle_followup_due_event(session, event)
                    logger.info(
                        "follow-up consumer: %s source_id=%s action=%s",
                        event.event_type,
                        event.source_id,
                        outcome.action,
                    )
                else:
                    outcomes = await handle_policy_event(session, event)
                    logger.info(
                        "follow-up consumer: %s student_id=%s fulfilled=%d",
                        event.event_type,
                        event.student_id,
                        sum(
                            1
                            for o in outcomes
                            if o.action in ("fulfilled", "resolved", "replan")
                        ),
                    )
            except Exception:
                await session.rollback()
                logger.exception(
                    "follow-up consumer: handler failed event_type=%s source_id=%s",
                    event.event_type,
                    event.source_id,
                )
                raise


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
