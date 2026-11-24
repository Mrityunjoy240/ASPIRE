# tests/test_plan_proposal_pg.py
# R3 proposal production integration evidence (11_ROADMAP R3): real
# PostgreSQL plan persistence (IN_REVIEW/REPLAN_REQUIRED → PLAN_PROPOSED),
# canonical DEC-01 evidence round-trip, SYSTEM_AGENT audit row, threshold
# rule provenance, and domain refusals (illegal transition, undecided
# proposal) — via the real ServiceBackedTools + plan_proposal service.
# Skips when ASPIRE_TEST_PG_DSN is unset (same safety guard as conftest).

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.llm_service as llm_module
from app.agents.attendance_specialist import AttendanceSpecialist
from app.agents.proposal import build_proposal_facts_context
from app.agents.tools import ServiceBackedTools
from app.models.academic import Batch, Course, CourseRun, Programme, Semester
from app.models.attendance import AttendanceDerivedState
from app.models.audit import AuditLog
from app.models.enums import InterventionCaseStatus
from app.models.institutions import Institution
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.llm_audit import LLMAttemptAudit
from app.models.rules import InstitutionRule
from app.models.student import StudentProfile
from app.models.users import User
from app.services.evidence import validate_evidence_entries
from app.services.llm_service import (
    InMemoryLLMAuditSink,
    LLMService,
    SqlLLMAuditSink,
    get_llm_service,
)
from app.services.plan_proposal_service import (
    PlanProposalError,
    propose_intervention_plan,
)
from app.services.student_action_service import decide_plan

pytestmark = pytest.mark.integration

NOW = datetime.now(UTC)


@pytest.fixture
def mock_llm(monkeypatch):
    """Fresh MOCK-mode LLMService regardless of any local .env values."""
    from types import SimpleNamespace as NS

    previous = llm_module._llm_service
    llm_module._llm_service = None
    monkeypatch.setattr(
        llm_module,
        "settings",
        NS(
            llm_provider="mock",
            llm_api_key="",
            llm_model="mock-model",
            llm_max_retries=1,
            llm_backoff_base=0.0,
            llm_timeout=1.0,
        ),
    )
    service = get_llm_service(audit_sink=InMemoryLLMAuditSink())
    yield service
    llm_module._llm_service = previous


@pytest.fixture
async def sql_audit_llm(pg_engine, monkeypatch):
    """MOCK-mode LLMService persisting per-attempt audit rows through
    SqlLLMAuditSink into the throwaway schema (migration 014)."""
    from types import SimpleNamespace as NS

    monkeypatch.setattr(
        llm_module,
        "settings",
        NS(
            llm_provider="mock",
            llm_api_key="",
            llm_model="mock-model",
            llm_max_retries=1,
            llm_backoff_base=0.0,
            llm_timeout=1.0,
        ),
    )
    sink = SqlLLMAuditSink(session_factory=_pg_session_maker(pg_engine))
    return LLMService(audit_sink=sink)


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


