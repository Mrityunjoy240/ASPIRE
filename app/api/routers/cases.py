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
    require_mentor_hod_or_admin,
    require_roles,
    get_session,
)
from app.api.schemas import (
    CaseQueueItemResponse,
    CaseApproveRequest,
    CaseApproveResponse,
    CaseCloseResponse,
    CaseEscalateRequest,
    CaseEscalateResponse,
    FollowUpCreateRequest,
    FollowUpCreateResponse,
    FollowUpResponse,
    StudentDecisionRequest,
    StudentDecisionResponse,
)
from app.core.events import EventBus
from app.models.academic import Batch
from app.models.intervention import InterventionCase, InterventionFollowUp, InterventionPlan
from app.models.student import StudentProfile
from app.models.tasks import StudentTask
from app.models.users import User
from app.models.enums import InterventionCaseStatus, UserRole
from app.services.case_service import CaseApprovalError, approve_plan
from app.services.case_lifecycle_service import (
    CaseLifecycleError,
    close_case,
    escalate_case,
)
from app.services.follow_up_service import FollowUpError, schedule_followup
from app.services.student_action_service import StudentActionError, decide_plan
from app.engines.priority import PriorityEngine, QueueEntry


router = APIRouter(prefix="/api/v1/cases", tags=["Intervention Cases"])


