# app/services/plan_proposal_service.py
# Plan Proposal Service — sole owner of agent-produced intervention plans
# and the §10.2 agent-transition rows (03_SYSTEM_SPEC):
#   IN_REVIEW       → PLAN_PROPOSED  (Agent proposes plan)
#   REPLAN_REQUIRED → PLAN_PROPOSED  (New plan proposed)
# Pattern mirrors case_service / student_action_service: validate → insert
# plan (PROPOSED) → transition → audit row (07 §4 action PLAN_PROPOSED) →
# commit. No domain event is emitted: the canonical catalog (03 §8.2) has
# no plan-proposed event; PLAN_PROPOSED is a mandatory AUDIT action only.
#
# Concurrency: the caller MUST hold SELECT ... FOR UPDATE on the case row
# in this session (same pattern as the cases router / F-03), so concurrent
# proposal attempts serialize and the loser observes the committed state.

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import log_audit
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan
from app.services.evidence import dump_evidence_entries, validate_evidence_entries

PLAN_STATUS_PROPOSED = "PROPOSED"
CREATED_BY_SYSTEM_AGENT = "SYSTEM_AGENT"
AUDIT_ACTION_PLAN_PROPOSED = "PLAN_PROPOSED"

# 09 EC-AG-05: after 3 consecutive student declines the system stops
# auto-generating new plans ("Student not engaging with AI guidance").
# Only student declines count; an acceptance/customization (or any plan
# without a student decline) breaks the streak.
MAX_CONSECUTIVE_STUDENT_DECLINES = 3
_STUDENT_DECLINE_DECISION = "DECLINED"

# 03 §10.2 agent rows: exactly these two source states may transition via
# an agent proposal. Any other state is refused (no actor may perform a
# transition not listed in the table).
PROPOSAL_SOURCE_STATES: frozenset[str] = frozenset(
    {
        InterventionCaseStatus.IN_REVIEW.value,
        InterventionCaseStatus.REPLAN_REQUIRED.value,
    }
)


class PlanProposalError(Exception):
    """Domain error: the proposal could not be persisted; the case keeps its
    previous valid state (nothing is partially applied)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class PlanProposalResult:
    case_id: UUID
    plan_id: UUID
    case_status: str
    plan_status: str


async def propose_intervention_plan(
    session: AsyncSession,
    *,
    case: InterventionCase,
    existing_plans: Sequence[InterventionPlan],
    reason_codes: Sequence[str],
    plan_actions: Sequence[dict],
    evidence_entries: Sequence[dict],
) -> PlanProposalResult:
    """Persist one PROPOSED plan and perform the legal case transition.

    Guards (in order):
    1. Source state ∈ {IN_REVIEW, REPLAN_REQUIRED} — else ILLEGAL_TRANSITION.
    2. No undecided PROPOSED plan already exists — else
       UNDECIDED_PROPOSAL_EXISTS (an active proposal is never silently
       replaced or duplicated; replan appends only after the prior plan was
       decided).
    3. Fewer than MAX_CONSECUTIVE_STUDENT_DECLINES trailing consecutive
       student declines — else TOO_MANY_DECLINES (09 EC-AG-05).
    4. Non-empty reason_codes / plan_actions — else INVALID_REQUEST.
    5. Evidence re-validated at the persistence boundary (DEC-01 contract:
       canonical entries, unique UUID ids, typed scalars, verified
       provenance) — malformed input refuses with INVALID_EVIDENCE.

    Sequence: insert plan → transition case → audit row → commit, in one
    transaction. Any failure rolls back everything (caller's session
    context), leaving the case in its previous valid state.
    """
    previous_status = _status_value(case.status)
    if previous_status not in PROPOSAL_SOURCE_STATES:
        raise PlanProposalError(
            "ILLEGAL_TRANSITION",
            (
                f"Case {case.id} is {previous_status}; agent proposals require "
                f"{' or '.join(sorted(PROPOSAL_SOURCE_STATES))} (03_SYSTEM_SPEC §10.2)"
            ),
        )

    undecided = [
        p
        for p in existing_plans
        if p.status == PLAN_STATUS_PROPOSED and p.student_decision is None
    ]
    if undecided:
        raise PlanProposalError(
            "UNDECIDED_PROPOSAL_EXISTS",
            (
                f"Case {case.id} already has {len(undecided)} undecided PROPOSED "
                "plan(s); a new proposal is refused until the student decides "
                "(F-01-style ambiguity refusal)"
            ),
        )

    declines = _trailing_consecutive_student_declines(existing_plans)
    if declines >= MAX_CONSECUTIVE_STUDENT_DECLINES:
        raise PlanProposalError(
            "TOO_MANY_DECLINES",
            (
                f"Case {case.id} has {declines} consecutive student-declined "
                f"plan(s); auto-generation stops after "
                f"{MAX_CONSECUTIVE_STUDENT_DECLINES} (09 EC-AG-05 — student "
                "not engaging with AI guidance; the mentor takes over)"
            ),
        )

    codes = [str(code) for code in reason_codes]
    if not codes:
        raise PlanProposalError(
            "INVALID_REQUEST", "reason_codes must be non-empty"
        )
    actions = [dict(action) for action in plan_actions]
    if not actions:
        raise PlanProposalError("INVALID_REQUEST", "plan_actions must be non-empty")

    try:
        entries = validate_evidence_entries(list(evidence_entries))
    except (ValueError, ValidationError) as exc:
        raise PlanProposalError("INVALID_EVIDENCE", str(exc)) from exc

    now = datetime.now(UTC)
    plan = InterventionPlan(
        id=uuid.uuid4(),
        case_id=case.id,
        created_by=CREATED_BY_SYSTEM_AGENT,
        status=PLAN_STATUS_PROPOSED,
        plan_actions=actions,
        reason_codes=codes,
        evidence=dump_evidence_entries(entries),
        created_at=now,
        updated_at=now,
    )
    session.add(plan)

    previous_state = {
        "case_id": str(case.id),
        "case_status": previous_status,
    }
    case.status = InterventionCaseStatus.PLAN_PROPOSED
    case.updated_at = now
    new_state = {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "case_status": InterventionCaseStatus.PLAN_PROPOSED.value,
        "plan_status": PLAN_STATUS_PROPOSED,
    }

    await log_audit(
        session,
        actor_id=None,  # SYSTEM_AGENT run — no acting user (07 §13)
        actor_type="SYSTEM_AGENT",
        action_type=AUDIT_ACTION_PLAN_PROPOSED,  # 07 §4 mandatory audit event
        entity_table="intervention_plans",
        entity_id=plan.id,
        previous_state=previous_state,
        new_state=new_state,
        source_system="AGENT",
    )

    await session.commit()

    return PlanProposalResult(
        case_id=case.id,
        plan_id=plan.id,
        case_status=InterventionCaseStatus.PLAN_PROPOSED.value,
        plan_status=PLAN_STATUS_PROPOSED,
    )


def _trailing_consecutive_student_declines(
    plans: Sequence[InterventionPlan],
) -> int:
    """Count the newest-first run of student-declined plans (09 EC-AG-05).

    Ordering is created_at DESC (newest first); a plan without a student
    DECLINED decision (pending, accepted, customized, or agent-authored
    history without a student verdict) ends the streak.
    """
    ordered = sorted(
        plans,
        key=lambda p: (p.created_at is not None, p.created_at),
        reverse=True,
    )
    count = 0
    for plan in ordered:
        if plan.student_decision == _STUDENT_DECLINE_DECISION:
            count += 1
        else:
            break
    return count


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)
