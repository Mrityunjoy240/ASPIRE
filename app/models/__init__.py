# app/models/__init__.py
# SQLAlchemy 2.x models - export all

from app.models.academic import Batch, Course, CourseRun, Programme, Semester
from app.models.assessment import (
    AssessmentComponent,
    AssessmentComponentType,
    AssessmentSubmission,
    AssessmentSubmissionStatus,
)
from app.models.attendance import AttendanceDerivedState, AttendanceRecord, AttendanceStatus
from app.models.audit import AuditLog
from app.models.conflicts import DataConflict
from app.models.institutions import Institution
from app.models.intervention import InterventionCase, InterventionCaseStatus, InterventionPlan
from app.models.learning import DocumentChunk, LearningDocument
from app.models.llm_audit import LLMAttemptAudit
from app.models.rules import InstitutionRule
from app.models.scheduler import SchedulerOccurrence
from app.models.student import StudentProfile
from app.models.tasks import StudentTask, TaskSourceType, TaskStatus
from app.models.users import User, UserRole, UserRoleAssignment

__all__ = [
    "Institution",
    "User",
    "UserRole",
    "UserRoleAssignment",
    "Programme",
    "Batch",
    "Semester",
    "Course",
    "CourseRun",
    "StudentProfile",
    "AttendanceRecord",
    "AttendanceDerivedState",
    "AttendanceStatus",
    "AssessmentComponent",
    "AssessmentSubmission",
    "AssessmentComponentType",
    "AssessmentSubmissionStatus",
    "AuditLog",
    "LLMAttemptAudit",
    "StudentTask",
    "TaskSourceType",
    "TaskStatus",
    "InterventionCase",
    "InterventionPlan",
    "InterventionCaseStatus",
    "LearningDocument",
    "DocumentChunk",
    "DataConflict",
    "InstitutionRule",
    "SchedulerOccurrence",
]
