# tests/test_plan_proposal.py
# R3 proposal production tests (11_ROADMAP R3): strict LLM schema, semantic
# validation against verified facts, DEC-01 evidence rebuild, specialist
# refusal codes, and Supervisor proposal-hook wiring. Unit tests use fakes
# for tools and the MOCK LLM — no database, no network.

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.services.llm_service as llm_module
from app.agents.attendance_specialist import (
    AttendanceSpecialist,
    build_proposal_messages,
)
from app.agents.proposal import (
    ALLOWED_REASON_CODES,
    AttendancePlanProposal,
    AttendanceProposalFacts,
    ProposalOutcome,
    ProposalValidationError,
    SubjectAttendanceFact,
    build_proposal_facts_context,
    is_schema_valid,
    validate_proposal_output,
)
from app.agents.supervisor import (
    ATTENDANCE_AGENT,
    DECISION_ESCALATE,
    DECISION_ROUTE,
    EVENT_ATTENDANCE_RISK_WARNING,
    EVENT_PLAN_DECLINED,
    EVENT_TASK_OVERDUE,
    INTERVENTION_AGENT,
    CaseUnavailable,
    DerivedStateSummary,
    Supervisor,
)
from app.core.events import DomainEvent
from app.services.llm_service import (
    InMemoryLLMAuditSink,
    LLMRetryExhausted,
    LLMService,
    get_llm_service,
)

AGENTS_DIR = Path(__file__).resolve().parents[1] / "app" / "agents"
NOW = datetime(2026, 10, 12, 8, 30, tzinfo=UTC)


def make_facts(
    *,
    risk_band: str | None = "WARNING",
    percentage: float | None = 64.50,
    attended: int = 13,
    conducted: int = 20,
    required_to_recover: int | None = 4,
    threshold: float | None = 75.0,
    subjects: tuple[str, ...] = ("DBMS", "OS"),
    has_data_conflict: bool = False,
) -> AttendanceProposalFacts:
    risk = None
    if risk_band is not None:
        risk = SubjectAttendanceFact(
            course_run_id=uuid.uuid4(),
            subject="DBMS",
            classes_conducted=conducted,
            classes_attended=attended,
            attendance_percentage=percentage,
            risk_band=risk_band,
            required_to_recover=required_to_recover,
            computed_at=NOW,
        )
    return AttendanceProposalFacts(
        risk=risk,
        all_subjects=subjects,
        threshold=threshold,
        threshold_observed_at=NOW if threshold is not None else None,
        has_data_conflict=has_data_conflict,
    )


def valid_output(**overrides) -> AttendancePlanProposal:
    payload: dict = {
        "decision": "PLAN_PROPOSED",
        "reason_codes": ["LOW_ATTENDANCE"],
        "evidence": [
            "attendance_percentage: 64.5",
            "classes_attended: 13",
        ],
        "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
        "approval_required": True,
        "confidence_level": "HIGH",
    }
    payload.update(overrides)
    return AttendancePlanProposal.model_validate(payload)


# --- Strict schema (extra=forbid; model-invented provenance impossible) -----


def test_schema_rejects_float_confidence():
    with pytest.raises(ValidationError):
        AttendancePlanProposal.model_validate(
            {
                "decision": "PLAN_PROPOSED",
                "reason_codes": ["LOW_ATTENDANCE"],
                "evidence": ["attendance_percentage: 64.5"],
                "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                "approval_required": True,
                "confidence_level": 0.95,
            }
        )


def test_schema_rejects_wrong_decision():
    with pytest.raises(ValidationError):
        AttendancePlanProposal.model_validate(
            {
                "decision": "APPROVED",
                "reason_codes": ["LOW_ATTENDANCE"],
                "evidence": ["attendance_percentage: 64.5"],
                "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                "approval_required": True,
                "confidence_level": "HIGH",
            }
        )


def test_schema_rejects_model_invented_provenance_on_evidence():
    """Evidence is list[str] claims only (A-05). A model attempting to
    supply its own source/timestamp dicts is schema-rejected — provenance
    is structurally impossible to invent."""
    with pytest.raises(ValidationError):
        AttendancePlanProposal.model_validate(
            {
                "decision": "PLAN_PROPOSED",
                "reason_codes": ["LOW_ATTENDANCE"],
                "evidence": [
                    {
                        "label": "attendance_percentage",
                        "value": 99.9,
                        "source": "fabricated",
                        "timestamp": "2026-01-01T00:00:00Z",
                    }
                ],
                "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                "approval_required": True,
                "confidence_level": "HIGH",
            }
        )


