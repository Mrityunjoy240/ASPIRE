# app/services/llm_service.py
# LLMService — DM-LLM01: All LLM calls pass through here.
# Exactly two modes: LIVE (OpenRouter) and MOCK (deterministic fixtures).
# One bounded retry with bounded backoff. Reject malformed structured outputs.
# Per-attempt audit lifecycle (06 §5, 07 §4): an IN_PROGRESS row is durably
# committed BEFORE each provider dispatch (no dispatch without it), and the
# terminal outcome is committed AFTER the attempt (no result returned without
# it). IN_PROGRESS means the attempt was initiated and its terminal outcome
# is not yet durably known — never treated as success.

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

# 06 §5 failure taxonomy -> persisted `outcome` / `failure_reason` vocabulary
# (documented in 05 §7 `llm_attempt_audit`).
OUTCOME_IN_PROGRESS = "IN_PROGRESS"  # row committed before dispatch; terminal outcome unknown
OUTCOME_SUCCESS = "SUCCESS"
OUTCOME_SCHEMA_REJECTED = "SCHEMA_REJECTED"
OUTCOME_PROVIDER_FAILURE = "PROVIDER_FAILURE"
OUTCOME_RETRY_EXHAUSTED = "RETRY_EXHAUSTED"

REASON_TIMEOUT = "timeout"
REASON_RATE_LIMIT = "rate_limit"
REASON_HTTP_ERROR = "http_error"
REASON_NETWORK_ERROR = "network_error"
REASON_INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"

# MOCK invokes no provider and no model — audit rows must not claim otherwise.
MOCK_PROVIDER = "mock"
MOCK_MODEL = "mock-fixture"


class LLMError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMSchemaError(LLMError):
    """Raised when structured output fails validation."""
    pass


class LLMUnavailableError(LLMError):
    """Raised when the provider stays unavailable after the allowed bounded
    retry/failover path (06 §5, 09 EC-AG-01)."""


class LLMAuditError(LLMError):
    """Raised when a mandatory per-attempt audit write could not be persisted.

    Fail-closed at both ends of the lifecycle (06 §5 "every attempt
    records"): no provider dispatch without a durable IN_PROGRESS start
    row, and business logic never consumes the result of an attempt whose
    terminal outcome update did not commit (the IN_PROGRESS row then
    remains discoverable — the outcome is explicitly *not* durably known).
    """


# Pre-existing code name kept as an alias of the spec-frozen
# LLMUnavailableError (06 §5/§6, 09 EC-AG-01) so existing imports keep working.
LLMRetryExhausted = LLMUnavailableError


@dataclass(frozen=True, slots=True)
class LLMAttemptReport:
    """Transport-side facts for one finished provider attempt; the audit port
    wraps them with the request-level audit metadata (06 §5)."""

    attempt: int
    outcome: str
    failure_reason: str | None
    latency_ms: int
    input_token_count: int | None
    output_token_count: int | None


@dataclass(frozen=True, slots=True)
class LLMAttemptStart:
    """Pre-dispatch audit record: committed durably BEFORE the provider is
    called. One per actual dispatch attempt (each bounded retry gets its own
    row id and `attempt` number).

    Metadata only — never prompt content, never student PII.
    """

    id: UUID
    request_id: UUID
    caller_agent: str
    prompt_version: str | None
    response_schema_version: str | None
    provider: str
    model: str
    attempt: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LLMAttemptRecord:
    """Terminal audit record for one attempt (06 §5, 07 §4).

    `id` is the row identity shared with its `LLMAttemptStart` — the terminal
    update lands on the pre-committed IN_PROGRESS row. `created_at` is the
    attempt initiation time from the start record (never rewritten).

    Metadata only — never prompt content, never student PII.
    """

    id: UUID
    request_id: UUID
    caller_agent: str
    prompt_version: str | None
    response_schema_version: str | None
    provider: str
    model: str
    attempt: int
    outcome: str
    failure_reason: str | None
    latency_ms: int
    input_token_count: int | None
    output_token_count: int | None
    created_at: datetime


