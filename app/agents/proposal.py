# app/agents/proposal.py
# Attendance Specialist proposal production (11_ROADMAP R3; 06_AGENT_SPEC §2
# output contract; DEC-01 evidence boundary).
#
# Pure module (no SQLAlchemy, no HTTP): strict LLM response schema, semantic
# validation against verified backend facts, and canonical DEC-01 evidence
# building. The LLM output `evidence` is list[str] claims (CONSTITUTION A-05);
# every claim must exactly match a backend-rendered fact — unverifiable
# claims refuse persistence. Provenance (source/timestamp) is backend-only
# and structurally impossible for the model to supply (extra="forbid").

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.evidence import EvidenceProvenance, build_evidence_entry

# Approved reason-code vocabulary for the attendance path (06 §2 example
# codes restricted to what R3 backend facts can support — EXAM_APPROACHING
# needs Calendar Engine output, roadmap R4, and is refused until then).
ALLOWED_REASON_CODES: frozenset[str] = frozenset({"LOW_ATTENDANCE"})

MAX_PLAN_ACTIONS = 5
MAX_EVIDENCE_CLAIMS = 20
MAX_TOPIC_LENGTH = 200
MAX_SUBJECT_LENGTH = 200
MIN_DURATION_MIN = 5
MAX_DURATION_MIN = 480
MAX_ATTEND_COUNT = 20


class AttendClassAction(BaseModel):
    """Propose attending upcoming classes in a subject the student is
    enrolled in (subject must exist in the verified backend context)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ATTEND_CLASS"]
    subject: str = Field(min_length=1, max_length=MAX_SUBJECT_LENGTH)
    count: int = Field(ge=1, le=MAX_ATTEND_COUNT)


class StudyBlockAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["STUDY_BLOCK"]
    topic: str = Field(min_length=1, max_length=MAX_TOPIC_LENGTH)
    duration_min: int = Field(ge=MIN_DURATION_MIN, le=MAX_DURATION_MIN)


class PracticeQuizAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["PRACTICE_QUIZ"]
    topic: str = Field(min_length=1, max_length=MAX_TOPIC_LENGTH)


PlanAction = Annotated[
    AttendClassAction | StudyBlockAction | PracticeQuizAction,
    Field(discriminator="type"),
]


class AttendancePlanProposal(BaseModel):
    """06 §2 specialist output envelope as the strict LLM structured-output
    schema. Extra fields are rejected so model-invented keys (e.g. a
    fabricated `source`/`timestamp` on evidence) can never pass validation."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["PLAN_PROPOSED"]
    reason_codes: list[str] = Field(min_length=1, max_length=10)
    evidence: list[str] = Field(min_length=1, max_length=MAX_EVIDENCE_CLAIMS)
    actions: list[PlanAction] = Field(min_length=1, max_length=MAX_PLAN_ACTIONS)
    approval_required: bool
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True, slots=True)
class SubjectAttendanceFact:
    """One attendance_derived_state row plus its course name (backend only)."""

    course_run_id: UUID
    subject: str
    classes_conducted: int
    classes_attended: int
    attendance_percentage: float | None
    risk_band: str | None  # SAFE | WARNING | CRITICAL | DATA_CONFLICT
    required_to_recover: int | None
    computed_at: datetime


@dataclass(frozen=True, slots=True)
class AttendanceProposalFacts:
    """Verified facts for one proposal: the primary risk subject (worst
    band, deterministic tie-break), every enrolled subject name, and the
    institution threshold with its own provenance (None = no rule row —
    never defaulted, per DEC-01 fail-closed provenance)."""

    risk: SubjectAttendanceFact | None
    all_subjects: tuple[str, ...]
    threshold: float | None
    threshold_observed_at: datetime | None
    has_data_conflict: bool


@dataclass(frozen=True, slots=True)
class VerifiedFact:
    label: str
    value: str | int | float | bool
    source: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class ValidatedProposal:
    reason_codes: tuple[str, ...]
    plan_actions: tuple[dict, ...]
    evidence_entries: tuple[dict, ...]
    confidence_level: str


