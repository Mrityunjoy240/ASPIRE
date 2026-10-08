# tests/test_case_service.py
# Case Approval Service — state machine (03_SYSTEM_SPEC §10.2), audit row,
# commit-before-emit ordering, INTERVENTION_PLAN_APPROVED contract (ADR-002).

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.events import DomainEvent, EventBus
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.audit import AuditLog
from app.services.case_service import (
    EVENT_INTERVENTION_PLAN_APPROVED,
    CaseApprovalError,
    approve_plan,
)


def make_case(status: InterventionCaseStatus, mentor_id: uuid.UUID) -> InterventionCase:
    now = datetime.now(timezone.utc)
    return InterventionCase(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        mentor_id=mentor_id,
        status=status,
        urgency_band="URGENT",
        opened_at=now,
        created_at=now,
        updated_at=now,
    )


def make_plan(case: InterventionCase) -> InterventionPlan:
    now = datetime.now(timezone.utc)
    return InterventionPlan(
        id=uuid.uuid4(),
        case_id=case.id,
        created_by="SYSTEM_AGENT",
        status="ACCEPTED",
        plan_actions=[{"type": "MENTOR_CHECKIN"}],
        reason_codes=["ATTENDANCE_RISK"],
        evidence={},
        created_at=now,
        updated_at=now,
    )


def make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


async def run_approval(
    decision: str,
    case_status: InterventionCaseStatus = InterventionCaseStatus.PENDING_APPROVAL,
    event_bus: EventBus | None = None,
):
    mentor_id = uuid.uuid4()
    case = make_case(case_status, mentor_id)
    plan = make_plan(case)
    session = make_session()
    committed_before_emit: list[bool] = []

    if event_bus is None:
        event_bus = EventBus()

    async def probe(event: DomainEvent):
        committed_before_emit.append(session.commit.called)

    event_bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, probe)

    result = await approve_plan(
        session,
        case=case,
        plan=plan,
        decision=decision,
        mentor_notes="looks good",
        actor_id=mentor_id,
        event_bus=event_bus,
    )
    return result, case, plan, session, committed_before_emit, event_bus


async def test_approve_transitions_case_to_active_and_emits():
    result, case, plan, session, committed_before_emit, _ = await run_approval("APPROVED")

    assert case.status == InterventionCaseStatus.ACTIVE
    assert plan.mentor_decision == "APPROVED"
    assert plan.mentor_notes == "looks good"
    assert plan.mentor_acted_at is not None
    assert plan.status == "ACCEPTED"  # unchanged; no APPROVED plan status exists (05 §9)
    assert result.case_status == "ACTIVE"
    assert result.decision == "APPROVED"

    # commit strictly before emit
    assert committed_before_emit == [True]
    session.commit.assert_awaited()


async def test_edited_sets_customized_and_active():
    result, case, plan, session, _, _ = await run_approval("EDITED")
    assert case.status == InterventionCaseStatus.ACTIVE
    assert plan.status == "CUSTOMIZED"
    assert plan.mentor_decision == "EDITED"
    assert result.case_status == "ACTIVE"


async def test_reject_sets_replan_without_event():
    events: list[DomainEvent] = []

    async def recorder(event: DomainEvent):
        events.append(event)

    bus = EventBus()
    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    result, case, plan, session, _, _ = await run_approval("REJECTED", event_bus=bus)

    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert plan.status == "DECLINED"
    assert plan.mentor_decision == "REJECTED"
    assert result.case_status == "REPLAN_REQUIRED"
    assert events == []  # rejection emits no APPROVED event (ADR-002)
    session.commit.assert_awaited()


async def test_audit_row_written_for_every_decision():
    for decision in ("APPROVED", "EDITED", "REJECTED"):
        _, _, _, session, _, _ = await run_approval(decision)
        session.add.assert_called_once()
        audit = session.add.call_args[0][0]
        assert isinstance(audit, AuditLog)
        assert audit.actor_type == "USER"
        assert audit.source_system == "MENTOR_WEB"
        assert audit.entity_table == "intervention_plans"
        expected = "PLAN_REJECTED_BY_MENTOR" if decision == "REJECTED" else "PLAN_APPROVED_BY_MENTOR"
        assert audit.action_type == expected
        assert audit.previous_state["case_status"] == "PENDING_APPROVAL"
        assert audit.new_state["mentor_decision"] == decision
        # no PII keys (07 §4: reference by UUID only)
        for key in (*audit.previous_state.keys(), *audit.new_state.keys()):
            assert key not in ("email", "full_name", "name", "roll_number")


async def test_illegal_transition_refused():
    with pytest.raises(CaseApprovalError) as exc:
        await run_approval("APPROVED", case_status=InterventionCaseStatus.ACTIVE)
    assert exc.value.code == "ILLEGAL_TRANSITION"


async def test_illegal_transition_does_not_commit_or_emit():
    events = []

    async def recorder(event: DomainEvent):
        events.append(event)

    bus = EventBus()
    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    with pytest.raises(CaseApprovalError):
        await run_approval("APPROVED", case_status=InterventionCaseStatus.MONITORING, event_bus=bus)

    assert events == []


async def test_invalid_decision_refused():
    with pytest.raises(CaseApprovalError) as exc:
        await run_approval("MAYBE")
    assert exc.value.code == "INVALID_DECISION"


async def test_emitted_event_matches_minimal_contract():
    received: list[DomainEvent] = []

    async def recorder(event: DomainEvent):
        received.append(event)

    bus = EventBus()
    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    _, case, plan, _, _, _ = await run_approval("APPROVED", event_bus=bus)

    assert len(received) == 1
    event = received[0]
    data = event.to_dict()
    assert set(data.keys()) == {
        "event_id", "event_type", "student_id", "source_id",
        "occurred_at", "data_version", "payload",
    }
    assert event.event_type == "INTERVENTION_PLAN_APPROVED"
    assert event.student_id == case.student_id
    assert event.source_id == plan.id
    assert event.payload == {
        "case_id": str(case.id),
        "plan_id": str(plan.id),
        "mentor_id": str(event.payload["mentor_id"]),
        "decision": "APPROVED",
        "previous_status": "PENDING_APPROVAL",
        "new_status": "ACTIVE",
    }
