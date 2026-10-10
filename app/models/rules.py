# app/models/rules.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InstitutionRule(Base):
    __tablename__ = "institution_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # DEC-02 (approved): every rule is institution-owned; NOT NULL enforced by
    # migration 013 (012 originally omitted it). No global rules.
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    rule_id: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., 'attendance_threshold', 'assessment_scheme'
    scope_level: Mapped[str] = mapped_column(Text, nullable=False)  # INSTITUTION | BATCH | PROGRAMME | SEMESTER
    scope_id: Mapped[UUID | None] = mapped_column()
    # JSONB per migration 012 (schema authority); none_as_null: a Python None
    # becomes SQL NULL and is rejected by the NOT NULL contract.
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB(none_as_null=True), nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    effective_to: Mapped[datetime | None]
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    institution: Mapped["Institution"] = relationship()
    updater: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("institution_id", "rule_id", "scope_level", "scope_id", "version", name="unique_institution_rule"),
        Index("idx_institution_rules_institution", "institution_id"),
        Index("idx_institution_rules_scope", "scope_level", "scope_id"),
        Index("idx_institution_rules_effective", "effective_from", "effective_to"),
    )
