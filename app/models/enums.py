# app/models/enums.py
# PostgreSQL enum types as Python enums (for type safety in models)

import enum


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    CLASS_TEACHER = "CLASS_TEACHER"
    MENTOR = "MENTOR"
    HOD = "HOD"
    ADMIN = "ADMIN"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"  # Reserved/unsupported in v1 (DM-NEW-LATE01)
    CANCELLED = "CANCELLED"


class AssessmentComponentType(str, enum.Enum):
    CIA = "CIA"
    CIA_1 = "CIA-1"
    CIA_2 = "CIA-2"
    PCIA = "PCIA"
    ESE = "ESE"
    PESE = "PESE"
    LAB = "LAB"
    ASSIGNMENT = "ASSIGNMENT"
    CLASS_TEST = "CLASS_TEST"
    ATTENDANCE = "ATTENDANCE"
    QUIZ = "QUIZ"
    PROJECT = "PROJECT"
    VIVA = "VIVA"


class AssessmentSubmissionStatus(str, enum.Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED_PENDING_EVALUATION = "SUBMITTED_PENDING_EVALUATION"
    GRADED = "GRADED"
    OFFICIAL_ZERO = "OFFICIAL_ZERO"
    WITHHELD = "WITHHELD"
    CANCELLED = "CANCELLED"


class TaskSourceType(str, enum.Enum):
    CALENDAR = "CALENDAR"
    ASSESSMENT = "ASSESSMENT"
    AI_PLAN = "AI_PLAN"
    MENTOR = "MENTOR"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SNOOZED = "SNOOZED"


class InterventionCaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    PLAN_PROPOSED = "PLAN_PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    REPLAN_REQUIRED = "REPLAN_REQUIRED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class RecordStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    CONFLICT = "CONFLICT"
    SUPERSEDED = "SUPERSEDED"


class ActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM_AGENT = "SYSTEM_AGENT"


class SourceSystem(str, enum.Enum):
    CSV_IMPORT = "CSV_IMPORT"
    MENTOR_WEB = "MENTOR_WEB"
    RULE_ENGINE = "RULE_ENGINE"
    AGENT = "AGENT"
