# tests/test_scheduler.py
# R4 unit tests — time-based scheduler (DM-AG03) without a database.
# Catalog/idempotency contract behavior on real PostgreSQL lives in
# tests/test_scheduler_pg.py (SCH-01..07, EC-SCH-01..06).

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.events import EventBus
from app.services import scheduler as sched
from app.services.scheduler import (
    DEFAULT_CONDITIONS,
    DEFERRED_CONDITIONS,
    EVENT_TASK_OVERDUE,
    SCHEDULER_INTERVAL_SECONDS,
    TaskOverdueCondition,
    cancel_scheduler_task,
    create_scheduler_task,
)


def test_task_overdue_constant_matches_supervisor_catalog():
    """03 §8.1 drift guard: producer and Supervisor must agree on the name."""
    from app.agents.supervisor import EVENT_TASK_OVERDUE as supervisor_name

    assert EVENT_TASK_OVERDUE == supervisor_name == "TASK_OVERDUE"


def test_default_conditions_cover_exactly_task_overdue():
    """R4 contract gate: only TASK_OVERDUE is evaluated; the two blocked
    conditions are declared deferred with their documented blockers."""
    assert [type(c) for c in DEFAULT_CONDITIONS] == [TaskOverdueCondition]
    assert DEFAULT_CONDITIONS[0].event_type == EVENT_TASK_OVERDUE
    assert set(DEFERRED_CONDITIONS) == {"EXAM_APPROACHING", "MENTOR_FOLLOWUP_DUE"}
    assert EVENT_TASK_OVERDUE not in DEFERRED_CONDITIONS
    assert "calendar" in DEFERRED_CONDITIONS["EXAM_APPROACHING"]
    assert "schedule_followup" in DEFERRED_CONDITIONS["MENTOR_FOLLOWUP_DUE"]


def test_frozen_interval_is_five_minutes():
    assert SCHEDULER_INTERVAL_SECONDS == 300


def test_scheduler_disabled_in_test_environment():
    """tests/conftest.py disables the scheduler before app.core.config is
    imported, so no lifespan test can ever open the configured DATABASE_URL
    (CI backend invariant)."""
    assert settings.scheduler_enabled is False


def test_create_scheduler_task_disabled_returns_none():
    assert create_scheduler_task(EventBus()) is None


async def test_create_scheduler_task_enabled_starts_and_cancels(monkeypatch):
    """Enabled path builds the loop task (name-checked) and shuts down
    cleanly without letting the real loop touch a database."""
    started = asyncio.Event()

    async def fake_loop(bus, *, session_maker=None, interval=300, clock=None):
        started.set()
        await asyncio.Event().wait()  # runs until cancelled

    monkeypatch.setattr(sched, "scheduler_loop", fake_loop)
    monkeypatch.setattr(settings, "scheduler_enabled", True)
    try:
        task = create_scheduler_task(EventBus())
        assert task is not None
        assert task.get_name() == "aspire-scheduler"
        await asyncio.wait_for(started.wait(), timeout=2)
        await cancel_scheduler_task(task)
        assert task.cancelled()
    finally:
        monkeypatch.setattr(settings, "scheduler_enabled", False)


async def test_scheduler_loop_survives_a_failing_cycle(monkeypatch):
    """A cycle failure is logged and the loop keeps its cadence (03 §8.3:
    missed/delayed cycles recover on the next evaluation)."""
    calls: list[object] = []
    second_cycle = asyncio.Event()

    class _FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    class _FakeMaker:
        def __call__(self):
            return _FakeSession()

    async def fake_run_cycle(session, bus, now):
        calls.append(now)
        if len(calls) == 1:
            raise RuntimeError("first cycle fails on purpose")
        second_cycle.set()
        return sched.CycleReport(evaluated_at=now)

    monkeypatch.setattr(sched, "run_cycle", fake_run_cycle)
    clock_calls = iter(range(100))

    def fake_clock():
        from datetime import UTC, datetime

        return datetime(2026, 1, 1, tzinfo=UTC).replace(second=next(clock_calls))

    task = asyncio.create_task(
        sched.scheduler_loop(
            EventBus(),
            session_maker=_FakeMaker(),
            interval=0.01,
            clock=fake_clock,
        )
    )
    try:
        await asyncio.wait_for(second_cycle.wait(), timeout=2)
        assert len(calls) == 2  # first failure did not stop the loop
    finally:
        await cancel_scheduler_task(task)
    assert task.done() and task.cancelled()


def test_lifespan_scheduler_disabled_start_to_finish():
    """Lifespan wiring: with the scheduler disabled (tests/conftest.py),
    startup/shutdown creates no task and never opens the configured
    DATABASE_URL; the existing supervisor registration still runs."""
    from app.main import app

    with TestClient(app):
        assert getattr(app.state, "scheduler_task", "missing") is None
    assert app.state.supervisor is not None
