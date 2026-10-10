# app/api/schemas.py
# Pydantic response/request models for API contracts (DM-API01)

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, model_validator


class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    version: str
    env: str


# --- Student Schemas ---

class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    batch_id: UUID
    roll_number: str
    mentor_id: Optional[UUID]
    class_teacher_id: Optional[UUID]
    enrollment_year: int
    created_at: datetime
    updated_at: datetime


class StudentSelfResponse(StudentProfileResponse):
    """Extended profile for self-view (includes computed fields)."""
    pass


class StudentMentorViewResponse(StudentProfileResponse):
    """Profile for mentor/faculty view (includes risk signals)."""
    attendance_risk_band: Optional[str] = None
    assessment_trend: Optional[str] = None
    overdue_tasks_count: int = 0


# --- Attendance Schemas ---

class AttendanceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: UUID
    course_id: UUID
    course_name: str
    classes_conducted: int
    classes_attended: int
    attendance_percentage: Optional[Decimal]
    risk_band: str  # SAFE | WARNING | CRITICAL | DATA_CONFLICT
    required_to_recover: Optional[int]
    computed_at: datetime


class AttendanceWhatIfRequest(BaseModel):
    target_percentage: Decimal = Field(..., gt=0, le=100, description="Target attendance % (e.g., 75.0)")


class AttendanceWhatIfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    current_percentage: Optional[Decimal]
    current_conducted: int
    current_attended: int
    target_percentage: Decimal
    required_future_classes: Optional[int]
    projected_percentage: Optional[Decimal]
    disclaimer: str = "Planning estimate — not an official academic eligibility decision."


# --- Assessment Schemas ---

class AssessmentComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    type: str
    max_marks: Decimal
    weight_percent: Optional[Decimal]
    is_mandatory: bool


class AssessmentSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    component_id: UUID
    component_name: str
    component_type: str
    status: str  # GRADED | SUBMITTED_PENDING_EVALUATION | OFFICIAL_ZERO | WITHHELD | CANCELLED | NOT_SUBMITTED
    obtained_marks: Optional[Decimal]
    maximum_marks: Decimal
    percentage: Optional[Decimal]
    weight_percent: Optional[Decimal]
    submitted_at: Optional[datetime]
    graded_at: Optional[datetime]


class AssessmentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: UUID
    course_id: UUID
    course_name: str
    weighted_average: Optional[Decimal]
    trend: str  # IMPROVING | STABLE | DECLINING | TREND_NOT_ESTABLISHED
    components: list[AssessmentSubmissionResponse]
    missing_components: list[str]


# --- Task Schemas ---

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    source_type: str
    source_id: UUID
    created_by: UUID
    title: str
    deadline: Optional[datetime]
    status: str  # PENDING | COMPLETED | SNOOZED
    explicit_priority: Optional[int]
    urgency_score: Optional[int]
    created_at: datetime
    updated_at: datetime


class TaskCompleteRequest(BaseModel):
    pass  # No body needed for completion


class TaskCompleteResponse(BaseModel):
    task_id: UUID
    status: str
    completed_at: datetime


# --- Case/Intervention Schemas ---

class CaseQueueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: UUID
    student_id: UUID
    student_name: str
    student_roll: str
    urgency_band: str  # URGENT | ATTENTION | MONITOR
    status: str  # OPEN | IN_REVIEW | PLAN_PROPOSED | ...
    trigger_events: list[str]
    opened_at: datetime
    nearest_exam_days: Optional[int]
    days_since_last_action: Optional[int]


class CaseApproveRequest(BaseModel):
    mentor_notes: Optional[str] = None
    decision: Literal["APPROVED", "EDITED", "REJECTED"]


class CaseApproveResponse(BaseModel):
    case_id: UUID
    mentor_decision: str
    acted_at: datetime


class StudentDecisionRequest(BaseModel):
    """Student plan decision (03_SYSTEM_SPEC §10.2 student rows).

    ACCEPTED / CUSTOMIZED move the case PLAN_PROPOSED → PENDING_APPROVAL
    (event PLAN_ACCEPTED); DECLINED moves it PLAN_PROPOSED → REPLAN_REQUIRED
    (event PLAN_DECLINED). The decline reason is optional (02_USER_JOURNEYS
    1.1 Step 6; 05 §9 `student_reason`) and may only accompany DECLINED.
    """
    decision: Literal["ACCEPTED", "CUSTOMIZED", "DECLINED"]
    plan_actions: list[dict] | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check_plan_actions(self) -> "StudentDecisionRequest":
        # 02_USER_JOURNEYS 1.1 Step 6: "There is no silent default."
        if self.decision == "CUSTOMIZED" and not self.plan_actions:
            raise ValueError(
                "plan_actions is required and must be non-empty for a CUSTOMIZED decision"
            )
        if self.decision != "CUSTOMIZED" and self.plan_actions is not None:
            raise ValueError(
                "plan_actions may only accompany a CUSTOMIZED decision"
            )
        if self.decision != "DECLINED" and self.reason is not None:
            raise ValueError(
                "reason may only accompany a DECLINED decision"
            )
        return self


class StudentDecisionResponse(BaseModel):
    case_id: UUID
    student_decision: str
    decided_at: datetime