async def _seed_proposal_case(
    pg_engine,
    *,
    case_status: str = "IN_REVIEW",
    conflict: bool = False,
    threshold_rule: bool = True,
    second_risk_band: str | None = "SAFE",
    undecided_plan: bool = False,
):
    """Institution → batch → semester → courses → course runs → student →
    derived attendance state → threshold rule → intervention case."""
    tok = uuid.uuid4().hex[:8]
    inst = Institution(
        id=uuid.uuid4(), name=f"R3 {tok}", slug=f"r3-{tok}", status="ACTIVE"
    )
    prog = Programme(
        id=uuid.uuid4(), institution_id=inst.id, name="BCA", code=f"BCA-{tok}",
        total_semesters=6, created_at=NOW, updated_at=NOW,
    )
    batch = Batch(
        id=uuid.uuid4(), institution_id=inst.id, programme_id=prog.id,
        name=f"Batch {tok}", start_year=2024, end_year=2028, status="ACTIVE",
        created_at=NOW, updated_at=NOW,
    )
    semester = Semester(
        id=uuid.uuid4(), batch_id=batch.id, semester_number=1,
        start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
        status="ONGOING", created_at=NOW, updated_at=NOW,
    )
    faculty_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"f-{tok}@example.test",
        full_name="R3 Faculty", status="ACTIVE", created_at=NOW, updated_at=NOW,
    )
    student_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"s-{tok}@example.test",
        full_name="R3 Student", status="ACTIVE", created_at=NOW, updated_at=NOW,
    )
    mentor_user = User(
        id=uuid.uuid4(), institution_id=inst.id, email=f"m-{tok}@example.test",
        full_name="R3 Mentor", status="ACTIVE", created_at=NOW, updated_at=NOW,
    )
    profile = StudentProfile(
        id=uuid.uuid4(), user_id=student_user.id, batch_id=batch.id,
        roll_number=f"R3-{tok}", enrollment_year=2024,
        mentor_id=mentor_user.id, created_at=NOW, updated_at=NOW,
    )
    dbms = Course(
        id=uuid.uuid4(), institution_id=inst.id, name="DBMS", code=f"CS-{tok}",
        credit_hours=4, created_at=NOW, updated_at=NOW,
    )
    os_course = Course(
        id=uuid.uuid4(), institution_id=inst.id, name="OS", code=f"OS-{tok}",
        credit_hours=4, created_at=NOW, updated_at=NOW,
    )
    run_dbms = CourseRun(
        id=uuid.uuid4(), course_id=dbms.id, semester_id=semester.id,
        batch_id=batch.id, faculty_id=faculty_user.id, total_classes=20,
        created_at=NOW, updated_at=NOW,
    )
    run_os = CourseRun(
        id=uuid.uuid4(), course_id=os_course.id, semester_id=semester.id,
        batch_id=batch.id, faculty_id=faculty_user.id, total_classes=20,
        created_at=NOW, updated_at=NOW,
    )
    derived_dbms = AttendanceDerivedState(
        id=uuid.uuid4(), student_id=profile.id, course_run_id=run_dbms.id,
        classes_conducted=20, classes_attended=13,
        attendance_percentage=Decimal("64.50"),
        risk_band="DATA_CONFLICT" if conflict else "WARNING",
        required_to_recover=4, computed_at=NOW,
    )
    if second_risk_band is not None:
        derived_os = AttendanceDerivedState(
            id=uuid.uuid4(), student_id=profile.id, course_run_id=run_os.id,
            classes_conducted=20, classes_attended=18,
            attendance_percentage=Decimal("90.00"),
            risk_band=second_risk_band, required_to_recover=None,
            computed_at=NOW,
        )
    else:
        derived_os = None

    rule = None
    if threshold_rule:
        rule = InstitutionRule(
            id=uuid.uuid4(), institution_id=inst.id,
            rule_id="attendance_threshold", scope_level="INSTITUTION",
            scope_id=None, value={"threshold": 75},
            effective_from=NOW, version=1, status="ACTIVE",
            created_at=NOW, updated_at=NOW,
        )

    case = InterventionCase(
        id=uuid.uuid4(), student_id=profile.id, mentor_id=mentor_user.id,
        status=InterventionCaseStatus(case_status), urgency_band="ATTENTION",
        opened_at=NOW, created_at=NOW, updated_at=NOW,
    )
    undecided = None
    if undecided_plan:
        undecided = InterventionPlan(
            id=uuid.uuid4(), case_id=case.id, created_by="SYSTEM_AGENT",
            status="PROPOSED",
            plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
            reason_codes=["LOW_ATTENDANCE"], evidence=[],
            created_at=NOW, updated_at=NOW,
        )

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add_all(
            [
                inst, prog, batch, semester, faculty_user, student_user,
                mentor_user, profile, dbms, os_course, run_dbms, run_os,
                derived_dbms, case,
            ]
        )
        if derived_os is not None:
            session.add(derived_os)
        if rule is not None:
            session.add(rule)
        if undecided is not None:
            session.add(undecided)
        await session.commit()

    return SimpleNamespace(
        student_profile_id=profile.id,
        student_user_id=student_user.id,
        case_id=case.id,
        dbms_run_id=run_dbms.id,
        institution_id=inst.id,
    )


