# app/api/routers/students.py
# Student API Router — self profile, own case view, and plan response (R6).

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    get_event_bus,
    require_student_self_or_mentor,
    get_session,
)
from app.api.schemas import (
    StudentSelfResponse,
    StudentMentorViewResponse,
    StudentCaseResponse,
    StudentDecisionRequest,
    StudentDecisionResponse,
    InterventionPlanResponse,
)
from app.core.events import EventBus
from app.models.intervention import InterventionCase, InterventionPlan
from app.models.student import StudentProfile
from app.services.student_action_service import StudentActionError, decide_plan

router = APIRouter(prefix="/api/v1/students", tags=["Students"])


@router.get(
    "/me",
    response_model=StudentSelfResponse,
    summary="Get own student profile",
)
async def get_own_profile(
    auth = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    """Return authenticated student's own profile."""
    if not auth.is_student():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == auth.user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found"
        )
    return profile


@router.get(
    "/me/case",
    response_model=StudentCaseResponse,
    summary="Get own current intervention case (R6)",
)
async def get_own_case(
    auth = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
):
    """Return the current intervention case and proposed plan for the authenticated student.

    Returns 404 when no case is in PLAN_PROPOSED state (meaning the student has
    nothing to act on right now — case may be in a different state or no case exists).
    """
    if not auth.is_student():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )

    # Resolve the student profile (needed for student_id FK)
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == auth.user_id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found"
        )

    # Find the case waiting for this student's response (PLAN_PROPOSED state)
    case_res = await session.execute(
        select(InterventionCase).where(
            InterventionCase.student_id == profile.id,
            InterventionCase.status == "PLAN_PROPOSED",
        )
    )
    case = case_res.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No plan currently awaiting your response",
        )

    # Fetch all plans (history), pick the most recent authoritative proposed one
    plans_res = await session.execute(
        select(InterventionPlan)
        .where(InterventionPlan.case_id == case.id)
        .order_by(InterventionPlan.created_at.desc())
    )
    plans = plans_res.scalars().all()

    # The current plan is the most recent PROPOSED one with no student decision
    current_plan = next(
        (p for p in plans if p.status == "PROPOSED" and p.student_decision is None),
        plans[0] if plans else None,
    )

    # plan_actions is stored as a JSONB list on the plan row
    raw_actions = (current_plan.plan_actions or []) if current_plan else []

    return StudentCaseResponse(
        case_id=case.id,
        status=case.status,
        urgency_band=case.urgency_band,
        opened_at=case.opened_at,
        current_plan=current_plan,
        plan_actions=raw_actions,
        next_step=(
            "Please review your intervention plan and respond with ACCEPT, CUSTOMIZE, or DECLINE."
        ),
    )


@router.post(
    "/me/case/respond",
    response_model=StudentDecisionResponse,
    summary="Respond to the proposed intervention plan (R6)",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Case not in PLAN_PROPOSED, or multiple proposed plans await a decision",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "No proposed plan awaiting a student decision",
        },
    },
)
async def respond_to_case(
    request: StudentDecisionRequest,
    auth = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
    event_bus: EventBus = Depends(get_event_bus),
):
    """Student accepts, customizes, or declines their proposed intervention plan.

    This endpoint is the student-self version of POST /cases/{case_id}/student-decision.
    It resolves the student's own case and delegates to the Student Action Service
    (student_action_service.decide_plan) which owns:
      - PostgreSQL FOR UPDATE row lock (concurrency safety)
      - State transition (PLAN_PROPOSED → PENDING_APPROVAL or REPLAN_REQUIRED)
      - Audit log row (07 §4, STUDENT_APP source)
      - Domain event emission (PLAN_ACCEPTED or PLAN_DECLINED, 03 §8.2)
    """
    if not auth.is_student():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )

    # Resolve student profile
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == auth.user_id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found"
        )

    # Lock the case row for update (same pattern as cases.py student-decision endpoint)
    case_res = await session.execute(
        select(InterventionCase)
        .where(
            InterventionCase.student_id == profile.id,
            InterventionCase.status == "PLAN_PROPOSED",
        )
        .with_for_update()
    )
    case = case_res.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No plan currently awaiting your response",
        )

    # Fetch all plans for this case (service selects the authoritative one)
    plans_res = await session.execute(
        select(InterventionPlan)
        .where(InterventionPlan.case_id == case.id)
        .order_by(InterventionPlan.created_at.desc())
    )
    plans = list(plans_res.scalars().all())

    # Delegate to the service — it owns state transitions, audit, and events
    try:
        result = await decide_plan(
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
        http_code = (
            status.HTTP_409_CONFLICT
            if exc.code in ("ILLEGAL_TRANSITION", "AMBIGUOUS_PLAN")
            else status.HTTP_422_UNPROCESSABLE_ENTITY
            if exc.code == "INVALID_REQUEST"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=http_code, detail=exc.detail) from exc

    return StudentDecisionResponse(
        case_id=result.case_id,
        student_decision=result.student_decision,
        decided_at=result.decided_at,
    )


@router.get(
    "/{student_id}",
    response_model=StudentMentorViewResponse,
    summary="Get student profile (mentor/faculty/admin view)",
    dependencies=[Depends(require_student_self_or_mentor)],
)
async def get_student_mentor_view(
    student_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Return student profile with risk signals for mentor/faculty."""
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.id == student_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    return profile
