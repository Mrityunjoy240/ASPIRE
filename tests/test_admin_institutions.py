# tests/test_admin_institutions.py
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_context, get_session
from app.main import app
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.institutions import Institution
from app.models.rules import InstitutionRule
from app.models.users import User


class MockAdminAuth:
    def __init__(self, user_id=None, institution_id=None, role=UserRole.ADMIN):
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


def test_admin_institutions_rejects_student(client):
    """Students and mentors must be forbidden from accessing admin endpoints."""
    mock_student = MockAdminAuth(role=UserRole.STUDENT)
    app.dependency_overrides[get_auth_context] = lambda: mock_student
    try:
        res = client.get("/api/v1/admin/institutions")
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_auth_context, None)


def test_admin_list_and_get_institutions(client):
    """Admin can list and retrieve institutions."""
    inst_id = uuid4()
    inst = Institution(id=inst_id, name="BCREC College", slug="bcrec", status="ACTIVE")

    mock_admin = MockAdminAuth(role=UserRole.ADMIN)
    mock_session = AsyncMock()

    # Mock list
    mock_result_list = MagicMock()
    mock_result_list.scalars.return_value.all.return_value = [inst]

    # Mock get
    mock_result_get = MagicMock()
    mock_result_get.scalar_one_or_none.return_value = inst

    # Mock rules
    mock_result_rules = MagicMock()
    mock_result_rules.scalars.return_value.all.return_value = [
        InstitutionRule(
            institution_id=inst_id,
            rule_id="attendance_threshold",
            scope_level="INSTITUTION",
            value={"threshold": 75.0},
            effective_from=datetime.now(timezone.utc),
            status="ACTIVE",
        )
    ]

    mock_session.execute.side_effect = [
        mock_result_list,
        mock_result_get,
        mock_result_rules,
    ]

    app.dependency_overrides[get_auth_context] = lambda: mock_admin
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        # 1. List
        res_list = client.get("/api/v1/admin/institutions")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) == 1
        assert items[0]["slug"] == "bcrec"

        # 2. Get single
        res_get = client.get(f"/api/v1/admin/institutions/{inst_id}")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["name"] == "BCREC College"
        assert data["rules"]["attendance_threshold"] == 75.0
    finally:
        app.dependency_overrides.pop(get_auth_context, None)
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_admin_institution_crud_and_rules_pg(client, pg_engine):
    """Full PostgreSQL integration test (runs when ASPIRE_TEST_PG_DSN is provided)."""
    admin_id = uuid4()
    inst_id = uuid4()
    mock_auth = MockAdminAuth(user_id=admin_id, institution_id=inst_id, role=UserRole.ADMIN)

    app.dependency_overrides[get_auth_context] = lambda: mock_auth

    try:
        # 1. Create Institution (POST /api/v1/admin/institutions)
        slug = f"college-test-{uuid4().hex[:6]}"
        res = client.post(
            "/api/v1/admin/institutions",
            json={"name": "Bengal College of Engineering", "slug": slug},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        created_id = data["id"]
        assert data["name"] == "Bengal College of Engineering"
        assert data["slug"] == slug
        assert data["status"] == "ACTIVE"
        assert data["rules"] is not None
        assert data["rules"]["attendance_threshold"] == 75.0

        # Duplicate slug conflict
        res_dup = client.post(
            "/api/v1/admin/institutions",
            json={"name": "Another College", "slug": slug},
        )
        assert res_dup.status_code == 409

        # 2. Get Institution (GET /api/v1/admin/institutions/{id})
        res_get = client.get(f"/api/v1/admin/institutions/{created_id}")
        assert res_get.status_code == 200
        assert res_get.json()["slug"] == slug

        # 3. Update Institution Rules (PATCH /api/v1/admin/institutions/{id}/rules)
        res_rules = client.patch(
            f"/api/v1/admin/institutions/{created_id}/rules",
            json={"attendance_threshold": 80.0, "escalation_days": 5},
        )
        assert res_rules.status_code == 200
        updated_rules = res_rules.json()["rules"]
        assert updated_rules["attendance_threshold"] == 80.0
        assert updated_rules["escalation_days"] == 5

        # 4. Verify in DB and Audit Log
        async with AsyncSession(pg_engine) as session:
            rule_res = await session.execute(
                select(InstitutionRule).where(
                    InstitutionRule.institution_id == created_id,
                    InstitutionRule.rule_id == "attendance_threshold",
                )
            )
            rule = rule_res.scalar_one_or_none()
            assert rule is not None
            assert rule.value["threshold"] == 80.0

            # Audit log check
            audit_res = await session.execute(
                select(AuditLog).where(
                    AuditLog.entity_id == created_id,
                    AuditLog.action_type == "INSTITUTION_RULES_UPDATED",
                )
            )
            audit = audit_res.scalar_one_or_none()
            assert audit is not None
            assert audit.source_system == "ADMIN_WEB"

    finally:
        app.dependency_overrides.pop(get_auth_context, None)
