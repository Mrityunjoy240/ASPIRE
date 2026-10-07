# app/services/llm_service.py
# LLMService — DM-LLM01: All LLM calls pass through here.
# Exactly two modes: LIVE (OpenRouter) and MOCK (deterministic fixtures).
# One bounded retry with bounded backoff. Reject malformed structured outputs.

import asyncio
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMSchemaError(LLMError):
    """Raised when structured output fails validation."""
    pass


class LLMRetryExhausted(LLMError):
    """Raised when all retries exhausted."""
    pass


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def complete(self, messages: list[dict], response_model: type[T] | None = None) -> T | str:
        pass


class MockLLMClient(LLMClient):
    """Deterministic mock client for testing and development."""

    def __init__(self):
        self._fixtures: dict[str, Any] = {}
        self._call_log: list[dict] = []

    def load_fixture(self, key: str, value: Any) -> None:
        """Load a deterministic fixture for a given prompt key."""
        self._fixtures[key] = value

    async def complete(self, messages: list[dict], response_model: type[T] | None = None) -> T | str:
        # Use last user message as key
        key = messages[-1].get("content", "") if messages else ""
        self._call_log.append({"messages": messages, "response_model": response_model})

        if key in self._fixtures:
            result = self._fixtures[key]
        else:
            # Default empty structured response
            if response_model:
                result = response_model.model_construct()
            else:
                result = ""

        if response_model and isinstance(result, dict):
            try:
                return response_model.model_validate(result)
            except ValidationError as e:
                raise LLMSchemaError(f"Mock fixture validation failed: {e}") from e

        return result


class OpenRouterClient(LLMClient):
    """OpenRouter HTTP client with retry/backoff and schema validation."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 1,
        backoff_base: float = 0.5,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def complete(self, messages: list[dict], response_model: type[T] | None = None) -> T | str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if response_model:
            payload["response_format"] = {"type": "json_schema", "json_schema": response_model.model_json_schema()}

        last_error = None
        for attempt in range(self.max_retries + 1):
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
                content = data["choices"][0]["message"]["content"]

                if response_model:
                    try:
                        return response_model.model_validate_json(content)
                    except ValidationError as e:
                        raise LLMSchemaError(f"OpenRouter response validation failed: {e}") from e
                return content

            except (httpx.HTTPError, httpx.TimeoutException, LLMSchemaError) as e:
                last_error = e
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                    continue
                break

        raise LLMRetryExhausted(f"OpenRouter failed after {self.max_retries + 1} attempts: {last_error}") from last_error

    async def _backoff(self, attempt: int) -> None:
        delay = self.backoff_base * (2 ** attempt)
        await asyncio.sleep(delay)

    async def close(self) -> None:
        await self._client.aclose()


class LLMService:
    """
    Central LLM service (DM-LLM01).
    - LIVE mode: calls OpenRouter with bounded retry/backoff, schema validation
    - MOCK mode: returns deterministic fixtures
    """

    def __init__(self):
        self._client: LLMClient
        self._mode = settings.llm_provider

        if self._mode == "openrouter":
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
    ) -> T | str:
        """Complete a chat request with optional structured output validation."""
        return await self._client.complete(messages, response_model)

    async def close(self) -> None:
        if hasattr(self._client, "close"):
            await self._client.close()


# Global singleton (FastAPI lifespan will manage)
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
