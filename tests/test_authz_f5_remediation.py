import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_auth_context
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import User, UserRole
from app.models.institutions import Institution
from app.models.student import StudentProfile
from app.models.academic import Batch
from app.models.intervention import InterventionCase, InterventionCaseStatus
from app.models.audit import AuditLog

# Mock Auth Context
class MockAuthContext:
    def __init__(self, user_id, institution_id, roles):
        self.user_id = user_id
        self.institution_id = institution_id
        self.roles = roles

async def override_get_auth_context():
    return getattr(app.state, "mock_auth", None)

app.dependency_overrides[get_auth_context] = override_get_auth_context

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def setup_data(session: AsyncSession):
    # 1. Create Institutions
    inst_a = Institution(name="Inst A")
    inst_b = Institution(name="Inst B")
    session.add_all([inst_a, inst_b])
    await session.flush()

    # 2. Create Users
    mentor_a = User(username="mentor_a", role=UserRole.MENTOR)
    mentor_b = User(username="mentor_b", role=UserRole.MENTOR)
    hod_a = User(username="hod_a", role=UserRole.HOD)
    student_a = User(username="student_a", role=UserRole.STUDENT)
    student_b = User(username="student_b", role=UserRole.STUDENT)
    session.add_all([mentor_a, mentor_b, hod_a, student_a, student_b])
    await session.flush()

    # 3. Create Batches
    batch_a = Batch(name="Batch A", institution_id=inst_a.id)
    batch_b = Batch(name="Batch B", institution_id=inst_b.id)
    session.add_all([batch_a, batch_b])
    await session.flush()

    # 4. Create Student Profiles
    prof_a = StudentProfile(user_id=student_a.id, batch_id=batch_a.id, mentor_id=mentor_a.id)
    prof_b = StudentProfile(user_id=student_b.id, batch_id=batch_b.id, mentor_id=mentor_b.id)
    session.add_all([prof_a, prof_b])
    await session.flush()

    # 5. Create a Case for Student A
    case_a = InterventionCase(
        student_id=prof_a.id,
        status=InterventionCaseStatus.PENDING_APPROVAL,
        urgency_band="URGENT"
    )
    session.add(case_a)
    await session.flush()

    return {
        "inst_a": inst_a, "inst_b": inst_b,
        "mentor_a": mentor_a, "mentor_b": mentor_b, "hod_a": hod_a,
        "student_a": student_a, "student_b": student_b,
        "case_a": case_a, "prof_a": prof_a, "prof_b": prof_b
    }

@pytest.mark.asyncio
async def test_cross_institution_deny(client, pg_engine, setup_data):
    data = await setup_data
    # Mentor B (Inst B) tries to approve Case A (Inst A)
    app.state.mock_auth = MockAuthContext(data["mentor_b"].id, data["inst_b"].id, ["MENTOR"])

    response = client.post(f"/api/v1/cases/{data['case_a'].id}/approve", json={"decision": "APPROVED"})

    assert response.status_code == 403
    assert response.json()["detail"] == "STUDENT_SCOPE_DENIED"

    # Verify no audit logs
    async with AsyncSession(pg_engine) as session:
        result = await session.execute(AuditLog.__table__.select())
        assert len(result.all()) == 0

@pytest.mark.asyncio
async def test_hod_mentor_write_deny(client, pg_engine, setup_data):
    data = await setup_data
    # HOD A tries to approve a non-escalated case
    app.state.mock_auth = MockAuthContext(data["hod_a"].id, data["inst_a"].id, ["HOD"])

    response = client.post(f"/api/v1/cases/{data['case_a'].id}/approve", json={"decision": "APPROVED"})

    assert response.status_code == 403
    assert response.json()["detail"] == "STUDENT_SCOPE_DENIED"

    # Verify no audit logs
    async with AsyncSession(pg_engine) as session:
        result = await session.execute(AuditLog.__table__.select())
        assert len(result.all()) == 0

@pytest.mark.asyncio
async def test_hod_escalation_allow(client, pg_engine, setup_data):
    data = await setup_data
    # Set case to ESCALATION_REQUIRED
    async with AsyncSession(pg_engine) as session:
        # We need to get the object from the session to modify it
        from sqlalchemy import select
        res = await session.execute(select(InterventionCase).where(InterventionCase.id == data["case_a"].id))
        case = res.scalar_one()
        case.status = InterventionCaseStatus.ESCALATION_REQUIRED
        await session.commit()

    # HOD A tries to access escalated case
    app.state.mock_auth = MockAuthContext(data["hod_a"].id, data["inst_a"].id, ["HOD"])

    # Using the queue endpoint which is HOD-accessible for escalated cases
    response = client.get("/api/v1/cases/queue")

    # Should be allowed to see it in the queue
    assert response.status_code == 200
    # Verify case A is in the queue
    assert any(item["id"] == str(data["case_a"].id) for item in response.json())

@pytest.mark.asyncio
async def test_no_side_effects_on_forbidden(client, pg_engine, setup_data):
    data = await setup_data
    # Random user tries to approve
    app.state.mock_auth = MockAuthContext(uuid4(), uuid4(), ["USER"])

    response = client.post(f"/api/v1/cases/{data['case_a'].id}/approve", json={"decision": "APPROVED"})

    assert response.status_code == 403

    # Verify no state change
    async with AsyncSession(pg_engine) as session:
        from sqlalchemy import select
        res = await session.execute(select(InterventionCase).where(InterventionCase.id == data["case_a"].id))
        case = res.scalar_one()
        assert case.status == InterventionCaseStatus.PENDING_APPROVAL

        # Verify no audit record
        result = await session.execute(AuditLog.__table__.select())
        assert len(result.all()) == 0

