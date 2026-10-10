# app/services/student_action_service.py
# Student Action Service — single owner of student plan-decision transitions.
# State machine: docs/03_SYSTEM_SPEC.md §10.2 (student acceptance rows).
# Event: PLAN_ACCEPTED after commit (docs/03_SYSTEM_SPEC.md §8.1/§8.2).
# Audit: separate audit_log row (docs/07_SECURITY_TRUST.md §4).
#
# Scope of this slice: acceptance only — PLAN_PROPOSED → PENDING_APPROVAL for
# decisions ACCEPTED and CUSTOMIZED. Decline (PLAN_PROPOSED → REPLAN_REQUIRED,
# event PLAN_DECLINED) is deferred to a later slice; a decline decision is
# therefore refused here as an unknown decision (never silently honored).

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import log_audit
from app.core.events import DomainEvent, EventBus
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan

EVENT_PLAN_ACCEPTED = "PLAN_ACCEPTED"

# 03_SYSTEM_SPEC §10.2 student acceptance rows: from PLAN_PROPOSED, a student
# acceptance always lands on PENDING_APPROVAL. Plan statuses are constrained
# to PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED (05 §9,
# migration 009); both acceptance outcomes emit PLAN_ACCEPTED — the canonical
# catalog has no separate customized-plan event (03 §8.2).
_ACCEPTANCE_DECISIONS = frozenset({"ACCEPTED", "CUSTOMIZED"})

# Plan statuses that can be awaiting a student verdict in PLAN_PROPOSED:
# exactly the agent-proposed plan (status PROPOSED, no student_decision yet).
# Decided/dead plans (ACCEPTED/CUSTOMIZED/DECLINED/SUPERSEDED history) are
# never the authoritative target (F-05 mirror).
_AWAITING_PLAN_STATUS = "PROPOSED"


class StudentActionError(Exception):
    """Domain error mapped to an HTTP status by the router layer."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class StudentActionResult:
    case_id: UUID
    plan_id: UUID
    student_decision: str
    decided_at: datetime
    case_status: str


async def decide_plan(
    session: AsyncSession,
    *,
    case: InterventionCase,
    plans: list[InterventionPlan],
    decision: str,
    plan_actions: list[dict] | None,
    actor_id: UUID,
    event_bus: EventBus | None = None,
) -> StudentActionResult:
    """Apply a student acceptance decision to the proposed plan.

    Sequence (03 §10.2 student rows): validate decision → validate state →
    select the authoritative plan → apply payload rules → transition → audit
    row → commit → emit PLAN_ACCEPTED. The audit row is written
    independently of the domain event (07 §4).

    Plan selection: plan history is expected (replan cycles append plans), so
    exactly one plan may be awaiting the student verdict — status PROPOSED
    with no student_decision yet. Zero such plans → NO_PLAN (400). More than
    one → AMBIGUOUS_PLAN (409): §10.2 defines a single transition for a
    single plan, so ambiguous data is refused rather than resolved by picking
    an arbitrary row.
    """
    if decision not in _ACCEPTANCE_DECISIONS:
        raise StudentActionError(
            "INVALID_DECISION",
            f"Unknown student decision '{decision}'",
        )

    previous_status = _status_value(case.status)
    if previous_status != InterventionCaseStatus.PLAN_PROPOSED.value:
        raise StudentActionError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {previous_status}; student decisions require "
                f"{InterventionCaseStatus.PLAN_PROPOSED.value} (03_SYSTEM_SPEC §10.2)"
            ),
        )

    awaiting = [
        p
        for p in plans
        if p.status == _AWAITING_PLAN_STATUS and p.student_decision is None
    ]
    if not awaiting:
        raise StudentActionError(
            "NO_PLAN",
            f"No proposed plan awaiting a student decision for case {case.id}",
        )
    if len(awaiting) > 1:
        raise StudentActionError(
            "AMBIGUOUS_PLAN",
            (
                f"Case {case.id} has {len(awaiting)} plans awaiting a student "
                "decision; §10.2 permits exactly one (03_SYSTEM_SPEC §10.2)"
            ),
        )
    plan = awaiting[0]

    # Payload rules (02_USER_JOURNEYS 1.1 Step 6): a customized plan must
    # carry the student's adjusted actions — never a silent default; a plain
    # acceptance must not smuggle in edits. The request schema enforces this
    # at the HTTP boundary; the service re-checks for direct callers.
    if decision == "CUSTOMIZED":
        if not plan_actions:
            raise StudentActionError(
                "INVALID_REQUEST",
                "CUSTOMIZED decisions require non-empty plan_actions "
                "(02_USER_JOURNEYS 1.1 Step 6)",
            )
    elif plan_actions:
        raise StudentActionError(
            "INVALID_REQUEST",
            "plan_actions may only accompany a CUSTOMIZED decision",
        )

    previous_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": previous_status,
        "plan_status": plan.status,
    }

    decided_at = datetime.now(UTC)
    plan.student_decision = decision
    plan.decided_at = decided_at
    plan.status = decision  # ACCEPTED or CUSTOMIZED (05 §9 status set)
    if decision == "CUSTOMIZED":
        plan.plan_actions = plan_actions
    plan.updated_at = decided_at
    case.status = InterventionCaseStatus.PENDING_APPROVAL
    case.updated_at = decided_at

    new_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": InterventionCaseStatus.PENDING_APPROVAL.value,
        "plan_status": plan.status,
        "student_decision": decision,
    }

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type="PLAN_ACCEPTED",  # 07 §4 mandatory audit event
        entity_table="intervention_plans",
        entity_id=plan.id,
        previous_state=previous_state,
        new_state=new_state,
        source_system="STUDENT_APP",
    )

    # Commit before emitting so subscribers only ever see persisted state
    # (get_session's teardown commit then becomes a no-op).
    await session.commit()

    if event_bus is not None:
        event = DomainEvent(
            event_type=EVENT_PLAN_ACCEPTED,
            student_id=case.student_id,
            source_id=plan.id,
            payload={
                "case_id": str(case.id),
                "plan_id": str(plan.id),
                "decision": decision,
                "previous_status": previous_status,
                "new_status": InterventionCaseStatus.PENDING_APPROVAL.value,
            },
        )
        await event_bus.publish(event)

    return StudentActionResult(
        case_id=case.id,
        plan_id=plan.id,
        student_decision=decision,
        decided_at=decided_at,
        case_status=InterventionCaseStatus.PENDING_APPROVAL.value,
    )


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
