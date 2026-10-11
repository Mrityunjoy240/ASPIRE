# app/agents/attendance_specialist.py
# Attendance Specialist Agent — R2 stub (11_ROADMAP R2: "route to attendance
# specialist stub"). Reads engine-derived attendance state (06 §2: the agent
# does NOT calculate), asks LLMService (MOCK in tests/dev) for a structured
# human-readable explanation, and returns it. NOTHING is persisted: plan
# production (PLAN_PROPOSED rows, DEC-01 evidence) is roadmap R3.
#
# Boundaries (06 §0/§2): no SQLAlchemy, no HTTP/provider client — LLM calls
# go through LLMService only (DM-LLM01). Facts sent to the LLM carry no
# direct identifiers (06 §0 rule 11: UUIDs and engine numbers only).

from __future__ import annotations

import json
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.agents.supervisor import AttendanceAssessment, DerivedStateSummary
from app.services.llm_service import LLMError, LLMService

logger = logging.getLogger(__name__)

CONFIDENCE_HIGH = "HIGH"

_SYSTEM_PROMPT = (
    "You explain an attendance risk to a mentor using ONLY the engine-computed "
    "facts provided. Never invent numbers. Reply with JSON matching the schema."
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


class AttendanceSpecialist:
    """R2 stub: read derived state → LLMService structured explanation."""

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
            )
        except LLMError:
            # 06 §6 degradation: unavailable — no fabricated explanation,
            # no state change. Metadata-only logging (06 §5: never raw
            # prompt content in production).
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
