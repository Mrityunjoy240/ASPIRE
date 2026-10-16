# tests/test_follow_up.py
# Follow-up domain service + RULE_ENGINE consumer unit tests (ADR-004) —
# no database. Real-PostgreSQL persistence/concurrency lives in
# tests/test_follow_up_pg.py.

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.follow_up_service as fu
from app.core.events import DomainEvent, EventBus
from app.models.enums import (
    FollowUpStatus,
    FollowUpTriggerType,
    InterventionCaseStatus,
)
from app.models.intervention import InterventionCase, InterventionFollowUp, InterventionPlan
from app.services.follow_up_service import (
    EVENT_ASSESSMENT_GRADED,
    EVENT_ATTENDANCE_UPDATED,
    EVENT_MENTOR_FOLLOWUP_DUE,
    EVENT_PATH_TRIGGER_TYPES,
    EVENT_QUIZ_COMPLETED,
    EVENT_TASK_OVERDUE,
    FollowUpConsumer,
    FollowUpError,
    check_improvement,
    handle_followup_due_event,
    handle_policy_event,
    schedule_followup,
)

# ---- helpers ----------------------------------------------------------------


class FakeResult:
    """Minimal stand-in for a SQLAlchemy Result in service unit tests."""

    def __init__(self, *, scalar=None, first=None, one=None, rows=None, scalars_list=None):
        self._scalar = scalar
        self._first = first
        self._one = one
        self._rows = rows if rows is not None else []
        self._scalars_list = scalars_list if scalars_list is not None else []

    def scalar_one_or_none(self):
        return self._scalar

    def first(self):
        return self._first

    def one(self):
        return self._one

    def scalars(self):
        return FakeScalars(self._scalars_list)

    def __iter__(self):
        return iter(self._rows)


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def __iter__(self):
        return iter(self._items)


def make_session(results: list | None = None):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=results or [])
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def make_case(status: InterventionCaseStatus = InterventionCaseStatus.ACTIVE) -> InterventionCase:
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


def make_follow_up(
    *,
    case_id: uuid.UUID,
    status: FollowUpStatus = FollowUpStatus.SCHEDULED,
    trigger_type: str = FollowUpTriggerType.CUSTOM_DATE.value,
    due_at: datetime | None = None,
    window_end: datetime | None = None,
) -> InterventionFollowUp:
    now = datetime.now(UTC)
    return InterventionFollowUp(
        id=uuid.uuid4(),
        case_id=case_id,
        trigger_type=trigger_type,
        status=status.value,
        due_at=due_at,
        evaluation_window_ends_at=window_end,
        created_by=str(uuid.uuid4()),
        created_at=now,
    )


def followup_event(
    follow_up: InterventionFollowUp, *, phase: str = "DUE", event_type: str | None = None
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type or EVENT_MENTOR_FOLLOWUP_DUE,
        student_id=uuid.uuid4(),
        source_id=follow_up.id,
        payload={
            "case_id": str(follow_up.case_id),
            "follow_up_id": str(follow_up.id),
            "trigger_type": follow_up.trigger_type,
            "phase": phase,
        },
    )


@pytest.fixture
def fixed_rules(monkeypatch):
    """Pin the shared rule readers (ADR-004 §2.5/§2.6 defaults)."""

    async def threshold(_session, _student_id):
        return Decimal("75.00")

    async def window(_session, _student_id):
        return 7

    monkeypatch.setattr(fu, "get_attendance_threshold", threshold)
    monkeypatch.setattr(fu, "get_followup_evaluation_window_days", window)


def make_plan(
    case,
    *,
    decision: str | None = "APPROVED",
    actions=None,
    reasons=None,
) -> InterventionPlan:
    """Approved intervention plan fixture (ADR-004 §2.5 predicate input)."""
    now = datetime.now(UTC)
    return InterventionPlan(
        id=uuid.uuid4(),
        case_id=case.id,
        created_by="SYSTEM_AGENT",
        status="ACCEPTED",
        plan_actions=actions if actions is not None else [{"type": "ATTEND_CLASS"}],
        reason_codes=reasons if reasons is not None else ["LOW_ATTENDANCE"],
        evidence=[],
        mentor_decision=decision,
        created_at=now,
        updated_at=now,
    )


