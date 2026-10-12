# tests/test_llm_audit.py
# DM-LLM01 per-attempt LLM audit metadata (06 §5, 07 §4, 11_ROADMAP C):
# frozen field set, outcome/failure_reason taxonomy, bounded-retry semantics,
# fail-closed persistence, and prompt-content exclusion. Network-free
# (httpx.MockTransport) and database-free (in-memory / failing sinks).

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

import app.services.llm_service as llm_module
from app.services.llm_service import (
    InMemoryLLMAuditSink,
    LLMAttemptRecord,
    LLMAttemptStart,
    LLMAuditError,
    LLMRetryExhausted,
    LLMSchemaError,
    LLMService,
    LLMUnavailableError,
    OpenRouterClient,
    SqlLLMAuditSink,
    get_llm_service,
)

# Distinctive markers: must never appear in any persisted audit field.
SYSTEM_PROMPT_MARK = "SYSTEM_PROMPT_DO_NOT_PERSIST"
USER_PROMPT_MARK = "USER_PROMPT_DO_NOT_PERSIST"

# The frozen per-attempt field set (06 §5 lines 292-295 + DM-LLM01 audit set).
# `id` is the row identity shared between the pre-dispatch start record and
# its terminal update — it is schema identity, not spec metadata.
FROZEN_FIELDS = {
    "request_id",
    "caller_agent",
    "prompt_version",
    "response_schema_version",
    "provider",
    "model",
    "attempt",
    "outcome",
    "failure_reason",
    "latency_ms",
    "input_token_count",
    "output_token_count",
    "created_at",
}
START_FIELDS = {
    "id",
    "request_id",
    "caller_agent",
    "prompt_version",
    "response_schema_version",
    "provider",
    "model",
    "attempt",
    "created_at",
}


class DemoOutput(BaseModel):
    value: str


def _messages(content: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT_MARK},
        {"role": "user", "content": content},
    ]


def _settings_stub(provider: str = "mock") -> SimpleNamespace:
    return SimpleNamespace(
        llm_provider=provider,
        llm_api_key="",
        llm_model="openai/gpt-4o-mini",
        llm_max_retries=1,
        llm_backoff_base=0.0,
        llm_timeout=1.0,
    )


@pytest.fixture
def mock_service(monkeypatch):
    """Fresh MOCK-mode singleton with an in-memory audit sink (no network/DB)."""
    previous = llm_module._llm_service
    llm_module._llm_service = None
    monkeypatch.setattr(llm_module, "settings", _settings_stub("mock"))
    sink = InMemoryLLMAuditSink()
    service = get_llm_service(audit_sink=sink)
    yield service, sink
    llm_module._llm_service = previous


def _openrouter_service(
    sink: InMemoryLLMAuditSink | ObservingFailingSink,
    handler,
    *,
    max_retries: int = 1,
) -> LLMService:
    client = OpenRouterClient(
        api_key="test-key",
        model="openai/gpt-4o-mini",
        max_retries=max_retries,
        backoff_base=0.0,
        timeout=1.0,
        transport=httpx.MockTransport(handler),
    )
    return LLMService(audit_sink=sink, client=client)


def _completion(content: str, usage: dict | None = None) -> httpx.Response:
    body: dict = {"choices": [{"message": {"content": content}}]}
    if usage is not None:
        body["usage"] = usage
    return httpx.Response(200, json=body)


def _make_record(**overrides) -> LLMAttemptRecord:
    fields = dict(
        id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        caller_agent="attendance_specialist",
        prompt_version=None,
        response_schema_version="DemoOutput",
        provider="mock",
        model="mock-fixture",
        attempt=1,
        outcome="SUCCESS",
        failure_reason=None,
        latency_ms=1,
        input_token_count=None,
        output_token_count=None,
        created_at=datetime.now(UTC),
    )
    fields.update(overrides)
    return LLMAttemptRecord(**fields)


def _make_start(**overrides) -> LLMAttemptStart:
    fields = dict(
        id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        caller_agent="attendance_specialist",
        prompt_version=None,
        response_schema_version="DemoOutput",
        provider="mock",
        model="mock-fixture",
        attempt=1,
        created_at=datetime.now(UTC),
    )
    fields.update(overrides)
    return LLMAttemptStart(**fields)