VALID_FIXTURE = {
    "decision": "PLAN_PROPOSED",
    "reason_codes": ["LOW_ATTENDANCE"],
    "evidence": [
        "attendance_percentage: 64.5",
        "classes_attended: 13",
        "classes_conducted: 20",
    ],
    "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
    "approval_required": True,
    "confidence_level": "HIGH",
}


async def _propose(pg_engine, mock_llm, seed):
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    mock_llm.mock_client.load_fixture(
        json.dumps(build_proposal_facts_context(facts), sort_keys=True),
        VALID_FIXTURE,
    )
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    return await specialist.produce_proposal(
        student_id=seed.student_profile_id, case_id=seed.case_id
    )


# --- Facts read path ---------------------------------------------------------


async def test_read_attendance_facts_from_real_pg(pg_engine):
    seed = await _seed_proposal_case(pg_engine)
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    assert facts.risk is not None
    assert facts.risk.subject == "DBMS"
    assert facts.risk.risk_band == "WARNING"
    assert facts.risk.attendance_percentage == 64.5
    assert facts.all_subjects == ("DBMS", "OS")
    assert facts.threshold == 75.0
    assert facts.threshold_observed_at is not None
    assert facts.has_data_conflict is False


async def test_worst_band_subject_wins_risk_selection(pg_engine):
    # DBMS CRITICAL at 50% + OS WARNING at 90% → CRITICAL row is primary.
    tok_seed = await _seed_proposal_case(pg_engine, second_risk_band="WARNING")
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        os_row = (
            await session.execute(
                select(AttendanceDerivedState).where(
                    AttendanceDerivedState.student_id == tok_seed.student_profile_id,
                    AttendanceDerivedState.course_run_id != tok_seed.dbms_run_id,
                )
            )
        ).scalar_one()
        os_row.risk_band = "WARNING"
        os_row.attendance_percentage = Decimal("55.00")
        os_row.required_to_recover = 8
        await session.commit()
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(tok_seed.student_profile_id)
    # Deterministic pick: lowest percentage among risk rows (55.0 < 64.5).
    assert facts.risk.attendance_percentage == 55.0
    assert facts.risk.required_to_recover == 8


async def test_missing_threshold_rule_is_none_never_defaulted(pg_engine):
    seed = await _seed_proposal_case(pg_engine, threshold_rule=False)
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    assert facts.threshold is None
    assert facts.threshold_observed_at is None


# --- Happy path: plan + transition + audit + evidence ------------------------


async def test_proposal_persists_plan_case_transition_and_audit(pg_engine, mock_llm):
    seed = await _seed_proposal_case(pg_engine)
    outcome = await _propose(pg_engine, mock_llm, seed)
    assert outcome.proposed is True
    assert outcome.plan_id is not None

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase).where(InterventionCase.id == seed.case_id)
            )
        ).scalar_one()
        assert case.status == InterventionCaseStatus.PLAN_PROPOSED

        plans = list(
            (
                await session.execute(
                    select(InterventionPlan).where(
                        InterventionPlan.case_id == seed.case_id
                    )
                )
            ).scalars()
        )
        assert len(plans) == 1
        plan = plans[0]
        assert plan.id == outcome.plan_id
        assert plan.status == "PROPOSED"
        assert plan.created_by == "SYSTEM_AGENT"
        assert plan.student_decision is None
        assert plan.reason_codes == ["LOW_ATTENDANCE"]
        assert plan.plan_actions[0]["type"] == "ATTEND_CLASS"
        # DEC-01 canonical evidence: re-validates with typed values and
        # backend provenance only.
        entries = validate_evidence_entries(plan.evidence)
        by_label = {e.label: e for e in entries}
        assert by_label["attendance_percentage"].value == 64.5
        assert by_label["classes_attended"].value == 13
        assert by_label["attendance_percentage"].source == "attendance_derived_state"

        audits = list(
            (
                await session.execute(
                    select(AuditLog).where(AuditLog.entity_id == plan.id)
                )
            ).scalars()
        )
        assert len(audits) == 1
        audit = audits[0]
        assert audit.action_type == "PLAN_PROPOSED"  # 07 §4 mandatory event
        assert audit.actor_type == "SYSTEM_AGENT"
        assert audit.actor_id is None
        assert audit.source_system == "AGENT"
        assert audit.entity_table == "intervention_plans"
        assert audit.new_state["case_status"] == "PLAN_PROPOSED"
        assert audit.new_state["plan_status"] == "PROPOSED"
        for state in (audit.previous_state, audit.new_state):
            for value in state.values():
                assert value is None or isinstance(value, (str, int))


