# app/models/assessment.py
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    AssessmentComponentType,
    AssessmentSubmissionStatus,
    RecordStatus,
)


class AssessmentComponent(Base):
    __tablename__ = "assessment_components"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    course_run_id: Mapped[UUID] = mapped_column(ForeignKey("course_runs.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AssessmentComponentType] = mapped_column(nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_mandatory: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    course_run: Mapped["CourseRun"] = relationship()

    __table_args__ = (
        Index("idx_assessment_components_course_run", "course_run_id"),
    )


class AssessmentSubmission(Base):
    __tablename__ = "assessment_submissions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"))
    assessment_component_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_components.id", ondelete="RESTRICT"))
    status: Mapped[AssessmentSubmissionStatus] = mapped_column(nullable=False)
    obtained_marks: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    maximum_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    submitted_at: Mapped[datetime | None]
    graded_at: Mapped[datetime | None]
    graded_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    record_status: Mapped[str] = mapped_column(String, default=RecordStatus.VERIFIED.value)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    student: Mapped["StudentProfile"] = relationship()
    component: Mapped["AssessmentComponent"] = relationship()
    grader: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("student_id", "assessment_component_id", "version", name="unique_assessment_submission"),
        Index("idx_assessment_submissions_student", "student_id"),
        Index("idx_assessment_submissions_component", "assessment_component_id"),
        Index("idx_assessment_submissions_status", "status"),
    )