def _attendance_rows(attended, conducted, band="SAFE"):
    """Single rows-query result for check_improvement (F2: one query)."""
    if attended is None and conducted is None:
        return FakeResult(rows=[])
    return FakeResult(rows=[(attended, conducted, band)])


# ---- drift guards (catalog / ADR constants) --------------------------------


def test_mentor_followup_due_matches_supervisor_catalog():
    from app.agents.supervisor import EVENT_MENTOR_FOLLOWUP_DUE as supervisor_name

    assert EVENT_MENTOR_FOLLOWUP_DUE == supervisor_name == "MENTOR_FOLLOWUP_DUE"


def test_event_path_keys_are_canonical_catalog_names():
    """03 §8.2 producer names — the consumer may only react to catalog events."""
    assert set(EVENT_PATH_TRIGGER_TYPES) == {
        "ATTENDANCE_UPDATED",
        "ASSESSMENT_GRADED",
        "QUIZ_COMPLETED",
        "TASK_OVERDUE",
    }
    from app.services.scheduler import EVENT_TASK_OVERDUE as sched_overdue

    assert EVENT_TASK_OVERDUE == sched_overdue


def test_phase_constants_match_scheduler():
    from app.services.scheduler import PHASE_DUE as sched_due
    from app.services.scheduler import PHASE_EXPIRY as sched_expiry

    assert fu.PHASE_DUE == sched_due == "DUE"
    assert fu.PHASE_EXPIRY == sched_expiry == "EXPIRY"


def test_trigger_policy_mapping_matches_06_section_4():
    """06 §4 / 02 §2.1 Step 6 policies."""
    assert EVENT_PATH_TRIGGER_TYPES[EVENT_ATTENDANCE_UPDATED] == (
        FollowUpTriggerType.ATTENDANCE_INTERVENTION.value,
    )
    assert EVENT_PATH_TRIGGER_TYPES[EVENT_ASSESSMENT_GRADED] == (
        FollowUpTriggerType.STUDY_INTERVENTION.value,
    )
    assert EVENT_PATH_TRIGGER_TYPES[EVENT_QUIZ_COMPLETED] == (
        FollowUpTriggerType.STUDY_INTERVENTION.value,
    )
    assert EVENT_PATH_TRIGGER_TYPES[EVENT_TASK_OVERDUE] == (
        FollowUpTriggerType.ASSIGNMENT_INTERVENTION.value,
    )


# ---- schedule_followup ------------------------------------------------------


async def test_schedule_custom_date_happy_path():
    case = make_case()
    session = make_session()
    due = datetime.now(UTC) + timedelta(days=2)

    result = await schedule_followup(
        session,
        case=case,
        trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
        due_at=due,
        actor_id=case.mentor_id,
    )

    assert result.status == FollowUpStatus.SCHEDULED.value
    assert result.due_at == due
    assert result.case_id == case.id
    assert session.add.call_count == 2  # audit row + follow-up row
    audit = session.add.call_args_list[0][0][0]
    assert audit.action_type == "FOLLOW_UP_SCHEDULED"
    assert audit.entity_table == "intervention_follow_ups"
    assert audit.actor_id == case.mentor_id
    session.commit.assert_awaited_once()


async def test_schedule_event_driven_type_forbids_due_at():
    case = make_case()
    session = make_session()

    with pytest.raises(FollowUpError) as exc_info:
        await schedule_followup(
            session,
            case=case,
            trigger_type=FollowUpTriggerType.ATTENDANCE_INTERVENTION.value,
            due_at=datetime.now(UTC) + timedelta(days=1),
            actor_id=case.mentor_id,
        )
    assert exc_info.value.code == "INVALID_REQUEST"