def test_schema_rejects_unknown_action_type_and_extra_keys():
    with pytest.raises(ValidationError):
        AttendancePlanProposal.model_validate(
            {
                "decision": "PLAN_PROPOSED",
                "reason_codes": ["LOW_ATTENDANCE"],
                "evidence": ["attendance_percentage: 64.5"],
                "actions": [{"type": "DROP_OUT", "subject": "DBMS"}],
                "approval_required": True,
                "confidence_level": "HIGH",
            }
        )
    with pytest.raises(ValidationError):
        AttendancePlanProposal.model_validate(
            {
                "decision": "PLAN_PROPOSED",
                "reason_codes": ["LOW_ATTENDANCE"],
                "evidence": ["attendance_percentage: 64.5"],
                "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
                "approval_required": True,
                "confidence_level": "HIGH",
                "mentor_email": "leak@example.test",
            }
        )


def test_allowed_reason_codes_is_low_attendance_only():
    assert ALLOWED_REASON_CODES == {"LOW_ATTENDANCE"}


# --- Semantic validation (validate_proposal_output) -------------------------


def test_success_round_trip_rebuilds_backend_evidence():
    facts = make_facts()
    validated = validate_proposal_output(valid_output(), facts)
    assert validated.reason_codes == ("LOW_ATTENDANCE",)
    assert validated.confidence_level == "HIGH"
    assert validated.plan_actions == (
        {"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3},
    )
    entries = list(validated.evidence_entries)
    assert len(entries) == 2
    by_label = {e["label"]: e for e in entries}
    # Typed value preserved: 64.5 stays float, 13 stays int (DEC-01).
    assert by_label["attendance_percentage"]["value"] == 64.5
    assert by_label["classes_attended"]["value"] == 13
    # Backend provenance — never model-supplied.
    for entry in entries:
        assert entry["source"] == "attendance_derived_state"
        assert datetime.fromisoformat(entry["timestamp"]) == NOW
        uuid.UUID(entry["id"])  # canonical UUID identity


def test_threshold_claim_allowed_with_rule_provenance():
    validated = validate_proposal_output(
        valid_output(evidence=["threshold: 75.0"]), make_facts()
    )
    threshold = [e for e in validated.evidence_entries if e["label"] == "threshold"]
    assert threshold and threshold[0]["source"] == "institution_rules"


def test_threshold_claim_refused_without_rule_row():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(evidence=["threshold: 75.0"]), make_facts(threshold=None)
        )
    assert excinfo.value.code == "EVIDENCE_UNVERIFIED"


def test_duplicate_claims_collapse_to_one_entry():
    validated = validate_proposal_output(
        valid_output(
            evidence=[
                "attendance_percentage: 64.5",
                "attendance_percentage: 64.5",
            ]
        ),
        make_facts(),
    )
    assert len(validated.evidence_entries) == 1


def test_invented_evidence_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(evidence=["student_gpa: 9.1"]), make_facts()
        )
    assert excinfo.value.code == "EVIDENCE_UNVERIFIED"


def test_manipulated_number_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(evidence=["attendance_percentage: 88.0"]), make_facts()
        )
    assert excinfo.value.code == "EVIDENCE_UNVERIFIED"


def test_approval_required_must_stay_true():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(valid_output(approval_required=False), make_facts())
    assert excinfo.value.code == "APPROVAL_REQUIRED_FALSE"


def test_unsupported_reason_code_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(
                reason_codes=["LOW_ATTENDANCE", "EXAM_APPROACHING"],
                evidence=["threshold: 75.0"],
            ),
            make_facts(),
        )
    assert excinfo.value.code == "UNSUPPORTED_REASON_CODE"


def test_empty_reason_codes_fail_at_schema_level():
    with pytest.raises(ValidationError):
        valid_output(reason_codes=[])


def test_unknown_subject_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(
                actions=[{"type": "ATTEND_CLASS", "subject": "PHYSICS", "count": 2}]
            ),
            make_facts(),
        )
    assert excinfo.value.code == "UNKNOWN_SUBJECT"


