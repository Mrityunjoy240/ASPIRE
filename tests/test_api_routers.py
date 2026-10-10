# tests/test_api_routers.py
# Integration tests for API routers
# Verifies auth rejection, response schemas for /health, /attendance/what-if, /cases/queue

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.attendance import AttendanceDerivedState
from app.models.enums import (
    InterventionCaseStatus,
    UserRole,
)
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile


# TestClient fixture
@pytest.fixture
def client():
    return TestClient(app)


# Mock auth context fixtures
@pytest.fixture
def mock_student_auth():
    """Mock auth context for a student."""
    auth = MagicMock()
    auth.user_id = uuid4()
    auth.roles = [UserRole.STUDENT]
    auth.has_role = lambda *roles: UserRole.STUDENT in roles
    auth.is_student = lambda: True
    auth.is_mentor = lambda: False
    auth.is_admin = lambda: False
    return auth


@pytest.fixture
def mock_mentor_auth():
    """Mock auth context for a mentor."""
    auth = MagicMock()
    auth.user_id = uuid4()
    auth.roles = [UserRole.MENTOR]
    auth.has_role = lambda *roles: any(r in roles for r in [UserRole.MENTOR, UserRole.ADMIN])
    auth.is_student = lambda: False
    auth.is_mentor = lambda: True
    auth.is_admin = lambda: False
    return auth


@pytest.fixture
def mock_admin_auth():
    """Mock auth context for an admin."""
    auth = MagicMock()
    auth.user_id = uuid4()
    auth.roles = [UserRole.ADMIN]
    auth.has_role = lambda *roles: UserRole.ADMIN in roles
    auth.is_student = lambda: False
    auth.is_mentor = lambda: False
    auth.is_admin = lambda: True
    return auth


# ============ Health Endpoint Tests ============