async def test_proposal_persists_llm_attempt_audit_row(pg_engine, sql_audit_llm):
    """06 §5: one committed `llm_attempt_audit` row per LLM attempt with the
    full frozen metadata set — and never any prompt content (07 §4)."""
    seed = await _seed_proposal_case(pg_engine)
    outcome = await _propose(pg_engine, sql_audit_llm, seed)
    assert outcome.proposed is True

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        rows = list((await session.execute(select(LLMAttemptAudit))).scalars())
    assert len(rows) == 1
    row = rows[0]
    assert row.request_id is not None
    assert row.caller_agent == "attendance_specialist"
    assert row.prompt_version == "attendance.proposal.v1"
    assert row.response_schema_version == "AttendancePlanProposal"
    assert row.provider == "mock"
    assert row.model == "mock-fixture"  # MOCK never claims a real model was used
    assert row.attempt == 1
    assert row.outcome == "SUCCESS"
    assert row.failure_reason is None
    assert row.latency_ms >= 0
    assert row.input_token_count is None
    assert row.output_token_count is None
    assert row.created_at is not None

    # Metadata only: no prompt text, no evidence/facts payload in any column.
    text_columns = (
        row.caller_agent,
        row.prompt_version,
        row.response_schema_version,
        row.provider,
        row.model,
        row.outcome,
        row.failure_reason or "",
    )
    for marker in ("attendance specialist for ASPIRE", "engine-computed", "classes_attended"):
        assert all(marker not in value for value in text_columns)


