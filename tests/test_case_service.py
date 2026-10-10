# tests/test_case_service.py
# Case Approval Service — state machine (03_SYSTEM_SPEC §10.2), audit row,
# commit-before-emit ordering, INTERVENTION_PLAN_APPROVED contract (ADR-002).

import uuid
from datetime import datetime, timedelta, timezone
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
        evidence=[],
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
    plans: list[InterventionPlan] | None = None,
):
    mentor_id = uuid.uuid4()
    case = make_case(case_status, mentor_id)
    if plans is None:
        plans = [make_plan(case)]
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
        plans=plans,
        decision=decision,
        mentor_notes="looks good",
        actor_id=mentor_id,
        event_bus=event_bus,
    )
    return result, case, plans, session, committed_before_emit, event_bus


def make_plan_with(
    case: InterventionCase,
    *,
    status: str = "ACCEPTED",
    mentor_decision: str | None = None,
    created_days_ago: int = 0,
) -> InterventionPlan:
    now = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
    return InterventionPlan(
        id=uuid.uuid4(),
        case_id=case.id,
        created_by="SYSTEM_AGENT",
        status=status,
        plan_actions=[{"type": "MENTOR_CHECKIN"}],
        reason_codes=["ATTENDANCE_RISK"],
        evidence=[],
        mentor_decision=mentor_decision,
        created_at=now,
        updated_at=now,
    )


async def test_approve_transitions_case_to_active_and_emits():
    result, case, plans, session, committed_before_emit, _ = await run_approval("APPROVED")

    assert case.status == InterventionCaseStatus.ACTIVE
    assert plans[0].mentor_decision == "APPROVED"
    assert plans[0].mentor_notes == "looks good"
    assert plans[0].mentor_acted_at is not None
    assert plans[0].status == "ACCEPTED"  # unchanged; no APPROVED plan status exists (05 §9)
    assert result.case_status == "ACTIVE"
    assert result.decision == "APPROVED"

    # commit strictly before emit
    assert committed_before_emit == [True]
    session.commit.assert_awaited()


async def test_edited_sets_customized_and_active():
    result, case, plans, session, _, _ = await run_approval("EDITED")
    assert case.status == InterventionCaseStatus.ACTIVE
    assert plans[0].status == "CUSTOMIZED"
    assert plans[0].mentor_decision == "EDITED"
    assert result.case_status == "ACTIVE"


async def test_reject_sets_replan_without_event():
    events: list[DomainEvent] = []

    async def recorder(event: DomainEvent):
        events.append(event)

    bus = EventBus()
    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    result, case, plans, session, _, _ = await run_approval("REJECTED", event_bus=bus)

    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert plans[0].status == "DECLINED"
    assert plans[0].mentor_decision == "REJECTED"
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

    _, case, plans, _, _, _ = await run_approval("APPROVED", event_bus=bus)

    assert len(received) == 1
    event = received[0]
    data = event.to_dict()
    assert set(data.keys()) == {
        "event_id", "event_type", "student_id", "source_id",
        "occurred_at", "data_version", "payload",
    }
    assert event.event_type == "INTERVENTION_PLAN_APPROVED"
    assert event.student_id == case.student_id
    assert event.source_id == plans[0].id
    assert event.payload == {
        "case_id": str(case.id),
        "plan_id": str(plans[0].id),
        "mentor_id": str(event.payload["mentor_id"]),
        "decision": "APPROVED",
        "previous_status": "PENDING_APPROVAL",
        "new_status": "ACTIVE",
    }


# ---- F-01: authoritative plan selection across plan history ----
# Regression coverage for the MultipleResultsFound failure proven at
# cb300da (scalar_one_or_none on a query that returns 1..N plans once
# replan cycles append history). The service must select exactly the plan
# awaiting the mentor verdict (ADR-002 §5) or refuse ambiguity.

async def test_f01_zero_plans_refused_no_commit_no_event():
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    with pytest.raises(CaseApprovalError) as exc:
        await approve_plan(
            session, case=case, plans=[], decision="APPROVED",
            mentor_notes=None, actor_id=mentor_id, event_bus=bus,
        )
    assert exc.value.code == "NO_PLAN"
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


async def test_f01_one_pending_plan_approves():
    """Baseline: exactly one awaiting plan → normal approval."""
    result, case, plans, session, _, _ = await run_approval("APPROVED")
    assert len(plans) == 1
    assert plans[0].mentor_decision == "APPROVED"
    assert result.case_status == "ACTIVE"