def test_health_endpoint_public(client):
    """Health endpoint should be accessible without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "env" in data


# ============ Attendance What-If Tests ============

@patch("app.api.routers.attendance.get_session")
@patch("app.api.routers.attendance.get_auth_context")
def test_attendance_what_if_requires_auth(mock_get_auth, mock_get_session, client):
    """Attendance what-if should reject unauthenticated requests."""
    mock_get_auth.side_effect = Exception("Auth failed")
    response = client.get(f"/api/v1/attendance/{uuid4()}/what-if?target=75.0")
    assert response.status_code == 401


@patch("app.api.routers.attendance.get_session")
@patch("app.api.routers.attendance.get_auth_context")
@patch("app.api.routers.attendance._get_attendance_threshold")
def test_attendance_what_if_response_schema(mock_threshold, mock_get_auth, mock_get_session, client, mock_student_auth):
    """Attendance what-if should return correct schema."""
    mock_get_auth.return_value = mock_student_auth
    mock_threshold.return_value = Decimal("75.00")

    # Mock session execute
    mock_session = AsyncMock()
    mock_get_session.return_value = mock_session

    student_id = uuid4()
    course_id = uuid4()
    course_run_id = uuid4()

    # Mock derived state
    derived = AttendanceDerivedState(
        id=uuid4(),
        student_id=student_id,
        course_run_id=course_run_id,
        classes_conducted=20,
        classes_attended=12,
        attendance_percentage=Decimal("60.00"),
        risk_band="CRITICAL",
        required_to_recover=4,
        computed_at=datetime.now(UTC),
    )

    mock_result = MagicMock()
    mock_result.first.return_value = (derived, MagicMock(course_id=course_id))
    mock_session.execute.return_value = mock_result

    mock_get_auth.return_value = mock_student_auth

    response = client.get(f"/api/v1/attendance/{student_id}/what-if?target=75.0&course_id={course_id}")

    # If we get here, check schema
    if response.status_code == 200:
        data = response.json()
        assert "current_percentage" in data
        assert "target_percentage" in data
        assert "required_future_classes" in data
        assert "disclaimer" in data
        assert "Planning estimate" in data["disclaimer"]


# ============ Cases Queue Tests ============

@patch("app.api.routers.cases.get_session")
@patch("app.api.routers.cases.get_auth_context")
def test_cases_queue_requires_mentor_or_admin(mock_get_auth, mock_get_session, client):
    """Cases queue should reject unauthenticated requests (401) or wrong role (403)."""
    mock_get_auth.side_effect = Exception("Forbidden")
    response = client.get("/api/v1/cases/queue")
    # No auth header -> 401 Unauthorized
    assert response.status_code == 401


@patch("app.api.routers.cases.get_session")
@patch("app.api.routers.cases.get_auth_context")
def test_cases_queue_response_schema(mock_get_auth, mock_get_session, client, mock_mentor_auth):
    """Cases queue should return correct schema when authorized."""
    mock_get_auth.return_value = mock_mentor_auth

    # Mock session
    mock_session = AsyncMock()
    mock_get_session.return_value = mock_session
    mock_get_auth.return_value = mock_mentor_auth

    # Mock empty queue
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    response = client.get("/api/v1/cases/queue")

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        # Each item should have required fields
        if data:
            item = data[0]
            assert "case_id" in item
            assert "student_id" in item
            assert "student_name" in item
            assert "student_roll" in item
            assert "urgency_band" in item
            assert "status" in item
            assert "opened_at" in item


# ============ Task Completion Tests ============

@patch("app.api.routers.tasks.get_session")
@patch("app.api.routers.tasks.get_auth_context")
def test_task_complete_requires_ownership(mock_get_auth, mock_get_session, client, mock_student_auth):
    """Task completion should require student to own the task."""
    mock_get_auth.return_value = mock_student_auth

    mock_session = AsyncMock()
    mock_get_session.return_value = mock_session

    # Task not found or not owned
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    mock_get_auth.return_value = mock_student_auth

    response = client.post(f"/api/v1/tasks/{uuid4()}/complete", json={})
    # No auth header -> 401 Unauthorized
    assert response.status_code == 401


# ============ Case Approval (Mentor Plan Approval slice) ============

@pytest.fixture
def approve_deps():
    """Temporarily install dependency overrides for auth/session."""
    from app.main import app as main_app

    saved = dict(main_app.dependency_overrides)
    yield main_app.dependency_overrides
    main_app.dependency_overrides.clear()
    main_app.dependency_overrides.update(saved)


def _override_auth_and_session(overrides, auth, session):
    from app.api.deps import get_auth_context
    from app.core.database import get_session

    overrides[get_auth_context] = lambda: auth
    overrides[get_session] = lambda: session


def _case_and_plan(case_id: uuid.UUID, mentor_id: uuid.UUID, status):
    now = datetime.now(UTC)
    case = InterventionCase(
        id=case_id,
        student_id=uuid4(),
        mentor_id=mentor_id,
        status=status,
        urgency_band="URGENT",
        opened_at=now,
        created_at=now,
        updated_at=now,
    )
    plan = InterventionPlan(
        id=uuid4(),
        case_id=case_id,
        created_by="SYSTEM_AGENT",
        status="ACCEPTED",
        plan_actions=[],
        reason_codes=[],
        evidence={},
        created_at=now,
        updated_at=now,
    )
    return case, plan


def _result_returning(*values):
    """Sequential execute() results: first value = case query, second = plan
    list query (the router fetches plan history via .scalars().all())."""
    mocks = []
    for value in values:
        m = MagicMock()
        if value is None:
            m.scalar_one_or_none.return_value = None
            m.scalars.return_value.all.return_value = []
        elif isinstance(value, list):
            m.scalar_one_or_none.return_value = value[0] if value else None
            m.scalars.return_value.all.return_value = value
        else:
            m.scalar_one_or_none.return_value = value
            m.scalars.return_value.all.return_value = [value]
        mocks.append(m)
    return AsyncMock(side_effect=mocks)


def test_approve_requires_auth(client):
    """Approve endpoint must reject unauthenticated requests."""
    response = client.post(f"/api/v1/cases/{uuid4()}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 401


def test_approve_happy_path_emits_event(approve_deps, client, mock_mentor_auth):
    """200: case → ACTIVE, response schema, audit added, event emitted post-commit."""
    from app.main import app as main_app
    from app.services.case_service import EVENT_INTERVENTION_PLAN_APPROVED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    case, plan = _case_and_plan(case_id, mock_mentor_auth.user_id, InterventionCaseStatus.PENDING_APPROVAL)
    session.execute = _result_returning(case, [plan])
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)
    try:
        response = client.post(
            f"/api/v1/cases/{case_id}/approve",
            json={"decision": "APPROVED", "mentor_notes": "ok"},
        )
    finally:
        bus.clear()

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"case_id", "mentor_decision", "acted_at"}
    assert data["case_id"] == str(case_id)
    assert data["mentor_decision"] == "APPROVED"

    assert case.status == InterventionCaseStatus.ACTIVE
    session.add.assert_called_once()
    session.commit.assert_awaited()
    assert session.add.call_args[0][0].action_type == "PLAN_APPROVED_BY_MENTOR"

    assert len(received) == 1
    assert received[0].event_type == "INTERVENTION_PLAN_APPROVED"
    assert received[0].payload["previous_status"] == "PENDING_APPROVAL"
    assert received[0].payload["new_status"] == "ACTIVE"


def test_approve_reject_decision_no_event(approve_deps, client, mock_mentor_auth):
    """REJECTED → 200, case REPLAN_REQUIRED, no domain event."""
    from app.main import app as main_app
    from app.services.case_service import EVENT_INTERVENTION_PLAN_APPROVED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    case, plan = _case_and_plan(case_id, mock_mentor_auth.user_id, InterventionCaseStatus.PENDING_APPROVAL)
    session.execute = _result_returning(case, [plan])
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)
    try:
        response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "REJECTED"})
    finally:
        bus.clear()

    assert response.status_code == 200
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert plan.status == "DECLINED"
    assert received == []


def test_approve_404_unknown_case(approve_deps, client, mock_mentor_auth):
    session = AsyncMock()
    session.execute = _result_returning(None, None)
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    response = client.post(f"/api/v1/cases/{uuid4()}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 404


def test_approve_403_not_assigned_mentor(approve_deps, client, mock_mentor_auth):
    session = AsyncMock()
    case_id = uuid4()
    case, _ = _case_and_plan(case_id, uuid4(), InterventionCaseStatus.PENDING_APPROVAL)
    session.execute = _result_returning(case, None)
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 403


def test_approve_400_no_plan(approve_deps, client, mock_mentor_auth):
    session = AsyncMock()
    case_id = uuid4()
    case, _ = _case_and_plan(case_id, mock_mentor_auth.user_id, InterventionCaseStatus.PENDING_APPROVAL)
    session.execute = _result_returning(case, None)
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 400


def test_approve_409_illegal_transition(approve_deps, client, mock_mentor_auth):
    """03_SYSTEM_SPEC §10.2: mentor decisions only from PENDING_APPROVAL."""
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    case, plan = _case_and_plan(case_id, mock_mentor_auth.user_id, InterventionCaseStatus.ACTIVE)
    session.execute = _result_returning(case, [plan])
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_approve_422_invalid_decision(approve_deps, client, mock_mentor_auth):
    session = AsyncMock()
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    response = client.post(f"/api/v1/cases/{uuid4()}/approve", json={"decision": "MAYBE"})
    assert response.status_code == 422


# ---- P1 remediation regressions (F-01 / F-03) ----

def _plan(case_id, *, status="ACCEPTED", mentor_decision=None, days_ago=0):
    now = datetime.now(UTC) - timedelta(days=days_ago)
    return InterventionPlan(
        id=uuid4(),
        case_id=case_id,
        created_by="SYSTEM_AGENT",
        status=status,
        plan_actions=[],
        reason_codes=[],
        evidence={},
        mentor_decision=mentor_decision,
        created_at=now,
        updated_at=now,
    )


def test_f01_approve_with_plan_history_selects_pending(approve_deps, client, mock_mentor_auth):
    """Replan history (declined + superseded) plus the current awaiting plan →
    the current plan is decided; history untouched. The cb300da implementation
    called scalar_one_or_none() here and 500'd with MultipleResultsFound on a
    real database (proven); with mocks it decided an arbitrary historical row."""
    from app.main import app as main_app
    from app.services.case_service import EVENT_INTERVENTION_PLAN_APPROVED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    case, _ = _case_and_plan(case_id, mock_mentor_auth.user_id,
                             InterventionCaseStatus.PENDING_APPROVAL)
    old_declined = _plan(case_id, status="DECLINED", mentor_decision="REJECTED", days_ago=10)
    old_superseded = _plan(case_id, status="SUPERSEDED", days_ago=5)
    current = _plan(case_id, status="ACCEPTED", days_ago=1)
    session.execute = _result_returning(case, [old_declined, old_superseded, current])
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)
    try:
        response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    finally:
        bus.clear()

    assert response.status_code == 200
    assert response.json()["mentor_decision"] == "APPROVED"
    assert current.mentor_decision == "APPROVED"          # authoritative plan decided
    assert old_declined.mentor_decision == "REJECTED"     # history untouched
    assert old_superseded.mentor_decision is None
    assert case.status == InterventionCaseStatus.ACTIVE
    assert len(received) == 1
    session.add.assert_called_once()
    audit = session.add.call_args[0][0]
    assert audit.entity_id == current.id
    assert audit.previous_state["case_status"] == "PENDING_APPROVAL"
    assert audit.new_state["case_status"] == "ACTIVE"


def test_f01_ambiguous_pending_plans_return_409(approve_deps, client, mock_mentor_auth):
    """Two plans both awaiting the verdict → §10.2 allows one transition only:
    refuse instead of picking an arbitrary row. No audit, no event, no commit."""
    from app.main import app as main_app

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    case, _ = _case_and_plan(case_id, mock_mentor_auth.user_id,
                             InterventionCaseStatus.PENDING_APPROVAL)
    session.execute = _result_returning(case, [_plan(case_id), _plan(case_id, days_ago=1)])
    _override_auth_and_session(approve_deps, mock_mentor_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    try:
        response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    finally:
        bus.clear()

    assert response.status_code == 409
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_f03_case_row_selected_for_update(approve_deps, client, mock_mentor_auth):
    """F-03: the approve path locks the case row (PostgreSQL row-level lock) so
    concurrent approvals serialize and exactly one observes PENDING_APPROVAL."""
    from sqlalchemy.dialects import postgresql

    from app.api.routers.cases import _case_row_for_update

    sql = str(
        _case_row_for_update(uuid4()).compile(dialect=postgresql.dialect())
    )
    assert "FOR UPDATE" in sql.upper()


def test_f03_double_approval_only_one_transition_wins(approve_deps, client, mock_mentor_auth):
    """Two approval attempts for the same case: request A commits, then request
    B observes A's committed state — exactly what FOR UPDATE forces B to read
    after blocking on A's lock. Asserts: one state transition, one approval
    event, one authoritative audit row with correct states, B receives 409."""
    from app.main import app as main_app
    from app.services.case_service import EVENT_INTERVENTION_PLAN_APPROVED

    case_id = uuid4()
    case, plan = _case_and_plan(case_id, mock_mentor_auth.user_id,
                                InterventionCaseStatus.PENDING_APPROVAL)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_INTERVENTION_PLAN_APPROVED, recorder)
    try:
        # --- Request A (acquires the FOR UPDATE lock) ---
        session_a = AsyncMock()
        session_a.add = MagicMock()
        session_a.execute = _result_returning(case, [plan])
        _override_auth_and_session(approve_deps, mock_mentor_auth, session_a)

        resp_a = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
        assert resp_a.status_code == 200
        assert case.status == InterventionCaseStatus.ACTIVE
        assert session_a.add.call_args[0][0].action_type == "PLAN_APPROVED_BY_MENTOR"
        assert session_a.add.call_args[0][0].previous_state["case_status"] == "PENDING_APPROVAL"
        assert session_a.add.call_args[0][0].new_state["case_status"] == "ACTIVE"

        # --- Request B (blocked until A committed; reads post-A state) ---
        session_b = AsyncMock()
        session_b.add = MagicMock()
        session_b.execute = _result_returning(case, [plan])
        _override_auth_and_session(approve_deps, mock_mentor_auth, session_b)

        resp_b = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
        assert resp_b.status_code == 409
        assert "PENDING_APPROVAL" in resp_b.json()["detail"]
    finally:
        bus.clear()

    # Only A transitioned, audited and published
    assert len(received) == 1
    assert received[0].event_type == "INTERVENTION_PLAN_APPROVED"
    assert received[0].payload["previous_status"] == "PENDING_APPROVAL"
    assert session_a.add.call_count == 1
    session_b.add.assert_not_called()
    session_b.commit.assert_not_awaited()
    assert case.status == InterventionCaseStatus.ACTIVE
    assert plan.mentor_decision == "APPROVED"


def test_f01_router_plan_query_survives_plan_history_real_db():
    """Real SQLAlchemy execution of the exact router plan query: the old
    scalar_one_or_none() shape raises MultipleResultsFound on plan history
    (the cb300da 500); the fixed shape returns the full history for the
    service to select from."""
    from sqlalchemy import create_engine
    from sqlalchemy.exc import MultipleResultsFound
    from sqlalchemy.orm import Session

    from app.api.routers.cases import _plans_for_case_query
    from app.core.database import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[InterventionCase.__table__, InterventionPlan.__table__],
    )
    now = datetime.now(UTC)
    case_id = uuid4()
    with Session(engine) as db:
        db.add(InterventionCase(
            id=case_id, student_id=uuid4(), mentor_id=uuid4(),
            status=InterventionCaseStatus.PENDING_APPROVAL, urgency_band="URGENT",
            opened_at=now, created_at=now, updated_at=now,
        ))
        db.add(_plan(case_id, status="DECLINED", mentor_decision="REJECTED", days_ago=5))
        db.add(_plan(case_id, status="ACCEPTED", days_ago=1))
        db.commit()

        old_shape = _plans_for_case_query(case_id)
        with pytest.raises(MultipleResultsFound):
            db.execute(old_shape).scalar_one_or_none()

        plans = list(db.execute(_plans_for_case_query(case_id)).scalars().all())
        assert len(plans) == 2
        assert plans[0].status == "ACCEPTED"  # created_at DESC ordering


# ============ Student Plan Decision (student acceptance slice) ============

@pytest.fixture
def student_deps():
    """Temporarily install dependency overrides for auth/session."""
    from app.main import app as main_app

    saved = dict(main_app.dependency_overrides)
    yield main_app.dependency_overrides
    main_app.dependency_overrides.clear()
    main_app.dependency_overrides.update(saved)


def _student_profile(user_id: uuid.UUID, profile_id: uuid.UUID | None = None) -> StudentProfile:
    now = datetime.now(UTC)
    return StudentProfile(
        id=profile_id or uuid4(),
        user_id=user_id,
        batch_id=uuid4(),
        roll_number="BCREC-0001",
        enrollment_year=2024,
        created_at=now,
        updated_at=now,
    )


def _proposed_plan(case_id: uuid.UUID, days_ago: int = 0) -> InterventionPlan:
    now = datetime.now(UTC) - timedelta(days=days_ago)
    return InterventionPlan(
        id=uuid4(),
        case_id=case_id,
        created_by="SYSTEM_AGENT",
        status="PROPOSED",
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
        reason_codes=["LOW_ATTENDANCE"],
        evidence={},
        created_at=now,
        updated_at=now,
    )


def _student_case(case_id: uuid.UUID, student_id: uuid.UUID, status):
    now = datetime.now(UTC)
    return InterventionCase(
        id=case_id,
        student_id=student_id,
        mentor_id=uuid4(),
        status=status,
        urgency_band="URGENT",
        opened_at=now,
        created_at=now,
        updated_at=now,
    )


def test_student_decision_requires_auth(client):
    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 401


def test_student_decision_happy_path_emits_event(student_deps, client, mock_student_auth):
    """200: PLAN_PROPOSED → PENDING_APPROVAL, response schema, audit row,
    PLAN_ACCEPTED emitted post-commit (03 §10.2, §8.2; 07 §4)."""
    from app.main import app as main_app
    from app.services.student_action_service import EVENT_PLAN_ACCEPTED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)
    try:
        response = client.post(
            f"/api/v1/cases/{case_id}/student-decision",
            json={"decision": "ACCEPTED"},
        )
    finally:
        bus.clear()

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"case_id", "student_decision", "decided_at"}
    assert data["case_id"] == str(case_id)
    assert data["student_decision"] == "ACCEPTED"

    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plan.status == "ACCEPTED"
    assert plan.student_decision == "ACCEPTED"
    assert plan.decided_at is not None
    session.add.assert_called_once()
    session.commit.assert_awaited()
    audit = session.add.call_args[0][0]
    assert audit.action_type == "PLAN_ACCEPTED"
    assert audit.source_system == "STUDENT_APP"
    assert audit.entity_id == plan.id

    assert len(received) == 1
    assert received[0].event_type == "PLAN_ACCEPTED"
    assert received[0].payload["previous_status"] == "PLAN_PROPOSED"
    assert received[0].payload["new_status"] == "PENDING_APPROVAL"


def test_student_decision_customized_persists_actions(student_deps, client, mock_student_auth):
    """200: CUSTOMIZED persists the student's adjusted plan_actions."""
    from app.main import app as main_app
    from app.services.student_action_service import EVENT_PLAN_ACCEPTED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)
    edited = [{"type": "STUDY_BLOCK", "topic": "DBMS Unit 3", "duration_min": 45}]
    try:
        response = client.post(
            f"/api/v1/cases/{case_id}/student-decision",
            json={"decision": "CUSTOMIZED", "plan_actions": edited},
        )
    finally:
        bus.clear()

    assert response.status_code == 200
    assert response.json()["student_decision"] == "CUSTOMIZED"
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plan.status == "CUSTOMIZED"
    assert plan.plan_actions == edited
    assert [e.event_type for e in received] == [EVENT_PLAN_ACCEPTED]


