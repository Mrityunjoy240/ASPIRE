# tests/test_student_loop.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_context, get_session
from app.main import app
from app.models.academic import Batch
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.institutions import Institution
from app.models.intervention import InterventionCase, InterventionCaseStatus, InterventionPlan
from app.models.student import StudentProfile
from app.models.users import User


class MockStudentAuth:
    def __init__(self, user_id=None, institution_id=None, role=UserRole.STUDENT):
        self.user_id = user_id or uuid4()
        self.institution_id = institution_id or uuid4()
        self.role = role

    def is_student(self):
        return self.role == UserRole.STUDENT

    def is_mentor(self):
        return self.role == UserRole.MENTOR

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def has_role(self, *roles):
        return self.role in roles


@pytest.fixture
def client():
    return TestClient(app)


def test_student_endpoints_require_student_role(client):
    """Non-students must be refused 403 on /me/case endpoints."""
    mock_auth = MockStudentAuth(role=UserRole.MENTOR)
    app.dependency_overrides[get_auth_context] = lambda: mock_auth
    try:
        res = client.get("/api/v1/students/me/case")
        assert res.status_code == 403
        res_post = client.post("/api/v1/students/me/case/respond", json={"decision": "ACCEPTED"})
        assert res_post.status_code == 403
    finally:
        app.dependency_overrides.pop(get_auth_context, None)


def test_student_get_case_mocked(client):
    """Student retrieves their pending intervention plan."""
    student_user_id = uuid4()
    student_profile_id = uuid4()
    case_id = uuid4()
    plan_id = uuid4()
    now = datetime.now(timezone.utc)

    profile = StudentProfile(id=student_profile_id, user_id=student_user_id, roll_number="BCREC-001")
    case = InterventionCase(
        id=case_id,
        student_id=student_profile_id,
        status="PLAN_PROPOSED",
        urgency_band="URGENT",
        opened_at=now,
    )
    plan = InterventionPlan(
        id=plan_id,
        case_id=case_id,
        status="PROPOSED",
        created_by="AGENT",
        created_at=now,
        updated_at=now,
        plan_actions=[{"id": "a1", "type": "STUDY_SESSION", "description": "Attend tutoring"}],
    )

    mock_session = AsyncMock()
    mock_prof_res = MagicMock()
    mock_prof_res.scalar_one_or_none.return_value = profile

    mock_case_res = MagicMock()
    mock_case_res.scalar_one_or_none.return_value = case

    mock_plans_res = MagicMock()
    mock_plans_res.scalars.return_value.all.return_value = [plan]

    mock_session.execute.side_effect = [
        mock_prof_res,
        mock_case_res,
        mock_plans_res,
    ]

    mock_auth = MockStudentAuth(user_id=student_user_id, role=UserRole.STUDENT)
    app.dependency_overrides[get_auth_context] = lambda: mock_auth
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        res = client.get("/api/v1/students/me/case")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == str(case_id)
        assert data["status"] == "PLAN_PROPOSED"
        assert len(data["plan_actions"]) == 1
        assert data["plan_actions"][0]["id"] == "a1"
    finally:
        app.dependency_overrides.pop(get_auth_context, None)
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_student_full_loop_pg(client, pg_engine):
    """Live PostgreSQL round-trip test (runs when ASPIRE_TEST_PG_DSN is provided)."""
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        # 1. Setup Data
        inst = Institution(name="Test Inst", slug=f"inst-{uuid4().hex[:6]}")
        session.add(inst)
        await session.flush()

        batch = Batch(name="Batch 1", institution_id=inst.id)
        session.add(batch)
        await session.flush()

        user = User(username=f"student-{uuid4().hex[:6]}", role=UserRole.STUDENT, institution_id=inst.id)
        session.add(user)
        await session.flush()

        prof = StudentProfile(user_id=user.id, batch_id=batch.id, roll_number="S123")
        session.add(prof)
        await session.flush()

        case = InterventionCase(student_id=prof.id, status=InterventionCaseStatus.PLAN_PROPOSED, urgency_band="URGENT")
        session.add(case)
        await session.flush()

        plan = InterventionPlan(
            case_id=case.id,
            status="PROPOSED",
            created_by="SYSTEM",
            plan_actions=[{"id": "a1", "type": "ATTEND_CLASS", "description": "Attend class"}],
            reason_codes=["LOW_ATTENDANCE"],
            evidence=[],
        )
        session.add(plan)
        await session.commit()

        # 2. Test: GET /me/case
        mock_auth = MockStudentAuth(user_id=user.id, institution_id=inst.id, role=UserRole.STUDENT)
        app.dependency_overrides[get_auth_context] = lambda: mock_auth
        try:
            res_get = client.get("/api/v1/students/me/case")
            assert res_get.status_code == 200
            data = res_get.json()
            assert data["case_id"] == str(case.id)
            assert data["status"] == "PLAN_PROPOSED"
            assert len(data["plan_actions"]) == 1

            # 3. Test: POST /me/case/respond (ACCEPT)
            res_post = client.post("/api/v1/students/me/case/respond", json={"decision": "ACCEPTED"})
            assert res_post.status_code == 200
            assert res_post.json()["student_decision"] == "ACCEPTED"

            # 4. Verify state transition
            await session.refresh(case)
            assert case.status == "PENDING_APPROVAL"

            # 5. Verify Audit Log
            result = await session.execute(select(AuditLog).where(AuditLog.entity_id == plan.id))
            logs = result.scalars().all()
            assert len(logs) > 0
            assert any(log.action_type == "PLAN_ACCEPTED" for log in logs)
        finally:
            app.dependency_overrides.pop(get_auth_context, None)
