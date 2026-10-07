# app/api/routers/students.py
# Student API Router — self profile, mentor/faculty view

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    require_roles,
    require_student_self_or_mentor,
    get_session,
)
from app.api.schemas import StudentSelfResponse, StudentMentorViewResponse
from app.models.student import StudentProfile
from app.models.enums import UserRole


router = APIRouter(prefix="/api/v1/students", tags=["Students"])


@router.get(
    "/me",
    response_model=StudentSelfResponse,
    summary="Get own student profile",
)
async def get_own_profile(
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Return authenticated student's own profile."""
    if not auth.is_student():
        raise status.HTTP_403_FORBIDDEN
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == auth.user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise status.HTTP_404_NOT_FOUND
    return profile


@router.get(
    "/{student_id}",
    response_model=StudentMentorViewResponse,
    summary="Get student profile (mentor/faculty/admin view)",
    dependencies=[Depends(require_roles(UserRole.MENTOR, UserRole.ADMIN, UserRole.HOD, UserRole.FACULTY))],
)
async def get_student_mentor_view(
    student_id: UUID,
    session = Depends(get_session),
):
    """Return student profile with risk signals for mentor/faculty."""
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.id == student_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise status.HTTP_404_NOT_FOUND
    # TODO: enrich with risk signals (attendance risk, assessment trend, overdue tasks)
    return profile