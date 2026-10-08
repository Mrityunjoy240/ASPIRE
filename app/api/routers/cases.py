# app/api/routers/cases.py
# Cases/Intervention API Router — mentor queue, approval

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    get_event_bus,
    require_mentor_or_admin,
    get_session,
)
from app.api.schemas import CaseQueueItemResponse, CaseApproveRequest, CaseApproveResponse
from app.core.events import EventBus
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile
from app.models.tasks import StudentTask
from app.models.users import User
from app.models.enums import InterventionCaseStatus
from app.services.case_service import CaseApprovalError, approve_plan
from app.engines.priority import PriorityEngine, QueueEntry


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
    queue_entries: list[QueueEntry] = []
    responses: dict = {}
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
        
        queue_entries.append(QueueEntry(
            case_id=case.id,
            urgency_band=case.urgency_band,
            exam_days_remaining=nearest_exam_days,
            days_since_last_mentor_action=days_since_last_action,
            created_at=case.created_at or case.opened_at,
        ))
        responses[case.id] = CaseQueueItemResponse(
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
        )

    # Canonical DM-SS03 ordering (03 §6.2 FROZEN): computed here, single source
    # of truth. Clients render this order as-is and must not re-rank it.
    ordered = priority_engine.sort_mentor_queue(queue_entries)
    return [responses[entry.case_id] for entry in ordered]


def _case_for_approval_query(case_id: UUID):
    """Case row locked FOR UPDATE so concurrent approval attempts serialize:
    only the first transaction can observe PENDING_APPROVAL; a blocked second
    request re-reads the committed result and receives 409 (03 §10.2 allows a
    single transition). PostgreSQL row-level lock; no external lock service."""
    return select(InterventionCase).where(InterventionCase.id == case_id).with_for_update()


def _plans_for_case_query(case_id: UUID):
    """Every plan for the case, history included — never scalar_one_or_none().

    The authoritative pending plan is selected inside the Case Approval
    Service (ADR-002 §5); ambiguous plan sets are refused, never guessed."""
    return (
        select(InterventionPlan)
        .where(InterventionPlan.case_id == case_id)
        .order_by(InterventionPlan.created_at.desc())
    )


@router.post(
    "/{case_id}/approve",
    response_model=CaseApproveResponse,
    summary="Mentor human-in-the-loop approval",
    dependencies=[Depends(require_mentor_or_admin)],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Case not in PENDING_APPROVAL, or multiple plans await a mentor "
                "decision (03_SYSTEM_SPEC §10.2)"
            ),
        },
        status.HTTP_400_BAD_REQUEST: {"description": "No plan awaiting mentor decision for this case"},
    },
)
async def approve_case(
    case_id: UUID,
    request: CaseApproveRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
    event_bus: EventBus = Depends(get_event_bus),
):
    """Mentor approves/edits/rejects intervention plan.

    Transition ownership, plan selection and event emission live in the Case
    Approval Service (03_SYSTEM_SPEC §10.2, ADR-002): audit row + commit, then
    INTERVENTION_PLAN_APPROVED for approval decisions only.
    """
    result = await session.execute(_case_for_approval_query(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if not (auth.is_admin() or auth.has_role("HOD") or case.mentor_id == auth.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not this case's mentor")

    result = await session.execute(_plans_for_case_query(case_id))
    plans = list(result.scalars().all())

    try:
        approval = await approve_plan(
            session,
            case=case,
            plans=plans,
            decision=request.decision,
            mentor_notes=request.mentor_notes,
            actor_id=auth.user_id,
            event_bus=event_bus,
        )
    except CaseApprovalError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code in ("ILLEGAL_TRANSITION", "AMBIGUOUS_PLAN")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.detail) from exc

    return CaseApproveResponse(
        case_id=approval.case_id,
        mentor_decision=approval.decision,
        acted_at=approval.acted_at,
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