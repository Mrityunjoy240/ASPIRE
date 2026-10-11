# app/agents/tools.py
# Concrete Supervisor tools (06 §1 allowed list) — the only agent-side code
# that touches services/DB helpers. The Supervisor module itself stays free
# of SQLAlchemy (boundary-tested). DB access goes through the domain service
# (case_intake) or read-only queries mirroring what the mentor-queue/attendance
# endpoints already read; session_context is the documented non-FastAPI
# session entry point ("engines, agents" — core/database).

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.supervisor import CaseUnavailable, DerivedStateSummary
from app.core.database import session_context
from app.models.attendance import AttendanceDerivedState
from app.models.intervention import InterventionCase
from app.services.case_intake import (
    NON_TERMINAL_CASE_STATUSES,
    CaseIntakeError,
    ensure_risk_case,
)

SessionMaker = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class ServiceBackedTools:
    """Default tool wiring: session_context + case_intake service."""

    def __init__(self, session_maker: SessionMaker | None = None) -> None:
        self._session_maker: SessionMaker = session_maker or session_context

    async def read_student_derived_state(self, student_id: UUID) -> DerivedStateSummary:
        async with self._session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(AttendanceDerivedState.risk_band).where(
                            AttendanceDerivedState.student_id == student_id
                        )
                    )
                ).scalars()
            )
        return DerivedStateSummary(
            row_count=len(rows),
            has_risk_band=any(band in ("WARNING", "CRITICAL") for band in rows),
            has_data_conflict=any(band == "DATA_CONFLICT" for band in rows),
        )

    async def read_open_cases(self, student_id: UUID) -> UUID | None:
        async with self._session_maker() as session:
            return (
                await session.execute(
                    select(InterventionCase.id)
                    .where(
                        InterventionCase.student_id == student_id,
                        InterventionCase.status.in_(
                            [s.value for s in NON_TERMINAL_CASE_STATUSES]
                        ),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

    async def create_intervention_case(
        self,
        *,
        student_id: UUID,
        trigger_event_id: UUID,
        urgency_band: str,
    ) -> UUID:
        try:
            result = await ensure_risk_case(
                student_id=student_id,
                trigger_event_id=trigger_event_id,
                urgency_band=urgency_band,
                session_maker=self._session_maker,
            )
        except CaseIntakeError as exc:
            raise CaseUnavailable(exc.code, exc.detail) from exc
        return result.case_id