class AttemptAuditPort(Protocol):
    """Per-request audit port handed to LLM clients.

    `start` commits the IN_PROGRESS row and returns its id — raising
    LLMAuditError on failure, in which case the client MUST NOT dispatch.
    `finish` commits the terminal outcome — raising LLMAuditError on failure,
    in which case the client's result must not escape (fail-closed).
    """

    async def start(self, attempt: int) -> UUID: ...

    async def finish(self, row_id: UUID, report: LLMAttemptReport) -> None: ...


class LLMAuditSink(Protocol):
    """Where audit rows go; `begin`/`finish` persist or raise."""

    async def begin(self, start: LLMAttemptStart) -> None: ...

    async def finish(self, attempt: LLMAttemptRecord) -> None: ...


class InMemoryLLMAuditSink:
    """Non-persistent sink: unit tests and DB-less local MOCK runs.

    `starts` holds the pre-dispatch records (semantically IN_PROGRESS);
    `records` holds the terminal updates.
    """

    def __init__(self) -> None:
        self.starts: list[LLMAttemptStart] = []
        self.records: list[LLMAttemptRecord] = []

    async def begin(self, start: LLMAttemptStart) -> None:
        self.starts.append(start)

    async def finish(self, attempt: LLMAttemptRecord) -> None:
        self.records.append(attempt)


