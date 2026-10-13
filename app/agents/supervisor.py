# app/agents/supervisor.py
# Supervisor Agent (06_AGENT_SPEC §1) — deterministic routing of catalog
# events on the in-process event bus (11_ROADMAP R2: wiring slice; R3 adds
# the optional proposal hook below).
#
# Boundaries (06 §0/§1; Constitution A-01/A-04):
#   * Routing is a pure lookup on the §1 table — never an LLM decision
#     (06 §6: LLM unavailability must not block routing).
#   * This module imports neither SQLAlchemy nor an HTTP/provider client.
#     All reads/writes go through injected tools (06 §1 allowed tools:
#     read_student_derived_state, read_open_cases, create_intervention_case).
#   * Case writes are owned by app.services.case_intake (domain service);
#     the Supervisor never mutates tables directly.
#   * No LangGraph graph in R2/R3 — plain deterministic wiring; the graph
#     framework arrives with the specialist slices that need it.
#
# R2 scope decisions (recorded in docs/AI_WORKING_STATE.md):
#   * Case-ensure applies to the attendance risk path (WARNING/CRITICAL)
#     only; other triggers are route-only (specialists beyond the attendance
#     stub land in later slices). No approved contract mandates case creation
#     for any other catalog event (03 §6.1/§10.2, 06 §1, 02 §1.1; roadmap R2).
#   * Initial urgency band: CRITICAL → URGENT, WARNING → ATTENTION — the
#     primary disjuncts of 03_SYSTEM_SPEC §6.1 (URGENT: CRITICAL OR risk+exam;
#     ATTENTION: WARNING OR missed assessment). The second URGENT disjunct
#     (any risk + Exam < exam_approaching_days) needs exam_days_remaining
#     from the Calendar Engine (03 §9 / roadmap R4).
#   * Route-only runs (no case write) are logged, not audit-logged: 07 §4
#     requires audit rows for privileged writes; a pure routing decision
#     writes nothing.

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.agents.proposal import ProposalOutcome
from app.core.events import DomainEvent, EventBus

logger = logging.getLogger(__name__)

# Canonical catalog names — must match 03_SYSTEM_SPEC §8 exactly.
EVENT_ATTENDANCE_RISK_WARNING = "ATTENDANCE_RISK_WARNING"
EVENT_ATTENDANCE_RISK_CRITICAL = "ATTENDANCE_RISK_CRITICAL"
EVENT_ASSESSMENT_TREND_DECLINING = "ASSESSMENT_TREND_DECLINING"
EVENT_ASSESSMENT_MISSING_URGENT = "ASSESSMENT_MISSING_URGENT"
EVENT_EXAM_APPROACHING = "EXAM_APPROACHING"
EVENT_TASK_OVERDUE = "TASK_OVERDUE"
EVENT_PLAN_DECLINED = "PLAN_DECLINED"
EVENT_MENTOR_FOLLOWUP_DUE = "MENTOR_FOLLOWUP_DUE"

# 06 §1 Supervisor triggers (exact names, subscription set).
SUPERVISOR_TRIGGERS: tuple[str, ...] = (
    EVENT_ATTENDANCE_RISK_WARNING,
    EVENT_ATTENDANCE_RISK_CRITICAL,
    EVENT_ASSESSMENT_TREND_DECLINING,
    EVENT_ASSESSMENT_MISSING_URGENT,
    EVENT_EXAM_APPROACHING,
    EVENT_TASK_OVERDUE,
    EVENT_PLAN_DECLINED,
    EVENT_MENTOR_FOLLOWUP_DUE,
)

ATTENDANCE_AGENT = "ATTENDANCE_AGENT"
LEARNING_AGENT = "LEARNING_AGENT"
INTERVENTION_AGENT = "INTERVENTION_AGENT"

DECISION_ROUTE = "ROUTE"
DECISION_ESCALATE = "ESCALATE"
DECISION_NO_ACTION = "NO_ACTION"

URGENCY_URGENT = "URGENT"
URGENCY_ATTENTION = "ATTENTION"

# 06 §1 deterministic routing table (fixed events only; EXAM_APPROACHING is
# conditional and resolved in handle()).
_FIXED_ROUTES: dict[str, str] = {
    EVENT_ATTENDANCE_RISK_WARNING: ATTENDANCE_AGENT,
    EVENT_ATTENDANCE_RISK_CRITICAL: ATTENDANCE_AGENT,
    EVENT_ASSESSMENT_TREND_DECLINING: LEARNING_AGENT,
    EVENT_ASSESSMENT_MISSING_URGENT: INTERVENTION_AGENT,
    EVENT_TASK_OVERDUE: INTERVENTION_AGENT,
    EVENT_PLAN_DECLINED: INTERVENTION_AGENT,
    EVENT_MENTOR_FOLLOWUP_DUE: INTERVENTION_AGENT,
}