@dataclass(frozen=True, slots=True)
class ProposalOutcome:
    """Traceable result of one produce_proposal invocation (R3).

    proposed=True → plan persisted (plan_id set). proposed=False → refused;
    refusal_code names the controlled failure (06 §6 degradation — the case
    keeps its previous valid state; nothing is fabricated).
    """

    proposed: bool
    plan_id: UUID | None
    reason_codes: tuple[str, ...]
    refusal_code: str | None


class ProposalValidationError(Exception):
    """Refusal: the LLM proposal failed semantic validation (06 §6 — never
    coerced, never partially accepted)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def build_proposal_facts_context(facts: AttendanceProposalFacts) -> dict:
    """De-identified LLM context: engine numbers and subject labels only —
    no names, emails, roll numbers, UUIDs, or raw records (06 §0 rule 11)."""
    risk = facts.risk
    context: dict = {
        "subjects": list(facts.all_subjects),
        "data_conflict": facts.has_data_conflict,
    }
    if risk is not None:
        context.update(
            {
                "risk_subject": risk.subject,
                "risk_band": risk.risk_band,
                "attendance_percentage": risk.attendance_percentage,
                "classes_attended": risk.classes_attended,
                "classes_conducted": risk.classes_conducted,
                "required_to_recover": risk.required_to_recover,
            }
        )
    if facts.threshold is not None:
        context["threshold"] = facts.threshold
    return context


def _risk_fact_registry(facts: AttendanceProposalFacts) -> dict[str, VerifiedFact]:
    """Facts the LLM may claim, each with backend provenance.

    attendance_percentage/threshold are floats (Numeric(5,2)/rule value);
    rendering must match the context serialization exactly so claims are
    checkable. Threshold is excluded when no rule row supplied provenance.
    """
    risk = facts.risk
    if risk is None:
        return {}
    registry: dict[str, VerifiedFact] = {}
    if risk.attendance_percentage is not None:
        registry["attendance_percentage"] = VerifiedFact(
            label="attendance_percentage",
            value=risk.attendance_percentage,
            source="attendance_derived_state",
            timestamp=risk.computed_at,
        )
    if risk.required_to_recover is not None:
        registry["required_to_recover"] = VerifiedFact(
            label="required_to_recover",
            value=risk.required_to_recover,
            source="attendance_derived_state",
            timestamp=risk.computed_at,
        )
    registry["classes_attended"] = VerifiedFact(
        label="classes_attended",
        value=risk.classes_attended,
        source="attendance_derived_state",
        timestamp=risk.computed_at,
    )
    registry["classes_conducted"] = VerifiedFact(
        label="classes_conducted",
        value=risk.classes_conducted,
        source="attendance_derived_state",
        timestamp=risk.computed_at,
    )
    if facts.threshold is not None and facts.threshold_observed_at is not None:
        registry["threshold"] = VerifiedFact(
            label="threshold",
            value=facts.threshold,
            source="institution_rules",
            timestamp=facts.threshold_observed_at,
        )
    return registry


def _render_claim(fact: VerifiedFact) -> str:
    return f"{fact.label}: {fact.value}"


def validate_proposal_output(
    output: AttendancePlanProposal,
    facts: AttendanceProposalFacts,
) -> ValidatedProposal:
    """Semantic validation of a schema-valid LLM proposal against verified
    backend facts. Raises ProposalValidationError — never coerces.

    Rules enforced:
    * approval_required must stay true (humans approve consequential
      decisions — Constitution; 06 §2 example sets it true).
    * reason codes ⊆ approved vocabulary; LOW_ATTENDANCE always required on
      the attendance path.
    * ATTEND_CLASS.subject must be a verified enrolled subject; count may
      not exceed the engine's required_to_recover when known (proposal
      heuristic — never contradicts the engine).
    * every evidence claim must exactly match a backend-rendered fact;
      entries are rebuilt from backend values + provenance (the model's
      string is never the persisted value or metadata source).
    """
    if facts.risk is None:
        raise ProposalValidationError(
            "NO_RISK_FACTS",
            "no verified attendance risk facts — proposal refused",
        )
    if not output.approval_required:
        raise ProposalValidationError(
            "APPROVAL_REQUIRED_FALSE",
            "approval_required must be true (06 §2; human approval gate)",
        )

    reason_codes = tuple(dict.fromkeys(output.reason_codes))
    for code in reason_codes:
        if code not in ALLOWED_REASON_CODES:
            raise ProposalValidationError(
                "UNSUPPORTED_REASON_CODE",
                f"reason code '{code}' is not in the approved vocabulary",
            )
    if "LOW_ATTENDANCE" not in reason_codes:
        raise ProposalValidationError(
            "MISSING_REASON_CODE",
            "attendance proposals must carry LOW_ATTENDANCE",
        )

    subjects = set(facts.all_subjects)
    plan_actions: list[dict] = []
    for action in output.actions:
        if isinstance(action, AttendClassAction):
            if action.subject not in subjects:
                raise ProposalValidationError(
                    "UNKNOWN_SUBJECT",
                    f"subject '{action.subject}' is not a verified enrolled subject",
                )
            required = facts.risk.required_to_recover
            if required is not None and required >= 1 and action.count > required:
                raise ProposalValidationError(
                    "COUNT_EXCEEDS_REQUIREMENT",
                    (
                        f"count {action.count} exceeds engine required_to_recover "
                        f"{required} — proposals never contradict the engine"
                    ),
                )
        plan_actions.append(action.model_dump())

    registry = _risk_fact_registry(facts)
    allowed_claims = {_render_claim(fact): fact for fact in registry.values()}
    evidence_entries: list[dict] = []
    used_labels: set[str] = set()
    for claim in output.evidence:
        normalized = claim.strip()
        fact = allowed_claims.get(normalized)
        if fact is None:
            raise ProposalValidationError(
                "EVIDENCE_UNVERIFIED",
                f"evidence claim does not match any verified backend fact: {normalized!r}",
            )
        if fact.label in used_labels:
            continue  # duplicate claim of the same fact — one entry
        used_labels.add(fact.label)
        evidence_entries.append(
            build_evidence_entry(
                fact.label,
                fact.value,
                provenance=EvidenceProvenance(source=fact.source, timestamp=fact.timestamp),
            )
        )
    if not evidence_entries:
        raise ProposalValidationError(
            "NO_EVIDENCE",
            "no verifiable evidence claims — nothing may be persisted",
        )

    return ValidatedProposal(
        reason_codes=reason_codes,
        plan_actions=tuple(plan_actions),
        evidence_entries=tuple(evidence_entries),
        confidence_level=output.confidence_level,
    )


def is_schema_valid(raw: object) -> AttendancePlanProposal | None:
    """Validate a raw LLM result against the strict envelope; None = invalid
    (used where a caller must distinguish malformed output from outages).

    Instances are re-validated through model_dump(): an empty
    model_construct() (MOCK fixture miss) or a partially built object dumps
    to missing/invalid fields and is rejected like any other malformed reply.
    """
    candidate = raw.model_dump() if isinstance(raw, BaseModel) else raw
    try:
        return AttendancePlanProposal.model_validate(candidate)
    except (ValidationError, ValueError, TypeError):
        return None


__all__ = [
    "ALLOWED_REASON_CODES",
    "AttendClassAction",
    "AttendancePlanProposal",
    "AttendanceProposalFacts",
    "PracticeQuizAction",
    "ProposalOutcome",
    "ProposalValidationError",
    "StudyBlockAction",
    "SubjectAttendanceFact",
    "ValidatedProposal",
    "VerifiedFact",
    "build_proposal_facts_context",
    "is_schema_valid",
    "validate_proposal_output",
]