class SqlLLMAuditSink:
    """Default production sink: the IN_PROGRESS row for each attempt is
    committed BEFORE the dispatch, and the terminal outcome is committed
    AFTER it, in `llm_attempt_audit` (migration 014). Either persistence
    failure raises LLMAuditError — callers never dispatch unrecorded and
    never consume an unrecorded result (06 §5)."""

    def __init__(self, session_factory: Callable[[], Any] | None = None) -> None:
        # session_factory yields an open AsyncSession (defaults to the
        # app-wide sessionmaker); the sink owns the commit.
        self._session_factory = session_factory

    def _factory(self) -> Callable[[], Any]:
        if self._session_factory is not None:
            return self._session_factory
        from app.core.database import async_session_maker

        return async_session_maker

    async def begin(self, start: LLMAttemptStart) -> None:
        from app.models.llm_audit import LLMAttemptAudit

        try:
            async with self._factory()() as session:
                session.add(
                    LLMAttemptAudit(
                        id=start.id,
                        request_id=start.request_id,
                        caller_agent=start.caller_agent,
                        prompt_version=start.prompt_version,
                        response_schema_version=start.response_schema_version,
                        provider=start.provider,
                        model=start.model,
                        attempt=start.attempt,
                        outcome=OUTCOME_IN_PROGRESS,
                        failure_reason=None,
                        latency_ms=0,  # wall time unknown until the attempt finishes
                        input_token_count=None,
                        output_token_count=None,
                        created_at=start.created_at,
                    )
                )
                await session.commit()
        except Exception as exc:
            raise LLMAuditError(
                f"LLM attempt audit not started: request_id={start.request_id} "
                f"attempt={start.attempt}"
            ) from exc

    async def finish(self, attempt: LLMAttemptRecord) -> None:
        from app.models.llm_audit import LLMAttemptAudit

        try:
            async with self._factory()() as session:
                row = await session.get(LLMAttemptAudit, attempt.id)
                if row is None:
                    raise LLMAuditError(
                        f"LLM attempt audit start row missing: "
                        f"request_id={attempt.request_id} attempt={attempt.attempt}"
                    )
                row.outcome = attempt.outcome
                row.failure_reason = attempt.failure_reason
                row.latency_ms = attempt.latency_ms
                row.input_token_count = attempt.input_token_count
                row.output_token_count = attempt.output_token_count
                await session.commit()
        except LLMAuditError:
            raise
        except Exception as exc:
            raise LLMAuditError(
                f"LLM attempt audit terminal outcome not persisted: "
                f"request_id={attempt.request_id} attempt={attempt.attempt}"
            ) from exc


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _token_count(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _classify_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return REASON_TIMEOUT
    if isinstance(exc, httpx.HTTPStatusError):
        return REASON_RATE_LIMIT if exc.response.status_code == 429 else REASON_HTTP_ERROR
    if isinstance(exc, httpx.TransportError):
        return REASON_NETWORK_ERROR
    return REASON_HTTP_ERROR


class _AttemptAudit:
    """Per-request audit port (one per `LLMService.complete()` call).

    `start` commits an IN_PROGRESS row before the dispatch — failure means
    the provider is never called. `finish` commits the terminal outcome —
    failure means the result never escapes. IN_PROGRESS rows left behind by
    a failed/crashed terminal update remain discoverable and are never
    treated as success.
    """

    def __init__(
        self,
        sink: LLMAuditSink,
        *,
        request_id: UUID,
        caller_agent: str,
        prompt_version: str | None,
        response_schema_version: str | None,
        provider: str,
        model: str,
    ) -> None:
        self._sink = sink
        self._request_id = request_id
        self._caller_agent = caller_agent
        self._prompt_version = prompt_version
        self._response_schema_version = response_schema_version
        self._provider = provider
        self._model = model
        self._started: dict[UUID, datetime] = {}

    async def start(self, attempt: int) -> UUID:
        row_id = uuid4()
        start = LLMAttemptStart(
            id=row_id,
            request_id=self._request_id,
            caller_agent=self._caller_agent,
            prompt_version=self._prompt_version,
            response_schema_version=self._response_schema_version,
            provider=self._provider,
            model=self._model,
            attempt=attempt,
            created_at=datetime.now(UTC),
        )
        try:
            await self._sink.begin(start)
        except LLMAuditError:
            raise
        except Exception as exc:
            raise LLMAuditError(
                f"LLM attempt audit not started: request_id={self._request_id} "
                f"attempt={attempt}"
            ) from exc
        self._started[row_id] = start.created_at
        return row_id

    async def finish(self, row_id: UUID, report: LLMAttemptReport) -> None:
        record = LLMAttemptRecord(
            id=row_id,
            request_id=self._request_id,
            caller_agent=self._caller_agent,
            prompt_version=self._prompt_version,
            response_schema_version=self._response_schema_version,
            provider=self._provider,
            model=self._model,
            attempt=report.attempt,
            outcome=report.outcome,
            failure_reason=report.failure_reason,
            latency_ms=report.latency_ms,
            input_token_count=report.input_token_count,
            output_token_count=report.output_token_count,
            created_at=self._started.pop(row_id, datetime.now(UTC)),
        )
        try:
            await self._sink.finish(record)
        except LLMAuditError:
            raise
        except Exception as exc:
            raise LLMAuditError(
                f"LLM attempt audit terminal outcome not persisted: "
                f"request_id={self._request_id} attempt={report.attempt}"
            ) from exc


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider identity for audit rows (06 §5)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identity for audit rows (06 §5)."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        response_model: type[T] | None = None,
        *,
        audit: AttemptAuditPort,
    ) -> T | str:
        """Run one request. Contract: `await audit.start(n)` BEFORE each
        dispatch (abort if it raises — no dispatch without a durable
        IN_PROGRESS row) and `await audit.finish(row_id, report)` exactly
        once per dispatched attempt (a failure there must not let the
        result escape)."""


