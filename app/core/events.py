# app/core/events.py
# In-process asyncio domain event bus — ADR-001 (ARCH-02): no Redis/Kafka/Temporal in v1.
# Event contract: docs/03_SYSTEM_SPEC.md §8.1 (Minimal Event Contract).

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[["DomainEvent"], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Minimal Event Contract (03_SYSTEM_SPEC §8.1).

    Emitted strictly after the originating database transaction commits
    (producer responsibility). Audit rows are separate from domain events.
    """

    event_type: str
    student_id: uuid.UUID
    source_id: uuid.UUID
    payload: dict[str, Any]
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    data_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "student_id": str(self.student_id),
            "source_id": str(self.source_id),
            "occurred_at": self.occurred_at.isoformat(),
            "data_version": self.data_version,
            "payload": self.payload,
        }


class EventBus:
    """Asyncio in-process pub/sub (ARCH-02).

    Handlers are awaited inline at publish time so ordering is deterministic
    and testable. Long-running subscribers (agent workflows) must schedule
    their own background work (OQ-AG02) rather than block the producer.
    A failing handler never propagates to the producer.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def subscriber_count(self, event_type: str) -> int:
        """Number of handlers registered for a type (registration tests)."""
        return len(self._subscribers.get(event_type, []))

    async def publish(self, event: DomainEvent) -> None:
        logger.info(
            "Domain event published: %s (event_id=%s, student_id=%s)",
            event.event_type,
            event.event_id,
            event.student_id,
        )
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s (event_id=%s)",
                    getattr(handler, "__name__", repr(handler)),
                    event.event_type,
                    event.event_id,
                )

    def clear(self) -> None:
        self._subscribers.clear()
