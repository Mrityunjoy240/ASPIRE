# app/engines/priority.py
# Priority Engine — deterministic task ordering.
# Urgency score (0-100) + explicit priority + deadline proximity.
# DM-SS03: Mentor queue sort: Urgency Band → Exam Proximity → Days Since Last Mentor Action.

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

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

    def sort_mentor_queue(
        self,
        cases: list[dict],  # {case, student_tasks, last_mentor_action_days}
    ) -> list[dict]:
        """
        Sort mentor queue per DM-SS03:
        1. Urgency Band (URGENT > ATTENTION > MONITOR)
        2. Exam Proximity (nearest exam first)
        3. Days Since Last Mentor Action (staleness badge, not sort key)
        """
        def urgency_rank(band: UrgencyBand) -> int:
            return {"URGENT": 0, "ATTENTION": 1, "MONITOR": 2}[band.value]

        def sort_key(item):
            case = item["case"]
            # Get highest urgency band among student's tasks
            max_band = UrgencyBand.MONITOR
            for task_data in item.get("student_tasks", []):
                if task_data.get("urgency_band"):
                    band = UrgencyBand(task_data["urgency_band"])
                    if urgency_rank(band) < urgency_rank(max_band):
                        max_band = band

            # Exam proximity (earliest exam date)
            exam_date = case.get("nearest_exam_date")
            exam_days = 999
            if exam_date:
                exam_days = (exam_date - datetime.now(UTC)).days

            return (urgency_rank(max_band), exam_days)

        return sorted(cases, key=sort_key)
