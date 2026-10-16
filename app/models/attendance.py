# app/models/attendance.py
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AttendanceStatus, RecordStatus


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"))
    course_run_id: Mapped[UUID] = mapped_column(ForeignKey("course_runs.id", ondelete="RESTRICT"))
    class_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # CSV_IMPORT | MANUAL_ENTRY | API
    source_id: Mapped[str | None] = mapped_column(String)
    record_status: Mapped[str] = mapped_column(String, default=RecordStatus.VERIFIED.value)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    student: Mapped["StudentProfile"] = relationship()
    course_run: Mapped["CourseRun"] = relationship()
    recorder: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("student_id", "course_run_id", "class_date", "version", name="unique_attendance_record"),
        Index("idx_attendance_records_student_course", "student_id", "course_run_id"),
        Index("idx_attendance_records_course_run_date", "course_run_id", "class_date"),
        Index("idx_attendance_records_record_status", "record_status"),
    )


class AttendanceDerivedState(Base):
    __tablename__ = "attendance_derived_state"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student_profiles.id", ondelete="RESTRICT"))
    course_run_id: Mapped[UUID] = mapped_column(ForeignKey("course_runs.id", ondelete="RESTRICT"))
    classes_conducted: Mapped[int] = mapped_column(Integer, nullable=False)
    classes_attended: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    risk_band: Mapped[str | None] = mapped_column(String)  # SAFE | WARNING | CRITICAL | DATA_CONFLICT
    required_to_recover: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(nullable=False)

    student: Mapped["StudentProfile"] = relationship()
    course_run: Mapped["CourseRun"] = relationship()

    __table_args__ = (
        UniqueConstraint("student_id", "course_run_id", name="unique_attendance_derived"),
        Index("idx_attendance_derived_state_student", "student_id"),
        Index("idx_attendance_derived_state_risk_band", "risk_band"),
    )