async def test_f01_two_historical_plans_selects_pending():
    """Plan history (repro of the cb300da 500): declined + superseded history
    plus the current awaiting plan → the current plan is decided, history
    untouched. Old implementation raised MultipleResultsFound."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    old_declined = make_plan_with(case, status="DECLINED", created_days_ago=10)
    old_declined.mentor_decision = "REJECTED"
    old_superseded = make_plan_with(case, status="SUPERSEDED", created_days_ago=5)
    current = make_plan_with(case, status="ACCEPTED", created_days_ago=1)
    session = make_session()

    result = await approve_plan(
        session, case=case, plans=[old_declined, old_superseded, current],
        decision="APPROVED", mentor_notes=None, actor_id=mentor_id,
        event_bus=EventBus(),
    )

    assert result.case_status == "ACTIVE"
    assert current.mentor_decision == "APPROVED"
    # history is never re-decided
    assert old_declined.mentor_decision == "REJECTED"
    assert old_declined.status == "DECLINED"
    assert old_superseded.mentor_decision is None
    assert old_superseded.status == "SUPERSEDED"
    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert audit.entity_id == current.id  # audit names the decided plan


async def test_f01_prior_decided_plan_not_selected():
    """A prior mentor-decided plan (even with status ACCEPTED) is history:
    the still-undecided plan is the authoritative target."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    prior_decided = make_plan_with(
        case, status="ACCEPTED", mentor_decision="APPROVED", created_days_ago=7
    )
    current = make_plan_with(case, status="ACCEPTED", created_days_ago=1)
    session = make_session()

    await approve_plan(
        session, case=case, plans=[prior_decided, current],
        decision="EDITED", mentor_notes=None, actor_id=mentor_id,
        event_bus=EventBus(),
    )

    assert current.mentor_decision == "EDITED"
    assert prior_decided.mentor_decision == "APPROVED"  # untouched


async def test_f01_proposed_plan_is_not_approvable():
    """PROPOSED plans were never student-accepted (state machine): NO_PLAN."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    proposed = make_plan_with(case, status="PROPOSED")
    session = make_session()

    with pytest.raises(CaseApprovalError) as exc:
        await approve_plan(
            session, case=case, plans=[proposed], decision="APPROVED",
            mentor_notes=None, actor_id=mentor_id, event_bus=EventBus(),
        )
    assert exc.value.code == "NO_PLAN"
    session.commit.assert_not_awaited()


async def test_f01_ambiguous_two_pending_plans_refused():
    """Ambiguous data: two plans both awaiting the verdict → §10.2 defines a
    single transition for a single plan, so refuse (409) instead of guessing."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    plan_a = make_plan_with(case, status="ACCEPTED", created_days_ago=2)
    plan_b = make_plan_with(case, status="ACCEPTED", created_days_ago=1)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    with pytest.raises(CaseApprovalError) as exc:
        await approve_plan(
            session, case=case, plans=[plan_a, plan_b], decision="APPROVED",
            mentor_notes=None, actor_id=mentor_id, event_bus=bus,
        )
    assert exc.value.code == "AMBIGUOUS_PLAN"
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL  # unchanged
    assert plan_a.mentor_decision is None and plan_b.mentor_decision is None
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


async def test_f01_plan_state_validation_order_state_first():
    """State guard (§10.2) outranks plan selection: a non-PENDING case with a
    clean plan list still fails ILLEGAL_TRANSITION (409), not NO_PLAN."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.ACTIVE, mentor_id)
    current = make_plan_with(case, status="ACCEPTED")
    session = make_session()

    with pytest.raises(CaseApprovalError) as exc:
        await approve_plan(
            session, case=case, plans=[current], decision="APPROVED",
            mentor_notes=None, actor_id=mentor_id, event_bus=EventBus(),
        )
    assert exc.value.code == "ILLEGAL_TRANSITION"


# ---- F-05: dead plans never authorize an approval ----

@pytest.mark.parametrize("dead_status", ["DECLINED", "SUPERSEDED"])
async def test_f05_dead_plan_cannot_authorize_approval(dead_status: str):
    """F-05: a PENDING_APPROVAL case whose only plan is dead history
    (DECLINED/SUPERSEDED, possible after future replan flows) is refused —
    a dead plan never becomes the basis of an ACTIVE case."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    dead = make_plan_with(case, status=dead_status, created_days_ago=9)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)

    with pytest.raises(CaseApprovalError) as exc:
        await approve_plan(
            session, case=case, plans=[dead], decision="APPROVED",
            mentor_notes=None, actor_id=mentor_id, event_bus=bus,
        )
    assert exc.value.code == "NO_PLAN"
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert dead.status == dead_status
    assert dead.mentor_decision is None
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


# ---- F-02: rejection publishes nothing at all ----

async def test_f02_rejection_never_calls_bus_publish():
    """Stronger than 'no APPROVED event': spying on EventBus.publish proves a
    REJECTED decision publishes zero domain events of any type — no
    INTERVENTION_PLAN_REJECTED is invented (ADR-002 §2; catalog is canonical)."""
    mentor_id = uuid.uuid4()
    case = make_case(InterventionCaseStatus.PENDING_APPROVAL, mentor_id)
    plan = make_plan(case)
    session = make_session()
    bus = EventBus()

    published: list[DomainEvent] = []
    original_publish = bus.publish

    async def spy(event: DomainEvent):
        published.append(event)
        await original_publish(event)

    bus.publish = spy  # type: ignore[method-assign]

    await approve_plan(
        session, case=case, plans=[plan], decision="REJECTED",
        mentor_notes="no", actor_id=mentor_id, event_bus=bus,
    )

    assert published == []  # nothing published, any event_type
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    # audit still written (rejection is audit-only, ADR-002 §2)
    session.add.assert_called_once()
    assert session.add.call_args[0][0].action_type == "PLAN_REJECTED_BY_MENTOR"