class ExplodingSink:
    """Audit store offline at BEGIN — the provider must never be called."""

    async def begin(self, start: LLMAttemptStart) -> None:
        raise RuntimeError("audit store offline")

    async def finish(self, attempt: LLMAttemptRecord) -> None:
        raise AssertionError("finish must not run when begin failed")


class ObservingFailingSink:
    """Begin commits (IN_PROGRESS recorded), terminal update fails.

    Models the honest gap of any durable-write failure: the attempt ran
    (or its result was produced) but its terminal outcome could not be
    persisted — the IN_PROGRESS start record remains observable, and the
    result must never be consumed (06 §5 fail-closed).
    """

    def __init__(self) -> None:
        self.starts: list[LLMAttemptStart] = []
        self.failed_finishes: list[LLMAttemptRecord] = []

    async def begin(self, start: LLMAttemptStart) -> None:
        self.starts.append(start)

    async def finish(self, attempt: LLMAttemptRecord) -> None:
        self.failed_finishes.append(attempt)
        raise RuntimeError("audit store offline")


# --- MOCK-mode records -------------------------------------------------------


async def test_mock_success_records_frozen_metadata(mock_service):
    import dataclasses

    service, sink = mock_service
    service.mock_client.load_fixture(USER_PROMPT_MARK, {"value": "v"})
    result = await service.complete(
        _messages(USER_PROMPT_MARK),
        response_model=DemoOutput,
        caller_agent="attendance_specialist",
        prompt_version="attendance.proposal.v1",
    )
    assert result.value == "v"
    assert len(sink.records) == 1
    rec = sink.records[0]

    # Exactly the frozen 06 §5 field set + row identity — no prompt field.
    assert {f.name for f in dataclasses.fields(rec)} == FROZEN_FIELDS | {"id"}
    assert isinstance(rec.request_id, uuid.UUID)
    assert rec.caller_agent == "attendance_specialist"
    assert rec.prompt_version == "attendance.proposal.v1"
    assert rec.response_schema_version == "DemoOutput"
    assert rec.provider == "mock"
    assert rec.model == "mock-fixture"
    assert rec.attempt == 1
    assert rec.outcome == "SUCCESS"
    assert rec.failure_reason is None
    assert rec.latency_ms >= 0
    assert rec.input_token_count is None  # MOCK reports no usage — never fabricated
    assert rec.output_token_count is None
    assert rec.created_at.tzinfo is not None

    # Pre-dispatch record committed before the fixture was evaluated, and
    # the terminal update landed on that same row identity.
    assert len(sink.starts) == 1
    start = sink.starts[0]
    assert {f.name for f in dataclasses.fields(start)} == START_FIELDS
    assert start.id == rec.id
    assert start.request_id == rec.request_id
    assert start.attempt == 1
    assert start.provider == "mock"
    assert start.model == "mock-fixture"  # IN_PROGRESS row never claims a real model
    assert start.created_at == rec.created_at  # creation time never rewritten


async def test_mock_fixture_miss_is_schema_rejected(mock_service):
    service, sink = mock_service
    with pytest.raises(LLMSchemaError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
            prompt_version=None,
        )
    assert len(sink.records) == 1
    rec = sink.records[0]
    assert rec.outcome == "SCHEMA_REJECTED"
    assert rec.failure_reason == "invalid_structured_output"
    assert rec.prompt_version is None  # propagation-or-NULL contract


