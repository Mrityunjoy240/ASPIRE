# tests/test_case_lifecycle.py
# Case Lifecycle Service — remaining §10.2 mentor rows (03_SYSTEM_SPEC):
#   RESOLVED → CLOSED (Mentor closes; audit CASE_CLOSED, no domain event)
#   ESCALATION_REQUIRED → ESCALATION_REQUIRED (Mentor escalates to HOD/CT;
#   audit CASE_ESCALATED, no domain event — 07 §4, 02 §2.2)

import uuid
from datetime import UTC, datetime

import pytest

from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase
from app.services.case_lifecycle_service import (
    ESCALATION_TARGETS,
    CaseLifecycleError,
    close_case,
    escalate_case,
)


def make_case(status: InterventionCaseStatus) -> InterventionCase:
    now = datetime.now(UTC)
    return InterventionCase(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        mentor_id=uuid.uuid4(),
        status=status,
        urgency_band="URGENT",
        opened_at=now,
        resolved_at=now if status == InterventionCaseStatus.RESOLVED else None,
        created_at=now,
        updated_at=now,
    )


def make_session():
    from unittest.mock import AsyncMock, MagicMock

    session = AsyncMock()
    session.add = MagicMock()
    return session


# ---- RESOLVED → CLOSED ------------------------------------------------------


async def test_close_resolved_transitions_and_audits():
    case = make_case(InterventionCaseStatus.RESOLVED)
    resolved_at = case.resolved_at
    session = make_session()

    result = await close_case(session, case=case, actor_id=case.mentor_id)

    assert case.status == InterventionCaseStatus.CLOSED
    assert case.closed_at is not None
    assert result.case_status == "CLOSED"
    assert result.acted_at == case.closed_at
    assert case.resolved_at == resolved_at
    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert audit.action_type == "CASE_CLOSED"
    assert audit.entity_table == "intervention_cases"
    assert audit.entity_id == case.id
    assert audit.actor_id == case.mentor_id
    assert audit.previous_state["case_status"] == "RESOLVED"
    assert audit.new_state["case_status"] == "CLOSED"
    session.commit.assert_awaited_once()


async def test_close_emits_no_domain_event():
    """03 §8.2 has no case-closed event: close is audit-only (the mentor
    rejection precedent). The service takes no event bus at all."""
    import inspect

    params = inspect.signature(close_case).parameters
    assert "event_bus" not in params


@pytest.mark.parametrize(
    "status",
    [
        InterventionCaseStatus.OPEN,
        InterventionCaseStatus.IN_REVIEW,
        InterventionCaseStatus.PLAN_PROPOSED,
        InterventionCaseStatus.PENDING_APPROVAL,
        InterventionCaseStatus.ACTIVE,
        InterventionCaseStatus.MONITORING,
        InterventionCaseStatus.REPLAN_REQUIRED,
        InterventionCaseStatus.ESCALATION_REQUIRED,
        InterventionCaseStatus.CLOSED,
    ],
)
async def test_close_illegal_state_refused(status: InterventionCaseStatus):
    case = make_case(status)
    session = make_session()

    with pytest.raises(CaseLifecycleError) as exc_info:
        await close_case(session, case=case, actor_id=case.mentor_id)

    assert exc_info.value.code == "ILLEGAL_TRANSITION"
    assert case.status == status
    assert case.closed_at is None
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


async def test_close_already_closed_refused():
    case = make_case(InterventionCaseStatus.RESOLVED)
    session = make_session()
    await close_case(session, case=case, actor_id=case.mentor_id)

    session2 = make_session()
    with pytest.raises(CaseLifecycleError) as exc_info:
        await close_case(session2, case=case, actor_id=case.mentor_id)
    assert exc_info.value.code == "ILLEGAL_TRANSITION"
    session2.add.assert_not_called()


