# app/agents/attendance_specialist.py
# Attendance Specialist Agent — R2 stub + R3 proposal production
# (11_ROADMAP R3: "plan rows with evidence entries"). Reads engine-derived
# attendance state (06 §2: the agent does NOT calculate), asks LLMService
# (MOCK in tests/dev) for a structured proposal, validates it against
# verified backend facts, and persists one PROPOSED plan through the
# plan_proposal domain service (§10.2 agent rows).
#
# Boundaries (06 §0/§2): no SQLAlchemy, no HTTP/provider client — LLM calls
# go through LLMService only (DM-LLM01). Facts sent to the LLM carry no
# direct identifiers (06 §0 rule 11: engine numbers and subject labels only).
# Every LLMService call carries the 06 §5 audit context (caller_agent +
# prompt_version); attempt rows are persisted fail-closed by the service.

from __future__ import annotations

import json
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.agents.proposal import (
    AttendancePlanProposal,
    AttendanceProposalFacts,
    ProposalOutcome,
    ProposalValidationError,
    build_proposal_facts_context,
    is_schema_valid,
    validate_proposal_output,
)
from app.agents.supervisor import AttendanceAssessment, CaseUnavailable, DerivedStateSummary
from app.services.llm_service import LLMAuditError, LLMError, LLMSchemaError, LLMService

logger = logging.getLogger(__name__)

CONFIDENCE_HIGH = "HIGH"

# 06 §5 audit metadata: who calls LLMService, and which prompt produced the
# attempt (prompt_version is caller-supplied — bump when the prompt changes).
CALLER_AGENT = "attendance_specialist"
EXPLANATION_PROMPT_VERSION = "attendance.explanation.v1"
PROPOSAL_PROMPT_VERSION = "attendance.proposal.v1"

_REFUSAL_DATA_CONFLICT = "DATA_CONFLICT_QUARANTINE"

_SYSTEM_PROMPT = (
    "You explain an attendance risk to a mentor using ONLY the engine-computed "
    "facts provided. Never invent numbers. Reply with JSON matching the schema."
)

_PROPOSAL_SYSTEM_PROMPT = (
    "You are the attendance specialist for ASPIRE. Using ONLY the verified "
    "engine-computed facts provided, propose one structured recovery plan as "
    "JSON matching the schema. Rules: evidence must be exact copies of the "
    "provided facts in 'label: value' form; never invent facts, subjects, "
    "numbers, dates, or sources; approval_required must be true; reason_codes "
    "must include LOW_ATTENDANCE."
)


class AttendanceExplanation(BaseModel):
    """Structured LLM output for the attendance explanation (06 §2 envelope
    subset; confidence_level is a categorical enum, never a float — A-06)."""

    explanation: str
    reason_codes: list[str]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


def build_attendance_messages(state: DerivedStateSummary) -> list[dict]:
    """Deterministic prompt for the MOCK fixture key and LIVE call alike.

    Engine outputs only — attendance numbers/risk bands come from
    attendance_derived_state rows the tool read; no agent-side math.
    """
    facts = {
        "derived_state_rows": state.row_count,
        "risk_band_present": state.has_risk_band,
        "data_conflict": state.has_data_conflict,
    }
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(facts, sort_keys=True)},
    ]


def build_proposal_messages(facts: AttendanceProposalFacts) -> list[dict]:
    """Deterministic proposal prompt: de-identified backend facts only.

    The serialized context doubles as the MOCK fixture key, so tests load
    fixtures against exactly what the model sees.
    """
    context = build_proposal_facts_context(facts)
    return [
        {"role": "system", "content": _PROPOSAL_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, sort_keys=True)},
    ]


