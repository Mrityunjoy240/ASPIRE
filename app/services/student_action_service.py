# app/services/student_action_service.py
# Student Action Service — single owner of student plan-decision transitions.
# State machine: docs/03_SYSTEM_SPEC.md §10.2 (student rows).
# Events: PLAN_ACCEPTED / PLAN_DECLINED after commit (docs/03_SYSTEM_SPEC.md §8.1/§8.2).
# Audit: separate audit_log row (docs/07_SECURITY_TRUST.md §4).
#
# Rows implemented:
#   PLAN_PROPOSED + ACCEPTED/CUSTOMIZED → PENDING_APPROVAL (event PLAN_ACCEPTED)
#   PLAN_PROPOSED + DECLINED            → REPLAN_REQUIRED   (event PLAN_DECLINED)

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
EVENT_PLAN_DECLINED = "PLAN_DECLINED"

# 03_SYSTEM_SPEC §10.2 student rows: from PLAN_PROPOSED an acceptance always
# lands on PENDING_APPROVAL and a decline lands on REPLAN_REQUIRED. Plan
# statuses are constrained to PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED |
# SUPERSEDED (05 §9, migration 009); the acceptance outcomes emit
# PLAN_ACCEPTED — the canonical catalog has no separate customized-plan event
# (03 §8.2). Decline emits PLAN_DECLINED (03 §8.2).
_ACCEPTANCE_DECISIONS = frozenset({"ACCEPTED", "CUSTOMIZED"})
_DECLINE_DECISION = "DECLINED"
_VALID_DECISIONS = _ACCEPTANCE_DECISIONS | {_DECLINE_DECISION}

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
    reason: str | None = None,
    event_bus: EventBus | None = None,
) -> StudentActionResult:
    """Apply a student decision to the proposed plan.

    Sequence (03 §10.2 student rows): validate decision → validate state →
    select the authoritative plan → apply payload rules → transition → audit
    row → commit → emit PLAN_ACCEPTED or PLAN_DECLINED. The audit row is
    written independently of the domain event (07 §4).

    Decline reason: optional (02_USER_JOURNEYS 1.1 Step 6 "student
    optionally provides reason"; 05 §9 `student_reason`). It is persisted on
    the plan row only — never copied into the audit state JSON or the event
    payload, which are UUID/status-only (07 §4: no free text that might
    carry PII).

    Plan selection: plan history is expected (replan cycles append plans), so
    exactly one plan may be awaiting the student verdict — status PROPOSED
    with no student_decision yet. Zero such plans → NO_PLAN (400). More than
    one → AMBIGUOUS_PLAN (409): §10.2 defines a single transition for a
    single plan, so ambiguous data is refused rather than resolved by picking
    an arbitrary row.
    """
    if decision not in _VALID_DECISIONS:
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
    # acceptance or a decline must not smuggle in edits. The request schema
    # enforces this at the HTTP boundary; the service re-checks for direct
    # callers. A decline reason is optional and decline-only; provided text
    # is stored verbatim (no content rules are specified anywhere in 02/05).
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
    if decision != _DECLINE_DECISION and reason is not None:
        raise StudentActionError(
            "INVALID_REQUEST",
            "reason may only accompany a DECLINED decision",
        )

    target_status = (
        InterventionCaseStatus.REPLAN_REQUIRED
        if decision == _DECLINE_DECISION
        else InterventionCaseStatus.PENDING_APPROVAL
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
    plan.status = decision  # ACCEPTED | CUSTOMIZED | DECLINED (05 §9 status set)
    if decision == _DECLINE_DECISION:
        plan.student_reason = reason  # optional, plan row only (05 §9; 07 §4)
    if decision == "CUSTOMIZED":
        plan.plan_actions = plan_actions
    plan.updated_at = decided_at
    case.status = target_status
    case.updated_at = decided_at

    new_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": target_status.value,
        "plan_status": plan.status,
        "student_decision": decision,
    }

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type=(
            "PLAN_DECLINED"
            if decision == _DECLINE_DECISION
            else "PLAN_ACCEPTED"  # 07 §4 mandatory audit events
        ),
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
            event_type=(
                EVENT_PLAN_DECLINED
                if decision == _DECLINE_DECISION
                else EVENT_PLAN_ACCEPTED
            ),
            student_id=case.student_id,
            source_id=plan.id,
            payload={
                "case_id": str(case.id),
                "plan_id": str(plan.id),
                "decision": decision,
                "previous_status": previous_status,
                "new_status": target_status.value,
            },
        )
        await event_bus.publish(event)

    return StudentActionResult(
        case_id=case.id,
        plan_id=plan.id,
        student_decision=decision,
        decided_at=decided_at,
        case_status=target_status.value,
    )


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