async def test_initial_audit_failure_prevents_dispatch_and_writes_nothing(
    pg_engine, monkeypatch
):
    """Failure-path regression (06 §5 fail-closed, begin): the pre-dispatch
    IN_PROGRESS row cannot be persisted, so the provider is never called
    (MOCK fixture never evaluated). Refusal AUDIT_PERSISTENCE_FAILED, zero
    plan rows, case state unchanged, no audit_log delta, no
    llm_attempt_audit row."""
    from types import SimpleNamespace as NS

    seed = await _seed_proposal_case(pg_engine)

    async def _snapshot():
        async with AsyncSession(pg_engine, expire_on_commit=False) as session:
            case = (
                await session.execute(
                    select(InterventionCase).where(InterventionCase.id == seed.case_id)
                )
            ).scalar_one()
            plans = list(
                (
                    await session.execute(
                        select(InterventionPlan).where(
                            InterventionPlan.case_id == seed.case_id
                        )
                    )
                ).scalars()
            )
            audits = list((await session.execute(select(AuditLog))).scalars())
            attempts = list(
                (await session.execute(select(LLMAttemptAudit))).scalars()
            )
        return case, plans, audits, attempts

    monkeypatch.setattr(
        llm_module,
        "settings",
        NS(
            llm_provider="mock",
            llm_api_key="",
            llm_model="mock-model",
            llm_max_retries=1,
            llm_backoff_base=0.0,
            llm_timeout=1.0,
        ),
    )

    class ExplodingBeginSink:
        """Audit database unreachable before dispatch for this attempt."""

        async def begin(self, start):
            raise RuntimeError("audit store offline")

        async def finish(self, attempt):
            raise AssertionError("finish must not run when begin failed")

    llm = LLMService(audit_sink=ExplodingBeginSink())
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    llm.mock_client.load_fixture(
        json.dumps(build_proposal_facts_context(facts), sort_keys=True),
        VALID_FIXTURE,
    )
    specialist = AttendanceSpecialist(tools=tools, llm=llm)

    case_before, plans_before, audits_before, attempts_before = await _snapshot()
    assert case_before.status == InterventionCaseStatus.IN_REVIEW

    outcome = await specialist.produce_proposal(
        student_id=seed.student_profile_id, case_id=seed.case_id
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "AUDIT_PERSISTENCE_FAILED"
    assert outcome.plan_id is None
    assert llm.mock_client._call_log == []  # provider never dispatched

    case_after, plans_after, audits_after, attempts_after = await _snapshot()
    assert plans_after == plans_before  # no plan invented without an audit row
    assert case_after.status == InterventionCaseStatus.IN_REVIEW  # unchanged
    assert len(audits_after) == len(audits_before)  # no PLAN_PROPOSED business audit
    assert len(attempts_after) == len(attempts_before)  # the failed write persisted nothing


async def test_terminal_audit_failure_keeps_in_progress_row_inspectable(
    pg_engine, monkeypatch
):
    """Failure-path regression (06 §5 fail-closed, finish): the IN_PROGRESS
    row commits and the model output is produced, but the terminal audit
    update fails. The result is discarded end-to-end (refusal
    AUDIT_PERSISTENCE_FAILED, zero plan rows, case unchanged, no audit_log
    delta) and the pre-dispatch row remains inspectable in
    llm_attempt_audit with outcome IN_PROGRESS — the terminal outcome was
    never durably recorded."""
    from types import SimpleNamespace as NS

    seed = await _seed_proposal_case(pg_engine)

    async def _snapshot():
        async with AsyncSession(pg_engine, expire_on_commit=False) as session:
            case = (
                await session.execute(
                    select(InterventionCase).where(InterventionCase.id == seed.case_id)
                )
            ).scalar_one()
            plans = list(
                (
                    await session.execute(
                        select(InterventionPlan).where(
                            InterventionPlan.case_id == seed.case_id
                        )
                    )
                ).scalars()
            )
            audits = list((await session.execute(select(AuditLog))).scalars())
            attempts = list(
                (await session.execute(select(LLMAttemptAudit))).scalars()
            )
        return case, plans, audits, attempts

    monkeypatch.setattr(
        llm_module,
        "settings",
        NS(
            llm_provider="mock",
            llm_api_key="",
            llm_model="mock-model",
            llm_max_retries=1,
            llm_backoff_base=0.0,
            llm_timeout=1.0,
        ),
    )

    class FailingFinishSink:
        """begin commits for real (migration 014); the terminal update fails."""

        def __init__(self):
            self._real = SqlLLMAuditSink(session_factory=_pg_session_maker(pg_engine))
            self.failed_finishes = []

        async def begin(self, start):
            await self._real.begin(start)

        async def finish(self, attempt):
            self.failed_finishes.append(attempt)
            raise RuntimeError("audit store offline")

    sink = FailingFinishSink()
    llm = LLMService(audit_sink=sink)
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    llm.mock_client.load_fixture(
        json.dumps(build_proposal_facts_context(facts), sort_keys=True),
        VALID_FIXTURE,
    )
    specialist = AttendanceSpecialist(tools=tools, llm=llm)

    case_before, plans_before, audits_before, attempts_before = await _snapshot()
    assert case_before.status == InterventionCaseStatus.IN_REVIEW
    assert attempts_before == []  # nothing committed yet

    outcome = await specialist.produce_proposal(
        student_id=seed.student_profile_id, case_id=seed.case_id
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "AUDIT_PERSISTENCE_FAILED"
    assert outcome.plan_id is None
    assert len(llm.mock_client._call_log) == 1  # output was produced, not consumed
    assert len(sink.failed_finishes) == 1

    case_after, plans_after, audits_after, attempts_after = await _snapshot()
    assert plans_after == plans_before  # no plan invented from the unaudited result
    assert case_after.status == InterventionCaseStatus.IN_REVIEW  # unchanged
    assert len(audits_after) == len(audits_before)  # no PLAN_PROPOSED business audit

    # The pre-dispatch row survived the failed terminal update, still marked
    # IN_PROGRESS — this request's terminal outcome is not durably known.
    assert len(attempts_after) == 1
    row = attempts_after[0]
    assert row.outcome == "IN_PROGRESS"
    assert row.id == sink.failed_finishes[0].id
    assert row.attempt == 1
    assert row.failure_reason is None
    assert row.created_at is not None


async def test_threshold_rule_evidence_uses_institution_rules_source(pg_engine, mock_llm):
    seed = await _seed_proposal_case(pg_engine)
    tools = ServiceBackedTools(session_maker=_pg_session_maker(pg_engine))
    facts = await tools.read_attendance_facts(seed.student_profile_id)
    mock_llm.mock_client.load_fixture(
        json.dumps(build_proposal_facts_context(facts), sort_keys=True),
        {
            **VALID_FIXTURE,
            "evidence": [
                "attendance_percentage: 64.5",
                "threshold: 75.0",
            ],
        },
    )
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=seed.student_profile_id, case_id=seed.case_id
    )
    assert outcome.proposed is True
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        plan = (
            await session.execute(
                select(InterventionPlan).where(
                    InterventionPlan.id == outcome.plan_id
                )
            )
        ).scalar_one()
        entries = validate_evidence_entries(plan.evidence)
        threshold = [e for e in entries if e.label == "threshold"]
        assert threshold and threshold[0].source == "institution_rules"


# --- Domain refusals against real state --------------------------------------


async def test_conflict_quarantine_blocks_proposal_without_writes(pg_engine, mock_llm):
    seed = await _seed_proposal_case(pg_engine, conflict=True)
    outcome = await _propose(pg_engine, mock_llm, seed)
    assert outcome.proposed is False
    assert outcome.refusal_code == "DATA_CONFLICT_QUARANTINE"
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase).where(InterventionCase.id == seed.case_id)
            )
        ).scalar_one()
        assert case.status == InterventionCaseStatus.IN_REVIEW  # unchanged
        plans = list(
            (
                await session.execute(
                    select(InterventionPlan).where(
                        InterventionPlan.case_id == seed.case_id
                    )
                )
            ).scalars()
        )
        assert plans == []