async def test_schedule_invalid_trigger_type_refused():
    case = make_case()
    session = make_session()

    with pytest.raises(FollowUpError) as exc_info:
        await schedule_followup(
            session,
            case=case,
            trigger_type="TELEPATHY",
            due_at=None,
            actor_id=case.mentor_id,
        )
    assert exc_info.value.code == "INVALID_TRIGGER_TYPE"


@pytest.mark.parametrize(
    "status",
    [
        InterventionCaseStatus.OPEN,
        InterventionCaseStatus.PLAN_PROPOSED,
        InterventionCaseStatus.PENDING_APPROVAL,
        InterventionCaseStatus.MONITORING,
        InterventionCaseStatus.REPLAN_REQUIRED,
        InterventionCaseStatus.RESOLVED,
        InterventionCaseStatus.CLOSED,
    ],
)
async def test_schedule_requires_active_case(status):
    """ADR-004 §2.7: follow-ups are scheduled on ACTIVE cases only."""
    case = make_case(status)
    session = make_session()

    with pytest.raises(FollowUpError) as exc_info:
        await schedule_followup(
            session,
            case=case,
            trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
            due_at=datetime.now(UTC) + timedelta(days=1),
            actor_id=case.mentor_id,
        )
    assert exc_info.value.code == "ILLEGAL_TRANSITION"
    session.commit.assert_not_awaited()


async def test_schedule_custom_date_requires_due_at():
    case = make_case()
    session = make_session()

    with pytest.raises(FollowUpError) as exc_info:
        await schedule_followup(
            session,
            case=case,
            trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
            due_at=None,
            actor_id=case.mentor_id,
        )
    assert exc_info.value.code == "INVALID_REQUEST"


async def test_schedule_custom_date_rejects_past_due_at():
    case = make_case()
    session = make_session()

    with pytest.raises(FollowUpError) as exc_info:
        await schedule_followup(
            session,
            case=case,
            trigger_type=FollowUpTriggerType.CUSTOM_DATE.value,
            due_at=datetime.now(UTC) - timedelta(minutes=1),
            actor_id=case.mentor_id,
        )
    assert exc_info.value.code == "INVALID_REQUEST"


# ---- handle_followup_due_event: no-ops (dedup / stray dispatch) -------------


async def test_due_unknown_follow_up_is_noop():
    session = make_session([FakeResult(scalar=None)])
    event = DomainEvent(
        event_type=EVENT_MENTOR_FOLLOWUP_DUE,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={},
    )

    outcome = await handle_followup_due_event(session, event)

    assert outcome.action == "noop"
    session.commit.assert_not_awaited()


async def test_due_already_evaluated_is_noop():
    case = make_case()
    follow_up = make_follow_up(case_id=case.id, status=FollowUpStatus.EVALUATED)
    session = make_session([FakeResult(scalar=follow_up)])

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "noop"
    session.commit.assert_not_awaited()


async def test_due_future_custom_date_is_noop():
    """Stray early DUE dispatch for a custom date that has not arrived."""
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id,
        due_at=datetime.now(UTC) + timedelta(days=3),
    )
    session = make_session([FakeResult(scalar=follow_up)])

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "noop"
    session.commit.assert_not_awaited()


async def test_expiry_before_window_end_is_noop():
    """Fulfilled follow-up whose evaluation window has not ended yet."""
    case = make_case(status=InterventionCaseStatus.MONITORING)
    follow_up = make_follow_up(
        case_id=case.id,
        status=FollowUpStatus.FULFILLED,
        window_end=datetime.now(UTC) + timedelta(days=5),
    )
    session = make_session([FakeResult(scalar=follow_up)])

    outcome = await handle_followup_due_event(
        session, followup_event(follow_up, phase="EXPIRY")
    )

    assert outcome.action == "noop"
    session.commit.assert_not_awaited()


