# app/models/conflicts.py
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    entity_table: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    existing_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    incoming_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_a: Mapped[str] = mapped_column(Text, nullable=False)
    source_b: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN | RESOLVED | IGNORED
    resolver_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    resolved_at: Mapped[datetime | None]
    created_at: Mapped[datetime]

    resolver: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_data_conflicts_entity", "entity_table", "entity_id"),
        Index("idx_data_conflicts_status", "status"),
    )
