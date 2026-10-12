# tests/test_supervisor.py
# R2 Supervisor wiring tests (11_ROADMAP R2): deterministic routing per
# 06_AGENT_SPEC §1, case-ensure on the attendance risk path, attendance
# specialist MOCK round-trip, registration idempotence, failure isolation,
# and agent-module boundaries (no SQL / no provider / no LLM in routing).
# Unit tests use fakes for tools and the specialist — no database, no network.

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import app.services.llm_service as llm_module
from app.agents.attendance_specialist import (
    AttendanceExplanation,
    AttendanceSpecialist,
    build_attendance_messages,
)
from app.agents.supervisor import (
    ATTENDANCE_AGENT,
    DECISION_ESCALATE,
    DECISION_ROUTE,
    EVENT_ASSESSMENT_MISSING_URGENT,
    EVENT_ASSESSMENT_TREND_DECLINING,
    EVENT_ATTENDANCE_RISK_CRITICAL,
    EVENT_ATTENDANCE_RISK_WARNING,
    EVENT_EXAM_APPROACHING,
    EVENT_MENTOR_FOLLOWUP_DUE,
    EVENT_PLAN_DECLINED,
    EVENT_TASK_OVERDUE,
    INTERVENTION_AGENT,
    LEARNING_AGENT,
    SUPERVISOR_TRIGGERS,
    AttendanceAssessment,
    CaseUnavailable,
    DerivedStateSummary,
    Supervisor,
    initial_urgency_band,
)
from app.core.events import DomainEvent, EventBus
from app.services.llm_service import (
    InMemoryLLMAuditSink,
    LLMRetryExhausted,
    LLMService,
    get_llm_service,
)

AGENTS_DIR = Path(__file__).resolve().parents[1] / "app" / "agents"


def make_event(
    event_type: str = EVENT_ATTENDANCE_RISK_WARNING,
    payload: dict | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload=payload if payload is not None else {},
    )


class FakeTools:
    """Recording stand-in for SupervisorTools (no DB)."""

    def __init__(
        self,
        *,
        case_id: uuid.UUID | None = None,
        open_case_id: uuid.UUID | None = None,
        derived: DerivedStateSummary | None = None,
        mentor_assigned: bool = True,
        fail_with: Exception | None = None,
    ) -> None:
        self.case_id = case_id or uuid.uuid4()
        self.open_case_id = open_case_id
        self.derived = derived or DerivedStateSummary(
            row_count=0, has_risk_band=False, has_data_conflict=False
        )
        self.mentor_assigned = mentor_assigned
        self.fail_with = fail_with
        self.calls: list[tuple] = []

    async def read_student_derived_state(self, student_id):
        self.calls.append(("read_student_derived_state", student_id))
        if self.fail_with is not None:
            raise self.fail_with
        return self.derived

    async def read_open_cases(self, student_id):
        self.calls.append(("read_open_cases", student_id))
        return self.open_case_id

    async def create_intervention_case(self, *, student_id, trigger_event_id, urgency_band):
        self.calls.append(
            ("create_intervention_case", student_id, trigger_event_id, urgency_band)
        )
        if not self.mentor_assigned:
            raise CaseUnavailable("NO_MENTOR_ASSIGNED", "no mentor")
        return self.case_id


class FakeSpecialist:
    def __init__(self, assessment: AttendanceAssessment | None = None) -> None:
        self.assessment = assessment or AttendanceAssessment(
            available=True,
            explanation="Attend DBMS blocks to recover.",
            reason_codes=("LOW_ATTENDANCE",),
            confidence_level="HIGH",
        )
        self.calls: list[uuid.UUID] = []

    async def assess(self, student_id):
        self.calls.append(student_id)
        return self.assessment


def make_supervisor(tools=None, specialist=None) -> tuple[Supervisor, FakeTools, FakeSpecialist]:
    tools = tools or FakeTools()
    specialist = specialist or FakeSpecialist()
    return Supervisor(tools=tools, attendance_specialist=specialist), tools, specialist


# --- Routing table (06 §1) -------------------------------------------------


async def test_attendance_risk_events_route_to_attendance_agent():
    for event_type in (EVENT_ATTENDANCE_RISK_WARNING, EVENT_ATTENDANCE_RISK_CRITICAL):
        supervisor, _, specialist = make_supervisor()
        run = await supervisor.handle(make_event(event_type))
        assert run.decision == DECISION_ROUTE
        assert run.target_agent == ATTENDANCE_AGENT
        assert run.human_review_required is False
        assert len(specialist.calls) == 1


async def test_case_created_only_on_attendance_risk_path():
    supervisor, tools, specialist = make_supervisor()
    await supervisor.handle(make_event(EVENT_ATTENDANCE_RISK_WARNING))
    creates = [c for c in tools.calls if c[0] == "create_intervention_case"]
    assert len(creates) == 1
    assert creates[0][3] == "ATTENTION"  # urgency band
    assert specialist.calls  # specialist invoked after case-ensure


