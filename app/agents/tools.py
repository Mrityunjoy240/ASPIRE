# app/agents/tools.py
# Concrete specialist/Supervisor tools (06 §1/§2 allowed lists) — the only
# agent-side code that touches services/DB helpers. The Supervisor and
# proposal modules themselves stay free of SQLAlchemy (boundary-tested). DB
# access goes through domain services (case_intake, plan_proposal_service)
# or read-only queries mirroring what the attendance/queue endpoints
# already read; session_context is the documented non-FastAPI session entry
# point ("engines, agents" — core/database).

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.proposal import AttendanceProposalFacts, SubjectAttendanceFact
from app.agents.supervisor import CaseUnavailable, DerivedStateSummary
from app.core.database import session_context
from app.models.academic import Batch, Course, CourseRun
from app.models.attendance import AttendanceDerivedState
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.rules import InstitutionRule
from app.services.case_intake import (
    NON_TERMINAL_CASE_STATUSES,
    CaseIntakeError,
    ensure_risk_case,
)
from app.services.plan_proposal_service import (
    PlanProposalError,
    propose_intervention_plan,
)

SessionMaker = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_RISK_BANDS = ("WARNING", "CRITICAL")


class ServiceBackedTools:
    """Default tool wiring: session_context + domain services."""

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
            has_risk_band=any(band in _RISK_BANDS for band in rows),
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

    async def read_attendance_facts(self, student_id: UUID) -> AttendanceProposalFacts:
        """Verified attendance facts for proposal production (R3).

        Reads attendance_derived_state joined to course names, plus the
        institution/batch attendance_threshold rule for provenance. The
        primary risk subject is the worst-percentage WARNING/CRITICAL row
        (deterministic: percentage ASC NULLS FIRST, then course_run_id ASC).
        Threshold is None when no ACTIVE rule row exists — never defaulted
        (DEC-01 fail-closed provenance).
        """
        async with self._session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(
                            AttendanceDerivedState.course_run_id,
                            AttendanceDerivedState.classes_conducted,
                            AttendanceDerivedState.classes_attended,
                            AttendanceDerivedState.attendance_percentage,
                            AttendanceDerivedState.risk_band,
                            AttendanceDerivedState.required_to_recover,
                            AttendanceDerivedState.computed_at,
                            Course.name,
                            CourseRun.batch_id,
                        )
                        .join(CourseRun, CourseRun.id == AttendanceDerivedState.course_run_id)
                        .join(Course, Course.id == CourseRun.course_id)
                        .where(AttendanceDerivedState.student_id == student_id)
                    )
                ).all()
            )

            facts = [
                SubjectAttendanceFact(
                    course_run_id=row[0],
                    subject=row[7],
                    classes_conducted=row[1],
                    classes_attended=row[2],
                    attendance_percentage=(
                        float(row[3]) if row[3] is not None else None
                    ),
                    risk_band=row[4],
                    required_to_recover=row[5],
                    computed_at=row[6],
                )
                for row in rows
            ]

            threshold: float | None = None
            threshold_observed_at: datetime | None = None
            batch_ids = {row[8] for row in rows if row[8] is not None}
            if batch_ids:
                rule_result = (
                    await session.execute(
                        select(InstitutionRule)
                        .join(Batch, Batch.institution_id == InstitutionRule.institution_id)
                        .where(
                            Batch.id.in_(batch_ids),
                            InstitutionRule.rule_id == "attendance_threshold",
                            InstitutionRule.status == "ACTIVE",
                            InstitutionRule.scope_level.in_(["INSTITUTION", "BATCH"]),
                        )
                        .order_by(
                            # Institution-level first, then batch-scoped, then
                            # newest version — mirrors the attendance router.
                            InstitutionRule.scope_level.desc(),
                            InstitutionRule.version.desc(),
                        )
                    )
                ).scalars().first()
                if rule_result is not None:
                    value = rule_result.value
                    if isinstance(value, dict) and "threshold" in value:
                        try:
                            threshold = float(value["threshold"])
                        except (TypeError, ValueError):
                            threshold = None
                        threshold_observed_at = (
                            rule_result.updated_at or rule_result.effective_from
                        )

        risk_rows = [f for f in facts if f.risk_band in _RISK_BANDS]
        risk = None
        if risk_rows:
            risk = sorted(
                risk_rows,
                key=lambda f: (
                    f.attendance_percentage
                    if f.attendance_percentage is not None
                    else float("inf"),
                    str(f.course_run_id),
                ),
            )[0]
            # Worst first: lowest percentage; NULLS LAST within risk (a known
            # percentage outranks an unknown one), then course_run_id ASC.

        return AttendanceProposalFacts(
            risk=risk,
            all_subjects=tuple(sorted({f.subject for f in facts})),
            threshold=threshold,
            threshold_observed_at=threshold_observed_at,
            has_data_conflict=any(f.risk_band == "DATA_CONFLICT" for f in facts),
        )

    async def propose_intervention_plan(
        self,
        *,
        case_id: UUID,
        reason_codes: Sequence[str],
        plan_actions: Sequence[dict],
        evidence_entries: Sequence[dict],
    ) -> UUID:
        """Persist a PROPOSED plan via the domain service (06 §2 tool).

        Loads the case FOR UPDATE with its plans in the same transaction
        (F-03 concurrency pattern), then delegates validation/transition/
        audit/commit to plan_proposal_service. Raises CaseUnavailable with
        the domain error code so the specialist can refuse cleanly.
        """
        try:
            async with self._session_maker() as session:
                case = (
                    await session.execute(
                        select(InterventionCase)
                        .where(InterventionCase.id == case_id)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if case is None:
                    raise CaseUnavailable(
                        "CASE_NOT_FOUND", f"No intervention case {case_id}"
                    )
                plans = list(
                    (
                        await session.execute(
                            select(InterventionPlan).where(
                                InterventionPlan.case_id == case_id
                            )
                        )
                    ).scalars()
                )
                result = await propose_intervention_plan(
                    session,
                    case=case,
                    existing_plans=plans,
                    reason_codes=reason_codes,
                    plan_actions=plan_actions,
                    evidence_entries=evidence_entries,
                )
        except PlanProposalError as exc:
            raise CaseUnavailable(exc.code, exc.detail) from exc
        return result.plan_id