# Attendance risk events that drive the case-ensure path (R2 scope).
_CASE_CREATING_EVENTS: frozenset[str] = frozenset(
    {EVENT_ATTENDANCE_RISK_WARNING, EVENT_ATTENDANCE_RISK_CRITICAL}
)

_RISK_BANDS: frozenset[str] = frozenset({"WARNING", "CRITICAL"})


def initial_urgency_band(event_type: str) -> str:
    """Deterministic initial band for a newly created risk case (R2).

    CRITICAL → URGENT, WARNING → ATTENTION: the primary disjuncts of
    03_SYSTEM_SPEC §6.1. The second URGENT disjunct (any risk + Exam <
    exam_approaching_days) needs the Calendar Engine (03 §9 / roadmap R4);
    URGENT cases without exam data are a designed state (09 EC-MQ-01).
    """
    return URGENCY_URGENT if event_type == EVENT_ATTENDANCE_RISK_CRITICAL else URGENCY_ATTENTION


@dataclass(frozen=True, slots=True)
class DerivedStateSummary:
    """Read-only summary of attendance_derived_state (engine output only)."""

    row_count: int
    has_risk_band: bool  # any row with risk_band WARNING/CRITICAL
    has_data_conflict: bool  # any row with risk_band DATA_CONFLICT (quarantine)


@dataclass(frozen=True, slots=True)
class AttendanceAssessment:
    """Attendance specialist stub result (06 §2 envelope, non-persisted)."""

    available: bool
    explanation: str | None
    reason_codes: tuple[str, ...]
    confidence_level: str | None  # HIGH | MEDIUM | LOW (Constitution A-06)


