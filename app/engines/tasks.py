# app/engines/tasks.py
# Task Engine — deterministic task operations.
# Creates, updates, completes tasks. No LLM involvement.

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.priority import PriorityEngine
from app.models.enums import TaskSourceType, TaskStatus
from app.models.tasks import StudentTask


class TaskEngine:
    """Deterministic task management engine."""

    def __init__(self):
        self.priority_engine = PriorityEngine()

    async def create_task(
        self,
        session: AsyncSession,
        student_id: UUID,
        source_type: TaskSourceType,
        source_id: UUID,
        created_by: UUID,
        title: str,
        deadline: datetime | None = None,
        explicit_priority: int | None = None,
    ) -> StudentTask:
        """Create a new task."""
        task = StudentTask(
            id=uuid4(),
            student_id=student_id,
            source_type=source_type,
            source_id=source_id,
            created_by=created_by,
            title=title,
            deadline=deadline,
            status=TaskStatus.PENDING,
            explicit_priority=explicit_priority,
            urgency_score=None,  # Computed on read
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(task)
        await session.flush()
        return task

    async def complete_task(self, session: AsyncSession, task_id: UUID, student_id: UUID) -> StudentTask:
        """Mark task as completed by student."""
        result = await session.execute(
            select(StudentTask).where(StudentTask.id == task_id, StudentTask.student_id == student_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        if task.status == TaskStatus.COMPLETED:
            raise ValueError("Task already completed")

        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now(UTC)
        return task

    async def snooze_task(self, session: AsyncSession, task_id: UUID, student_id: UUID) -> StudentTask:
        """Snooze a task (student action)."""
        result = await session.execute(
            select(StudentTask).where(StudentTask.id == task_id, StudentTask.student_id == student_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")
        if task.status != TaskStatus.PENDING:
            raise ValueError("Only pending tasks can be snoozed")

        task.status = TaskStatus.SNOOZED
        task.updated_at = datetime.now(UTC)
        return task

    async def get_student_tasks(
        self,
        session: AsyncSession,
        student_id: UUID,
        status: TaskStatus | None = None,
    ) -> list[StudentTask]:
        """Get tasks for a student, optionally filtered by status."""
        query = select(StudentTask).where(StudentTask.student_id == student_id)
        if status:
            query = query.where(StudentTask.status == status)
        query = query.order_by(StudentTask.deadline.asc().nullslast())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def recalculate_urgency_scores(self, session: AsyncSession, student_id: UUID) -> None:
        """Recalculate urgency scores for all pending tasks (called by scheduler)."""
        tasks = await self.get_student_tasks(session, student_id, TaskStatus.PENDING)
        for task in tasks:
            urgency = self.priority_engine.calculate_task_urgency(task)
            task.urgency_score = urgency.urgency_score
            task.updated_at = datetime.now(UTC)
        await session.flush()
