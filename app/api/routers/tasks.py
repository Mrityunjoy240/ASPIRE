# app/api/routers/tasks.py
# Tasks API Router — student tasks, completion

from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_context,
    require_roles,
    require_student_self_or_mentor,
    get_session,
)
from app.api.schemas import TaskResponse, TaskCompleteRequest, TaskCompleteResponse
from app.models.tasks import StudentTask
from app.models.enums import TaskStatus
from app.engines.tasks import TaskEngine


router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.get(
    "/student/{student_id}",
    response_model=list[TaskResponse],
    summary="Active/pending tasks for a student",
    dependencies=[Depends(require_roles("STUDENT", "MENTOR", "ADMIN", "HOD", "FACULTY"))],
)
async def get_student_tasks(
    student_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Return all pending/active tasks for a student."""
    result = await session.execute(
        select(StudentTask)
        .where(
            StudentTask.student_id == student_id,
            StudentTask.status.in_([TaskStatus.PENDING, TaskStatus.SNOOZED]),
        )
        .order_by(StudentTask.deadline.asc().nullslast())
    )
    tasks = result.scalars().all()
    return tasks


@router.post(
    "/{task_id}/complete",
    response_model=TaskCompleteResponse,
    summary="Mark task as completed by student",
    dependencies=[Depends(require_roles("STUDENT"))],
)
async def complete_task(
    task_id: UUID,
    _: TaskCompleteRequest,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Student marks a task as completed."""
    result = await session.execute(
        select(StudentTask).where(
            StudentTask.id == task_id,
            StudentTask.student_id == auth.user_id,  # Self-only for completion
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise status.HTTP_404_NOT_FOUND
    if task.status == TaskStatus.COMPLETED:
        raise status.HTTP_400_BAD_REQUEST("Task already completed")
    
    task.status = TaskStatus.COMPLETED
    task.updated_at = datetime.now(timezone.utc)
    await session.flush()
    
    return TaskCompleteResponse(
        task_id=task_id,
        status=TaskStatus.COMPLETED.value,
        completed_at=datetime.now(timezone.utc),
    )


@router.post(
    "/{task_id}/snooze",
    response_model=TaskResponse,
    summary="Snooze a task (student action)",
    dependencies=[Depends(require_roles("STUDENT"))],
)
async def snooze_task(
    task_id: UUID,
    auth = Depends(get_auth_context),
    session = Depends(get_session),
):
    """Student snoozes a task."""
    result = await session.execute(
        select(StudentTask).where(
            StudentTask.id == task_id,
            StudentTask.student_id == auth.user_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise status.HTTP_404_NOT_FOUND
    if task.status != TaskStatus.PENDING:
        raise status.HTTP_400_BAD_REQUEST("Only pending tasks can be snoozed")
    
    task.status = TaskStatus.SNOOZED
    task.updated_at = datetime.now(timezone.utc)
    await session.flush()
    
    return task