async def test_mock_invalid_fixture_is_schema_rejected(mock_service):
    service, sink = mock_service
    service.mock_client.load_fixture(USER_PROMPT_MARK, {})  # missing required field
    with pytest.raises(LLMSchemaError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    rec = sink.records[0]
    assert rec.outcome == "SCHEMA_REJECTED"
    assert rec.failure_reason == "invalid_structured_output"


async def test_attempt_records_never_contain_prompt_content(mock_service):
    service, sink = mock_service
    service.mock_client.load_fixture(USER_PROMPT_MARK, {"value": "v"})
    await service.complete(
        _messages(USER_PROMPT_MARK),
        response_model=DemoOutput,
        caller_agent="attendance_specialist",
        prompt_version="attendance.proposal.v1",
    )
    blob = repr(sink.starts[0]) + repr(sink.records[0])
    assert SYSTEM_PROMPT_MARK not in blob
    assert USER_PROMPT_MARK not in blob


async def test_missing_caller_agent_is_rejected(mock_service):
    service, _ = mock_service
    service.mock_client.load_fixture(USER_PROMPT_MARK, {"value": "v"})
    with pytest.raises(ValueError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="",
        )


async def test_default_sink_is_sql_fail_closed(monkeypatch):
    monkeypatch.setattr(llm_module, "settings", _settings_stub("mock"))
    service = LLMService()
    assert isinstance(service._audit_sink, SqlLLMAuditSink)
    await service.close()


# --- Fail-closed persistence -------------------------------------------------


async def test_initial_audit_failure_prevents_provider_dispatch(mock_service):
    """Requirement: if the pre-dispatch IN_PROGRESS row cannot be committed,
    the provider is never called (MOCK fixture never evaluated)."""
    service_mock, _ = mock_service
    service = LLMService(audit_sink=ExplodingSink(), client=service_mock.mock_client)
    service.mock_client.load_fixture(USER_PROMPT_MARK, {"value": "v"})
    with pytest.raises(LLMAuditError) as excinfo:
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    # Original persistence error kept as the cause; no dispatch ever ran.
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert service.mock_client._call_log == []


async def test_terminal_audit_failure_after_mock_success_is_not_consumed(mock_service):
    """Requirement: IN_PROGRESS committed, fixture/model output produced,
    terminal update fails → LLMAuditError, nothing consumed, and the
    IN_PROGRESS start record remains observable."""
    service_mock, _ = mock_service
    sink = ObservingFailingSink()
    service = LLMService(audit_sink=sink, client=service_mock.mock_client)
    service.mock_client.load_fixture(USER_PROMPT_MARK, {"value": "v"})
    with pytest.raises(LLMAuditError) as excinfo:
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert len(service.mock_client._call_log) == 1  # output was produced
    assert len(sink.starts) == 1  # the committed pre-dispatch record
    assert len(sink.failed_finishes) == 1
    assert sink.failed_finishes[0].outcome == "SUCCESS"
    assert sink.failed_finishes[0].id == sink.starts[0].id


async def test_sql_sink_wraps_begin_persistence_errors_as_audit_error():
    class BrokenSessionFactory:
        async def __aenter__(self):
            raise ConnectionError("database unreachable")

        async def __aexit__(self, *exc_info):
            return False

    sink = SqlLLMAuditSink(session_factory=BrokenSessionFactory)
    with pytest.raises(LLMAuditError):
        await sink.begin(_make_start())


async def test_sql_sink_wraps_finish_persistence_errors_as_audit_error():
    class BrokenSessionFactory:
        async def __aenter__(self):
            raise ConnectionError("database unreachable")

        async def __aexit__(self, *exc_info):
            return False

    sink = SqlLLMAuditSink(session_factory=BrokenSessionFactory)
    with pytest.raises(LLMAuditError):
        await sink.finish(_make_record())


async def test_sql_sink_finish_requires_the_pre_committed_row():
    """Terminal update must fail closed when the IN_PROGRESS row is absent —
    an outcome is never silently recorded against a missing start record."""

    class EmptySessionFactory:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, model, row_id):
            return None

        async def add(self, obj):  # pragma: no cover - never reached
            raise AssertionError("finish must not insert rows")

        async def commit(self):  # pragma: no cover - never reached
            raise AssertionError("finish must not commit without a row")

    sink = SqlLLMAuditSink(session_factory=EmptySessionFactory)
    with pytest.raises(LLMAuditError):
        await sink.finish(_make_record())


# --- LIVE (OpenRouter) taxonomy ----------------------------------------------


