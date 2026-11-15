# app/engines/intervention.py
# Intervention Engine — deterministic case lifecycle.
# Engines calculate. Agents propose. Humans approve.

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.attendance import AttendanceEngine, DerivedState
from app.engines.priority import PriorityEngine
from app.models.enums import TaskSourceType
from app.models.tasks import StudentTask


class InterventionUrgency(str, Enum):
    URGENT = "URGENT"
    ATTENTION = "ATTENTION"
    MONITOR = "MONITOR"


@dataclass(frozen=True)
class TriggerEvent:
    event_type: str
    entity_id: str
    severity: str
    timestamp: str


@dataclass(frozen=True)
class InterventionPlanData:
    """Structured plan output (no prose)."""
    reason_codes: list[str]
    evidence: list[str]
    actions: list[dict]
    approval_required: bool
    confidence_level: str


class InterventionEngine:
    """
    Deterministic intervention logic.
    - Detects risk from engine outputs
    - Generates structured plans
    - Never mutates business state directly (scheduler does)
    """

    def __init__(
        self,
        attendance_engine: AttendanceEngine,
        priority_engine: PriorityEngine,
    ):
        self.attendance_engine = attendance_engine
        self.priority_engine = priority_engine

    def detect_risk(
        self,
        derived_state: DerivedState,
        assessment_trend: str,
        exam_days: int | None = None,
    ) -> list[TriggerEvent]:
        """Detect risk signals from engine outputs."""
        events = []

        # Attendance risk
        if derived_state.risk_band in ("WARNING", "CRITICAL"):
            events.append(TriggerEvent(
                event_type="ATTENDANCE_RISK",
                entity_id=derived_state.course_run_id,
                severity=derived_state.risk_band,
                timestamp=datetime.now(UTC).isoformat(),
            ))

        # Assessment trend risk
        if assessment_trend == "DECLINING":
            events.append(TriggerEvent(
                event_type="ASSESSMENT_TREND_DECLINING",
                entity_id=derived_state.course_run_id,
                severity="WARNING",
                timestamp=datetime.now(UTC).isoformat(),
            ))

        # Exam proximity
        if exam_days is not None and exam_days <= 14:
            events.append(TriggerEvent(
                event_type="EXAM_APPROACHING",
                entity_id=derived_state.course_run_id,
                severity="URGENT" if exam_days <= 7 else "ATTENTION",
                timestamp=datetime.now(UTC).isoformat(),
            ))

        return events

    def determine_urgency(self, events: list[TriggerEvent]) -> InterventionUrgency:
        """Determine case urgency from trigger events."""
        if any(e.severity == "URGENT" for e in events):
            return InterventionUrgency.URGENT
        if any(e.severity == "WARNING" for e in events):
            return InterventionUrgency.ATTENTION
        return InterventionUrgency.MONITOR

    def generate_plan(
        self,
        student_id: str,
        events: list[TriggerEvent],
        attendance_state: DerivedState,
    ) -> InterventionPlanData:
        """Generate structured recovery plan (no prose)."""
        reason_codes = []
        evidence = []
        actions = []

        for event in events:
            if event.event_type == "ATTENDANCE_RISK":
                reason_codes.append("LOW_ATTENDANCE")
                evidence.append(f"Attendance: {attendance_state.attendance_percentage}%")
                evidence.append(f"Threshold: {attendance_state.attendance_percentage + attendance_state.required_to_recover * 0.5}%")  # approx
                required = attendance_state.required_to_recover or 0
                actions.append({
                    "type": "ATTEND_CLASS",
                    "subject": event.entity_id,
                    "target_classes": required,
                })

            elif event.event_type == "ASSESSMENT_TREND_DECLINING":
                reason_codes.append("DECLINING_PERFORMANCE")
                evidence.append("Trend: DECLINING")
                actions.append({
                    "type": "STUDY_BLOCK",
                    "topic": "Weak areas in " + event.entity_id,
                    "duration_min": 60,
                })

            elif event.event_type == "EXAM_APPROACHING":
                reason_codes.append("EXAM_APPROACHING")
                evidence.append(f"Exam in {event.entity_id} approaching")
                actions.append({
                    "type": "REVIEW_SYLLABUS",
                    "subject": event.entity_id,
                    "duration_min": 90,
                })

        # Deduplicate
        reason_codes = list(dict.fromkeys(reason_codes))
        evidence = list(dict.fromkeys(evidence))

        return InterventionPlanData(
            reason_codes=reason_codes,
            evidence=evidence,
            actions=actions,
            approval_required=False,  # Student can accept/decline/edit
            confidence_level="HIGH" if len(evidence) >= 2 else "MEDIUM",
        )

    async def create_tasks_from_plan(
        self,
        session: AsyncSession,
        student_id: UUID,
        plan: InterventionPlanData,
        created_by: UUID,
    ) -> list[StudentTask]:
        """Create tasks from accepted plan (called by scheduler after student acceptance)."""
        from app.engines.tasks import TaskEngine
        task_engine = TaskEngine()
        tasks = []

        for action in plan.actions:
            task = await task_engine.create_task(
                session=session,
                student_id=student_id,
                source_type=TaskSourceType.AI_PLAN,
                source_id=uuid4(),  # plan ID would be passed in real impl
                created_by=created_by,
                title=f"{action['type']}: {action.get('subject', 'Study')}",
                deadline=None,  # Would be set based on action
                explicit_priority=None,
            )
            tasks.append(task)

        return tasks