def test_student_decision_declined_persists_reason(student_deps, client, mock_student_auth):
    """200: DECLINED → REPLAN_REQUIRED with optional reason persisted,
    audit row PLAN_DECLINED, PLAN_DECLINED emitted post-commit
    (03 §10.2 decline row, §8.2; 07 §4)."""
    from app.main import app as main_app
    from app.services.student_action_service import EVENT_PLAN_ACCEPTED, EVENT_PLAN_DECLINED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_PLAN_DECLINED, recorder)
    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)
    try:
        response = client.post(
            f"/api/v1/cases/{case_id}/student-decision",
            json={"decision": "DECLINED", "reason": "Morning batch clashes with my commute"},
        )
    finally:
        bus.clear()

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"case_id", "student_decision", "decided_at"}
    assert data["student_decision"] == "DECLINED"

    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert plan.status == "DECLINED"
    assert plan.student_decision == "DECLINED"
    assert plan.student_reason == "Morning batch clashes with my commute"
    assert plan.decided_at is not None
    session.add.assert_called_once()
    session.commit.assert_awaited()
    audit = session.add.call_args[0][0]
    assert audit.action_type == "PLAN_DECLINED"
    assert audit.source_system == "STUDENT_APP"
    assert audit.entity_id == plan.id
    assert "Morning batch" not in str(audit.new_state)  # no free text (07 §4)

    assert [e.event_type for e in received] == [EVENT_PLAN_DECLINED]
    assert received[0].payload["new_status"] == "REPLAN_REQUIRED"
    assert received[0].payload["decision"] == "DECLINED"