@router.get(
    "/queue",
    response_model=list[CaseQueueItemResponse],
    summary="Mentor priority triage queue",
    dependencies=[Depends(require_mentor_hod_or_admin)],
)
async def get_mentor_queue(
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor queue ordered by Urgency Band → Exam Proximity → Days Since Last Action (DM-SS03)."""

    # Mentors see only their assigned cases. Admin sees all cases within
    # their own institution. HOD sees **escalations only**, within their
    # own institution (07 §2 permission matrix: Admin = "All",
    # HOD = "Escalations" — review F5; `ESCALATION_REQUIRED` is itself the
    # pending-HOD/CT marker, 03 §10.2 / `escalate_case`). Student ->
    # institution resolves through batch_id (003/004). A NULL
    # institution_id matches nothing (fail closed). ESCALATION_REQUIRED
    # stays in the admin/mentor lists (02 §2.1/§2.2: the mentor sees the
    # escalation flag; admin sees everything).
    if auth.is_admin():
        result = await session.execute(
            select(InterventionCase)
            .join(StudentProfile, InterventionCase.student_id == StudentProfile.id)
            .join(Batch, StudentProfile.batch_id == Batch.id)
            .where(
                Batch.institution_id == auth.institution_id,
                InterventionCase.status.in_([
                InterventionCaseStatus.OPEN,
                InterventionCaseStatus.IN_REVIEW,
                InterventionCaseStatus.PLAN_PROPOSED,
                InterventionCaseStatus.PENDING_APPROVAL,
                InterventionCaseStatus.ACTIVE,
                InterventionCaseStatus.MONITORING,
                InterventionCaseStatus.REPLAN_REQUIRED,
                InterventionCaseStatus.ESCALATION_REQUIRED,
            ]))
        )
    elif auth.has_role(UserRole.HOD):
        result = await session.execute(
            select(InterventionCase)
            .join(StudentProfile, InterventionCase.student_id == StudentProfile.id)
            .join(Batch, StudentProfile.batch_id == Batch.id)
            .where(
                Batch.institution_id == auth.institution_id,
                InterventionCase.status == InterventionCaseStatus.ESCALATION_REQUIRED,
            )
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
                    InterventionCaseStatus.ESCALATION_REQUIRED,
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


def _case_row_for_update(case_id: UUID):
    """Case row locked FOR UPDATE so concurrent case-state transitions
    (student decision, mentor approval) serialize: only the first transaction
    can observe the current state; a blocked second request re-reads the
    committed result and receives 409 (03 §10.2 allows a single transition
    per state). PostgreSQL row-level lock; no external lock service."""
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


async def _authorize_mentor_case_write(
    auth, session: AsyncSession, case: InterventionCase
) -> None:
    """Record-level authorization for a mentor case write (07 §2): the
    assigned mentor always qualifies; admin qualifies inside their own
    institution (student -> batch -> institution); HOD qualifies **only on
    `ESCALATION_REQUIRED` cases** inside their own institution (07 §2
    matrix "HOD: Escalations" — review F5; that status is the
    pending-HOD/CT marker, 03 §10.2). Every refusal uses the same detail
    (no scope oracle). Shared by approve/close/escalate/follow-ups."""
    if case.mentor_id == auth.user_id:
        return
    if not (auth.is_admin() or auth.has_role(UserRole.HOD)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this case",
        )
    if not auth.is_admin() and case.status != InterventionCaseStatus.ESCALATION_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this case",
        )
    result = await session.execute(
        select(Batch.institution_id)
        .join(StudentProfile, StudentProfile.batch_id == Batch.id)
        .where(StudentProfile.id == case.student_id)
    )
    case_institution_id = result.scalar_one_or_none()
    if case_institution_id is None or case_institution_id != auth.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this case",
        )


@router.post(
    "/{case_id}/approve",
    response_model=CaseApproveResponse,
    summary="Mentor human-in-the-loop approval",
    dependencies=[Depends(require_mentor_hod_or_admin)],
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
    result = await session.execute(_case_row_for_update(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Record-level authorization (07 §2) — shared helper (no scope oracle).
    await _authorize_mentor_case_write(auth, session, case)

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


@router.post(
    "/{case_id}/student-decision",
    response_model=StudentDecisionResponse,
    summary="Student accepts, customizes or declines the proposed plan",
    dependencies=[Depends(require_roles(UserRole.STUDENT))],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Case not in PLAN_PROPOSED, or multiple proposed plans await "
                "a student decision (03_SYSTEM_SPEC §10.2)"
            ),
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "No proposed plan awaiting a student decision for this case",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Case does not belong to the authenticated student",
        },
    },
)
async def student_plan_decision(
    case_id: UUID,
    request: StudentDecisionRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
    event_bus: EventBus = Depends(get_event_bus),
):
    """Student accepts, customizes or declines the agent-proposed plan.

    Transition ownership, plan selection, audit row and PLAN_ACCEPTED /
    PLAN_DECLINED emission live in the Student Action Service
    (03_SYSTEM_SPEC §10.2, §8.2). Decline reason is optional
    (02_USER_JOURNEYS 1.1 Step 6).
    """
    result = await session.execute(_case_row_for_update(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Student (own data only — 03 §12, Constitution S-02): the profile behind
    # this user must own the case. A missing profile and a foreign case are
    # both 403 without distinguishing detail (no existence oracle).
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == auth.user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile or profile.id != case.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not this case's student")

    result = await session.execute(_plans_for_case_query(case_id))
    plans = list(result.scalars().all())

    try:
        decision = await decide_plan(
            session,
            case=case,
            plans=plans,
            decision=request.decision,
            plan_actions=request.plan_actions,
            reason=request.reason,
            actor_id=auth.user_id,
            event_bus=event_bus,
        )
    except StudentActionError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code in ("ILLEGAL_TRANSITION", "AMBIGUOUS_PLAN")
            else status.HTTP_422_UNPROCESSABLE_CONTENT
            if exc.code == "INVALID_REQUEST"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.detail) from exc

    return StudentDecisionResponse(
        case_id=decision.case_id,
        student_decision=decision.student_decision,
        decided_at=decision.decided_at,
    )


@router.post(
    "/{case_id}/escalate",
    response_model=CaseEscalateResponse,
    summary="Mentor escalates an ESCALATION_REQUIRED case to HOD/CT",
    dependencies=[Depends(require_mentor_hod_or_admin)],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Case not in ESCALATION_REQUIRED (03_SYSTEM_SPEC §10.2 "
                "self-transition)"
            ),
        },
        status.HTTP_400_BAD_REQUEST: {"description": "Unknown escalation target"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized for this case"},
    },
)
async def escalate_case_endpoint(
    case_id: UUID,
    request: CaseEscalateRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor escalates to HOD/CT — stays ESCALATION_REQUIRED (pending
    HOD/CT). Target selection + optional note land on the mandatory
    CASE_ESCALATED audit row (07 §4); no domain event exists in the
    catalog (03 §8.2). The frozen table names exactly HOD/CT (03 §10.2).
    """
    result = await session.execute(_case_row_for_update(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await _authorize_mentor_case_write(auth, session, case)

    try:
        escalation = await escalate_case(
            session,
            case=case,
            actor_id=auth.user_id,
            target=request.target,
            note=request.note,
        )
    except CaseLifecycleError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code == "ILLEGAL_TRANSITION"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.detail) from exc

    return CaseEscalateResponse(
        case_id=escalation.case_id,
        case_status=escalation.case_status,
        escalated_to=escalation.escalated_to or request.target,
        acted_at=escalation.acted_at,
    )


@router.post(
    "/{case_id}/close",
    response_model=CaseCloseResponse,
    summary="Mentor closes a RESOLVED case",
    dependencies=[Depends(require_mentor_hod_or_admin)],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Case not in RESOLVED (03_SYSTEM_SPEC §10.2 RESOLVED → CLOSED)"
            ),
        },
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized for this case"},
    },
)
async def close_case_endpoint(
    case_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor closes a resolved case: RESOLVED → CLOSED + closed_at, with
    the mandatory CASE_CLOSED audit row (07 §4). Audit-only — the catalog
    (03 §8.2) has no case-closed domain event (same precedent as a mentor
    plan rejection).
    """
    result = await session.execute(_case_row_for_update(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await _authorize_mentor_case_write(auth, session, case)

    try:
        closure = await close_case(
            session,
            case=case,
            actor_id=auth.user_id,
        )
    except CaseLifecycleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=exc.detail
        ) from exc

    return CaseCloseResponse(
        case_id=closure.case_id,
        case_status=closure.case_status,
        closed_at=closure.acted_at,
    )


@router.post(
    "/{case_id}/follow-ups",
    response_model=FollowUpCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mentor schedules a follow-up on an ACTIVE case",
    dependencies=[Depends(require_mentor_hod_or_admin)],
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Case not in ACTIVE (ADR-004 §2.7)",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid trigger_type/due_at combination (ADR-004 §2.7)",
        },
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized for this case"},
    },
)
async def create_follow_up(
    case_id: UUID,
    request: FollowUpCreateRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Mentor schedules a follow-up: ACTIVE case only (03 §10.2,
    ADR-004 §2.7). `CUSTOM_DATE` requires a future timezone-aware `due_at`;
    event-driven types (`ATTENDANCE_INTERVENTION`, `STUDY_INTERVENTION`,
    `ASSIGNMENT_INTERVENTION`) are fulfilled by their policy trigger events
    and forbid `due_at`. Persists an `intervention_follow_ups` SCHEDULED row
    plus the mandatory FOLLOW_UP_SCHEDULED audit row (ADR-004 §2.8).
    """
    result = await session.execute(_case_row_for_update(case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await _authorize_mentor_case_write(auth, session, case)

    try:
        follow_up = await schedule_followup(
            session,
            case=case,
            trigger_type=request.trigger_type,
            due_at=request.due_at,
            actor_id=auth.user_id,
        )
    except FollowUpError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code == "ILLEGAL_TRANSITION"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.detail) from exc

    return FollowUpCreateResponse(
        id=follow_up.follow_up_id,
        case_id=follow_up.case_id,
        trigger_type=follow_up.trigger_type,
        status=follow_up.status,
        due_at=follow_up.due_at,
        created_at=follow_up.created_at,
    )


@router.get(
    "/{case_id}/follow-ups",
    response_model=list[FollowUpResponse],
    summary="List follow-ups for a case",
    dependencies=[Depends(require_mentor_hod_or_admin)],
)
async def list_follow_ups(
    case_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Read-only list of a case's follow-ups (newest first). Same
    record-level authorization as the write path (07 §2)."""
    result = await session.execute(
        select(InterventionCase).where(InterventionCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await _authorize_mentor_case_write(auth, session, case)

    rows = await session.execute(
        select(InterventionFollowUp)
        .where(InterventionFollowUp.case_id == case_id)
        .order_by(InterventionFollowUp.created_at.desc())
    )
    return list(rows.scalars().all())


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