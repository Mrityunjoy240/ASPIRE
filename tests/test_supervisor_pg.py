# tests/test_supervisor_pg.py
# R2 Supervisor integration evidence (11_ROADMAP R2): real PostgreSQL case
# creation (OPEN → IN_REVIEW), SYSTEM_AGENT audit row, and dedup against a
# non-terminal case — via the real ServiceBackedTools + case_intake service.
# Skips when ASPIRE_TEST_PG_DSN is unset (same safety guard as conftest).

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.supervisor import (
    ATTENDANCE_AGENT,
    DECISION_ESCALATE,
    EVENT_ATTENDANCE_RISK_CRITICAL,
    EVENT_ATTENDANCE_RISK_WARNING,
    AttendanceAssessment,
    Supervisor,
)
from app.agents.tools import ServiceBackedTools
from app.core.events import DomainEvent, EventBus
from app.models.academic import Batch, Programme
from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.institutions import Institution
from app.models.intervention import InterventionCase
from app.models.student import StudentProfile
from app.models.users import User

pytestmark = pytest.mark.integration


class StubSpecialist:
    async def assess(self, student_id):
        return AttendanceAssessment(
            available=True,
            explanation="stub",
            reason_codes=(),
            confidence_level="HIGH",
        )


async def _seed_risk_student(pg_engine, *, mentor_assigned: bool = True):
    now = datetime.now(UTC)
    tok = uuid.uuid4().hex[:8]
    inst = Institution(
        id=uuid.uuid4(), name=f"Sup {tok}", slug=f"sup-{tok}", status="ACTIVE"
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
        id=uuid.uuid4(), institution_id=inst.id, email=f"s-{tok}@example.test",
        full_name="Sup Student", status="ACTIVE", created_at=now, updated_at=now,
    )
    mentor_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"m-{tok}@example.test",
        full_name="Sup Mentor", status="ACTIVE", created_at=now, updated_at=now,
    )
    profile = StudentProfile(
        id=uuid.uuid4(), user_id=student_user.id, batch_id=batch.id,
        roll_number=f"SP-{tok}", enrollment_year=2024,
        mentor_id=mentor_user.id if mentor_assigned else None,
        created_at=now, updated_at=now,
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add_all([inst, prog, batch, student_user, mentor_user, profile])
        await session.commit()
    return SimpleNamespace(
        student_profile_id=profile.id,
        mentor_id=mentor_user.id,
        institution_id=inst.id,
    )


def _pg_session_maker(pg_engine):
    @asynccontextmanager
    async def maker():
        async with AsyncSession(pg_engine, expire_on_commit=False) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return maker


def _make_supervisor(pg_engine) -> tuple[Supervisor, EventBus]:
    supervisor = Supervisor(
        tools=ServiceBackedTools(session_maker=_pg_session_maker(pg_engine)),
        attendance_specialist=StubSpecialist(),
    )
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    return supervisor, bus


def _event(event_type: str, student_id: uuid.UUID) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        student_id=student_id,
        source_id=uuid.uuid4(),
        payload={},
    )


async def test_risk_event_creates_case_in_review_with_audit_row(pg_engine):
    seed = await _seed_risk_student(pg_engine)
    supervisor, bus = _make_supervisor(pg_engine)

    await bus.publish(_event(EVENT_ATTENDANCE_RISK_WARNING, seed.student_profile_id))

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase).where(
                    InterventionCase.student_id == seed.student_profile_id
                )
            )
        ).scalar_one()
        assert case.status == InterventionCaseStatus.IN_REVIEW
        assert case.urgency_band == "ATTENTION"
        assert case.mentor_id == seed.mentor_id
        assert len(case.trigger_events) == 1
        uuid.UUID(case.trigger_events[0])

        audits = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.entity_id == case.id)
                )
            ).scalars()
        )
        assert len(audits) == 1
        audit = audits[0]
        assert audit.action_type == "CASE_OPENED_TO_IN_REVIEW"
        assert audit.actor_type == "SYSTEM_AGENT"
        assert audit.actor_id is None
        assert audit.source_system == "AGENT"
        assert audit.previous_state["case_status"] == "OPEN"
        assert audit.new_state["case_status"] == "IN_REVIEW"
        # 07 §4: UUID/status scalars only in state JSONs.
        for state in (audit.previous_state, audit.new_state):
            for value in state.values():
                assert value is None or isinstance(value, (str, int))


async def test_second_risk_event_reuses_open_case(pg_engine):
    seed = await _seed_risk_student(pg_engine)
    supervisor, bus = _make_supervisor(pg_engine)

    await bus.publish(_event(EVENT_ATTENDANCE_RISK_CRITICAL, seed.student_profile_id))
    await bus.publish(_event(EVENT_ATTENDANCE_RISK_WARNING, seed.student_profile_id))

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        cases = list(
            (
                await session.execute(
                    select(InterventionCase).where(
                        InterventionCase.student_id == seed.student_profile_id
                    )
                )
            ).scalars()
        )
        assert len(cases) == 1  # dedup: one non-terminal case per student
        assert cases[0].urgency_band == "URGENT"  # first (CRITICAL) creation wins
        audits = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.entity_id == cases[0].id)
                )
            ).scalars()
        )
        assert len(audits) == 1  # reuse performs no second mutation


async def test_no_mentor_student_escalates_without_case(pg_engine):
    seed = await _seed_risk_student(pg_engine, mentor_assigned=False)
    supervisor, bus = _make_supervisor(pg_engine)

    event = _event(EVENT_ATTENDANCE_RISK_CRITICAL, seed.student_profile_id)
    runs: list = []

    async def recorder(e: DomainEvent) -> None:
        runs.append(e)

    # Capture the run through a same-type peer; publish itself must not raise.
    bus.subscribe(EVENT_ATTENDANCE_RISK_CRITICAL, recorder)
    await bus.publish(event)

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        cases = list(
            (
                await session.execute(
                    select(InterventionCase).where(
                        InterventionCase.student_id == seed.student_profile_id
                    )
                )
            ).scalars()
        )
        assert cases == []  # no case invented without a mentor

    run = await supervisor.handle(event)
    assert run.decision == DECISION_ESCALATE
    assert run.human_review_required is True
    assert "NO_MENTOR_ASSIGNED" in run.reason_codes


async def test_attendance_route_decision_matches_specialist_invocation(pg_engine):
    seed = await _seed_risk_student(pg_engine)
    supervisor, bus = _make_supervisor(pg_engine)
    run = await supervisor.handle(_event(EVENT_ATTENDANCE_RISK_WARNING, seed.student_profile_id))
    assert run.target_agent == ATTENDANCE_AGENT
    assert run.case_id is not None