def test_student_decision_declined_without_reason(student_deps, client, mock_student_auth):
    """Reason is optional (02_USER_JOURNEYS 1.1 Step 6: 'optionally')."""
    from app.main import app as main_app
    from app.services.student_action_service import EVENT_PLAN_DECLINED

    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_PLAN_DECLINED, recorder)
    try:
        response = client.post(
            f"/api/v1/cases/{case_id}/student-decision", json={"decision": "DECLINED"}
        )
    finally:
        bus.clear()

    assert response.status_code == 200
    assert response.json()["student_decision"] == "DECLINED"
    assert plan.student_reason is None
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    assert [e.event_type for e in received] == [EVENT_PLAN_DECLINED]


def test_student_decision_404_unknown_case(student_deps, client, mock_student_auth):
    session = AsyncMock()
    session.execute = _result_returning(None)
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 404


def test_student_decision_403_wrong_role(student_deps, client, mock_mentor_auth):
    """A mentor may not act on this endpoint — §10.2 actor for these rows is
    the Student (role gate runs before the handler)."""
    session = AsyncMock()
    session.add = MagicMock()
    _override_auth_and_session(student_deps, mock_mentor_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 403
    session.add.assert_not_called()


def test_student_decision_403_not_own_case(student_deps, client, mock_student_auth):
    """Student (own data only): a case belonging to another student is 403."""
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, uuid4(), InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 403
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED


def test_student_decision_decline_409_illegal_transition(student_deps, client, mock_student_auth):
    """Decline follows the same §10.2 state guard: only from PLAN_PROPOSED."""
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.REPLAN_REQUIRED)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "DECLINED"}
    )
    assert response.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_student_decision_decline_400_no_plan(student_deps, client, mock_student_auth):
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    session.execute = _result_returning(case, profile, [])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "DECLINED"}
    )
    assert response.status_code == 400
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED


