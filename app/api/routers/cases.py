# app/api/routers/cases.py
# Cases/Intervention API Router — mentor queue, approval

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    require_mentor_or_admin,
    get_session,
)
from app.api.schemas import CaseQueueItemResponse, CaseApproveRequest, CaseApproveResponse
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile
from app.models.users import User
from app.models.enums import InterventionCaseStatus
from app.engines.priority import PriorityEngine


router = APIRouter(prefix="/api/v1/cases", tags=["Intervention Cases"])


@router.get(
    "/queue",
    response_model=list[CaseQueueItemResponse],
    summary="Mentor priority triage queue",
    dependencies=[Depends(require_mentor_or_admin)],
)
async def get_mentor_queue(
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor queue ordered by Urgency Band → Exam Proximity → Days Since Last Action (DM-SS03)."""
    
    # Get cases for this mentor (or all if admin/HOD)
    if auth.is_admin() or auth.has_role("HOD"):
        result = await session.execute(
            select(InterventionCase)
            .where(InterventionCase.status.in_([
                InterventionCaseStatus.OPEN,
                InterventionCaseStatus.IN_REVIEW,
                InterventionCaseStatus.PLAN_PROPOSED,
                InterventionCaseStatus.PENDING_APPROVAL,
                InterventionCaseStatus.ACTIVE,
                InterventionCaseStatus.MONITORING,
                InterventionCaseStatus.REPLAN_REQUIRED,
            ]))
        )
    else:
        # Mentor sees only their assigned cases
        result = await session.execute(
            select(InterventionCase)
            .where(
                InterventionCase.mentor_id == auth.user_id,
                InterventionCase.status.in_([
                    InterventionCaseStatus.OPEN,
                    InterventionCaseStatus.IN_REVIEW,
                    InterventionCaseStatus.PLAN_PROPOSED,
                    InterventionCaseStatus.PENDING_APPROVAL,
                    InterventionCaseStatus.ACTIVE,
                    InterventionCaseStatus.MONITORING,
                    InterventionCaseStatus.REPLAN_REQUIRED,
                ])
            )
        )
    
    cases = result.scalars().all()
    
    # Build queue items with student info and priority
    queue_items = []
    priority_engine = PriorityEngine()
    
    for case in cases:
        # Get student profile
        result = await session.execute(
            select(StudentProfile, User)
            .join(User, StudentProfile.user_id == User.id)
            .where(StudentProfile.id == case.student_id)
        )
        student_row = result.first()
        if not student_row:
            continue
        student_profile, user = student_row
        
        # Get student's pending tasks for urgency calculation
        result = await session.execute(
            select(StudentTask)
            .where(
                StudentTask.student_id == case.student_id,
                StudentTask.status == "PENDING",
            )
        )
        tasks = result.scalars().all()
        
        # Calculate urgency for each task
        student_tasks_data = []
        for task in tasks:
            urgency = priority_engine.calculate_task_urgency(task)
            student_tasks_data.append({
                "urgency_band": urgency.urgency_band.value,
                "days_until_deadline": urgency.days_until_deadline,
            })
        
        # Get nearest exam
        nearest_exam_days = await _get_nearest_exam_days(session, case.student_id)
        
        # Days since last mentor action
        days_since_last_action = None
        if case.updated_at:
            delta = datetime.now(timezone.utc) - case.updated_at
            days_since_last_action = delta.days
        
        queue_items.append(CaseQueueItemResponse(
            case_id=case.id,
            student_id=case.student_id,
            student_name=user.full_name,
            student_roll=student_profile.roll_number,
            urgency_band=case.urgency_band,
            status=case.status.value if hasattr(case.status, 'value') else str(case.status),
            trigger_events=case.trigger_events or [],
            opened_at=case.opened_at,
            nearest_exam_days=nearest_exam_days,
            days_since_last_action=days_since_last_action,
        ))
    
    # Sort per DM-SS03: Urgency Band → Exam Proximity → Days Since Last Action
    urgency_rank = {"URGENT": 0, "ATTENTION": 1, "MONITOR": 2}
    queue_items.sort(key=lambda x: (
        urgency_rank.get(x.urgency_band, 2),
        x.nearest_exam_days if x.nearest_exam_days is not None else 999,
        x.days_since_last_action if x.days_since_last_action is not None else 999,
    ))
    
    return queue_items


@router.post(
    "/{case_id}/approve",
    response_model=CaseApproveResponse,
    summary="Mentor human-in-the-loop approval",
    dependencies=[Depends(require_mentor_or_admin)],
)
async def approve_case(
    case_id: UUID,
    request: CaseApproveRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor approves/edits/rejects intervention plan."""
    result = await session.execute(
        select(InterventionCase).where(InterventionCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise status.HTTP_404_NOT_FOUND
    
    if not (auth.is_admin() or auth.has_role("HOD") or case.mentor_id == auth.user_id):
        raise status.HTTP_403_FORBIDDEN
    
    # Get the latest plan for this case
    result = await session.execute(
        select(InterventionPlan)
        .where(InterventionPlan.case_id == case_id)
        .order_by(InterventionPlan.created_at.desc())
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise status.HTTP_400_BAD_REQUEST("No plan to approve")
    
    plan.mentor_decision = request.decision
    plan.mentor_notes = request.mentor_notes
    plan.mentor_acted_at = datetime.now(timezone.utc)
    
    if request.decision == "APPROVED":
        plan.status = "APPROVED"
        case.status = InterventionCaseStatus.ACTIVE
    elif request.decision == "EDITED":
        plan.status = "CUSTOMIZED"
        case.status = InterventionCaseStatus.PLAN_PROPOSED
    elif request.decision == "REJECTED":
        plan.status = "DECLINED"
        case.status = InterventionCaseStatus.REPLAN_REQUIRED
    
    case.updated_at = datetime.now(timezone.utc)
    await session.flush()
    
    return CaseApproveResponse(
        case_id=case_id,
        mentor_decision=request.decision,
        acted_at=plan.mentor_acted_at,
    )


# --- Helper ---

async def _get_nearest_exam_days(session: AsyncSession, student_id: UUID) -> Optional[int]:
    """Get days until nearest exam for a student."""
    from app.models.student import StudentProfile
    from app.models.academic import CourseRun, Semester
    from sqlalchemy import and_
    
    result = await session.execute(
        select(StudentProfile.batch_id)
        .where(StudentProfile.id == student_id)
    )
    batch_row = result.first()
    if not batch_row:
        return None
    batch_id = batch_row[0]
    
    result = await session.execute(
        select(Semester.end_date)
        .join(CourseRun, CourseRun.semester_id == Semester.id)
        .join(StudentProfile, StudentProfile.batch_id == Semester.batch_id)
        .where(
            StudentProfile.id == student_id,
            Semester.status == "ACTIVE",
        )
        .order_by(Semester.end_date.asc())
        .limit(1)
    )
    exam_date = result.scalar_one_or_none()
    if not exam_date:
        return None
    
    delta = exam_date - datetime.now(timezone.utc).date()
    return delta.days if delta.days > 0 else 0