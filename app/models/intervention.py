# app/models/intervention.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import FollowUpStatus, FollowUpTriggerType, InterventionCaseStatus


class InterventionCase(Base):
    __tablename__ = "intervention_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"))
    mentor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    status: Mapped[InterventionCaseStatus] = mapped_column(default=InterventionCaseStatus.OPEN.value, nullable=False)
    urgency_band: Mapped[str] = mapped_column(String, nullable=False)  # URGENT | ATTENTION | MONITOR
    # JSONB per migration 009 (schema authority); sqlite variant serves only
    # the F-01 in-memory real-query test, where JSONB cannot compile DDL.
    # none_as_null: Python None stays SQL NULL (nullable contract).
    trigger_events: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON, "sqlite"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    student: Mapped["StudentProfile"] = relationship()
    mentor: Mapped["User"] = relationship()
    plans: Mapped[list["InterventionPlan"]] = relationship(back_populates="case")

    __table_args__ = (
        Index("idx_intervention_cases_student", "student_id"),
        Index("idx_intervention_cases_mentor", "mentor_id"),
        Index("idx_intervention_cases_status", "status"),
        Index("idx_intervention_cases_urgency", "urgency_band"),
    )


class InterventionPlan(Base):
    __tablename__ = "intervention_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("intervention_cases.id", ondelete="RESTRICT"))
    created_by: Mapped[str] = mapped_column(Text, nullable=False)  # 'SYSTEM_AGENT' or user UUID
    status: Mapped[str] = mapped_column(Text, nullable=False)  # PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED
    # JSONB per migration 009 (sqlite variant: see trigger_events note).
    plan_actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON, "sqlite"), nullable=False
    )
    # TEXT[] NOT NULL per migration 009 (the schema authority). The sqlite
    # variant exists only for the in-memory real-query regression tests,
    # where a PostgreSQL ARRAY type cannot compile DDL.
    reason_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"), nullable=False
    )
    # JSONB per migration 009 (sqlite variant: see trigger_events note).
    # DEC-01: canonical shape is an ARRAY of structured evidence entries
    # {id, label, value, source, timestamp} — validated by
    # app.services.evidence (schema documented in 05_DATA_API_CONTRACTS).
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB(none_as_null=True).with_variant(JSON, "sqlite"), nullable=False
    )
    student_decision: Mapped[str | None] = mapped_column(Text)  # ACCEPTED | DECLINED | CUSTOMIZED
    student_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None]
    mentor_decision: Mapped[str | None] = mapped_column(Text)  # APPROVED | EDITED | REJECTED
    mentor_notes: Mapped[str | None] = mapped_column(Text)
    mentor_acted_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    case: Mapped["InterventionCase"] = relationship(back_populates="plans")

    __table_args__ = (
        Index("idx_intervention_plans_case", "case_id"),
        Index("idx_intervention_plans_status", "status"),
    )


class InterventionFollowUp(Base):
    """Follow-up row (migrations 016 + 017, ADR-004 / 05 §9).

    Lifecycle SCHEDULED → FULFILLED → EVALUATED, or SCHEDULED → CANCELLED
    (superseded sibling, ADR-004 Amendment 1); the status flip under
    SELECT ... FOR UPDATE is the durable consumer-side dedup. due_at is
    CUSTOM_DATE only; event-driven types carry NULL and are fulfilled by
    their policy trigger events (02 §2.1 Step 6).
    """

    __tablename__ = "intervention_follow_ups"

    # DEC-03 pattern (review F6): server_default mirrors migration 017
    # (DEFAULT gen_random_uuid()) so real-PostgreSQL inserts that omit id
    # work — the ORM must not disagree with the schema authority.
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("intervention_cases.id", ondelete="RESTRICT"), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # FollowUpTriggerType values (06 §4 policies + CUSTOM_DATE)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=FollowUpStatus.SCHEDULED.value
    )
    due_at: Mapped[datetime | None] = mapped_column(nullable=True)  # CUSTOM_DATE only
    triggered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    evaluation_window_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)  # RESOLVED | REPLAN_REQUIRED
    created_by: Mapped[str] = mapped_column(Text, nullable=False)  # 'SYSTEM' or user UUID
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    case: Mapped["InterventionCase"] = relationship()

    __table_args__ = (
        Index("idx_intervention_follow_ups_case", "case_id"),
        Index("idx_intervention_follow_ups_status", "status"),
        Index("idx_intervention_follow_ups_due", "status", "due_at"),
        Index("idx_intervention_follow_ups_window", "status", "evaluation_window_ends_at"),
    )


# Re-export for convenience at call sites that import the model module.
__all__ = [
    "FollowUpStatus",
    "FollowUpTriggerType",
    "InterventionCase",
    "InterventionFollowUp",
    "InterventionPlan",
]
