# app/models/scheduler.py
# Scheduler occurrence bookkeeping (DM-AG03, migration 015).
# Technical deduplication state for time-based event emission: one row per
# logical occurrence, CLAIMED before publish, EMITTED after publish.
# Never business state — the scheduler mutates only this table.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SchedulerOccurrence(Base):
    __tablename__ = "scheduler_occurrences"

    event_type: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[UUID] = mapped_column(primary_key=True)
    trigger_value: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    # server_default mirrors migration 015 (DEFAULT 'CLAIMED' / DEFAULT now());
    # the scheduler sets both fields explicitly on claim.
    state: Mapped[str] = mapped_column(
        Text, nullable=False, default="CLAIMED", server_default=text("'CLAIMED'")
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
    emitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