async def test_openrouter_success_records_usage_tokens():
    sink = InMemoryLLMAuditSink()

    def handler(request: httpx.Request) -> httpx.Response:
        return _completion(
            json.dumps({"value": "v"}),
            usage={"prompt_tokens": 13, "completion_tokens": 7},
        )

    service = _openrouter_service(sink, handler)
    result = await service.complete(
        _messages(USER_PROMPT_MARK),
        response_model=DemoOutput,
        caller_agent="attendance_specialist",
    )
    assert result.value == "v"
    rec = sink.records[0]
    assert rec.outcome == "SUCCESS"
    assert rec.failure_reason is None
    assert rec.provider == "openrouter"
    assert rec.model == "openai/gpt-4o-mini"
    assert rec.attempt == 1
    assert rec.input_token_count == 13
    assert rec.output_token_count == 7
    # Pre-dispatch row committed before the HTTP call, on the same identity.
    assert len(sink.starts) == 1
    assert sink.starts[0].provider == "openrouter"
    assert sink.starts[0].id == rec.id
    await service.close()


async def test_openrouter_timeout_retries_then_succeeds_sharing_request_id():
    sink = InMemoryLLMAuditSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectTimeout("simulated timeout")
        return _completion(json.dumps({"value": "v"}))

    service = _openrouter_service(sink, handler)
    result = await service.complete(
        _messages(USER_PROMPT_MARK),
        response_model=DemoOutput,
        caller_agent="attendance_specialist",
    )
    assert result.value == "v"
    assert calls["n"] == 2
    first, second = sink.records
    assert first.attempt == 1
    assert first.outcome == "PROVIDER_FAILURE"
    assert first.failure_reason == "timeout"
    assert second.attempt == 2
    assert second.outcome == "SUCCESS"
    assert first.request_id == second.request_id  # one request, two attempts
    await service.close()


