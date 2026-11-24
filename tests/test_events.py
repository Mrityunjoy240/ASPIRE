# tests/test_events.py
# In-process event bus + Minimal Event Contract (03_SYSTEM_SPEC §8.1) tests.

import uuid
from datetime import datetime, timezone

import pytest

from app.core.events import DomainEvent, EventBus


def make_event(event_type: str = "INTERVENTION_PLAN_APPROVED") -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        student_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        payload={"decision": "APPROVED"},
    )


def test_domain_event_contract_fields():
    event = make_event()
    data = event.to_dict()
    assert set(data.keys()) == {
        "event_id",
        "event_type",
        "student_id",
        "source_id",
        "occurred_at",
        "data_version",
        "payload",
    }
    assert data["event_type"] == "INTERVENTION_PLAN_APPROVED"
    assert data["data_version"] == 1
    uuid.UUID(data["event_id"])
    uuid.UUID(data["student_id"])
    uuid.UUID(data["source_id"])
    assert isinstance(event.occurred_at, datetime)
    assert event.occurred_at.tzinfo is not None


def test_event_is_immutable():
    event = make_event()
    with pytest.raises(AttributeError):
        event.event_type = "PLAN_ACCEPTED"


async def test_publish_invokes_subscribers():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("INTERVENTION_PLAN_APPROVED", handler)
    event = make_event()
    await bus.publish(event)
    assert received == [event]


async def test_publish_only_dispatches_matching_type():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("INTERVENTION_PLAN_APPROVED", handler)
    await bus.publish(make_event("PLAN_DECLINED"))
    assert received == []


async def test_failing_handler_does_not_break_others_or_producer():
    bus = EventBus()
    received = []

    async def bad_handler(event: DomainEvent):
        raise RuntimeError("boom")

    async def good_handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("INTERVENTION_PLAN_APPROVED", bad_handler)
    bus.subscribe("INTERVENTION_PLAN_APPROVED", good_handler)
    await bus.publish(make_event())  # must not raise
    assert len(received) == 1