def test_count_exceeding_required_to_recover_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(
            valid_output(
                actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 9}]
            ),
            make_facts(required_to_recover=4),
        )
    assert excinfo.value.code == "COUNT_EXCEEDS_REQUIREMENT"


def test_count_allowed_when_requirement_unknown():
    validated = validate_proposal_output(
        valid_output(
            actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 9}]
        ),
        make_facts(required_to_recover=None),
    )
    assert validated.plan_actions[0]["count"] == 9


def test_no_risk_facts_refused():
    with pytest.raises(ProposalValidationError) as excinfo:
        validate_proposal_output(valid_output(), make_facts(risk_band=None))
    assert excinfo.value.code == "NO_RISK_FACTS"


def test_study_block_and_quiz_actions_pass_schema_dump():
    validated = validate_proposal_output(
        valid_output(
            actions=[
                {"type": "STUDY_BLOCK", "topic": "DBMS transactions", "duration_min": 45},
                {"type": "PRACTICE_QUIZ", "topic": "DBMS indexing"},
            ]
        ),
        make_facts(),
    )
    types = [a["type"] for a in validated.plan_actions]
    assert types == ["STUDY_BLOCK", "PRACTICE_QUIZ"]


# --- De-identified prompt context -------------------------------------------


def test_context_contains_no_direct_identifiers():
    user_content = build_proposal_messages(make_facts())[-1]["content"]
    for banned in ("name", "email", "roll", "phone", "student_id", "uuid"):
        assert banned not in user_content.lower()


def test_context_omits_threshold_when_absent():
    context = build_proposal_facts_context(make_facts(threshold=None))
    assert "threshold" not in context
    assert context["risk_subject"] == "DBMS"


# --- is_schema_valid hardening ----------------------------------------------


def test_is_schema_valid_rejects_empty_model_construct():
    assert is_schema_valid(AttendancePlanProposal.model_construct()) is None


def test_is_schema_valid_accepts_dict_and_instance():
    payload = valid_output()
    assert is_schema_valid(payload.model_dump()) is not None
    assert is_schema_valid(payload) is not None


# --- Specialist produce_proposal (MOCK LLM) ---------------------------------