class MockLLMClient(LLMClient):
    """Deterministic mock client for testing and development."""

    def __init__(self):
        self._fixtures: dict[str, Any] = {}
        self._call_log: list[dict] = []

    @property
    def provider(self) -> str:
        return MOCK_PROVIDER

    @property
    def model(self) -> str:
        return MOCK_MODEL

    def load_fixture(self, key: str, value: Any) -> None:
        """Load a deterministic fixture for a given prompt key."""
        self._fixtures[key] = value

    async def complete(
        self,
        messages: list[dict],
        response_model: type[T] | None = None,
        *,
        audit: AttemptAuditPort,
    ) -> T | str:
        # Pre-dispatch audit row (06 §5): no fixture work happens unless the
        # IN_PROGRESS record is durably committed — audit failure means the
        # attempt never "runs".
        row_id = await audit.start(1)
        started = time.perf_counter()
        # Use last user message as key
        key = messages[-1].get("content", "") if messages else ""
        self._call_log.append({"messages": messages, "response_model": response_model})
        outcome = OUTCOME_SUCCESS
        failure_reason: str | None = None
        try:
            if key not in self._fixtures:
                if response_model is None:
                    return ""
                # DM-LLM01: MOCK responses come only from explicit fixtures.
                # A fixture miss is rejected exactly like invalid provider
                # output — an empty model_construct() object is never handed
                # to business logic (06 §5: never accept partial output).
                outcome = OUTCOME_SCHEMA_REJECTED
                failure_reason = REASON_INVALID_STRUCTURED_OUTPUT
                raise LLMSchemaError(
                    f"No MOCK fixture for prompt key (response model {response_model.__name__})"
                )
            result = self._fixtures[key]
            if response_model is None:
                return result
            if isinstance(result, dict):
                try:
                    return response_model.model_validate(result)
                except ValidationError as e:
                    outcome = OUTCOME_SCHEMA_REJECTED
                    failure_reason = REASON_INVALID_STRUCTURED_OUTPUT
                    raise LLMSchemaError(f"Mock fixture validation failed: {e}") from e
            if isinstance(result, response_model):
                return result
            outcome = OUTCOME_SCHEMA_REJECTED
            failure_reason = REASON_INVALID_STRUCTURED_OUTPUT
            raise LLMSchemaError(f"Mock fixture is not a valid {response_model.__name__}")
        finally:
            # Terminal audit update — exactly one per attempt (success,
            # rejection, or fixture miss). A failure here discards the
            # result (fail-closed); the IN_PROGRESS row stays discoverable.
            await audit.finish(
                row_id,
                LLMAttemptReport(
                    attempt=1,
                    outcome=outcome,
                    failure_reason=failure_reason,
                    latency_ms=_elapsed_ms(started),
                    input_token_count=None,
                    output_token_count=None,
                ),
            )


