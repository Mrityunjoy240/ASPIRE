# tests/conftest.py
# Shared PostgreSQL integration-test infrastructure: the DSN safety guard and
# the throwaway-schema engine fixture used by the *_pg.py test modules.
#
# Run (never against a production database):
#   docker run --rm -d --name aspire-it-pg -p 55432:5432 \
#       -e POSTGRES_PASSWORD=aspire -e POSTGRES_DB=aspire_test pgvector/pgvector:pg16
#   set ASPIRE_TEST_PG_DSN=postgresql+psycopg://postgres:aspire@127.0.0.1:55432/aspire_test
#
# Safety: tests skip when ASPIRE_TEST_PG_DSN is unset (default local and CI
# runs — the unit suite must never need a DB), fail if the DSN database name
# does not end in "_test", apply db/migrations/*.sql inside a unique throwaway
# schema, and drop only that schema afterwards.

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.academic import Batch, Programme
from app.models.enums import InterventionCaseStatus
from app.models.institutions import Institution
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile
from app.models.users import User

DSN_ENV = "ASPIRE_TEST_PG_DSN"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"
# Windows + psycopg async: the default ProactorEventLoop cannot be used.
# pytest-asyncio builds loops from the policy, so switch before any loop for
# an integration test is created. Applied only when the test can actually run.
if sys.platform == "win32" and os.environ.get(DSN_ENV):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _require_dsn() -> str:
    dsn = os.environ.get(DSN_ENV)
    if not dsn:
        pytest.skip(f"{DSN_ENV} not set — PostgreSQL integration test not executed")
    database = dsn.rsplit("/", 1)[-1].split("?")[0]
    if not database.endswith("_test"):
        pytest.fail(
            f"refusing to run against database '{database}': {DSN_ENV} must point "
            "at a disposable database whose name ends in '_test'"
        )
    return dsn


@pytest.fixture
async def pg_engine():
    """Fresh throwaway schema + full migration chain per test, dropped after."""
    dsn = _require_dsn()
    schema = f"aspire_it_{uuid.uuid4().hex[:10]}"
    engine = create_async_engine(
        dsn,
        poolclass=NullPool,  # every checkout = a fresh independent connection
        future=True,
        # All DDL lands in the throwaway schema (first existing entry);
        # `public` stays on the path so CREATE EXTENSION's vector type from
        # migration 001 resolves (extension objects must live outside the
        # throwaway schema, or the teardown drop would remove them).
        connect_args={"options": f"-c search_path={schema},public"},
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            async with engine.begin() as conn:
                await conn.execute(text(path.read_text(encoding="utf-8")))
        yield engine
    finally:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            await engine.dispose()


@pytest.fixture
async def pg_seed(pg_engine):
    """A minimal PLAN_PROPOSED case with one PROPOSED plan, via the ORM."""
    now = datetime.now(UTC)
    tok = uuid.uuid4().hex[:8]
    inst = Institution(
        id=uuid.uuid4(), name=f"Integration {tok}", slug=f"it-{tok}", status="ACTIVE"
    )
    prog = Programme(
        id=uuid.uuid4(), institution_id=inst.id, name="BCA", code=f"BCA-{tok}",
        total_semesters=6, created_at=now, updated_at=now,
    )
    batch = Batch(
        id=uuid.uuid4(), institution_id=inst.id, programme_id=prog.id,
        name=f"Batch {tok}", start_year=2024, end_year=2028, status="ACTIVE",
        created_at=now, updated_at=now,
    )
    student_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"student-{tok}@example.test",
        full_name="Integration Student", status="ACTIVE", created_at=now, updated_at=now,
    )
    mentor_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"mentor-{tok}@example.test",
        full_name="Integration Mentor", status="ACTIVE", created_at=now, updated_at=now,
    )
    profile = StudentProfile(
        id=uuid.uuid4(), user_id=student_user.id, batch_id=batch.id,
        roll_number=f"IT-{tok}", enrollment_year=2024, created_at=now, updated_at=now,
    )
    case = InterventionCase(
        id=uuid.uuid4(), student_id=profile.id, mentor_id=mentor_user.id,
        status=InterventionCaseStatus.PLAN_PROPOSED, urgency_band="URGENT",
        opened_at=now, created_at=now, updated_at=now,
    )
    plan = InterventionPlan(
        id=uuid.uuid4(), case_id=case.id, created_by="SYSTEM_AGENT",
        status="PROPOSED",
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS"}],
        reason_codes=["LOW_ATTENDANCE"],
        evidence={},
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add_all([inst, prog, batch, student_user, mentor_user, profile, case])
        # ORM insert: reason_codes is TEXT[] (migration 009) and the model now
        # declares postgresql.ARRAY(Text) — the seed exercises the corrected
        # model type directly.
        session.add(plan)
        await session.commit()

    return SimpleNamespace(
        case_id=case.id,
        plan_id=plan.id,
        institution_id=inst.id,
        student_user_id=student_user.id,
        student_profile_id=profile.id,
    )
