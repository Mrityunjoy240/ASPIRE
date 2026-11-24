# tests/test_attendance_router_pg.py
# Regression for the attendance-router defect found by the DEC-02 evidence
# phase: _get_attendance_threshold selected StudentProfile.institution_id —
# a column that exists in NO migration/model (student_profiles carries only
# batch_id), so the helper raised UndefinedColumn against real PostgreSQL.
# DEC-02 fix resolves institution ownership through the verified chain
# student_profiles.batch_id -> batches.institution_id (003/004) with no new
# columns and no authorization changes.
# Covers the helper directly AND the /attendance/{id}/what-if endpoint path.
# DSN guard + throwaway schema: tests/conftest.py (pg_engine / pg_seed).

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context, get_session
from app.api.routers.attendance import _get_attendance_threshold
from app.main import app
from app.models.academic import Course, CourseRun, Semester
from app.models.attendance import AttendanceDerivedState
from app.models.enums import UserRole
from app.models.rules import InstitutionRule
from app.models.student import StudentProfile
from app.models.users import User

pytestmark = pytest.mark.integration


async def _batch_id_of(engine, profile_id) -> uuid.UUID:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                select(StudentProfile.batch_id).where(StudentProfile.id == profile_id)
            )
        ).scalar_one()


async def _insert_rule(engine, **kwargs) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(InstitutionRule(**kwargs))
        await session.commit()


async def test_threshold_resolves_institution_via_batch(pg_engine, pg_seed):
    """INSTITUTION-scope rule found through student -> batch -> institution.
    Pre-fix this raised UndefinedColumn on StudentProfile.institution_id."""
    await _insert_rule(
        pg_engine,
        institution_id=pg_seed.institution_id,
        rule_id="attendance_threshold",
        scope_level="INSTITUTION",
        scope_id=None,
        value={"threshold": 80},
        effective_from=datetime.now(UTC),
        version=1,
        status="ACTIVE",
    )
    async with AsyncSession(pg_engine) as session:
        threshold = await _get_attendance_threshold(session, pg_seed.student_profile_id)
    assert threshold == Decimal("80")


async def test_threshold_falls_back_to_batch_scope(pg_engine, pg_seed):
    """No INSTITUTION rule -> the BATCH-scoped rule for the student's batch is
    used (existing precedence order preserved unchanged by DEC-02)."""
    batch_id = await _batch_id_of(pg_engine, pg_seed.student_profile_id)
    await _insert_rule(
        pg_engine,
        institution_id=pg_seed.institution_id,
        rule_id="attendance_threshold",
        scope_level="BATCH",
        scope_id=batch_id,
        value={"threshold": 78.5},
        effective_from=datetime.now(UTC),
        version=1,
        status="ACTIVE",
    )
    async with AsyncSession(pg_engine) as session:
        threshold = await _get_attendance_threshold(session, pg_seed.student_profile_id)
    assert threshold == Decimal("78.5")


async def test_threshold_defaults_to_75_without_rules(pg_engine, pg_seed):
    async with AsyncSession(pg_engine) as session:
        threshold = await _get_attendance_threshold(session, pg_seed.student_profile_id)
    assert threshold == Decimal("75.00")


async def test_what_if_endpoint_end_to_end(pg_engine, pg_seed):
    """The actual attendance-router path: GET /attendance/{id}/what-if with a
    real session over PostgreSQL. Pre-fix the endpoint 500s inside
    _get_attendance_threshold (UndefinedColumn); now it resolves the
    institution rule through the batch and returns 200."""
    now = datetime.now(UTC)
    await _insert_rule(
        pg_engine,
        institution_id=pg_seed.institution_id,
        rule_id="attendance_threshold",
        scope_level="INSTITUTION",
        scope_id=None,
        value={"threshold": 80},
        effective_from=now,
        version=1,
        status="ACTIVE",
    )

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        batch_id = (
            await session.execute(
                select(StudentProfile.batch_id).where(
                    StudentProfile.id == pg_seed.student_profile_id
                )
            )
        ).scalar_one()
        faculty = User(
            id=uuid.uuid4(),
            institution_id=pg_seed.institution_id,
            email=f"faculty-{uuid.uuid4().hex[:8]}@example.test",
            full_name="Integration Faculty",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        course = Course(
            id=uuid.uuid4(),
            institution_id=pg_seed.institution_id,
            name="DBMS",
            code="CS-601",
            created_at=now,
            updated_at=now,
        )
        semester = Semester(
            id=uuid.uuid4(),
            batch_id=batch_id,
            semester_number=6,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 12, 31),
            status="ONGOING",
            created_at=now,
            updated_at=now,
        )
        run = CourseRun(
            id=uuid.uuid4(),
            course_id=course.id,
            semester_id=semester.id,
            batch_id=batch_id,
            faculty_id=faculty.id,
            total_classes=30,
            created_at=now,
            updated_at=now,
        )
        derived = AttendanceDerivedState(
            id=uuid.uuid4(),
            student_id=pg_seed.student_profile_id,
            course_run_id=run.id,
            classes_conducted=30,
            classes_attended=22,
            attendance_percentage=Decimal("73.33"),
            risk_band="WARNING",
            required_to_recover=3,
            computed_at=now,
        )
        session.add_all([faculty, course, semester, run, derived])
        await session.commit()
        student_user = (
            await session.execute(select(User).where(User.id == pg_seed.student_user_id))
        ).scalar_one()

    engine = pg_engine

    async def _override_session():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _override_auth():
        return AuthContext(
            user_id=student_user.id,
            user=student_user,
            roles=[UserRole.STUDENT],
            institution_id=pg_seed.institution_id,
        )

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_auth_context] = _override_auth
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/attendance/{pg_seed.student_profile_id}/what-if"
            f"?course_id={course.id}&target=70"
        )
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_auth_context, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert float(body["current_percentage"]) == 73.33  # Decimal JSON-safe
    assert body["current_conducted"] == 30
    assert body["current_attended"] == 22