class AttendanceSpecialist:
    """R2 assess() stub + R3 produce_proposal() (plan persistence)."""

    def __init__(self, tools, llm: LLMService) -> None:
        self._tools = tools
        self._llm = llm

    async def assess(self, student_id: UUID) -> AttendanceAssessment:
        state = await self._tools.read_student_derived_state(student_id)
        messages = build_attendance_messages(state)
        try:
            result = await self._llm.complete(
                messages,
                response_model=AttendanceExplanation,
                caller_agent=CALLER_AGENT,
                prompt_version=EXPLANATION_PROMPT_VERSION,
            )
        except LLMError:
            # 06 §6 degradation: unavailable — no fabricated explanation,
            # no state change. Covers LLMSchemaError (malformed output) and
            # LLMAuditError (attempt not persisted — fail-closed, 06 §5).
            # Metadata-only logging (06 §5: never raw prompt content in
            # production).
            logger.warning(
                "Attendance specialist LLM unavailable: student_id=%s", student_id
            )
            return AttendanceAssessment(
                available=False,
                explanation=None,
                reason_codes=(),
                confidence_level=None,
            )
        # model_construct() (empty mock fixture) leaves fields unset — treat
        # missing/blank output as malformed and degrade (DM-LLM01: never
        # coerce partial output into a business object).
        explanation = getattr(result, "explanation", None)
        if not isinstance(result, AttendanceExplanation) or not explanation:
            logger.warning(
                "Attendance specialist rejected malformed LLM output: student_id=%s",
                student_id,
            )
            return AttendanceAssessment(
                available=False,
                explanation=None,
                reason_codes=(),
                confidence_level=None,
            )
        reason_codes = tuple(str(code) for code in result.reason_codes)[:5]
        return AttendanceAssessment(
            available=True,
            explanation=explanation,
            reason_codes=reason_codes,
            confidence_level=result.confidence_level,
        )

    async def produce_proposal(
        self, *, student_id: UUID, case_id: UUID
    ) -> ProposalOutcome:
        """R3: validate an LLM proposal against verified facts and persist
        exactly one PROPOSED plan via the domain service.

        Refusal paths (case state always preserved — 06 §6): conflict
        quarantine, no risk facts, LLM outage, malformed output, semantic
        validation failure, and domain-service refusals (illegal transition,
        undecided proposal, invalid evidence) all return proposed=False with
        a stable refusal code.
        """
        facts = await self._tools.read_attendance_facts(student_id)

        if facts.has_data_conflict:
            # 06 §0 rule 3: never bypass a conflict quarantine.
            logger.warning(
                "Proposal refused: data conflict quarantine student_id=%s", student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code=_REFUSAL_DATA_CONFLICT,
            )
        if facts.risk is None:
            logger.warning(
                "Proposal refused: no verified risk facts student_id=%s", student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code="NO_RISK_FACTS",
            )

        messages = build_proposal_messages(facts)
        try:
            result = await self._llm.complete(
                messages,
                response_model=AttendancePlanProposal,
                caller_agent=CALLER_AGENT,
                prompt_version=PROPOSAL_PROMPT_VERSION,
            )
        except LLMAuditError:
            # 06 §5 fail-closed: an attempt that could not be audit-recorded
            # never reaches business logic — no proposal may be represented
            # as successful (09 EC-AG-14); case state untouched.
            logger.warning(
                "Proposal refused: LLM attempt audit not persisted student_id=%s",
                student_id,
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code="AUDIT_PERSISTENCE_FAILED",
            )
        except LLMSchemaError:
            logger.warning(
                "Proposal refused: malformed LLM output student_id=%s", student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code="MALFORMED_OUTPUT",
            )
        except LLMError:
            logger.warning(
                "Proposal refused: LLM unavailable student_id=%s", student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code="LLM_UNAVAILABLE",
            )

        # Strict re-validation: an empty model_construct() (MOCK fixture
        # miss) or partially built object never reaches business logic
        # (DM-LLM01: never consume unvalidated output).
        validated_output = is_schema_valid(result)
        if validated_output is None:
            logger.warning(
                "Proposal refused: unvalidated LLM output student_id=%s", student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code="MALFORMED_OUTPUT",
            )

        try:
            validated = validate_proposal_output(validated_output, facts)
        except ProposalValidationError as exc:
            logger.warning(
                "Proposal refused: code=%s student_id=%s", exc.code, student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code=exc.code,
            )

        try:
            plan_id = await self._tools.propose_intervention_plan(
                case_id=case_id,
                reason_codes=validated.reason_codes,
                plan_actions=validated.plan_actions,
                evidence_entries=validated.evidence_entries,
            )
        except CaseUnavailable as exc:
            # Domain refusals (illegal transition, undecided proposal,
            # missing case, invalid evidence) — controlled refusal codes.
            logger.warning(
                "Proposal refused: code=%s student_id=%s", exc.code, student_id
            )
            return ProposalOutcome(
                proposed=False,
                plan_id=None,
                reason_codes=(),
                refusal_code=exc.code,
            )

        return ProposalOutcome(
            proposed=True,
            plan_id=plan_id,
            reason_codes=validated.reason_codes,
            refusal_code=None,
        )