class OpenRouterClient(LLMClient):
    """OpenRouter HTTP client with retry/backoff and schema validation."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 1,
        backoff_base: float = 0.5,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = api_key
        self.model_name = model
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    @property
    def provider(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        return self.model_name

    async def complete(
        self,
        messages: list[dict],
        response_model: type[T] | None = None,
        *,
        audit: AttemptAuditPort,
    ) -> T | str:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_model:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": response_model.model_json_schema(),
            }

        last_error: Exception | None = None
        last_reason: str | None = None
        for attempt_no in range(self.max_retries + 1):
            # Pre-dispatch audit row: committed BEFORE the HTTP call. If it
            # cannot be committed the provider is never called (fail-closed),
            # and no automatic audit-write retry is attempted.
            row_id = await audit.start(attempt_no + 1)
            started = time.perf_counter()
            input_tokens: int | None = None
            output_tokens: int | None = None
            outcome = OUTCOME_SUCCESS
            failure_reason: str | None = None
            try:
                try:
                    resp = await self._client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://aspire.local",
                            "X-Title": "ASPIRE Mother System",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, dict) and isinstance(data.get("usage"), dict):
                        input_tokens = _token_count(data["usage"].get("prompt_tokens"))
                        output_tokens = _token_count(data["usage"].get("completion_tokens"))
                    content = data["choices"][0]["message"]["content"]
                    if response_model is None:
                        return content
                    return response_model.model_validate_json(content)
                except httpx.HTTPError as e:
                    outcome = (
                        OUTCOME_RETRY_EXHAUSTED
                        if attempt_no >= self.max_retries
                        else OUTCOME_PROVIDER_FAILURE
                    )
                    failure_reason = _classify_http_error(e)
                    last_error, last_reason = e, failure_reason
                    if attempt_no >= self.max_retries:
                        break
                except (ValueError, KeyError, IndexError, TypeError) as e:
                    # HTTP success does not imply a valid result (06 §5):
                    # malformed provider output is invalid structured output,
                    # rejected and never retried — the bounded retry covers
                    # transient failures and rate limits only (06 §5).
                    outcome = OUTCOME_SCHEMA_REJECTED
                    failure_reason = REASON_INVALID_STRUCTURED_OUTPUT
                    raise LLMSchemaError(f"OpenRouter response validation failed: {e}") from e
            finally:
                # Terminal audit update on the pre-committed row. Failure
                # discards the result and halts the retry loop; the
                # IN_PROGRESS row remains discoverable (never claimed as a
                # durably recorded outcome).
                await audit.finish(
                    row_id,
                    LLMAttemptReport(
                        attempt=attempt_no + 1,
                        outcome=outcome,
                        failure_reason=failure_reason,
                        latency_ms=_elapsed_ms(started),
                        input_token_count=input_tokens,
                        output_token_count=output_tokens,
                    ),
                )
            await self._backoff(attempt_no)

        # Unreachable unless the loop broke on a final provider failure.
        raise LLMUnavailableError(
            f"OpenRouter failed after {self.max_retries + 1} attempt(s): "
            f"{last_reason}: {last_error}"
        ) from last_error

    async def _backoff(self, attempt: int) -> None:
        delay = self.backoff_base * (2**attempt)
        await asyncio.sleep(delay)

    async def close(self) -> None:
        await self._client.aclose()


class LLMService:
    """
    Central LLM service (DM-LLM01).
    - LIVE mode: calls OpenRouter with bounded retry/backoff, schema validation
    - MOCK mode: returns deterministic fixtures
    - Per-attempt audit lifecycle (06 §5, 07 §4): IN_PROGRESS row committed
      before each dispatch, terminal outcome after — fail-closed at both ends
    """

    def __init__(
        self,
        audit_sink: LLMAuditSink | None = None,
        client: LLMClient | None = None,
    ) -> None:
        # Fail-closed default: production runs persist every attempt in
        # `llm_attempt_audit`; tests inject InMemoryLLMAuditSink explicitly
        # (get_llm_service(audit_sink=…)).
        self._audit_sink: LLMAuditSink = (
            audit_sink if audit_sink is not None else SqlLLMAuditSink()
        )
        self._client: LLMClient
        self._mode = settings.llm_provider

        if client is not None:
            self._client = client
        elif self._mode == "openrouter":
            if not settings.llm_api_key:
                raise ValueError("LLM_API_KEY required for openrouter mode")
            self._client = OpenRouterClient(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                max_retries=settings.llm_max_retries,
                backoff_base=settings.llm_backoff_base,
                timeout=settings.llm_timeout,
            )
        else:
            self._client = MockLLMClient()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def mock_client(self) -> MockLLMClient:
        if not isinstance(self._client, MockLLMClient):
            raise RuntimeError("Mock client only available in MOCK mode")
        return self._client

    async def complete(
        self,
        messages: list[dict],
        response_model: type[T] | None = None,
        *,
        caller_agent: str,
        prompt_version: str | None = None,
    ) -> T | str:
        """Complete a chat request with optional structured output validation.

        `caller_agent` and `prompt_version` are caller-supplied audit context
        (06 §5); `response_schema_version` is derived from the response model.
        The audit lifecycle is fail-closed at both ends: if the IN_PROGRESS
        row cannot be committed the provider is never called; if the terminal
        update cannot be committed the result is never returned
        (LLMAuditError in both cases).
        """
        if not caller_agent:
            raise ValueError("caller_agent is required for LLM audit metadata")
        request_id = uuid4()
        audit = _AttemptAudit(
            self._audit_sink,
            request_id=request_id,
            caller_agent=caller_agent,
            prompt_version=prompt_version,
            response_schema_version=(
                response_model.__name__ if response_model is not None else None
            ),
            provider=self._client.provider,
            model=self._client.model,
        )
        return await self._client.complete(messages, response_model, audit=audit)

    async def close(self) -> None:
        if hasattr(self._client, "close"):
            await self._client.close()


# Global singleton (FastAPI lifespan will manage)
_llm_service: LLMService | None = None


def get_llm_service(audit_sink: LLMAuditSink | None = None) -> LLMService:
    """Process-wide singleton. `audit_sink` is honoured only when the
    singleton is first created (production default: SqlLLMAuditSink)."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(audit_sink=audit_sink)
    return _llm_service