class CaseUnavailable(Exception):
    """Tool-level refusal: the case could not be created (expected path)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class SupervisorTools(Protocol):
    """06 §1 allowed tools — typed, read-only except create_intervention_case."""

    async def read_student_derived_state(self, student_id: UUID) -> DerivedStateSummary: ...

    async def read_open_cases(self, student_id: UUID) -> UUID | None: ...

    async def create_intervention_case(
        self,
        *,
        student_id: UUID,
        trigger_event_id: UUID,
        urgency_band: str,
    ) -> UUID: ...


class AttendanceSpecialistPort(Protocol):
    """Minimal surface the Supervisor needs from the attendance stub."""

    async def assess(self, student_id: UUID) -> AttendanceAssessment: ...


class ProposalSpecialistPort(Protocol):
    """Optional R3 surface: produce and persist an intervention plan for a
    resolved case. Default None keeps every R2 wiring/test intact."""

    async def produce_proposal(
        self, *, student_id: UUID, case_id: UUID
    ) -> ProposalOutcome: ...


@dataclass(frozen=True, slots=True)
class SupervisorRun:
    """06 §1 output contract plus originating-event traceability (§13).

    evidence is the routing/evaluation envelope (06 §2 note) — scalar
    identifiers and status strings only, never persisted and never PII.
    """

    event_id: uuid.UUID
    event_type: str
    student_id: uuid.UUID
    decision: str  # ROUTE | ESCALATE | NO_ACTION
    target_agent: str | None
    human_review_required: bool
    case_id: uuid.UUID | None
    reason_codes: tuple[str, ...]
    evidence: dict[str, str | None]


class Supervisor:
    """Event-bus entry point: subscribe → route deterministically → tools.

    One handler per trigger type; ensure_subscribed() is idempotent per bus
    so repeated lifespan startup/shutdown cycles never double-register.
    """

    def __init__(
        self,
        *,
        tools: SupervisorTools,
        attendance_specialist: AttendanceSpecialistPort,
        proposal_specialist: ProposalSpecialistPort | None = None,
    ) -> None:
        self._tools = tools
        self._attendance = attendance_specialist
        self._proposal = proposal_specialist
        self._bus: EventBus | None = None

    def ensure_subscribed(self, bus: EventBus) -> None:
        """Subscribe the Supervisor handler to its trigger events once."""
        if self._bus is bus:
            return
        for event_type in SUPERVISOR_TRIGGERS:
            bus.subscribe(event_type, self._on_event)
        self._bus = bus

    async def _on_event(self, event: DomainEvent) -> None:
        """Bus handler. Exceptions propagate to the bus, which isolates and
        logs them without affecting the producer or other subscribers."""
        run = await self.handle(event)
        logger.info(
            "Supervisor run: event_type=%s event_id=%s student_id=%s "
            "decision=%s target_agent=%s case_id=%s human_review=%s reasons=%s",
            run.event_type,
            run.event_id,
            run.student_id,
            run.decision,
            run.target_agent,
            run.case_id,
            run.human_review_required,
            ",".join(run.reason_codes),
        )

    async def handle(self, event: DomainEvent) -> SupervisorRun:
        """Apply the 06 §1 routing table to one event."""
        target_agent: str | None
        reasons: list[str] = []
        case_id: UUID | None = None

        if event.event_type == EVENT_EXAM_APPROACHING:
            state = await self._tools.read_student_derived_state(event.student_id)
            if state.has_data_conflict:
                # 06 §0 rule 3: never bypass a conflict quarantine.
                return self._escalate(event, ["DATA_CONFLICT_QUARANTINE"])
            if state.has_risk_band:
                target_agent = ATTENDANCE_AGENT
            else:
                target_agent = INTERVENTION_AGENT
        elif event.event_type in _FIXED_ROUTES:
            target_agent = _FIXED_ROUTES[event.event_type]
        else:
            # Unmatched event (06 §1 last row; ADR-002 §5: e.g.
            # INTERVENTION_PLAN_APPROVED falls through to human review).
            return self._escalate(event, ["UNMATCHED_EVENT"])

        # Case-ensure on the attendance risk path (R2 scope).
        if event.event_type in _CASE_CREATING_EVENTS:
            try:
                case_id = await self._tools.create_intervention_case(
                    student_id=event.student_id,
                    trigger_event_id=event.event_id,
                    urgency_band=initial_urgency_band(event.event_type),
                )
            except CaseUnavailable as exc:
                return self._escalate(event, [exc.code])
            reasons.append(event.event_type)

        # Attendance specialist stub: invoked for every attendance route
        # (R2: MOCK round-trip; no plan production — that is R3).
        specialist_note: str | None = None
        if target_agent == ATTENDANCE_AGENT:
            assessment = await self._attendance.assess(event.student_id)
            if assessment.available:
                specialist_note = "ASSESSED"
                reasons.extend(assessment.reason_codes)
            else:
                # 06 §6 degradation: routing stands; the LLM-dependent part
                # is unavailable. No fabricated plan, no failure transition.
                specialist_note = "LLM_UNAVAILABLE"
                reasons.append("LLM_UNAVAILABLE")
        elif case_id is None and target_agent == INTERVENTION_AGENT:
            # Route-only intervention events: attach the existing case when
            # the payload did not carry one (read_open_cases, read-only).
            payload_case = event.payload.get("case_id") if event.payload else None
            if payload_case:
                case_id = uuid.UUID(str(payload_case))
            else:
                case_id = await self._tools.read_open_cases(event.student_id)

        # R3: when an attendance route resolved a case and a proposal
        # specialist is wired, attempt plan production (06 §2; §10.2 agent
        # rows). R5: the PLAN_DECLINED route (case now REPLAN_REQUIRED,
        # §10.2 student rows) also invokes the specialist so the agent can
        # propose a new plan (§10.2 REPLAN_REQUIRED → PLAN_PROPOSED). The
        # specialist refuses cleanly on conflict/outage/undecided proposal/
        # EC-AG-05 stop — routing already stands, case state unchanged (06 §6).
        proposal_route = (
            target_agent == ATTENDANCE_AGENT
            or (
                target_agent == INTERVENTION_AGENT
                and event.event_type == EVENT_PLAN_DECLINED
            )
        )
        if self._proposal is not None and case_id is not None and proposal_route:
            outcome = await self._proposal.produce_proposal(
                student_id=event.student_id, case_id=case_id
            )
            reasons.extend(outcome.reason_codes)
            if not outcome.proposed and outcome.refusal_code == "DATA_CONFLICT_QUARANTINE":
                # 06 §0 rule 3: never bypass a conflict quarantine.
                return self._escalate(event, [outcome.refusal_code])
            if not outcome.proposed and outcome.refusal_code:
                # Soft refusal: routing stands, traceable refusal code kept.
                reasons.append(outcome.refusal_code)

        evidence: dict[str, str | None] = {
            "event_type": event.event_type,
            "route_rule": "06_AGENT_SPEC §1",
            "urgency_band": (
                initial_urgency_band(event.event_type)
                if event.event_type in _CASE_CREATING_EVENTS
                else None
            ),
            "specialist": specialist_note,
        }

        return SupervisorRun(
            event_id=event.event_id,
            event_type=event.event_type,
            student_id=event.student_id,
            decision=DECISION_ROUTE,
            target_agent=target_agent,
            human_review_required=False,
            case_id=case_id,
            reason_codes=tuple(dict.fromkeys(reasons)),  # stable dedup
            evidence=evidence,
        )

    def _escalate(self, event: DomainEvent, reasons: list[str]) -> SupervisorRun:
        return SupervisorRun(
            event_id=event.event_id,
            event_type=event.event_type,
            student_id=event.student_id,
            decision=DECISION_ESCALATE,
            target_agent=None,
            human_review_required=True,
            case_id=None,
            reason_codes=tuple(reasons),
            evidence={
                "event_type": event.event_type,
                "route_rule": "06_AGENT_SPEC §1",
                "urgency_band": None,
                "specialist": None,
            },
        )
