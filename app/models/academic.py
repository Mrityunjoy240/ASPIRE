# app/models/academic.py
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    total_semesters: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    institution: Mapped["Institution"] = relationship()
    batches: Mapped[list["Batch"]] = relationship(back_populates="programme")

    __table_args__ = (UniqueConstraint("institution_id", "code", name="unique_programme_code"),)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    programme_id: Mapped[UUID] = mapped_column(ForeignKey("programmes.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    institution: Mapped["Institution"] = relationship()
    programme: Mapped["Programme"] = relationship(back_populates="batches")
    semesters: Mapped[list["Semester"]] = relationship(back_populates="batch")
    student_profiles: Mapped[list["StudentProfile"]] = relationship(back_populates="batch")
    course_runs: Mapped[list["CourseRun"]] = relationship(back_populates="batch")


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"))
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, default="UPCOMING")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    batch: Mapped["Batch"] = relationship(back_populates="semesters")
    course_runs: Mapped[list["CourseRun"]] = relationship(back_populates="semester")

    __table_args__ = (UniqueConstraint("batch_id", "semester_number", name="unique_batch_semester"),)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    credit_hours: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    institution: Mapped["Institution"] = relationship()
    course_runs: Mapped[list["CourseRun"]] = relationship(back_populates="course")

    __table_args__ = (UniqueConstraint("institution_id", "code", name="unique_course_code"),)


class CourseRun(Base):
    __tablename__ = "course_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id", ondelete="RESTRICT"))
    semester_id: Mapped[UUID] = mapped_column(ForeignKey("semesters.id", ondelete="RESTRICT"))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id", ondelete="RESTRICT"))
    faculty_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    total_classes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    course: Mapped["Course"] = relationship(back_populates="course_runs")
    semester: Mapped["Semester"] = relationship(back_populates="course_runs")
    batch: Mapped["Batch"] = relationship(back_populates="course_runs")
    faculty: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("course_id", "semester_id", "batch_id", name="unique_course_run"),
    )
