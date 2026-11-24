# app/models/tasks.py
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TaskSourceType, TaskStatus


class StudentTask(Base):
    __tablename__ = "student_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"))
    source_type: Mapped[TaskSourceType] = mapped_column(nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[datetime | None]
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING.value, nullable=False)
    explicit_priority: Mapped[int | None] = mapped_column(Integer)
    urgency_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    student: Mapped["StudentProfile"] = relationship()
    creator: Mapped["User"] = relationship()

    __table_args__ = (
        Index("idx_student_tasks_student", "student_id"),
        Index("idx_student_tasks_deadline", "deadline"),
        Index("idx_student_tasks_status", "status"),
        Index("idx_student_tasks_source", "source_type", "source_id"),
    )
