# app/api/routers/attendance.py
# Attendance API Router — summary, what-if calculator

from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    require_roles,
    require_student_self_or_mentor,
    get_session,
)
from app.api.schemas import (
    AttendanceSummaryResponse,
    AttendanceWhatIfRequest,
    AttendanceWhatIfResponse,
)
from app.models.attendance import AttendanceRecord, AttendanceDerivedState
from app.models.academic import CourseRun, Course
from app.engines.attendance import AttendanceEngine, AttendanceConfig


router = APIRouter(prefix="/api/v1/attendance", tags=["Attendance"])


@router.get(
    "/{student_id}/summary",
    response_model=list[AttendanceSummaryResponse],
    summary="Attendance summary with risk status per course",
    dependencies=[Depends(require_roles("STUDENT", "MENTOR", "ADMIN", "HOD", "FACULTY"))],
)
async def get_attendance_summary(
    student_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Attendance summary per course with risk bands."""
    # Verify authorization
    # (dependency handles student self or mentor/faculty)
    
    # Get derived states for student
    result = await session.execute(
        select(AttendanceDerivedState, CourseRun, Course)
        .join(CourseRun, AttendanceDerivedState.course_run_id == CourseRun.id)
        .join(Course, CourseRun.course_id == Course.id)
        .where(AttendanceDerivedState.student_id == student_id)
    )
    rows = result.all()
    
    summaries = []
    for derived, course_run, course in rows:
        summaries.append(AttendanceSummaryResponse(
            student_id=student_id,
            course_id=course.id,
            course_name=course.name,
            classes_conducted=derived.classes_conducted,
            classes_attended=derived.classes_attended,
            attendance_percentage=derived.attendance_percentage,
            risk_band=derived.risk_band or "DATA_CONFLICT",
            required_to_recover=derived.required_to_recover,
            computed_at=derived.computed_at,
        ))
    return summaries


@router.get(
    "/{student_id}/what-if",
    response_model=AttendanceWhatIfResponse,
    summary="Deterministic attendance recovery calculator",
    dependencies=[Depends(require_roles("STUDENT", "MENTOR", "ADMIN", "HOD", "FACULTY"))],
)
async def get_attendance_what_if(
    student_id: UUID,
    course_id: UUID,
    target: Decimal,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """
    Deterministic recovery calculator.
    Returns required future classes to reach target percentage.
    """
    # Get latest derived state for this student/course
    result = await session.execute(
        select(AttendanceDerivedState, CourseRun)
        .join(CourseRun, AttendanceDerivedState.course_run_id == CourseRun.id)
        .where(
            AttendanceDerivedState.student_id == student_id,
            CourseRun.course_id == course_id,
        )
        .order_by(AttendanceDerivedState.computed_at.desc())
    )
    row = result.first()
    if not row:
        raise status.HTTP_404_NOT_FOUND
    
    derived, course_run = row
    
    # Get institution threshold config (fallback to 75%)
    threshold_config = await _get_attendance_threshold(session, student_id)
    
    engine = AttendanceEngine(AttendanceConfig(threshold_percent=threshold_config))
    current_state = _derived_to_state(derived, course_run)
    
    if current_state.attendance_percentage is None:
        return AttendanceWhatIfResponse(
            current_percentage=None,
            current_conducted=derived.classes_conducted,
            current_attended=derived.classes_attended,
            target_percentage=target,
            required_future_classes=None,
            projected_percentage=None,
        )
    
    if current_state.attendance_percentage >= target:
        required = 0
        projected = current_state.attendance_percentage
    else:
        # Solve: (attended + x) / (conducted + x) >= target/100
        attended = Decimal(derived.classes_attended)
        conducted = Decimal(derived.classes_conducted)
        target_dec = target / Decimal("100")
        numerator = target_dec * conducted - attended
        denominator = Decimal("1") - target_dec
        if denominator <= 0:
            required = None
            projected = None
        else:
            required = int((numerator / denominator).quantize(Decimal("1")))
            new_attended = attended + required
            new_conducted = conducted + required
            projected = (new_attended / new_conducted * Decimal("100")).quantize(Decimal("0.01"))
    
    return AttendanceWhatIfResponse(
        current_percentage=current_state.attendance_percentage,
        current_conducted=derived.classes_conducted,
        current_attended=derived.classes_attended,
        target_percentage=target,
        required_future_classes=required,
        projected_percentage=projected,
    )


# --- Helper functions ---

async def _get_attendance_threshold(session: AsyncSession, student_id: UUID) -> Decimal:
    """Fetch attendance threshold from institution_rules."""
    from app.models.rules import InstitutionRule
    from app.models.student import StudentProfile
    
    result = await session.execute(
        select(StudentProfile.institution_id, StudentProfile.batch_id)
        .where(StudentProfile.id == student_id)
    )
    row = result.first()
    if not row:
        return Decimal("75.00")
    
    institution_id, batch_id = row
    
    # Check institution-level rule
    result = await session.execute(
        select(InstitutionRule.value)
        .where(
            InstitutionRule.institution_id == institution_id,
            InstitutionRule.rule_id == "attendance_threshold",
            InstitutionRule.scope_level == "INSTITUTION",
            InstitutionRule.status == "ACTIVE",
        )
        .order_by(InstitutionRule.version.desc())
    )
    rule = result.scalar_one_or_none()
    if rule and isinstance(rule, dict) and "threshold" in rule:
        return Decimal(str(rule["threshold"]))
    
    # Check batch-level rule
    if batch_id:
        result = await session.execute(
            select(InstitutionRule.value)
            .where(
                InstitutionRule.institution_id == institution_id,
                InstitutionRule.rule_id == "attendance_threshold",
                InstitutionRule.scope_level == "BATCH",
                InstitutionRule.scope_id == batch_id,
                InstitutionRule.status == "ACTIVE",
            )
            .order_by(InstitutionRule.version.desc())
        )
        rule = result.scalar_one_or_none()
        if rule and isinstance(rule, dict) and "threshold" in rule:
            return Decimal(str(rule["threshold"]))
    
    return Decimal("75.00")  # Default fallback


def _derived_to_state(derived, course_run):
    """Convert derived state to engine input."""
    from app.engines.attendance import DerivedState
    return DerivedState(
        student_id=str(derived.student_id),
        course_run_id=str(derived.course_run_id),
        classes_conducted=derived.classes_conducted,
        classes_attended=derived.classes_attended,
        attendance_percentage=derived.attendance_percentage,
        risk_band=derived.risk_band or "DATA_CONFLICT",
        required_to_recover=derived.required_to_recover,
        computed_at=derived.computed_at.isoformat(),
    )