async def test_critical_event_maps_to_urgent_band():
    supervisor, tools, _ = make_supervisor()
    run = await supervisor.handle(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    creates = [c for c in tools.calls if c[0] == "create_intervention_case"]
    assert creates[0][3] == "URGENT"
    assert run.evidence["urgency_band"] == "URGENT"


def test_initial_urgency_band_mapping():
    assert initial_urgency_band(EVENT_ATTENDANCE_RISK_CRITICAL) == "URGENT"
    assert initial_urgency_band(EVENT_ATTENDANCE_RISK_WARNING) == "ATTENTION"


async def test_trend_declining_routes_to_learning_agent_no_case_write():
    supervisor, tools, specialist = make_supervisor()
    run = await supervisor.handle(make_event(EVENT_ASSESSMENT_TREND_DECLINING))
    assert run.target_agent == LEARNING_AGENT
    assert not any(c[0] == "create_intervention_case" for c in tools.calls)
    assert specialist.calls == []  # only attendance stub exists in R2


@pytest.mark.parametrize(
    "event_type",
    [
        EVENT_ASSESSMENT_MISSING_URGENT,
        EVENT_TASK_OVERDUE,
        EVENT_MENTOR_FOLLOWUP_DUE,
    ],
)
async def test_intervention_routes_without_case_write(event_type):
    supervisor, tools, _ = make_supervisor()
    run = await supervisor.handle(make_event(event_type))
    assert run.target_agent == INTERVENTION_AGENT
    assert run.decision == DECISION_ROUTE
    assert not any(c[0] == "create_intervention_case" for c in tools.calls)


async def test_plan_declined_uses_payload_case_id():
    case_id = uuid.uuid4()
    supervisor, tools, _ = make_supervisor()
    run = await supervisor.handle(
        make_event(EVENT_PLAN_DECLINED, payload={"case_id": str(case_id)})
    )
    assert run.target_agent == INTERVENTION_AGENT
    assert run.case_id == case_id
    assert not any(c[0] == "create_intervention_case" for c in tools.calls)
    assert not any(c[0] == "read_open_cases" for c in tools.calls)


async def test_intervention_route_without_payload_reads_open_case():
    open_case = uuid.uuid4()
    supervisor, tools, _ = make_supervisor(tools=FakeTools(open_case_id=open_case))
    run = await supervisor.handle(make_event(EVENT_TASK_OVERDUE))
    assert run.case_id == open_case
    assert any(c[0] == "read_open_cases" for c in tools.calls)


async def test_exam_approaching_with_risk_routes_attendance():
    tools = FakeTools(
        derived=DerivedStateSummary(row_count=2, has_risk_band=True, has_data_conflict=False)
    )
    supervisor, _, specialist = make_supervisor(tools=tools)
    run = await supervisor.handle(make_event(EVENT_EXAM_APPROACHING))
    assert run.target_agent == ATTENDANCE_AGENT
    assert specialist.calls


async def test_exam_approaching_without_risk_routes_intervention():
    supervisor, tools, specialist = make_supervisor()
    run = await supervisor.handle(make_event(EVENT_EXAM_APPROACHING))
    assert run.target_agent == INTERVENTION_AGENT
    assert specialist.calls == []


async def test_exam_approaching_data_conflict_escalates():
    tools = FakeTools(
        derived=DerivedStateSummary(row_count=1, has_risk_band=False, has_data_conflict=True)
    )
    supervisor, _, specialist = make_supervisor(tools=tools)
    run = await supervisor.handle(make_event(EVENT_EXAM_APPROACHING))
    assert run.decision == DECISION_ESCALATE
    assert run.human_review_required is True
    assert "DATA_CONFLICT_QUARANTINE" in run.reason_codes
    assert specialist.calls == []


@pytest.mark.parametrize(
    "event_type",
    [
        "INTERVENTION_PLAN_APPROVED",  # ADR-002 §5 fall-through
        "PLAN_ACCEPTED",
        "ATTENDANCE_UPDATED",
        "TOTALLY_UNKNOWN_EVENT",
    ],
)
async def test_unmatched_events_escalate_to_human_review(event_type):
    supervisor, tools, specialist = make_supervisor()
    run = await supervisor.handle(make_event(event_type))
    assert run.decision == DECISION_ESCALATE
    assert run.target_agent is None
    assert run.human_review_required is True
    assert "UNMATCHED_EVENT" in run.reason_codes
    assert tools.calls == []
    assert specialist.calls == []


# --- Case-ensure failure paths ---------------------------------------------


async def test_no_mentor_escalates_without_specialist():
    tools = FakeTools(mentor_assigned=False)
    supervisor, _, specialist = make_supervisor(tools=tools)
    run = await supervisor.handle(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    assert run.decision == DECISION_ESCALATE
    assert run.human_review_required is True
    assert "NO_MENTOR_ASSIGNED" in run.reason_codes
    assert run.case_id is None
    assert specialist.calls == []


# --- Attendance specialist stub + MOCK LLM ---------------------------------


@pytest.fixture
def mock_llm(monkeypatch):
    """Fresh MOCK-mode LLMService regardless of any local .env values.

    Never reads .env and never opens a network connection: the module-level
    settings reference is patched to a mock-mode stub before construction.
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
    service = get_llm_service(audit_sink=InMemoryLLMAuditSink())  # MOCK, no network/DB
    yield service
    llm_module._llm_service = previous


async def test_specialist_mock_round_trip(mock_llm):
    state = DerivedStateSummary(row_count=1, has_risk_band=True, has_data_conflict=False)
    tools = FakeTools(derived=state)
    messages = build_attendance_messages(state)
    mock_llm.mock_client.load_fixture(
        messages[-1]["content"],
        {
            "explanation": "Attendance is below threshold; attend 3 more classes.",
            "reason_codes": ["LOW_ATTENDANCE"],
            "confidence_level": "HIGH",
        },
    )
    specialist = AttendanceSpecialist(tools=tools, llm=mock_llm)
    result = await specialist.assess(uuid.uuid4())
    assert result.available is True
    assert result.confidence_level == "HIGH"
    assert result.reason_codes == ("LOW_ATTENDANCE",)
    assert result.explanation  # fixture explanation passed through untouched
    # MOCK client recorded the call deterministically (no network).
    assert len(mock_llm.mock_client._call_log) == 1


async def test_specialist_missing_fixture_is_unavailable(mock_llm):
    specialist = AttendanceSpecialist(tools=FakeTools(), llm=mock_llm)
    result = await specialist.assess(uuid.uuid4())
    assert result.available is False
    assert result.explanation is None


async def test_specialist_schema_rejection_is_unavailable(mock_llm):
    state = DerivedStateSummary(row_count=1, has_risk_band=True, has_data_conflict=False)
    messages = build_attendance_messages(state)
    # confidence_level as a raw float violates the A-06 enum contract.
    mock_llm.mock_client.load_fixture(
        messages[-1]["content"],
        {
            "explanation": "ok",
            "reason_codes": ["LOW_ATTENDANCE"],
            "confidence_level": 0.9,
        },
    )
    specialist = AttendanceSpecialist(tools=FakeTools(derived=state), llm=mock_llm)
    result = await specialist.assess(uuid.uuid4())
    assert result.available is False  # rejected, never coerced (DM-LLM01)


async def test_specialist_llm_unavailable_degrades_gracefully(mock_llm):
    class BrokenLLM:
        mode = "mock"

        async def complete(self, messages, response_model=None, **kwargs):
            raise LLMRetryExhausted("provider down")

    specialist = AttendanceSpecialist(tools=FakeTools(), llm=BrokenLLM())
    result = await specialist.assess(uuid.uuid4())
    assert result.available is False


async def test_specialist_audit_failure_is_unavailable(mock_llm):
    """06 §5 fail-closed: when the attempt audit row cannot be persisted
    (pre-dispatch begin fails) the explanation is unavailable — no
    unrecorded LLM output is consumed."""

    class ExplodingBeginSink:
        async def begin(self, start):
            raise RuntimeError("audit store offline")

        async def finish(self, attempt):
            raise AssertionError("finish must not run when begin failed")

    broken_service = LLMService(
        audit_sink=ExplodingBeginSink(), client=mock_llm.mock_client
    )
    specialist = AttendanceSpecialist(tools=FakeTools(), llm=broken_service)
    result = await specialist.assess(uuid.uuid4())
    assert result.available is False
    assert result.explanation is None


async def test_supervisor_routing_survives_specialist_llm_outage(mock_llm):
    """LLM-07: routing stays deterministic when the LLM is down (06 §6)."""

    class BrokenLLM:
        mode = "mock"

        async def complete(self, messages, response_model=None, **kwargs):
            raise LLMRetryExhausted("provider down")

    tools = FakeTools()
    specialist = AttendanceSpecialist(tools=tools, llm=BrokenLLM())
    supervisor = Supervisor(tools=tools, attendance_specialist=specialist)
    run = await supervisor.handle(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    assert run.decision == DECISION_ROUTE
    assert run.target_agent == ATTENDANCE_AGENT
    assert "LLM_UNAVAILABLE" in run.reason_codes
    assert run.human_review_required is False


async def test_facts_contain_no_direct_identifiers():
    state = DerivedStateSummary(row_count=3, has_risk_band=True, has_data_conflict=False)
    user_content = build_attendance_messages(state)[-1]["content"]
    for banned in ("name", "email", "roll", "phone"):
        assert banned not in user_content.lower()


# --- Bus wiring, ordering, isolation, registration --------------------------


async def test_real_bus_awaits_supervisor_handler_inline():
    supervisor, tools, specialist = make_supervisor()
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    await bus.publish(make_event(EVENT_ATTENDANCE_RISK_WARNING))
    # Inline awaited: effects are visible the moment publish() returns.
    assert specialist.calls
    assert any(c[0] == "create_intervention_case" for c in tools.calls)


async def test_supervisor_ignores_unsubscribed_event_types():
    supervisor, _, specialist = make_supervisor()
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    await bus.publish(make_event("PLAN_ACCEPTED"))  # not a Supervisor trigger
    assert specialist.calls == []


async def test_ensure_subscribed_is_idempotent_per_bus():
    supervisor, tools, specialist = make_supervisor()
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    supervisor.ensure_subscribed(bus)
    supervisor.ensure_subscribed(bus)
    assert bus.subscriber_count(EVENT_ATTENDANCE_RISK_WARNING) == 1
    await bus.publish(make_event(EVENT_ATTENDANCE_RISK_WARNING))
    assert len(specialist.calls) == 1


async def test_unexpected_tool_failure_is_isolated_from_producer_and_peers():
    supervisor, _, _ = make_supervisor(tools=FakeTools(fail_with=RuntimeError("db down")))
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    peer_received = []

    async def peer(event):
        peer_received.append(event)

    # Peer subscribed to a different type — must never be affected.
    bus.subscribe("INTERVENTION_PLAN_APPROVED", peer)
    # Must not raise: the bus isolates handler failures from the producer.
    await bus.publish(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    assert peer_received == []


async def test_supervisor_failure_does_not_block_same_type_peer():
    supervisor, _, _ = make_supervisor(tools=FakeTools(fail_with=RuntimeError("db down")))
    bus = EventBus()
    supervisor.ensure_subscribed(bus)
    peer_received = []

    async def peer(event):
        peer_received.append(event)

    bus.subscribe(EVENT_ATTENDANCE_RISK_CRITICAL, peer)
    await bus.publish(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    assert len(peer_received) == 1


def test_trigger_names_match_catalog_exactly():
    assert set(SUPERVISOR_TRIGGERS) == {
        EVENT_ATTENDANCE_RISK_WARNING,
        EVENT_ATTENDANCE_RISK_CRITICAL,
        EVENT_ASSESSMENT_TREND_DECLINING,
        EVENT_ASSESSMENT_MISSING_URGENT,
        EVENT_EXAM_APPROACHING,
        EVENT_TASK_OVERDUE,
        EVENT_PLAN_DECLINED,
        EVENT_MENTOR_FOLLOWUP_DUE,
    }


async def test_run_evidence_and_reasons_are_scalar_only():
    supervisor, _, _ = make_supervisor()
    run = await supervisor.handle(make_event(EVENT_ATTENDANCE_RISK_CRITICAL))
    for value in run.evidence.values():
        assert value is None or isinstance(value, str)
    assert run.reason_codes  # traceable to the originating event type


# --- Boundaries (06 §0/§1; Constitution A-01) ------------------------------


def test_agent_modules_have_no_sqlalchemy_or_http_client_imports():
    for name in ("supervisor.py", "attendance_specialist.py"):
        source = (AGENTS_DIR / name).read_text(encoding="utf-8")
        assert "import sqlalchemy" not in source, name
        assert "from sqlalchemy" not in source, name
        assert "import httpx" not in source, name
        assert "app.models" not in source, name  # pure agent boundary
    # tools.py is the sanctioned service/DB seam (06 §1 tool implementations);
    # it may use SQLAlchemy but never an HTTP/provider client.
    tools_source = (AGENTS_DIR / "tools.py").read_text(encoding="utf-8")
    assert "import httpx" not in tools_source
    assert "openrouter" not in tools_source.lower()


def test_supervisor_module_never_touches_the_llm():
    source = (AGENTS_DIR / "supervisor.py").read_text(encoding="utf-8")
    assert "llm_service" not in source
    assert "LLMService" not in source


def test_attendance_explanation_rejects_float_confidence():
    with pytest.raises(Exception):
        AttendanceExplanation.model_validate(
            {
                "explanation": "x",
                "reason_codes": [],
                "confidence_level": 0.9,
            }
        )


# --- App lifespan registration ----------------------------------------------


def test_lifespan_registers_supervisor_once_across_restarts():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app):
        pass
    with TestClient(app):
        pass

    bus = app.state.event_bus
    assert bus.subscriber_count(EVENT_ATTENDANCE_RISK_WARNING) == 1
    assert bus.subscriber_count(EVENT_TASK_OVERDUE) == 1
    assert app.state.supervisor is not None
