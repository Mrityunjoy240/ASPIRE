# tests/test_student_action_service.py
# Student Action Service — state machine (03_SYSTEM_SPEC §10.2 student
# acceptance rows), audit row (07 §4), commit-before-emit ordering and the
# PLAN_ACCEPTED contract (03 §8.1/§8.2).

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.events import DomainEvent, EventBus
from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.intervention import InterventionCase, InterventionPlan
from app.services.student_action_service import (
    EVENT_PLAN_ACCEPTED,
    StudentActionError,
    decide_plan,
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
        created_at=now,
        updated_at=now,
    )


def make_plan(
    case: InterventionCase,
    *,
    status: str = "PROPOSED",
    student_decision: str | None = None,
    created_days_ago: int = 0,
) -> InterventionPlan:
    now = datetime.now(UTC)
    return InterventionPlan(
        id=uuid.uuid4(),
        case_id=case.id,
        created_by="SYSTEM_AGENT",
        status=status,
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
        reason_codes=["LOW_ATTENDANCE"],
        evidence={},
        student_decision=student_decision,
        created_at=now,
        updated_at=now,
    )


def make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


async def run_decision(
    decision: str,
    *,
    case_status: InterventionCaseStatus = InterventionCaseStatus.PLAN_PROPOSED,
    plans: list[InterventionPlan] | None = None,
    plan_actions: list[dict] | None = None,
    event_bus: EventBus | None = None,
    actor_id: uuid.UUID | None = None,
):
    case = make_case(case_status)
    if plans is None:
        plans = [make_plan(case)]
    session = make_session()
    if event_bus is None:
        event_bus = EventBus()

    result = await decide_plan(
        session,
        case=case,
        plans=plans,
        decision=decision,
        plan_actions=plan_actions,
        actor_id=actor_id or uuid.uuid4(),
        event_bus=event_bus,
    )
    return result, case, plans, session, event_bus


async def test_accept_transitions_to_pending_approval_and_emits():
    received: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    result, case, plans, session, _ = await run_decision(
        "ACCEPTED", event_bus=bus
    )

    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plans[0].status == "ACCEPTED"
    assert plans[0].student_decision == "ACCEPTED"
    assert plans[0].decided_at is not None
    assert plans[0].plan_actions == [{"type": "ATTEND_CLASS", "subject": "DBMS"}]
    assert result.case_status == "PENDING_APPROVAL"
    assert result.student_decision == "ACCEPTED"
    assert result.plan_id == plans[0].id

    # commit strictly before emit
    session.commit.assert_awaited()
    assert len(received) == 1


async def test_customized_rewrites_actions_and_emits():
    received: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    edited = [{"type": "STUDY_BLOCK", "topic": "DBMS Unit 3", "duration_min": 45}]
    result, case, plans, session, _ = await run_decision(
        "CUSTOMIZED", plan_actions=edited, event_bus=bus
    )

    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plans[0].status == "CUSTOMIZED"
    assert plans[0].student_decision == "CUSTOMIZED"
    assert plans[0].plan_actions == edited  # student's adjusted actions persisted
    assert result.student_decision == "CUSTOMIZED"
    # catalog has no PLAN_CUSTOMIZED event: acceptance emits PLAN_ACCEPTED (03 §8.2)
    assert [e.event_type for e in received] == [EVENT_PLAN_ACCEPTED]
    assert received[0].payload["decision"] == "CUSTOMIZED"


async def test_customized_without_actions_refused():
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    plans = [make_plan(case)]
    session = make_session()
    bus = EventBus()
    events: list[DomainEvent] = []

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=plans, decision="CUSTOMIZED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert exc.value.code == "INVALID_REQUEST"
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED
    assert plans[0].student_decision is None
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


async def test_accept_with_actions_refused():
    """A plain acceptance must not smuggle in edits (no silent default)."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    plans = [make_plan(case)]
    session = make_session()

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=plans, decision="ACCEPTED",
            plan_actions=[{"type": "STUDY_BLOCK"}],
            actor_id=uuid.uuid4(), event_bus=EventBus(),
        )
    assert exc.value.code == "INVALID_REQUEST"
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


async def test_illegal_transition_refused():
    case = make_case(InterventionCaseStatus.ACTIVE)
    plans = [make_plan(case)]
    session = make_session()

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=plans, decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=EventBus(),
        )
    assert exc.value.code == "ILLEGAL_TRANSITION"
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


async def test_illegal_transition_does_not_emit():
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    case = make_case(InterventionCaseStatus.PENDING_APPROVAL)
    plans = [make_plan(case)]
    session = make_session()

    with pytest.raises(StudentActionError):
        await decide_plan(
            session, case=case, plans=plans, decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert events == []


@pytest.mark.parametrize("decision", ["DECLINED", "MAYBE"])
async def test_invalid_decision_refused(decision: str):
    """Decline is a deferred slice: it is refused as an unknown decision,
    never silently honored by this endpoint."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    plans = [make_plan(case)]
    session = make_session()

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=plans, decision=decision,
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=EventBus(),
        )
    assert exc.value.code == "INVALID_DECISION"
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


async def test_no_plans_refused():
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=[], decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert exc.value.code == "NO_PLAN"
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