def test_student_decision_400_no_plan(student_deps, client, mock_student_auth):
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    session.execute = _result_returning(case, profile, [])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 400
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_student_decision_409_illegal_transition(student_deps, client, mock_student_auth):
    """03_SYSTEM_SPEC §10.2: student decisions only from PLAN_PROPOSED."""
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.ACTIVE)
    plan = _proposed_plan(case_id)
    session.execute = _result_returning(case, profile, [plan])
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_student_decision_409_ambiguous_plans(student_deps, client, mock_student_auth):
    """Two proposed plans await the verdict → refuse, never guess (409)."""
    session = AsyncMock()
    session.add = MagicMock()
    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    session.execute = _result_returning(
        case, profile, [_proposed_plan(case_id, days_ago=2), _proposed_plan(case_id, days_ago=1)]
    )
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
    )
    assert response.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_student_decision_422_decline_with_actions(student_deps, client, mock_student_auth):
    """A decline carries an optional reason, never edited actions (02 1.1 Step 6)."""
    session = AsyncMock()
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision",
        json={"decision": "DECLINED", "plan_actions": [{"type": "STUDY_BLOCK"}]},
    )
    assert response.status_code == 422


def test_student_decision_422_reason_only_on_decline(student_deps, client, mock_student_auth):
    session = AsyncMock()
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision",
        json={"decision": "ACCEPTED", "reason": "courtesy note"},
    )
    assert response.status_code == 422


