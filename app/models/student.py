# app/models/student.py
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"))
    roll_number: Mapped[str] = mapped_column(String, nullable=False)
    mentor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    class_teacher_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    enrollment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    user: Mapped["User"] = relationship(foreign_keys="StudentProfile.user_id")
    batch: Mapped["Batch"] = relationship(back_populates="student_profiles")
    mentor: Mapped["User"] = relationship(foreign_keys=[mentor_id])
    class_teacher: Mapped["User"] = relationship(foreign_keys=[class_teacher_id])

    __table_args__ = (UniqueConstraint("batch_id", "roll_number", name="unique_batch_roll"),)