async def test_openrouter_exhausted_retries_raise_unavailable():
    sink = InMemoryLLMAuditSink()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("provider down")

    service = _openrouter_service(sink, handler, max_retries=1)
    with pytest.raises(LLMUnavailableError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    # 06 §5/§6 and 09 EC-AG-01 name LLMUnavailableError; the pre-existing
    # LLMRetryExhausted import keeps working as an alias.
    assert LLMRetryExhausted is LLMUnavailableError
    first, second = sink.records
    assert first.outcome == "PROVIDER_FAILURE"
    assert first.failure_reason == "timeout"
    assert second.attempt == 2
    assert second.outcome == "RETRY_EXHAUSTED"
    assert second.failure_reason == "timeout"
    await service.close()


async def test_openrouter_rate_limit_is_classified():
    sink = InMemoryLLMAuditSink()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    service = _openrouter_service(sink, handler, max_retries=1)
    with pytest.raises(LLMUnavailableError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    first, second = sink.records
    assert first.outcome == "PROVIDER_FAILURE"
    assert first.failure_reason == "rate_limit"
    assert second.outcome == "RETRY_EXHAUSTED"
    assert second.failure_reason == "rate_limit"
    await service.close()


async def test_openrouter_http_error_is_classified():
    sink = InMemoryLLMAuditSink()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    service = _openrouter_service(sink, handler, max_retries=1)
    with pytest.raises(LLMUnavailableError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    assert sink.records[0].failure_reason == "http_error"
    assert sink.records[1].failure_reason == "http_error"
    await service.close()


async def test_openrouter_invalid_json_is_schema_rejected_without_retry():
    sink = InMemoryLLMAuditSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _completion("this is not json {")

    service = _openrouter_service(sink, handler)
    with pytest.raises(LLMSchemaError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    # 06 §5: bounded retry covers transient/rate-limit only — schema
    # rejection is terminal (08_EVALS LLM-05), never silently retried.
    assert calls["n"] == 1
    rec = sink.records[0]
    assert rec.outcome == "SCHEMA_REJECTED"
    assert rec.failure_reason == "invalid_structured_output"
    assert rec.attempt == 1
    await service.close()


async def test_openrouter_malformed_response_shape_is_schema_rejected():
    sink = InMemoryLLMAuditSink()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})  # no message/content

    service = _openrouter_service(sink, handler)
    with pytest.raises(LLMSchemaError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    rec = sink.records[0]
    assert rec.outcome == "SCHEMA_REJECTED"
    assert rec.failure_reason == "invalid_structured_output"
    await service.close()


# --- Failure-path: pre-dispatch and terminal audit writes ---------------------


async def test_live_initial_audit_failure_prevents_provider_call():
    """Requirement: if the IN_PROGRESS row cannot be committed, the external
    provider is never called — zero HTTP dispatches."""
    sink = ExplodingSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _completion(json.dumps({"value": "v"}))

    service = _openrouter_service(sink, handler)
    with pytest.raises(LLMAuditError) as excinfo:
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    assert calls["n"] == 0  # provider never called
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    await service.close()


async def test_each_retry_gets_its_own_pre_attempt_record():
    """Requirement: one durable pre-dispatch record per actual dispatch —
    the bounded retry is a second row, never a reuse of the first."""
    sink = InMemoryLLMAuditSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectTimeout("simulated timeout")
        return _completion(json.dumps({"value": "v"}))

    service = _openrouter_service(sink, handler)
    result = await service.complete(
        _messages(USER_PROMPT_MARK),
        response_model=DemoOutput,
        caller_agent="attendance_specialist",
    )
    assert result.value == "v"
    assert calls["n"] == 2
    assert len(sink.starts) == 2
    assert len(sink.records) == 2
    start_first, start_second = sink.starts
    assert start_first.attempt == 1
    assert start_second.attempt == 2
    assert start_first.id != start_second.id  # distinct row per dispatch
    assert start_first.request_id == start_second.request_id  # one request
    # Each terminal update landed on its own pre-committed row identity.
    assert [rec.id for rec in sink.records] == [start.id for start in sink.starts]
    assert sink.records[0].outcome == "PROVIDER_FAILURE"
    assert sink.records[1].outcome == "SUCCESS"
    await service.close()


async def test_provider_success_with_terminal_audit_failure_is_never_consumed():
    """IN_PROGRESS committed → provider call succeeds (200 + valid JSON) →
    terminal update fails: the external attempt DID happen, its outcome did
    NOT persist durably, and the model output must never be returned to
    business logic (06 §5 fail-closed)."""
    sink = ObservingFailingSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return _completion(
            json.dumps({"value": "v"}),
            usage={"prompt_tokens": 5, "completion_tokens": 3},
        )

    service = _openrouter_service(sink, handler)
    with pytest.raises(LLMAuditError) as excinfo:
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    # The external provider attempt executed exactly once; its IN_PROGRESS
    # start row was committed before it, and the terminal write failed
    # (LLMAuditError, underlying error kept as the cause).
    assert calls["n"] == 1
    assert len(sink.starts) == 1
    assert len(sink.failed_finishes) == 1
    assert sink.failed_finishes[0].id == sink.starts[0].id
    assert sink.failed_finishes[0].outcome == "SUCCESS"
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    await service.close()


async def test_terminal_audit_failure_blocks_the_bounded_retry():
    """A retryable provider failure whose terminal audit update cannot be
    persisted must NOT trigger attempt 2: the retry runs only after the
    previous attempt's outcome row is durable, so a failed terminal write
    halts the request closed (the IN_PROGRESS row stays discoverable)."""
    sink = ObservingFailingSink()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, json={"error": "boom"})

    service = _openrouter_service(sink, handler, max_retries=1)
    with pytest.raises(LLMAuditError):
        await service.complete(
            _messages(USER_PROMPT_MARK),
            response_model=DemoOutput,
            caller_agent="attendance_specialist",
        )
    assert calls["n"] == 1  # bounded retry never ran after the failed write
    assert len(sink.starts) == 1  # the committed IN_PROGRESS record remains
    assert len(sink.failed_finishes) == 1
    assert sink.failed_finishes[0].attempt == 1
    assert sink.failed_finishes[0].outcome == "PROVIDER_FAILURE"
    assert sink.failed_finishes[0].failure_reason == "http_error"
    await service.close()
