# app/models/audit.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    # server_default mirrors migration 007 (DEFAULT gen_random_uuid()): the
    # column is omitted from INSERTs and RETURNING restores the identity —
    # without it a real-PostgreSQL flush fails with "NULL identity key"
    # (first surfaced by the genuine two-connection concurrency test).
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_type: Mapped[str] = mapped_column(String, nullable=False)  # USER | SYSTEM_AGENT
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_table: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    # JSONB per migration 007 (schema authority); none_as_null keeps Python
    # None as SQL NULL so the nullable columns match the migration contract.
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    new_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    actor: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_audit_log_actor", "actor_id"),
        Index("idx_audit_log_entity", "entity_table", "entity_id"),
        Index("idx_audit_log_action", "action_type"),
        Index("idx_audit_log_created_at", "created_at"),
    )