async def test_duplicate_due_dispatch_is_noop_after_fulfilment():
    """Lead option A: the FULFILLED row is the dedup identity — a duplicate
    DUE dispatch re-reads the committed status and (window pending) no-ops."""
    case = make_case(status=InterventionCaseStatus.MONITORING)
    follow_up = make_follow_up(
        case_id=case.id,
        status=FollowUpStatus.FULFILLED,
        window_end=datetime.now(UTC) + timedelta(days=6),
    )
    session = make_session([FakeResult(scalar=follow_up)])

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "noop"


# ---- DUE fulfilment ---------------------------------------------------------


def _due_session(
    case,
    follow_up,
    *,
    attended=None,
    conducted=None,
    band="SAFE",
    plans=None,
    task_statuses=None,
    stale=None,
):
    """Execute() side effects: lock-followup → lock-case → stale-sibling scan
    → attendance rows → plans [→ materialized task statuses when an approved
    plan exists]."""
    results = [
        FakeResult(scalar=follow_up),  # lock follow-up
        FakeResult(scalar=case),  # lock case
        FakeResult(scalars_list=stale or []),  # stale siblings (supersession)
        _attendance_rows(attended, conducted, band),  # derived-state rows
        FakeResult(scalars_list=plans or []),  # plans
    ]
    if any(
        p.mentor_decision in {"APPROVED", "EDITED"} for p in (plans or [])
    ):
        results.append(FakeResult(scalars_list=task_statuses or []))
    return make_session(results)


async def test_due_not_improved_fulfils_to_monitoring(fixed_rules):
    """No attendance data → improvement not verified (fail-closed,
    ADR-004 §2.5) → case stays MONITORING until the expiry re-check."""
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id, due_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    session = _due_session(case, follow_up)

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "fulfilled"
    assert outcome.case_status == InterventionCaseStatus.MONITORING.value
    assert case.status == InterventionCaseStatus.MONITORING
    assert follow_up.status == FollowUpStatus.FULFILLED.value
    assert follow_up.triggered_at is not None
    assert follow_up.evaluation_window_ends_at is not None
    assert follow_up.outcome is None
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["CASE_FOLLOWUP_DUE"]
    session.commit.assert_awaited_once()


async def test_due_improved_resolves_immediately(fixed_rules):
    """02 §2.1 Step 7: improvement verified at follow-up time →
    MONITORING then RESOLVED in the same consumer transaction."""
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id, due_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    approved = make_plan(case)
    session = _due_session(
        case,
        follow_up,
        attended=90,
        conducted=100,
        plans=[approved],
        task_statuses=["COMPLETED"],
    )

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "resolved"
    assert case.status == InterventionCaseStatus.RESOLVED
    assert case.resolved_at is not None
    assert follow_up.status == FollowUpStatus.EVALUATED.value
    assert follow_up.outcome == InterventionCaseStatus.RESOLVED.value
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["CASE_FOLLOWUP_DUE", "CASE_IMPROVEMENT_VERIFIED"]


