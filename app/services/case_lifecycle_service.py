# app/services/case_lifecycle_service.py
# Case Lifecycle Service — owner of the remaining post-approval mentor
# transitions (03_SYSTEM_SPEC §10.2):
#   RESOLVED            → CLOSED                (Mentor closes)
#   ESCALATION_REQUIRED → ESCALATION_REQUIRED   (Mentor escalates to HOD/CT)
# Pattern mirrors case_service: validate state (§10.2) → transition → audit
# row (07 §4) → commit. Neither row has a domain event in the canonical
# catalog (03 §8.2); both are audit-only writes — the same precedent as a
# mentor plan rejection (audit row, no event).
#
# Concurrency: the caller MUST hold SELECT ... FOR UPDATE on the case row
# in this session (F-03 pattern), so concurrent lifecycle actions serialize
# and the loser observes the committed state.

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import log_audit
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase

AUDIT_ACTION_CASE_CLOSED = "CASE_CLOSED"  # 07 §4 mandatory audit event
AUDIT_ACTION_CASE_ESCALATED = "CASE_ESCALATED"  # 07 §4 mandatory audit event

# 03 §10.2 escalation row: "Mentor escalates to HOD/CT (pending HOD)".
# The frozen transition table names exactly these two targets; 02 §2.2
# Step 4 also mentions Support Services, which the frozen table does not
# list — the table wins (no actor/target outside the frozen contract).
ESCALATION_TARGETS: frozenset[str] = frozenset({"HOD", "CT"})

_SOURCE_CLOSED = InterventionCaseStatus.RESOLVED.value
_SOURCE_ESCALATE = InterventionCaseStatus.ESCALATION_REQUIRED.value


class CaseLifecycleError(Exception):
    """Domain error mapped to an HTTP status by the router layer."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class CaseLifecycleResult:
    case_id: UUID
    case_status: str
    acted_at: datetime
    escalated_to: str | None = None


async def close_case(
    session: AsyncSession,
    *,
    case: InterventionCase,
    actor_id: UUID,
) -> CaseLifecycleResult:
    """Mentor closes a resolved case: RESOLVED → CLOSED (03 §10.2).

    Sequence: validate source state → set CLOSED + closed_at → audit row
    (07 §4 CASE_CLOSED) → commit. No domain event: the catalog (03 §8.2)
    has no case-closed event; closure is an audited human action only.
    """
    previous_status = _status_value(case.status)
    if previous_status != _SOURCE_CLOSED:
        raise CaseLifecycleError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {previous_status}; closing requires "
                f"{_SOURCE_CLOSED} (03_SYSTEM_SPEC §10.2)"
            ),
        )

    acted_at = datetime.now(UTC)
    case.status = InterventionCaseStatus.CLOSED
    case.closed_at = acted_at
    case.updated_at = acted_at

    previous_state = {
        "case_id": str(case.id),
        "case_status": previous_status,
    }
    new_state = {
        "case_id": str(case.id),
        "case_status": InterventionCaseStatus.CLOSED.value,
    }

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type=AUDIT_ACTION_CASE_CLOSED,
        entity_table="intervention_cases",
        entity_id=case.id,
        previous_state=previous_state,
        new_state=new_state,
        source_system="MENTOR_WEB",
    )

    await session.commit()

    return CaseLifecycleResult(
        case_id=case.id,
        case_status=InterventionCaseStatus.CLOSED.value,
        acted_at=acted_at,
    )


async def escalate_case(
    session: AsyncSession,
    *,
    case: InterventionCase,
    actor_id: UUID,
    target: str,
    note: str | None = None,
) -> CaseLifecycleResult:
    """Mentor escalates an already-escalated case to HOD/CT (03 §10.2
    self-transition: ESCALATION_REQUIRED → ESCALATION_REQUIRED, pending
    HOD/CT action; 02 §2.2 Steps 3-5).

    The frozen table keeps the case in ESCALATION_REQUIRED — the pending
    HOD/CT marker IS that state (the case is visible to HOD via the
    escalation scope in 07 §2). The mentor's target selection and optional
    note are recorded on the mandatory CASE_ESCALATED audit row (07 §4).
    No schema change: no follow-up/escalation columns exist in
    intervention_cases (05 §9) and inventing one would be an unapproved
    contract change.
    """
    previous_status = _status_value(case.status)
    if previous_status != _SOURCE_ESCALATE:
        raise CaseLifecycleError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {previous_status}; mentor escalation "
                f"requires {_SOURCE_ESCALATE} (03_SYSTEM_SPEC §10.2)"
            ),
        )

    if target not in ESCALATION_TARGETS:
        raise CaseLifecycleError(
            "INVALID_TARGET",
            (
                f"Unknown escalation target '{target}'; "
                f"allowed: {', '.join(sorted(ESCALATION_TARGETS))} "
                "(03_SYSTEM_SPEC §10.2)"
            ),
        )

    acted_at = datetime.now(UTC)
    # Self-transition: status stays ESCALATION_REQUIRED (the frozen table
    # row); only the clock moves so the mentor queue's days-since-action
    # reflects the escalation.
    case.updated_at = acted_at

    previous_state = {
        "case_id": str(case.id),
        "case_status": previous_status,
    }
    new_state = {
        "case_id": str(case.id),
        "case_status": previous_status,
        "escalated_to": target,
    }
    if note:
        new_state["escalation_note"] = note

    await log_audit(
        session,
        actor_id=actor_id,
        actor_type="USER",
        action_type=AUDIT_ACTION_CASE_ESCALATED,
        entity_table="intervention_cases",
        entity_id=case.id,
        previous_state=previous_state,
        new_state=new_state,
        source_system="MENTOR_WEB",
    )

    await session.commit()

    return CaseLifecycleResult(
        case_id=case.id,
        case_status=previous_status,
        acted_at=acted_at,
        escalated_to=target,
    )


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