async def test_duplicate_proposal_refused_while_undecided(pg_engine, mock_llm):
    seed = await _seed_proposal_case(pg_engine)
    first = await _propose(pg_engine, mock_llm, seed)
    assert first.proposed is True
    second = await _propose(pg_engine, mock_llm, seed)
    assert second.proposed is False
    assert second.refusal_code in ("UNDECIDED_PROPOSAL_EXISTS", "ILLEGAL_TRANSITION")
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        plans = list(
            (
                await session.execute(
                    select(InterventionPlan).where(
                        InterventionPlan.case_id == seed.case_id
                    )
                )
            ).scalars()
        )
        assert len(plans) == 1  # no second plan invented


async def test_undecided_plan_on_replan_state_is_refused(pg_engine):
    seed = await _seed_proposal_case(
        pg_engine, case_status="REPLAN_REQUIRED", undecided_plan=True
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        plans = list(
            (
                await session.execute(
                    select(InterventionPlan).where(
                        InterventionPlan.case_id == seed.case_id
                    )
                )
            ).scalars()
        )
        with pytest.raises(PlanProposalError) as excinfo:
            await propose_intervention_plan(
                session,
                case=case,
                existing_plans=plans,
                reason_codes=["LOW_ATTENDANCE"],
                plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                evidence_entries=[
                    {
                        "id": str(uuid.uuid4()),
                        "label": "classes_attended",
                        "value": 13,
                        "source": "attendance_derived_state",
                        "timestamp": NOW.isoformat(),
                    }
                ],
            )
        assert excinfo.value.code == "UNDECIDED_PROPOSAL_EXISTS"
        await session.rollback()


async def test_replan_required_without_undecided_proposal_succeeds(pg_engine):
    seed = await _seed_proposal_case(pg_engine, case_status="REPLAN_REQUIRED")
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        result = await propose_intervention_plan(
            session,
            case=case,
            existing_plans=[],
            reason_codes=["LOW_ATTENDANCE"],
            plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
            evidence_entries=[
                {
                    "id": str(uuid.uuid4()),
                    "label": "classes_attended",
                    "value": 13,
                    "source": "attendance_derived_state",
                    "timestamp": NOW.isoformat(),
                }
            ],
        )
        assert result.case_status == "PLAN_PROPOSED"
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase).where(InterventionCase.id == seed.case_id)
            )
        ).scalar_one()
        assert case.status == InterventionCaseStatus.PLAN_PROPOSED