async def test_due_case_moved_cancels_stale_scheduled(fixed_rules):
    """Branch (a) of the ADR-004 §2.1 consumption rule: the case left ACTIVE
    before the DUE dispatch landed (e.g. concurrent mentor action / a peer
    follow-up already drove the transition) → the stale SCHEDULED row is
    CANCELLED (audit FOLLOW_UP_SUPERSEDED) instead of lingering SCHEDULED
    behind an already-EMITTED occurrence. No case transition, no rollback —
    the cancellation commits."""
    case = make_case(status=InterventionCaseStatus.REPLAN_REQUIRED)
    follow_up = make_follow_up(
        case_id=case.id, due_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    session = make_session(
        [FakeResult(scalar=follow_up), FakeResult(scalar=case)]
    )

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "cancelled"
    assert outcome.case_status == InterventionCaseStatus.REPLAN_REQUIRED.value
    assert follow_up.status == FollowUpStatus.CANCELLED.value
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED  # untouched
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["FOLLOW_UP_SUPERSEDED"]
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


async def test_due_cancelled_follow_up_is_noop(fixed_rules):
    """A CANCELLED row is terminal — a duplicate/late DUE dispatch no-ops."""
    case = make_case(status=InterventionCaseStatus.MONITORING)
    follow_up = make_follow_up(
        case_id=case.id, status=FollowUpStatus.CANCELLED,
        due_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    session = make_session([FakeResult(scalar=follow_up)])

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "noop"
    session.commit.assert_not_awaited()


async def test_fulfilment_cancels_stale_siblings(fixed_rules):
    """Branch (b): one fulfilment per case cycle — competing SCHEDULED
    siblings are CANCELLED in the same transaction (audit order:
    FOLLOW_UP_SUPERSEDED … then CASE_FOLLOWUP_DUE)."""
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id, due_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    sibling = make_follow_up(
        case_id=case.id, trigger_type=FollowUpTriggerType.ATTENDANCE_INTERVENTION.value
    )
    session = _due_session(case, follow_up, stale=[sibling])

    outcome = await handle_followup_due_event(session, followup_event(follow_up))

    assert outcome.action == "fulfilled"
    assert follow_up.status == FollowUpStatus.FULFILLED.value
    assert sibling.status == FollowUpStatus.CANCELLED.value
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["FOLLOW_UP_SUPERSEDED", "CASE_FOLLOWUP_DUE"]
    session.commit.assert_awaited_once()


async def test_policy_event_same_case_second_sibling_noops(fixed_rules):
    """Event path scanning two SCHEDULED rows of one case: the first
    fulfils (and cancels the second in-transaction) — the loop sees the
    mutated sibling and appends noop; outcomes = [fulfilled, noop]."""
    case = make_case()
    first = make_follow_up(
        case_id=case.id,
        trigger_type=FollowUpTriggerType.ATTENDANCE_INTERVENTION.value,
    )
    second = make_follow_up(
        case_id=case.id,
        trigger_type=FollowUpTriggerType.ATTENDANCE_INTERVENTION.value,
    )
    session = make_session(
        [
            FakeResult(scalars_list=[first, second]),  # scan (both ACTIVE)
            FakeResult(scalar=case),  # lock case (_fulfil_due for first)
            FakeResult(scalars_list=[second]),  # stale sibling scan
            _attendance_rows(50, 100),
            FakeResult(scalars_list=[]),  # plans
        ]
    )
    event = DomainEvent(
        event_type=EVENT_ATTENDANCE_UPDATED,
        student_id=case.student_id,
        source_id=uuid.uuid4(),
        payload={},
    )

    outcomes = await handle_policy_event(session, event)

    assert [o.action for o in outcomes] == ["fulfilled", "noop"]
    assert first.status == FollowUpStatus.FULFILLED.value
    assert second.status == FollowUpStatus.CANCELLED.value


# ---- EXPIRY -----------------------------------------------------------------


def _expiry_session(
    case,
    follow_up,
    *,
    attended=None,
    conducted=None,
    band="SAFE",
    plans=None,
    task_statuses=None,
):
    results = [
        FakeResult(scalar=follow_up),
        FakeResult(scalar=case),
        _attendance_rows(attended, conducted, band),
        FakeResult(scalars_list=plans or []),
    ]
    if any(
        p.mentor_decision in {"APPROVED", "EDITED"} for p in (plans or [])
    ):
        results.append(FakeResult(scalars_list=task_statuses or []))
    return make_session(results)


async def test_expiry_not_improved_returns_to_replan(fixed_rules):
    """MONITORING → REPLAN_REQUIRED on window end with no improvement
    (03 §10.2; audit CASE_FOLLOWUP_EXPIRED)."""
    case = make_case(status=InterventionCaseStatus.MONITORING)
    follow_up = make_follow_up(
        case_id=case.id,
        status=FollowUpStatus.FULFILLED,
        window_end=datetime.now(UTC) - timedelta(minutes=1),
    )
    session = _expiry_session(case, follow_up)

    outcome = await handle_followup_due_event(
        session, followup_event(follow_up, phase="EXPIRY")
    )

    assert outcome.action == "replan"
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert follow_up.status == FollowUpStatus.EVALUATED.value
    assert follow_up.outcome == InterventionCaseStatus.REPLAN_REQUIRED.value
    assert follow_up.evaluated_at is not None
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["CASE_FOLLOWUP_EXPIRED"]
    session.commit.assert_awaited_once()


async def test_expiry_improved_resolves(fixed_rules):
    case = make_case(status=InterventionCaseStatus.MONITORING)
    follow_up = make_follow_up(
        case_id=case.id,
        status=FollowUpStatus.FULFILLED,
        window_end=datetime.now(UTC) - timedelta(minutes=1),
    )
    approved = make_plan(case)
    session = _expiry_session(
        case,
        follow_up,
        attended=80,
        conducted=100,
        plans=[approved],
        task_statuses=["COMPLETED"],
    )

    outcome = await handle_followup_due_event(
        session, followup_event(follow_up, phase="EXPIRY")
    )

    assert outcome.action == "resolved"
    assert case.status == InterventionCaseStatus.RESOLVED
    assert follow_up.outcome == InterventionCaseStatus.RESOLVED.value
    audit_actions = [c[0][0].action_type for c in session.add.call_args_list]
    assert audit_actions == ["CASE_IMPROVEMENT_VERIFIED"]


async def test_expiry_case_not_monitoring_is_noop(fixed_rules):
    case = make_case(status=InterventionCaseStatus.REPLAN_REQUIRED)
    follow_up = make_follow_up(
        case_id=case.id,
        status=FollowUpStatus.FULFILLED,
        window_end=datetime.now(UTC) - timedelta(minutes=1),
    )
    session = make_session([FakeResult(scalar=follow_up), FakeResult(scalar=case)])

    outcome = await handle_followup_due_event(
        session, followup_event(follow_up, phase="EXPIRY")
    )

    assert outcome.action == "noop"
    session.rollback.assert_awaited()


# ---- event-path fulfilment --------------------------------------------------


async def test_policy_event_unknown_type_returns_empty():
    session = make_session()
    event = DomainEvent(
        event_type="DATA_CONFLICT",
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={},
    )

    outcomes = await handle_policy_event(session, event)

    assert outcomes == []
    session.execute.assert_not_awaited()


async def test_attendance_updated_fulfils_attendance_follow_up(fixed_rules):
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id, trigger_type=FollowUpTriggerType.ATTENDANCE_INTERVENTION.value
    )
    session = make_session(
        [
            FakeResult(scalars_list=[follow_up]),  # scan (SCHEDULED + ACTIVE case)
            FakeResult(scalar=case),  # lock case (_fulfil_due)
            FakeResult(scalars_list=[]),  # stale siblings
            _attendance_rows(50, 100),  # below threshold
            FakeResult(scalars_list=[]),  # plans
        ]
    )
    event = DomainEvent(
        event_type=EVENT_ATTENDANCE_UPDATED,
        student_id=case.student_id,
        source_id=uuid.uuid4(),
        payload={},
    )

    outcomes = await handle_policy_event(session, event)

    assert len(outcomes) == 1
    assert outcomes[0].action == "fulfilled"
    assert case.status == InterventionCaseStatus.MONITORING
    assert follow_up.status == FollowUpStatus.FULFILLED.value


async def test_study_events_fulfil_study_follow_up(fixed_rules):
    for event_type in (EVENT_ASSESSMENT_GRADED, EVENT_QUIZ_COMPLETED):
        case = make_case()
        follow_up = make_follow_up(
            case_id=case.id,
            trigger_type=FollowUpTriggerType.STUDY_INTERVENTION.value,
        )
        session = make_session(
            [
                FakeResult(scalars_list=[follow_up]),
                FakeResult(scalar=case),
                FakeResult(scalars_list=[]),  # stale siblings
                _attendance_rows(10, 100),
                FakeResult(scalars_list=[]),
            ]
        )
        event = DomainEvent(
            event_type=event_type,
            student_id=case.student_id,
            source_id=uuid.uuid4(),
            payload={},
        )

        outcomes = await handle_policy_event(session, event)

        assert len(outcomes) == 1
        assert outcomes[0].action == "fulfilled"


async def test_task_overdue_fulfils_assignment_follow_up(fixed_rules):
    case = make_case()
    follow_up = make_follow_up(
        case_id=case.id, trigger_type=FollowUpTriggerType.ASSIGNMENT_INTERVENTION.value
    )
    session = make_session(
        [
            FakeResult(scalars_list=[follow_up]),
            FakeResult(scalar=case),
            FakeResult(scalars_list=[]),  # stale siblings
            _attendance_rows(10, 100),
            FakeResult(scalars_list=[]),
        ]
    )
    event = DomainEvent(
        event_type=EVENT_TASK_OVERDUE,
        student_id=case.student_id,
        source_id=uuid.uuid4(),
        payload={},
    )

    outcomes = await handle_policy_event(session, event)

    assert len(outcomes) == 1
    assert outcomes[0].action == "fulfilled"


async def test_policy_event_scan_requires_active_case():
    """The scan filters on ACTIVE — non-matching cases yield no candidates."""
    session = make_session([FakeResult(scalars_list=[])])
    event = DomainEvent(
        event_type=EVENT_ATTENDANCE_UPDATED,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={},
    )

    outcomes = await handle_policy_event(session, event)

    assert outcomes == []


# ---- improvement predicate (direct) ----------------------------------------


async def test_improvement_no_attendance_data_not_verified(fixed_rules):
    """No derived rows → attendance not verified; with no approved plan the
    task/reason legs fail closed too (ADR-004 §2.5, no vacuous pass)."""
    case = make_case()
    session = make_session(
        [
            _attendance_rows(None, None),  # no derived rows
            FakeResult(scalars_list=[]),  # plans
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.attendance_ok is False
    assert check.risk_cleared is True  # no risky rows — attendance gates anyway
    assert check.tasks_ok is False  # fail-closed: no approved plan
    assert check.reasons_ok is False
    assert check.verified is False
    assert check.attendance_percent is None


async def test_improvement_conflict_band_blocks_verification(fixed_rules):
    case = make_case()
    session = make_session(
        [
            _attendance_rows(90, 100, band="DATA_CONFLICT"),
            FakeResult(scalars_list=[]),
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.attendance_ok is False
    assert check.verified is False
    assert check.attendance_percent is None  # conflict is never aggregated


async def test_improvement_below_threshold_not_verified(fixed_rules):
    case = make_case()
    session = make_session(
        [
            _attendance_rows(60, 100),
            FakeResult(scalars_list=[]),
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.attendance_ok is False
    assert check.verified is False


async def test_improvement_above_threshold_without_approved_plan_not_verified(fixed_rules):
    """Attendance alone can never resolve a case: the approved plan and its
    reason codes are required (PENDING_APPROVAL → ACTIVE is the approval)."""
    case = make_case()
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[]),  # no plan at all
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.attendance_ok is True
    assert check.risk_cleared is True
    assert check.tasks_ok is False
    assert check.reasons_ok is False
    assert check.verified is False


@pytest.mark.parametrize("band", ["WARNING", "CRITICAL"])
async def test_improvement_active_risk_band_blocks_verification(fixed_rules, band):
    """Regression: an aggregate above threshold must NOT verify while any
    derived row still carries the original risk band — the ORIGINAL risk
    must be cleared (per-course-run bands can mask a still-at-risk run)."""
    case = make_case()
    approved = make_plan(case)
    session = make_session(
        [
            _attendance_rows(90, 100, band=band),  # 90% >= 75% but still risky
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=["COMPLETED"]),
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.attendance_ok is True
    assert check.risk_cleared is False
    assert check.reasons_ok is False  # LOW_ATTENDANCE needs risk cleared
    assert check.verified is False


async def test_improvement_zero_materialized_tasks_not_verified(fixed_rules):
    """Regression: a plan whose actions were never materialized as
    StudentTask rows must not vacuously pass (vacuous truth was ADR
    §2.5's documented gap — now closed)."""
    case = make_case()
    approved = make_plan(case, actions=[{"type": "ATTEND_CLASS"}])
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=[]),  # nothing materialized
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.tasks_ok is False
    assert check.verified is False


async def test_improvement_partial_materialization_not_verified(fixed_rules):
    case = make_case()
    approved = make_plan(
        case, actions=[{"type": "ATTEND_CLASS"}, {"type": "DAILY_QUIZ"}]
    )
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=["COMPLETED"]),  # only 1 of 2 actions
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.tasks_ok is False
    assert check.verified is False


async def test_improvement_pending_plan_task_blocks_verification(fixed_rules):
    case = make_case()
    approved = make_plan(case)
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=["PENDING"]),  # materialized but open
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.tasks_ok is False
    assert check.verified is False


async def test_improvement_completed_plan_tasks_ok(fixed_rules):
    case = make_case()
    approved = make_plan(case, decision="EDITED")
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=["COMPLETED"]),
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.tasks_ok is True
    assert check.reasons_ok is True
    assert check.verified is True


async def test_improvement_unknown_reason_code_blocks_verification(fixed_rules):
    """A reason code outside the evaluable vocabulary fails closed —
    verified never rests on an unevidenced assumption (ADR-004 §2.5)."""
    case = make_case()
    approved = make_plan(case, reasons=["SOME_FUTURE_CODE"])
    session = make_session(
        [
            _attendance_rows(90, 100),
            FakeResult(scalars_list=[approved]),
            FakeResult(scalars_list=["COMPLETED"]),
        ]
    )

    check = await check_improvement(session, case=case)

    assert check.reasons_ok is False
    assert check.verified is False


# ---- FollowUpConsumer -------------------------------------------------------


def test_consumer_subscribes_all_trigger_events_and_is_idempotent():
    consumer = FollowUpConsumer(session_maker=MagicMock())
    bus = EventBus()

    consumer.ensure_subscribed(bus)
    consumer.ensure_subscribed(bus)  # second call must not double-subscribe

    for event_type in FollowUpConsumer.SUBSCRIBED_EVENTS:
        assert bus.subscriber_count(event_type) == 1


async def test_consumer_on_event_routes_and_rolls_back_on_failure(monkeypatch):
    consumer = FollowUpConsumer(session_maker=MagicMock())
    seen = {}

    class _FakeSession:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    session = AsyncMock()
    session.rollback = AsyncMock()
    consumer._session_maker = MagicMock(return_value=_FakeSession())

    async def boom(_session, _event):
        raise RuntimeError("handler exploded")

    monkeypatch.setattr(fu, "handle_followup_due_event", boom)
    event = followup_event(
        make_follow_up(case_id=uuid.uuid4()), event_type=EVENT_MENTOR_FOLLOWUP_DUE
    )

    with pytest.raises(RuntimeError):
        await consumer._on_event(event)

    session.rollback.assert_awaited()
    assert seen == {}


async def test_consumer_on_policy_event_logs_fulfilled_count(monkeypatch):
    consumer = FollowUpConsumer(session_maker=MagicMock())
    calls = {}

    class _FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    consumer._session_maker = MagicMock(return_value=_FakeSession())

    async def fake_policy(_session, event):
        calls["event_type"] = event.event_type
        return [fu.ConsumerOutcome(action="fulfilled")]

    monkeypatch.setattr(fu, "handle_policy_event", fake_policy)
    event = DomainEvent(
        event_type=EVENT_ATTENDANCE_UPDATED,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={},
    )

    await consumer._on_event(event)

    assert calls["event_type"] == EVENT_ATTENDANCE_UPDATED