@pytest.fixture
def mock_llm(monkeypatch):
    """Fresh MOCK-mode LLMService regardless of any local .env values.

    Never reads .env and never opens a network connection.
    """
    from types import SimpleNamespace

    previous = llm_module._llm_service
    llm_module._llm_service = None
    monkeypatch.setattr(
        llm_module,
        "settings",
        SimpleNamespace(
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


class FakeProposalTools:
    """Recording stand-in for ServiceBackedTools' proposal seam (no DB)."""

    def __init__(self, facts: AttendanceProposalFacts, *, fail_with: Exception | None = None):
        self.facts = facts
        self.fail_with = fail_with
        self.fact_calls: list[uuid.UUID] = []
        self.propose_calls: list[dict] = []

    async def read_attendance_facts(self, student_id):
        self.fact_calls.append(student_id)
        return self.facts

    async def propose_intervention_plan(self, **kwargs):
        self.propose_calls.append(kwargs)
        if self.fail_with is not None:
            raise self.fail_with
        return uuid.uuid4()


def fixture_key(facts: AttendanceProposalFacts) -> str:
    import json

    return json.dumps(build_proposal_facts_context(facts), sort_keys=True)


async def test_produce_proposal_success_round_trip(mock_llm):
    facts = make_facts()
    key = fixture_key(facts)
    mock_llm.mock_client.load_fixture(
        key,
        {
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
        },
    )
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    case_id = uuid.uuid4()
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=case_id
    )
    assert outcome.proposed is True
    assert outcome.plan_id is not None
    assert outcome.refusal_code is None
    assert outcome.reason_codes == ("LOW_ATTENDANCE",)
    assert len(tools.propose_calls) == 1
    call = tools.propose_calls[0]
    assert call["case_id"] == case_id
    assert call["reason_codes"] == ("LOW_ATTENDANCE",)
    assert call["plan_actions"][0]["type"] == "ATTEND_CLASS"
    assert len(call["evidence_entries"]) == 3
    assert all(e["source"] == "attendance_derived_state" for e in call["evidence_entries"])


async def test_conflict_quarantine_never_calls_llm_or_persists(mock_llm):
    facts = make_facts(has_data_conflict=True)
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "DATA_CONFLICT_QUARANTINE"
    assert mock_llm.mock_client._call_log == []
    assert tools.propose_calls == []


async def test_no_risk_facts_never_calls_llm(mock_llm):
    tools = FakeProposalTools(make_facts(risk_band=None))
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.refusal_code == "NO_RISK_FACTS"
    assert mock_llm.mock_client._call_log == []
    assert tools.propose_calls == []


async def test_missing_fixture_is_malformed_output(mock_llm):
    tools = FakeProposalTools(make_facts())
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.refusal_code == "MALFORMED_OUTPUT"
    assert tools.propose_calls == []


async def test_schema_rejected_fixture_is_malformed_output(mock_llm):
    facts = make_facts()
    mock_llm.mock_client.load_fixture(
        fixture_key(facts),
        {
            "decision": "PLAN_PROPOSED",
            "reason_codes": ["LOW_ATTENDANCE"],
            "evidence": ["attendance_percentage: 64.5"],
            "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
            "approval_required": True,
            "confidence_level": 0.95,  # float — A-06 violation
        },
    )
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.refusal_code == "MALFORMED_OUTPUT"
    assert tools.propose_calls == []


@pytest.mark.parametrize(
    ("fixture", "expected_code"),
    [
        ({"approval_required": False}, "APPROVAL_REQUIRED_FALSE"),
        (
            {
                "actions": [{"type": "ATTEND_CLASS", "subject": "PHYSICS", "count": 2}]
            },
            "UNKNOWN_SUBJECT",
        ),
        ({"evidence": ["student_gpa: 9.1"]}, "EVIDENCE_UNVERIFIED"),
        (
            {
                "reason_codes": ["LOW_ATTENDANCE", "EXAM_APPROACHING"],
                "evidence": ["threshold: 75.0"],
            },
            "UNSUPPORTED_REASON_CODE",
        ),
    ],
)
async def test_semantic_refusal_codes(mock_llm, fixture, expected_code):
    facts = make_facts()
    payload: dict = {
        "decision": "PLAN_PROPOSED",
        "reason_codes": ["LOW_ATTENDANCE"],
        "evidence": [
            "attendance_percentage: 64.5",
            "classes_attended: 13",
        ],
        "actions": [{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
        "approval_required": True,
        "confidence_level": "HIGH",
    }
    payload.update(fixture)
    mock_llm.mock_client.load_fixture(fixture_key(facts), payload)
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == expected_code
    assert tools.propose_calls == []


async def test_llm_outage_is_controlled_refusal():
    class BrokenLLM:
        mode = "mock"

        async def complete(self, messages, response_model=None, **kwargs):
            raise LLMRetryExhausted("provider down")

    tools = FakeProposalTools(make_facts())
    specialist = AttendanceSpecialist(tools=tools, llm=BrokenLLM())
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.refusal_code == "LLM_UNAVAILABLE"
    assert tools.propose_calls == []


async def test_initial_audit_failure_is_controlled_refusal(mock_llm):
    """06 §5 fail-closed (begin): when the pre-dispatch IN_PROGRESS row
    cannot be persisted the provider is never called — no model output, no
    plan write (refusal, fixture never evaluated)."""

    class ExplodingBeginSink:
        async def begin(self, start):
            raise RuntimeError("audit store offline")

        async def finish(self, attempt):
            raise AssertionError("finish must not run when begin failed")

    facts = make_facts()
    mock_llm.mock_client.load_fixture(fixture_key(facts), valid_output().model_dump())
    broken_service = LLMService(
        audit_sink=ExplodingBeginSink(), client=mock_llm.mock_client
    )
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=broken_service)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "AUDIT_PERSISTENCE_FAILED"
    assert tools.propose_calls == []  # nothing persisted without an audit row
    assert broken_service.mock_client._call_log == []  # provider never dispatched


async def test_terminal_audit_failure_is_controlled_refusal(mock_llm):
    """06 §5 fail-closed (finish): the model output exists but its terminal
    audit update failed — the unaudited result is never consumed and no
    plan write happens; the IN_PROGRESS start record remains."""

    class FailingFinishSink:
        def __init__(self):
            self.starts = []
            self.failed_finishes = []

        async def begin(self, start):
            self.starts.append(start)

        async def finish(self, attempt):
            self.failed_finishes.append(attempt)
            raise RuntimeError("audit store offline")

    facts = make_facts()
    mock_llm.mock_client.load_fixture(fixture_key(facts), valid_output().model_dump())
    sink = FailingFinishSink()
    broken_service = LLMService(audit_sink=sink, client=mock_llm.mock_client)
    tools = FakeProposalTools(facts)
    specialist = AttendanceSpecialist(tools=tools, llm=broken_service)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "AUDIT_PERSISTENCE_FAILED"
    assert tools.propose_calls == []
    assert len(broken_service.mock_client._call_log) == 1  # output was produced
    assert len(sink.starts) == 1  # committed pre-dispatch record remains
    assert len(sink.failed_finishes) == 1
    assert sink.failed_finishes[0].outcome == "SUCCESS"


async def test_domain_refusal_code_surfaces(mock_llm):
    facts = make_facts()
    mock_llm.mock_client.load_fixture(fixture_key(facts), valid_output().model_dump())
    tools = FakeProposalTools(
        facts,
        fail_with=CaseUnavailable("UNDECIDED_PROPOSAL_EXISTS", "already proposed"),
    )
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    outcome = await specialist.produce_proposal(
        student_id=uuid.uuid4(), case_id=uuid.uuid4()
    )
    assert outcome.proposed is False
    assert outcome.refusal_code == "UNDECIDED_PROPOSAL_EXISTS"


# --- Supervisor proposal-hook wiring -----------------------------------------


def make_event(event_type: str = EVENT_ATTENDANCE_RISK_WARNING) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={},
    )


class FakeSupervisorTools:
    def __init__(self, *, case_id: uuid.UUID | None = None, derived=None) -> None:
        self.case_id = case_id or uuid.uuid4()
        self.derived = derived or DerivedStateSummary(
            row_count=1, has_risk_band=True, has_data_conflict=False
        )
        self.calls: list[tuple] = []

    async def read_student_derived_state(self, student_id):
        self.calls.append(("read_student_derived_state", student_id))
        return self.derived

    async def read_open_cases(self, student_id):
        self.calls.append(("read_open_cases", student_id))
        return None

    async def create_intervention_case(self, *, student_id, trigger_event_id, urgency_band):
        self.calls.append(("create_intervention_case", student_id, urgency_band))
        return self.case_id


class FakeAttendance:
    async def assess(self, student_id):
        from app.agents.supervisor import AttendanceAssessment

        return AttendanceAssessment(
            available=True,
            explanation="Attend DBMS blocks.",
            reason_codes=("LOW_ATTENDANCE",),
            confidence_level="HIGH",
        )


class FakeProposal:
    def __init__(self, outcome: ProposalOutcome | None = None) -> None:
        self.outcome = outcome or ProposalOutcome(
            proposed=True,
            plan_id=uuid.uuid4(),
            reason_codes=("LOW_ATTENDANCE",),
            refusal_code=None,
        )
        self.calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def produce_proposal(self, *, student_id, case_id):
        self.calls.append((student_id, case_id))
        return self.outcome


def make_supervisor_with_proposal(proposal):
    tools = FakeSupervisorTools()
    supervisor = Supervisor(
        tools=tools,
        attendance_specialist=FakeAttendance(),
        proposal_specialist=proposal,
    )
    return supervisor, tools


async def test_attendance_route_invokes_proposal_with_resolved_case():
    proposal = FakeProposal()
    supervisor, tools = make_supervisor_with_proposal(proposal)
    run = await supervisor.handle(make_event())
    assert run.decision == DECISION_ROUTE
    assert run.target_agent == ATTENDANCE_AGENT
    assert len(proposal.calls) == 1
    student_id, case_id = proposal.calls[0]
    assert run.case_id == case_id
    assert student_id == run.student_id


async def test_proposal_specialist_none_keeps_route_only():
    tools = FakeSupervisorTools()
    supervisor = Supervisor(
        tools=tools,
        attendance_specialist=FakeAttendance(),
        proposal_specialist=None,
    )
    run = await supervisor.handle(make_event())
    assert run.decision == DECISION_ROUTE
    assert run.case_id is not None


async def test_intervention_route_other_events_never_invoke_proposal():
    """R5 scope: only PLAN_DECLINED (the replan trigger) joins the proposal
    hook on the intervention route. TASK_OVERDUE and friends stay route-only
    (no contracted proposal behavior for those events)."""
    proposal = FakeProposal()
    supervisor, tools = make_supervisor_with_proposal(proposal)
    run = await supervisor.handle(make_event(EVENT_TASK_OVERDUE))
    assert run.target_agent == INTERVENTION_AGENT
    assert proposal.calls == []


async def test_plan_declined_route_invokes_proposal():
    """R5 (§10.2 REPLAN_REQUIRED → PLAN_PROPOSED): the PLAN_DECLINED route
    invokes the proposal specialist so the agent can propose a new plan."""
    proposal = FakeProposal()
    supervisor, tools = make_supervisor_with_proposal(proposal)
    case_id = uuid.uuid4()
    event = DomainEvent(
        event_type=EVENT_PLAN_DECLINED,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={"case_id": str(case_id)},
    )
    run = await supervisor.handle(event)
    assert run.decision == DECISION_ROUTE
    assert run.target_agent == INTERVENTION_AGENT
    assert len(proposal.calls) == 1
    student_id, proposed_case_id = proposal.calls[0]
    assert proposed_case_id == case_id
    assert student_id == run.student_id
    assert run.case_id == case_id


async def test_plan_declined_specialist_none_stays_route_only():
    tools = FakeSupervisorTools()
    supervisor = Supervisor(
        tools=tools,
        attendance_specialist=FakeAttendance(),
        proposal_specialist=None,
    )
    event = DomainEvent(
        event_type=EVENT_PLAN_DECLINED,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={"case_id": str(uuid.uuid4())},
    )
    run = await supervisor.handle(event)
    assert run.target_agent == INTERVENTION_AGENT
    assert run.decision == DECISION_ROUTE


async def test_plan_declined_too_many_declines_keeps_route():
    """EC-AG-05 stop surfaces as a soft refusal: routing stands, the reason
    code is traceable, the case state is unchanged (06 §6)."""
    proposal = FakeProposal(
        ProposalOutcome(
            proposed=False,
            plan_id=None,
            reason_codes=(),
            refusal_code="TOO_MANY_DECLINES",
        )
    )
    supervisor, _ = make_supervisor_with_proposal(proposal)
    event = DomainEvent(
        event_type=EVENT_PLAN_DECLINED,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={"case_id": str(uuid.uuid4())},
    )
    run = await supervisor.handle(event)
    assert run.decision == DECISION_ROUTE
    assert run.target_agent == INTERVENTION_AGENT
    assert "TOO_MANY_DECLINES" in run.reason_codes
    assert run.human_review_required is False


async def test_proposal_conflict_refusal_escalates():
    proposal = FakeProposal(
        ProposalOutcome(
            proposed=False,
            plan_id=None,
            reason_codes=(),
            refusal_code="DATA_CONFLICT_QUARANTINE",
        )
    )
    supervisor, _ = make_supervisor_with_proposal(proposal)
    run = await supervisor.handle(make_event())
    assert run.decision == DECISION_ESCALATE
    assert run.human_review_required is True
    assert "DATA_CONFLICT_QUARANTINE" in run.reason_codes


async def test_proposal_soft_refusal_keeps_route():
    proposal = FakeProposal(
        ProposalOutcome(
            proposed=False,
            plan_id=None,
            reason_codes=(),
            refusal_code="LLM_UNAVAILABLE",
        )
    )
    supervisor, _ = make_supervisor_with_proposal(proposal)
    run = await supervisor.handle(make_event())
    assert run.decision == DECISION_ROUTE
    assert "LLM_UNAVAILABLE" in run.reason_codes
    assert run.human_review_required is False


# --- Boundaries (06 §0; Constitution A-01) ----------------------------------


def test_proposal_module_is_pure():
    source = (AGENTS_DIR / "proposal.py").read_text(encoding="utf-8")
    assert "import sqlalchemy" not in source
    assert "from sqlalchemy" not in source
    assert "import httpx" not in source
    assert "app.models" not in source


def test_attendance_specialist_still_has_no_sqlalchemy_or_http():
    source = (AGENTS_DIR / "attendance_specialist.py").read_text(encoding="utf-8")
    assert "import sqlalchemy" not in source
    assert "from sqlalchemy" not in source
    assert "import httpx" not in source
    assert "app.models" not in source


# --- EC-AG-05: consecutive student declines stop auto-generation --------------


def _lifecycle_case(status):
    from app.models.intervention import InterventionCase

    now = datetime.now(UTC)
    return InterventionCase(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        mentor_id=uuid.uuid4(),
        status=status,
        urgency_band="ATTENTION",
        opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _decided_plan(
    *, student_decision: str | None, days_ago: int, mentor_decision: str | None = None
):
    from app.models.intervention import InterventionPlan

    created = datetime.now(UTC) - timedelta(days=days_ago)
    return InterventionPlan(
        id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        created_by="SYSTEM_AGENT",
        status="DECLINED" if student_decision == "DECLINED" else "ACCEPTED",
        plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
        reason_codes=["LOW_ATTENDANCE"],
        evidence=[],
        student_decision=student_decision,
        mentor_decision=mentor_decision,
        created_at=created,
        updated_at=created,
    )


async def _propose_with_plans(case, plans):
    from unittest.mock import AsyncMock, MagicMock

    from app.services.plan_proposal_service import (
        PlanProposalError,
        propose_intervention_plan,
    )

    session = AsyncMock()
    session.add = MagicMock()
    try:
        result = await propose_intervention_plan(
            session,
            case=case,
            existing_plans=plans,
            reason_codes=["LOW_ATTENDANCE"],
            plan_actions=[{"type": "ATTEND_CLASS", "subject": "DBMS", "count": 3}],
            evidence_entries=[],
        )
    except PlanProposalError as exc:
        return session, exc
    return session, result


async def test_ec_ag_05_three_consecutive_declines_stop_generation():
    from app.models.enums import InterventionCaseStatus

    case = _lifecycle_case(InterventionCaseStatus.REPLAN_REQUIRED)
    plans = [
        _decided_plan(student_decision="DECLINED", days_ago=1),
        _decided_plan(student_decision="DECLINED", days_ago=8),
        _decided_plan(student_decision="DECLINED", days_ago=15),
    ]
    session, outcome = await _propose_with_plans(case, plans)
    assert getattr(outcome, "code", None) == "TOO_MANY_DECLINES"
    assert case.status == InterventionCaseStatus.REPLAN_REQUIRED
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


async def test_ec_ag_05_two_declines_still_allows_generation():
    from app.models.enums import InterventionCaseStatus

    case = _lifecycle_case(InterventionCaseStatus.REPLAN_REQUIRED)
    plans = [
        _decided_plan(student_decision="DECLINED", days_ago=1),
        _decided_plan(student_decision="DECLINED", days_ago=8),
        _decided_plan(student_decision="ACCEPTED", days_ago=20),
    ]
    session, outcome = await _propose_with_plans(case, plans)
    assert getattr(outcome, "code", None) is None
    assert outcome.case_status == "PLAN_PROPOSED"
    assert case.status == InterventionCaseStatus.PLAN_PROPOSED
    session.commit.assert_awaited_once()


async def test_ec_ag_05_customization_breaks_the_decline_streak():
    from app.models.enums import InterventionCaseStatus

    case = _lifecycle_case(InterventionCaseStatus.REPLAN_REQUIRED)
    plans = [
        _decided_plan(student_decision="DECLINED", days_ago=1),
        _decided_plan(student_decision="CUSTOMIZED", days_ago=8),
        _decided_plan(student_decision="DECLINED", days_ago=15),
        _decided_plan(student_decision="DECLINED", days_ago=22),
    ]
    session, outcome = await _propose_with_plans(case, plans)
    assert getattr(outcome, "code", None) is None
    assert outcome.case_status == "PLAN_PROPOSED"


async def test_ec_ag_05_mentor_rejection_does_not_count_as_student_decline():
    """EC-AG-05 counts STUDENT declines only: a plan the student accepted
    (then the mentor rejected) breaks the streak."""
    from app.models.enums import InterventionCaseStatus

    case = _lifecycle_case(InterventionCaseStatus.REPLAN_REQUIRED)
    plans = [
        _decided_plan(
            student_decision="DECLINED",
            days_ago=1,
        ),
        _decided_plan(
            student_decision="ACCEPTED", days_ago=8, mentor_decision="REJECTED"
        ),
        _decided_plan(student_decision="DECLINED", days_ago=15),
        _decided_plan(student_decision="DECLINED", days_ago=22),
    ]
    session, outcome = await _propose_with_plans(case, plans)
    assert getattr(outcome, "code", None) is None
    assert outcome.case_status == "PLAN_PROPOSED"
