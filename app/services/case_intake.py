# app/services/case_intake.py
# Case Intake Service — the Supervisor/risk-path producer for intervention
# case creation (11_ROADMAP R2; 03_SYSTEM_SPEC §10.2 row: Supervisor Agent
# performs OPEN → IN_REVIEW as the "System creates case" action).
#
# Sequence: validate student/mentor → dedup against non-terminal cases →
# insert case (OPEN) → transition OPEN → IN_REVIEW → audit row (07 §4,
# actor SYSTEM_AGENT) → commit. No domain event is emitted: the canonical
# catalog (03 §8.2) has no case-creation event, and adding one requires the
# ADR process (ADR-002 precedent).

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import log_audit
from app.core.database import session_context
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase
from app.models.student import StudentProfile

# Non-terminal case states (§10.1 lifecycle): RESOLVED/CLOSED are terminal
# and do not block a new risk case for the same student.
NON_TERMINAL_CASE_STATUSES: frozenset[InterventionCaseStatus] = frozenset(
    {
        InterventionCaseStatus.OPEN,
        InterventionCaseStatus.IN_REVIEW,
        InterventionCaseStatus.PLAN_PROPOSED,
        InterventionCaseStatus.PENDING_APPROVAL,
        InterventionCaseStatus.ACTIVE,
        InterventionCaseStatus.MONITORING,
        InterventionCaseStatus.REPLAN_REQUIRED,
        InterventionCaseStatus.ESCALATION_REQUIRED,
    }
)

AUDIT_ACTION_CASE_OPENED = "CASE_OPENED_TO_IN_REVIEW"

SessionMaker = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class CaseIntakeError(Exception):
    """Domain error: the risk case could not be created."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class CaseIntakeResult:
    case_id: UUID
    created: bool  # False = reused the student's existing non-terminal case
    case_status: str  # IN_REVIEW when this call performed the transition


async def ensure_risk_case(
    *,
    student_id: UUID,
    trigger_event_id: UUID,
    urgency_band: str,
    session_maker: SessionMaker = session_context,
) -> CaseIntakeResult:
    """Create (or reuse) the student's non-terminal case for the risk path.

    Exactly one non-terminal case may exist per student: a second risk event
    reuses it rather than duplicating (F-01-style ambiguity refusal is not
    needed here — reuse is the defined behavior). The student must have an
    assigned mentor (intervention_cases.mentor_id is NOT NULL); otherwise
    CaseIntakeError("NO_MENTOR_ASSIGNED") — the caller escalates to a human
    instead of inventing an assignment.
    """
    async with session_maker() as session:
        profile = (
            await session.execute(
                select(StudentProfile).where(StudentProfile.id == student_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            raise CaseIntakeError(
                "STUDENT_NOT_FOUND",
                f"No student profile {student_id}",
            )

        existing = (
            await session.execute(
                select(InterventionCase.id, InterventionCase.status)
                .where(
                    InterventionCase.student_id == student_id,
                    InterventionCase.status.in_(
                        [s.value for s in NON_TERMINAL_CASE_STATUSES]
                    ),
                )
                .limit(1)
            )
        ).first()
        if existing is not None:
            return CaseIntakeResult(
                case_id=existing[0],
                created=False,
                case_status=_status_value(existing[1]),
            )

        if profile.mentor_id is None:
            raise CaseIntakeError(
                "NO_MENTOR_ASSIGNED",
                f"Student {student_id} has no assigned mentor",
            )

        now = datetime.now(UTC)
        case = InterventionCase(
            id=uuid.uuid4(),
            student_id=student_id,
            mentor_id=profile.mentor_id,
            status=InterventionCaseStatus.OPEN,  # model default; set explicitly
            urgency_band=urgency_band,
            trigger_events=[str(trigger_event_id)],
            opened_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(case)

        # §10.2: Supervisor Agent performs OPEN → IN_REVIEW.
        previous_state = {
            "case_id": str(case.id),
            "student_id": str(student_id),
            "case_status": InterventionCaseStatus.OPEN.value,
            "urgency_band": urgency_band,
        }
        case.status = InterventionCaseStatus.IN_REVIEW
        case.updated_at = now
        new_state = {
            "case_id": str(case.id),
            "case_status": InterventionCaseStatus.IN_REVIEW.value,
            "trigger_event_id": str(trigger_event_id),
        }

        await log_audit(
            session,
            actor_id=None,  # SYSTEM_AGENT run — no acting user (07 §13)
            actor_type="SYSTEM_AGENT",
            action_type=AUDIT_ACTION_CASE_OPENED,
            entity_table="intervention_cases",
            entity_id=case.id,
            previous_state=previous_state,
            new_state=new_state,
            source_system="AGENT",
        )

        await session.commit()

        return CaseIntakeResult(
            case_id=case.id,
            created=True,
            case_status=InterventionCaseStatus.IN_REVIEW.value,
        )


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
