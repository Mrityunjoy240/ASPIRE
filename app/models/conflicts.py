# app/models/conflicts.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    # DEC-03 (approved): server_default mirrors migration 011
    # (DEFAULT gen_random_uuid(), per 05 "all tables have" convention) — the
    # database owns id generation; without it a real-PostgreSQL insert that
    # omits id fails with "NULL identity key" (same defect audit.py documents).
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    entity_table: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    # JSONB per migration 011 (schema authority); none_as_null: Python None
    # stays SQL NULL — NOT NULL columns reject None instead of storing null.
    existing_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB(none_as_null=True), nullable=False
    )
    incoming_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB(none_as_null=True), nullable=False
    )
    source_a: Mapped[str] = mapped_column(Text, nullable=False)
    source_b: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN | RESOLVED | IGNORED
    resolver_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolution: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    resolved_at: Mapped[datetime | None]
    created_at: Mapped[datetime]

    resolver: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_data_conflicts_entity", "entity_table", "entity_id"),
        Index("idx_data_conflicts_status", "status"),
    )