async def test_close_refreshes_updated_at():
    case = make_case(InterventionCaseStatus.RESOLVED)
    old_updated = case.updated_at
    session = make_session()
    await close_case(session, case=case, actor_id=case.mentor_id)
    assert case.updated_at >= old_updated


# ---- ESCALATION_REQUIRED → ESCALATION_REQUIRED ------------------------------


async def test_escalate_self_transition_keeps_status_and_audits():
    case = make_case(InterventionCaseStatus.ESCALATION_REQUIRED)
    session = make_session()

    result = await escalate_case(
        session, case=case, actor_id=case.mentor_id, target="HOD"
    )

    assert case.status == InterventionCaseStatus.ESCALATION_REQUIRED
    assert result.case_status == "ESCALATION_REQUIRED"
    assert result.escalated_to == "HOD"
    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert audit.action_type == "CASE_ESCALATED"
    assert audit.entity_table == "intervention_cases"
    assert audit.entity_id == case.id
    assert audit.actor_id == case.mentor_id
    assert audit.previous_state["case_status"] == "ESCALATION_REQUIRED"
    assert audit.new_state["case_status"] == "ESCALATION_REQUIRED"
    assert audit.new_state["escalated_to"] == "HOD"
    assert "escalation_note" not in audit.new_state
    session.commit.assert_awaited_once()


async def test_escalate_refreshes_updated_at():
    case = make_case(InterventionCaseStatus.ESCALATION_REQUIRED)
    old_updated = case.updated_at
    session = make_session()
    await escalate_case(session, case=case, actor_id=case.mentor_id, target="CT")
    assert case.updated_at >= old_updated


async def test_escalate_note_recorded_on_audit_row():
    case = make_case(InterventionCaseStatus.ESCALATION_REQUIRED)
    session = make_session()
    await escalate_case(
        session,
        case=case,
        actor_id=case.mentor_id,
        target="HOD",
        note="Student not engaging with AI guidance",
    )
    audit = session.add.call_args[0][0]
    assert audit.new_state["escalation_note"] == (
        "Student not engaging with AI guidance"
    )


@pytest.mark.parametrize("target", sorted(ESCALATION_TARGETS))
async def test_escalate_allowed_targets(target: str):
    case = make_case(InterventionCaseStatus.ESCALATION_REQUIRED)
    session = make_session()
    result = await escalate_case(
        session, case=case, actor_id=case.mentor_id, target=target
    )
    assert result.escalated_to == target


@pytest.mark.parametrize(
    "status",
    [
        InterventionCaseStatus.OPEN,
        InterventionCaseStatus.IN_REVIEW,
        InterventionCaseStatus.PLAN_PROPOSED,
        InterventionCaseStatus.PENDING_APPROVAL,
        InterventionCaseStatus.ACTIVE,
        InterventionCaseStatus.MONITORING,
        InterventionCaseStatus.REPLAN_REQUIRED,
        InterventionCaseStatus.RESOLVED,
        InterventionCaseStatus.CLOSED,
    ],
)
async def test_escalate_illegal_state_refused(status: InterventionCaseStatus):
    case = make_case(status)
    session = make_session()

    with pytest.raises(CaseLifecycleError) as exc_info:
        await escalate_case(
            session, case=case, actor_id=case.mentor_id, target="HOD"
        )

    assert exc_info.value.code == "ILLEGAL_TRANSITION"
    assert case.status == status
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.parametrize("target", ["SUPPORT_SERVICES", "ADMIN", "", "hod"])
async def test_escalate_invalid_target_refused(target: str):
    case = make_case(InterventionCaseStatus.ESCALATION_REQUIRED)
    session = make_session()

    with pytest.raises(CaseLifecycleError) as exc_info:
        await escalate_case(
            session, case=case, actor_id=case.mentor_id, target=target
        )

    assert exc_info.value.code == "INVALID_TARGET"
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


async def test_escalate_emits_no_domain_event():
    import inspect

    params = inspect.signature(escalate_case).parameters
    assert "event_bus" not in params