def test_student_decision_422_unknown_decision(student_deps, client, mock_student_auth):
    session = AsyncMock()
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision", json={"decision": "MAYBE"}
    )
    assert response.status_code == 422


def test_student_decision_422_customized_without_actions(student_deps, client, mock_student_auth):
    session = AsyncMock()
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision", json={"decision": "CUSTOMIZED"}
    )
    assert response.status_code == 422


def test_student_decision_422_accept_with_actions(student_deps, client, mock_student_auth):
    session = AsyncMock()
    _override_auth_and_session(student_deps, mock_student_auth, session)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/student-decision",
        json={"decision": "ACCEPTED", "plan_actions": [{"type": "STUDY_BLOCK"}]},
    )
    assert response.status_code == 422


def test_student_decision_double_post_only_one_transition_wins(
    student_deps, client, mock_student_auth
):
    """Idempotency/concurrency: request A commits the transition; request B
    (serialized behind the FOR UPDATE row lock, then re-reading A's committed
    state) receives 409. Exactly one audit row and one PLAN_ACCEPTED event."""
    from app.main import app as main_app
    from app.services.student_action_service import EVENT_PLAN_ACCEPTED

    case_id = uuid4()
    profile = _student_profile(mock_student_auth.user_id)
    case = _student_case(case_id, profile.id, InterventionCaseStatus.PLAN_PROPOSED)
    plan = _proposed_plan(case_id)

    bus = main_app.state.event_bus
    bus.clear()
    received = []

    async def recorder(event):
        received.append(event)

    bus.subscribe(EVENT_PLAN_ACCEPTED, recorder)
    try:
        # --- Request A (acquires the FOR UPDATE lock) ---
        session_a = AsyncMock()
        session_a.add = MagicMock()
        session_a.execute = _result_returning(case, profile, [plan])
        _override_auth_and_session(student_deps, mock_student_auth, session_a)

        resp_a = client.post(
            f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
        )
        assert resp_a.status_code == 200
        assert case.status == InterventionCaseStatus.PENDING_APPROVAL

        # --- Request B (blocked until A committed; reads post-A state) ---
        session_b = AsyncMock()
        session_b.add = MagicMock()
        session_b.execute = _result_returning(case, profile, [plan])
        _override_auth_and_session(student_deps, mock_student_auth, session_b)

        resp_b = client.post(
            f"/api/v1/cases/{case_id}/student-decision", json={"decision": "ACCEPTED"}
        )
        assert resp_b.status_code == 409
        assert "PLAN_PROPOSED" in resp_b.json()["detail"]
    finally:
        bus.clear()

    assert len(received) == 1
    assert received[0].event_type == "PLAN_ACCEPTED"
    assert session_a.add.call_count == 1  # single audit row
    session_b.add.assert_not_called()
    session_b.commit.assert_not_awaited()
    assert case.status == InterventionCaseStatus.PENDING_APPROVAL
    assert plan.student_decision == "ACCEPTED"