@pytest.mark.parametrize("dead_status", ["DECLINED", "SUPERSEDED"])
async def test_dead_plan_never_selected(dead_status: str):
    """F-05 mirror: dead plan history never becomes the basis of a student
    acceptance — the case stays PLAN_PROPOSED with no side effects."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    dead = make_plan(case, status=dead_status, created_days_ago=9)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=[dead], decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert exc.value.code == "NO_PLAN"
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED
    assert dead.status == dead_status
    assert dead.student_decision is None
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


async def test_decided_plan_history_not_reselected():
    """A plan already decided by the student is history, never re-decided."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    prior = make_plan(
        case, status="DECLINED", student_decision="DECLINED", created_days_ago=7
    )
    session = make_session()

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=[prior], decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=EventBus(),
        )
    assert exc.value.code == "NO_PLAN"
    assert prior.student_decision == "DECLINED"  # untouched


async def test_plan_history_selects_proposed():
    """Replan history (declined + superseded) plus the current PROPOSED plan →
    the proposed plan is decided; history untouched."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    old_declined = make_plan(
        case, status="DECLINED", student_decision="DECLINED", created_days_ago=10
    )
    old_superseded = make_plan(case, status="SUPERSEDED", created_days_ago=5)
    current = make_plan(case, status="PROPOSED", created_days_ago=1)
    session = make_session()

    result = await decide_plan(
        session, case=case, plans=[old_declined, old_superseded, current],
        decision="ACCEPTED", plan_actions=None, actor_id=uuid.uuid4(),
        event_bus=EventBus(),
    )
    assert result.plan_id == current.id
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert current.student_decision == "ACCEPTED"
    assert old_declined.student_decision == "DECLINED"  # history untouched
    assert old_declined.status == "DECLINED"
    assert old_superseded.student_decision is None
    assert old_superseded.status == "SUPERSEDED"
    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert audit.entity_id == current.id  # audit names the decided plan


async def test_ambiguous_two_proposed_plans_refused():
    """Ambiguous data: two plans both awaiting the student verdict → §10.2
    defines a single transition for a single plan, so refuse instead of
    guessing. No commit, no audit, no event."""
    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    plan_a = make_plan(case, created_days_ago=2)
    plan_b = make_plan(case, created_days_ago=1)
    session = make_session()
    events: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        events.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=[plan_a, plan_b], decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert exc.value.code == "AMBIGUOUS_PLAN"
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED
    assert plan_a.student_decision is None and plan_b.student_decision is None
    session.commit.assert_not_awaited()
    session.add.assert_not_called()
    assert events == []


async def test_state_guard_outranks_plan_selection():
    """State guard (§10.2) outranks plan selection: a non-PLAN_PROPOSED case
    with an empty plan list still fails ILLEGAL_TRANSITION, not NO_PLAN."""
    case = make_case(InterventionCaseStatus.MONITORING)
    session = make_session()

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=[], decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=EventBus(),
        )
    assert exc.value.code == "ILLEGAL_TRANSITION"


async def test_audit_row_contract():
    actor = uuid.uuid4()
    _, case, plans, session, _ = await run_decision("ACCEPTED", actor_id=actor)

    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert isinstance(audit, AuditLog)
    assert audit.actor_id == actor
    assert audit.actor_type == "USER"
    assert audit.action_type == "PLAN_ACCEPTED"  # 07 §4 mandatory audit event
    assert audit.entity_table == "intervention_plans"
    assert audit.entity_id == plans[0].id
    assert audit.source_system == "STUDENT_APP"
    assert audit.previous_state["case_status"] == "PLAN_PROPOSED"
    assert audit.previous_state["plan_status"] == "PROPOSED"
    assert audit.new_state["case_status"] == "PENDING_APPROVAL"
    assert audit.new_state["student_decision"] == "ACCEPTED"
    # no PII keys (07 §4: reference by UUID only)
    for key in (*audit.previous_state.keys(), *audit.new_state.keys()):
        assert key not in ("email", "full_name", "name", "roll_number")


async def test_emitted_event_matches_minimal_contract():
    received: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    result, case, plans, session, _ = await run_decision(
        "ACCEPTED", event_bus=bus
    )

    assert len(received) == 1
    event = received[0]
    data = event.to_dict()
    assert set(data.keys()) == {
        "event_id", "event_type", "student_id", "source_id",
        "occurred_at", "data_version", "payload",
    }
    assert event.event_type == "PLAN_ACCEPTED"
    assert event.student_id == case.student_id
    assert event.source_id == plans[0].id
    assert event.payload == {
        "case_id": str(case.id),
        "plan_id": str(plans[0].id),
        "decision": "ACCEPTED",
        "previous_status": "PLAN_PROPOSED",
        "new_status": "PENDING_APPROVAL",
    }


async def test_idempotent_second_decision_refused():
    """Sequential re-submission (the FOR UPDATE-serialized outcome of a
    concurrent double-POST): exactly one transition, one audit row, one event;
    the second attempt receives ILLEGAL_TRANSITION."""
    received: list[DomainEvent] = []
    bus = EventBus()

    async def recorder(event: DomainEvent):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)

    case = make_case(InterventionCaseStatus.PLAN_PROPOSED)
    plans = [make_plan(case)]
    session = make_session()

    await decide_plan(
        session, case=case, plans=plans, decision="ACCEPTED",
        plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
    )

    with pytest.raises(StudentActionError) as exc:
        await decide_plan(
            session, case=case, plans=plans, decision="ACCEPTED",
            plan_actions=None, actor_id=uuid.uuid4(), event_bus=bus,
        )
    assert exc.value.code == "ILLEGAL_TRANSITION"
    assert len(received) == 1
    assert session.add.call_count == 1  # single audit row
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plans[0].student_decision == "ACCEPTED"
