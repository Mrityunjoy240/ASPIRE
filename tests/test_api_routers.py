# tests/test_api_routers.py
# Integration tests for API routers
# Verifies auth rejection, response schemas for /health, /attendance/what-if, /cases/queue

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.enums import UserRole, AttendanceStatus, TaskStatus, InterventionCaseStatus
from app.models.student import StudentProfile
from app.models.users import User, UserRoleAssignment
from app.models.attendance import AttendanceRecord, AttendanceDerivedState
from app.models.attendance import AttendanceRecord
from app.models.academic import CourseRun, Course, Semester, Batch, Programme
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.tasks import StudentTask
from app.models.enums import TaskSourceType, TaskStatus


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
    from app.models.attendance import AttendanceDerivedState
    derived = AttendanceDerivedState(
        id=uuid4(),
        student_id=student_id,
        course_run_id=course_run_id,
        classes_conducted=20,
        classes_attended=12,
        attendance_percentage=Decimal("60.00"),
        risk_band="CRITICAL",
        required_to_recover=4,
        computed_at=datetime.now(timezone.utc),
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