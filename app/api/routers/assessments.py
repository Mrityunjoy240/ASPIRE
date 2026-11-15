# app/api/routers/assessments.py
# Assessments API Router — component breakdown & trend signals

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    require_student_self_or_mentor,
    get_session,
)
from app.api.schemas import AssessmentSummaryResponse
from app.models.assessment import AssessmentComponent, AssessmentSubmission
from app.models.academic import CourseRun, Course
from app.engines.assessment import AssessmentEngine, AssessmentScheme


router = APIRouter(prefix="/api/v1/assessments", tags=["Assessments"])


@router.get(
    "/{student_id}/summary",
    response_model=AssessmentSummaryResponse,
    summary="Assessment breakdown & trend signals per course",
    dependencies=[Depends(require_student_self_or_mentor)],
)
async def get_assessment_summary(
    student_id: UUID,
    course_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Assessment component breakdown with trend for a specific course."""
    
    # Get course run for this student/course (active semester)
    from app.models.student import StudentProfile
    from app.models.academic import Semester
    
    result = await session.execute(
        select(StudentProfile.batch_id, StudentProfile.enrollment_year)
        .where(StudentProfile.id == student_id)
    )
    student_info = result.first()
    if not student_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    
    batch_id, enrollment_year = student_info
    
    # Get current semester for batch
    result = await session.execute(
        select(Semester.id)
        .where(Semester.batch_id == batch_id, Semester.status == "ACTIVE")
        .order_by(Semester.start_date.desc())
    )
    semester_id = result.scalar_one_or_none()
    if not semester_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active semester found"
        )
    
    # Get course run
    result = await session.execute(
        select(CourseRun.id, CourseRun.course_id, Course.name)
        .join(Course, CourseRun.course_id == Course.id)
        .where(
            CourseRun.course_id == course_id,
            CourseRun.semester_id == semester_id,
        )
    )
    course_run = result.first()
    if not course_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course run not found"
        )
    
    course_run_id, _, course_name = course_run
    
    # Get assessment components for this course run
    result = await session.execute(
        select(AssessmentComponent).where(AssessmentComponent.course_run_id == course_run_id)
    )
    components = result.scalars().all()
    
    # Get submissions
    result = await session.execute(
        select(AssessmentSubmission)
        .where(
            AssessmentSubmission.student_id == student_id,
            AssessmentSubmission.assessment_component_id.in_([c.id for c in components]),
        )
    )
    submissions = result.scalars().all()
    
    # Build scheme for engine
    scheme = AssessmentScheme(components=[
        {
            "id": str(c.id),
            "name": c.name,
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "weight_percent": float(c.weight_percent) if c.weight_percent else None,
            "is_mandatory": c.is_mandatory,
        }
        for c in components
    ])
    
    # Compute via engine
    engine = AssessmentEngine(scheme)
    state = engine.compute(submissions)
    
    # Build component responses
    component_responses = []
    for sub in submissions:
        comp = next((c for c in components if c.id == sub.assessment_component_id), None)
        if not comp:
            continue
        
        percentage = None
        if sub.obtained_marks is not None and sub.maximum_marks > 0:
            percentage = (sub.obtained_marks / sub.maximum_marks * Decimal("100")).quantize(Decimal("0.01"))
        
        component_responses.append({
            "id": sub.id,
            "component_id": sub.assessment_component_id,
            "component_name": comp.name,
            "component_type": comp.type.value if hasattr(comp.type, 'value') else str(comp.type),
            "status": sub.status.value if hasattr(sub.status, 'value') else str(sub.status),
            "obtained_marks": sub.obtained_marks,
            "maximum_marks": sub.maximum_marks,
            "percentage": percentage,
            "weight_percent": comp.weight_percent,
            "submitted_at": sub.submitted_at,
            "graded_at": sub.graded_at,
        })
    
    return AssessmentSummaryResponse(
        student_id=student_id,
        course_id=course_id,
        course_name=course_name,
        weighted_average=state.weighted_average,
        trend=state.trend,
        components=component_responses,
        missing_components=state.missing_components,
    )


# Import Decimal here for the inline usage
from decimal import Decimal
