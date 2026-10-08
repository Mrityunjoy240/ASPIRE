# app/engines/priority.py
# Priority Engine — deterministic task ordering.
# Urgency score (0-100) + explicit priority + deadline proximity.
# DM-SS03: Mentor queue sort: Urgency Band → Exam Proximity → Days Since Last Mentor Action.

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from app.models.enums import TaskStatus
from app.models.tasks import StudentTask


class UrgencyBand(str, Enum):
    URGENT = "URGENT"
    ATTENTION = "ATTENTION"
    MONITOR = "MONITOR"


@dataclass(frozen=True)
class TaskUrgency:
    task_id: str
    urgency_score: int  # 0-100
    urgency_band: UrgencyBand
    days_until_deadline: int | None
    is_overdue: bool
    explicit_priority: int | None


@dataclass(frozen=True)
class QueueEntry:
    """One mentor-queue row as required by DM-SS03 ordering (03 §6.2)."""

    case_id: UUID
    urgency_band: str  # URGENT | ATTENTION | MONITOR
    exam_days_remaining: int | None
    days_since_last_mentor_action: int | None
    created_at: datetime | None


class PriorityEngine:
    """
    Deterministic priority calculation for student tasks and mentor queue.
    Score = base_urgency + deadline_factor + explicit_priority_bonus
    """

    # Weights (configurable via institution_rules in future)
    BASE_URGENCY_WEIGHT = 0.5
    DEADLINE_WEIGHT = 0.4
    EXPLICIT_PRIORITY_WEIGHT = 0.1

    # Deadline urgency curves
    CRITICAL_DAYS = 1   # Due today/tomorrow
    URGENT_DAYS = 3     # Due in 3 days
    ATTENTION_DAYS = 7  # Due in a week

    def calculate_task_urgency(self, task: StudentTask, now: datetime | None = None) -> TaskUrgency:
        """Calculate urgency for a single task."""
        now = now or datetime.now(UTC)

        if task.status != TaskStatus.PENDING or task.deadline is None:
            return TaskUrgency(
                task_id=str(task.id),
                urgency_score=0,
                urgency_band=UrgencyBand.MONITOR,
                days_until_deadline=None,
                is_overdue=False,
                explicit_priority=task.explicit_priority,
            )

        # Days until deadline
        delta = task.deadline - now
        days_until = delta.days
        is_overdue = days_until < 0

        # Base urgency from deadline
        if is_overdue:
            deadline_urgency = 100
        elif days_until <= self.CRITICAL_DAYS:
            deadline_urgency = 90
        elif days_until <= self.URGENT_DAYS:
            deadline_urgency = 70
        elif days_until <= self.ATTENTION_DAYS:
            deadline_urgency = 40
        else:
            deadline_urgency = 10

        # Explicit priority bonus (higher = more urgent)
        priority_bonus = 0
        if task.explicit_priority is not None:
            # Map priority 1-10 to 0-20 bonus
            priority_bonus = min(20, max(0, (task.explicit_priority - 1) * 2))

        # Source type base urgency
        source_base = {
            "AI_PLAN": 60,      # AI plans are time-sensitive
            "ASSESSMENT": 50,   # Assessment deadlines
            "CALENDAR": 30,     # Calendar events
            "MENTOR": 40,       # Mentor-assigned
        }.get(task.source_type.value, 30)

        # Composite score
        score = (
            self.BASE_URGENCY_WEIGHT * source_base
            + self.DEADLINE_WEIGHT * deadline_urgency
            + self.EXPLICIT_PRIORITY_WEIGHT * priority_bonus
        )
        score = min(100, max(0, int(score)))

        # Urgency band
        if score >= 80 or is_overdue:
            band = UrgencyBand.URGENT
        elif score >= 50:
            band = UrgencyBand.ATTENTION
        else:
            band = UrgencyBand.MONITOR

        return TaskUrgency(
            task_id=str(task.id),
            urgency_score=score,
            urgency_band=band,
            days_until_deadline=days_until if days_until >= 0 else None,
            is_overdue=is_overdue,
            explicit_priority=task.explicit_priority,
        )

    def sort_student_tasks(self, tasks: list[StudentTask]) -> list[StudentTask]:
        """Sort tasks for student view: overdue first, then by urgency desc, then deadline asc."""
        now = datetime.now(UTC)
        scored = [(t, self.calculate_task_urgency(t, now)) for t in tasks]

        def sort_key(item):
            task, urgency = item
            return (
                0 if urgency.is_overdue else 1,
                -urgency.urgency_score,
                task.deadline or datetime.max.replace(tzinfo=UTC),
            )

        scored.sort(key=sort_key)
        return [t for t, _ in scored]

    def sort_mentor_queue(self, entries: list[QueueEntry]) -> list[QueueEntry]:
        """Canonical DM-SS03 mentor-queue ordering (03 §6.2 FROZEN / OQ-SS03).

        Single source of truth: the API returns this order; clients must not
        re-rank it (AGENTS: no duplicated business logic in clients).

        Key sequence:
        1. Urgency Band: URGENT > ATTENTION > MONITOR (unknown band last).
        2. URGENT only: exam_days_remaining ASC, NULLS LAST.
        3. All bands: days_since_last_mentor_action DESC, NULLS FIRST
           (outside URGENT this is the primary in-band key; exam proximity
           is NOT a sort key in ATTENTION/MONITOR).
        4. Tie-breakers (every band): created_at ASC, then case_id ASC.
        data_staleness_hours is badge/display-only and never a sort key.
        """
        far = datetime.max.replace(tzinfo=UTC)
        band_rank = {"URGENT": 0, "ATTENTION": 1, "MONITOR": 2}

        def sort_key(entry: QueueEntry) -> tuple:
            band = band_rank.get(entry.urgency_band, 3)
            if entry.urgency_band == "URGENT":
                exam_key = (
                    (1, 0)
                    if entry.exam_days_remaining is None
                    else (0, entry.exam_days_remaining)
                )
            else:
                # Exam proximity does not influence ATTENTION/MONITOR (§6.2).
                exam_key = (0, 0)
            days = entry.days_since_last_mentor_action
            days_key = (0, 0) if days is None else (1, -days)
            created = entry.created_at
            if created is None:
                created_key = far
            elif created.tzinfo is None:
                created_key = created.replace(tzinfo=UTC)
            else:
                created_key = created
            return (band, exam_key, days_key, created_key, str(entry.case_id))

        return sorted(entries, key=sort_key)