async def test_illegal_source_states_refused(pg_engine):
    for status in ("PLAN_PROPOSED", "PENDING_APPROVAL", "ACTIVE", "RESOLVED"):
        seed = await _seed_proposal_case(pg_engine, case_status=status)
        async with AsyncSession(pg_engine, expire_on_commit=False) as session:
            case = (
                await session.execute(
                    select(InterventionCase)
                    .where(InterventionCase.id == seed.case_id)
                    .with_for_update()
                )
            ).scalar_one()
            with pytest.raises(PlanProposalError) as excinfo:
                await propose_intervention_plan(
                    session,
                    case=case,
                    existing_plans=[],
                    reason_codes=["LOW_ATTENDANCE"],
                    plan_actions=[
                        {"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}
                    ],
                    evidence_entries=[
                        {
                            "id": str(uuid.uuid4()),
                            "label": "classes_attended",
                            "value": 13,
                            "source": "attendance_derived_state",
                            "timestamp": NOW.isoformat(),
                        }
                    ],
                )
            assert excinfo.value.code == "ILLEGAL_TRANSITION"
            await session.rollback()


async def test_malformed_evidence_refused_at_persistence_boundary(pg_engine):
    seed = await _seed_proposal_case(pg_engine)
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        with pytest.raises(PlanProposalError) as excinfo:
            await propose_intervention_plan(
                session,
                case=case,
                existing_plans=[],
                reason_codes=["LOW_ATTENDANCE"],
                plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                evidence_entries=[{"label": "no-id-or-provenance"}],
            )
        assert excinfo.value.code == "INVALID_EVIDENCE"
        await session.rollback()


# --- R2 regression: student accept still reaches PENDING_APPROVAL ------------


async def test_student_accept_after_agent_proposal_reaches_pending_approval(
    pg_engine, mock_llm
):
    seed = await _seed_proposal_case(pg_engine)
    outcome = await _propose(pg_engine, mock_llm, seed)
    assert outcome.proposed is True

    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        case = (
            await session.execute(
                select(InterventionCase)
                .where(InterventionCase.id == seed.case_id)
                .with_for_update()
            )
        ).scalar_one()
        plans = list(
            (
                await session.execute(
                    select(InterventionPlan).where(
                        InterventionPlan.case_id == seed.case_id
                    )
                )
            ).scalars()
        )
        result = await decide_plan(
            session,
            case=case,
            plans=plans,
            decision="ACCEPTED",
            plan_actions=None,
            actor_id=seed.student_user_id,
        )
        assert result.case_status == "PENDING_APPROVAL"
        assert result.student_decision == "ACCEPTED"

    # And a further agent proposal on PENDING_APPROVAL is refused (03 §10.2:
    # mentor rows own that state).
    again = await _propose(pg_engine, mock_llm, seed)
    assert again.proposed is False
    assert again.refusal_code == "ILLEGAL_TRANSITION"