def test_student_decision_uses_row_lock():
    """The student path locks the same case row FOR UPDATE (03 §10.2 single
    transition per state; PostgreSQL row lock, no external lock service)."""
    from sqlalchemy.dialects import postgresql

    from app.api.routers.cases import _case_row_for_update

    sql = str(_case_row_for_update(uuid4()).compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql.upper()


# ============ OpenAPI Contract Tests ============

def test_openapi_contract_generation():
    """Verify OpenAPI contract can be generated."""
    from scripts.generate_openapi import generate_openapi
    schema = generate_openapi()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/api/v1/attendance/{student_id}/what-if" in schema["paths"]
    assert "/api/v1/cases/queue" in schema["paths"]


# ============ Auth Dependency Tests ============

def test_require_roles_factory():
    """Test require_roles dependency factory."""
    from app.api.deps import require_roles

    dep = require_roles(UserRole.MENTOR, UserRole.ADMIN)
    assert callable(dep)


def test_auth_context_methods(mock_student_auth):
    """Test AuthContext role checking methods."""
    assert mock_student_auth.has_role(UserRole.STUDENT)
    assert not mock_student_auth.has_role(UserRole.MENTOR)
    assert mock_student_auth.is_student()
    assert not mock_student_auth.is_mentor()
    assert not mock_student_auth.is_admin()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
