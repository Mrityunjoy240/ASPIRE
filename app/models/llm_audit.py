# app/models/llm_audit.py
# Per-attempt LLM gateway audit metadata (06 §5, 07 §4, DM-LLM01).
# Lifecycle: row committed with outcome IN_PROGRESS before the provider
# dispatch, updated to the terminal outcome after it (migration 014).
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMAttemptAudit(Base):
    __tablename__ = "llm_attempt_audit"

    # server_default mirrors migration 014 (DEFAULT gen_random_uuid()): kept
    # for SQL-level inserts, but the audit lifecycle sets `id` explicitly —
    # the terminal update keys on this pre-committed row identity.
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    caller_agent: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_schema_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_llm_attempt_audit_request", "request_id"),
        Index("idx_llm_attempt_audit_outcome", "outcome"),
        Index("idx_llm_attempt_audit_created_at", "created_at"),
    )
