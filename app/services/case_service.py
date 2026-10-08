# app/services/case_service.py
# Case Approval Service — single owner of mentor decision transitions.
# State machine: docs/03_SYSTEM_SPEC.md §10.2 (mentor rows).
# Event: INTERVENTION_PLAN_APPROVED after commit (docs/decisions/ADR-002).
# Audit: separate audit_log row (docs/07_SECURITY_TRUST.md §4).

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import log_audit
from app.core.events import DomainEvent, EventBus
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan

EVENT_INTERVENTION_PLAN_APPROVED = "INTERVENTION_PLAN_APPROVED"

# 03_SYSTEM_SPEC §10.2 mentor rows: PENDING_APPROVAL + mentor action → next state.
# The service refuses any transition not listed here.
# plan_status: None = leave unchanged. Plan statuses are constrained to
# PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED (05 §9, migration 009);
# the mentor verdict lives in mentor_decision (APPROVED | EDITED | REJECTED).
_MENTOR_DECISIONS: dict[str, dict[str, str | None]] = {
    "APPROVED": {"case_status": InterventionCaseStatus.ACTIVE.value, "plan_status": None},
    "EDITED": {"case_status": InterventionCaseStatus.ACTIVE.value, "plan_status": "CUSTOMIZED"},
    "REJECTED": {"case_status": InterventionCaseStatus.REPLAN_REQUIRED.value, "plan_status": "DECLINED"},
}

# Decisions that emit INTERVENTION_PLAN_APPROVED (ADR-002 emission rule).
_APPROVAL_DECISIONS = frozenset({"APPROVED", "EDITED"})

_AUDIT_ACTIONS: dict[str, str] = {
    "APPROVED": "PLAN_APPROVED_BY_MENTOR",
    "EDITED": "PLAN_APPROVED_BY_MENTOR",
    "REJECTED": "PLAN_REJECTED_BY_MENTOR",
}


class CaseApprovalError(Exception):
    """Domain error mapped to an HTTP status by the router layer."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class CaseApprovalResult:
    case_id: UUID
    decision: str
    acted_at: datetime
    case_status: str


async def approve_plan(
    session: AsyncSession,
    *,
    case: InterventionCase,
    plan: InterventionPlan,
    decision: str,
    mentor_notes: str | None,
    actor_id: UUID,
    event_bus: EventBus | None = None,
) -> CaseApprovalResult:
    """Apply a mentor decision to a plan in PENDING_APPROVAL.

    Sequence (ADR-002): validate → transition (§10.2) → audit row → commit →
    emit INTERVENTION_PLAN_APPROVED (approval decisions only). The audit row
    is written independently of the domain event.
    """
    mapping = _MENTOR_DECISIONS.get(decision)
    if mapping is None:
        raise CaseApprovalError(
            "INVALID_DECISION",
            f"Unknown mentor decision '{decision}'",
        )

    previous_status = _status_value(case.status)
    if previous_status != InterventionCaseStatus.PENDING_APPROVAL.value:
        raise CaseApprovalError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {previous_status}; mentor decisions require "
                f"{InterventionCaseStatus.PENDING_APPROVAL.value} (03_SYSTEM_SPEC §10.2)"
            ),
        )

    previous_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": previous_status,
        "plan_status": plan.status,
    }

    acted_at = datetime.now(timezone.utc)
    plan.mentor_decision = decision
    plan.mentor_notes = mentor_notes
    plan.mentor_acted_at = acted_at
    if mapping["plan_status"] is not None:
        plan.status = mapping["plan_status"]
    case.status = InterventionCaseStatus(mapping["case_status"])
    case.updated_at = acted_at

    new_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": mapping["case_status"],
        "plan_status": plan.status,
        "mentor_decision": decision,
    }

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type=_AUDIT_ACTIONS[decision],
        entity_table="intervention_plans",
        entity_id=plan.id,
        previous_state=previous_state,
        new_state=new_state,
        source_system="MENTOR_WEB",
    )

    # Commit before emitting so subscribers only ever see persisted state
    # (get_session's teardown commit then becomes a no-op).
    await session.commit()

    if decision in _APPROVAL_DECISIONS and event_bus is not None:
        event = DomainEvent(
            event_type=EVENT_INTERVENTION_PLAN_APPROVED,
            student_id=case.student_id,
            source_id=plan.id,
            payload={
                "case_id": str(case.id),
                "plan_id": str(plan.id),
                "mentor_id": str(actor_id),
                "decision": decision,
                "previous_status": previous_status,
                "new_status": mapping["case_status"],
            },
        )
        await event_bus.publish(event)

    return CaseApprovalResult(
        case_id=case.id,
        decision=decision,
        acted_at=acted_at,
        case_status=mapping["case_status"],
    )


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
