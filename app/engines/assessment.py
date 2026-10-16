# app/engines/assessment.py
# Assessment Engine — deterministic, pure Python.
# Configuration-driven via institution_rules (DM-ASSESS01).
# No hardcoded CIA/PCIA weightings.

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.assessment import AssessmentSubmission
from app.models.enums import AssessmentSubmissionStatus


@dataclass(frozen=True)
class AssessmentScheme:
    """Effective assessment scheme for a course run (from institution_rules)."""
    components: list[dict]  # [{name, type, weight_percent, is_mandatory}, ...]


@dataclass(frozen=True)
class ComponentResult:
    """Per-component calculation result."""
    component_id: str
    component_name: str
    status: str
    obtained_marks: Decimal | None
    max_marks: Decimal
    weight_percent: Decimal | None
    percentage: Decimal | None
    is_included: bool  # Whether included in weighted average


@dataclass(frozen=True)
class StudentAssessmentState:
    """Complete assessment state for a student in a course run."""
    student_id: str
    course_run_id: str
    component_results: list[ComponentResult]
    weighted_average: Decimal | None  # None if no gradable components
    trend: str  # IMPROVING | STABLE | DECLINING | TREND_NOT_ESTABLISHED
    missing_components: list[str]


class AssessmentEngine:
    """
    Deterministic assessment engine.
    - Uses configuration-driven scheme (institution_rules)
    - SUBMITTED_PENDING_EVALUATION != 0 (never treated as zero)
    - OFFICIAL_ZERO is a real zero, recorded
    - WITHHELD/CANCELLED excluded from averages
    """

    MIN_EVALUATIONS_FOR_TREND = 6

    def __init__(self, scheme: AssessmentScheme):
        self.scheme = scheme
        self._components_by_id = {c["id"]: c for c in scheme.components}

    def compute(self, submissions: list[AssessmentSubmission]) -> StudentAssessmentState:
        """Compute full assessment state from submissions."""
        if not submissions:
            raise ValueError("No submissions provided")

        student_id = str(submissions[0].student_id)
        course_run_id = str(submissions[0].assessment_component.course_run_id)

        # Group by component
        results = []
        included_results = []
        graded_results = []

        for sub in submissions:
            comp_config = self._components_by_id.get(str(sub.assessment_component_id))
            if not comp_config:
                continue

            weight = Decimal(str(comp_config.get("weight_percent", 0))) if comp_config.get("weight_percent") else None
            is_mandatory = comp_config.get("is_mandatory", True)

            # Status-based handling
            if sub.status == AssessmentSubmissionStatus.GRADED:
                percentage = None
                if sub.obtained_marks is not None and sub.maximum_marks > 0:
                    percentage = (sub.obtained_marks / sub.maximum_marks * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                result = ComponentResult(
                    component_id=str(sub.assessment_component_id),
                    component_name=comp_config["name"],
                    status=sub.status.value,
                    obtained_marks=sub.obtained_marks,
                    max_marks=sub.maximum_marks,
                    weight_percent=weight,
                    percentage=percentage,
                    is_included=True,
                )
                results.append(result)
                if percentage is not None and weight is not None and weight > 0:
                    included_results.append(result)

            elif sub.status == AssessmentSubmissionStatus.OFFICIAL_ZERO:
                # Official zero IS included in average (it's a real zero, recorded)
                result = ComponentResult(
                    component_id=str(sub.assessment_component_id),
                    component_name=comp_config["name"],
                    status=sub.status.value,
                    obtained_marks=Decimal("0"),
                    max_marks=sub.maximum_marks,
                    weight_percent=weight,
                    percentage=Decimal("0"),
                    is_included=True,
                )
                results.append(result)
                if weight is not None and weight > 0:
                    included_results.append(result)

            elif sub.status == AssessmentSubmissionStatus.SUBMITTED_PENDING_EVALUATION:
                # PENDING ≠ 0 — excluded from average, flagged separately
                result = ComponentResult(
                    component_id=str(sub.assessment_component_id),
                    component_name=comp_config["name"],
                    status=sub.status.value,
                    obtained_marks=None,
                    max_marks=sub.maximum_marks,
                    weight_percent=weight,
                    percentage=None,
                    is_included=False,
                )
                results.append(result)

            elif sub.status in (AssessmentSubmissionStatus.WITHHELD, AssessmentSubmissionStatus.CANCELLED):
                # Excluded from average
                result = ComponentResult(
                    component_id=str(sub.assessment_component_id),
                    component_name=comp_config["name"],
                    status=sub.status.value,
                    obtained_marks=None,
                    max_marks=sub.maximum_marks,
                    weight_percent=weight,
                    percentage=None,
                    is_included=False,
                )
                results.append(result)

            else:
                # NOT_SUBMITTED — not included, flagged
                result = ComponentResult(
                    component_id=str(sub.assessment_component_id),
                    component_name=comp_config["name"],
                    status=sub.status.value,
                    obtained_marks=None,
                    max_marks=sub.maximum_marks,
                    weight_percent=weight,
                    percentage=None,
                    is_included=False,
                )
                results.append(result)

        # Weighted average calculation
        weighted_average = self._calculate_weighted_average(included_results)

        # Trend: need at least 6 graded evaluations
        graded_count = sum(1 for r in results if r.status == "GRADED")
        if graded_count >= self.MIN_EVALUATIONS_FOR_TREND:
            # Simple trend: compare first half vs second half of graded components
            graded_percentages = [r.percentage for r in results if r.status == "GRADED" and r.percentage is not None]
            if len(graded_percentages) >= self.MIN_EVALUATIONS_FOR_TREND:
                mid = len(graded_percentages) // 2
                first_half = sum(graded_percentages[:mid]) / mid
                second_half = sum(graded_percentages[mid:]) / (len(graded_percentages) - mid)
                diff = second_half - first_half
                if diff > 2:
                    trend = "IMPROVING"
                elif diff < -2:
                    trend = "DECLINING"
                else:
                    trend = "STABLE"
            else:
                trend = "TREND_NOT_ESTABLISHED"
        else:
            trend = "TREND_NOT_ESTABLISHED"

        # Missing components (mandatory but not submitted)
        missing = []
        for comp_id, comp in self._components_by_id.items():
            if comp.get("is_mandatory", True):
                sub = next((s for s in submissions if str(s.assessment_component_id) == comp_id), None)
                if not sub or sub.status in (
                    AssessmentSubmissionStatus.NOT_SUBMITTED,
                    AssessmentSubmissionStatus.SUBMITTED_PENDING_EVALUATION,
                ):
                    missing.append(comp["name"])

        return StudentAssessmentState(
            student_id=str(submissions[0].student_id),
            course_run_id=course_run_id,
            component_results=results,
            weighted_average=weighted_average,
            trend=trend,
            missing_components=missing,
        )

    def _calculate_weighted_average(self, included: list[ComponentResult]) -> Decimal | None:
        """Calculate weighted average from included components."""
        if not included:
            return None

        total_weight = sum(r.weight_percent for r in included if r.weight_percent is not None)
        if total_weight == 0:
            return None

        weighted_sum = sum(
            r.percentage * r.weight_percent
            for r in included
            if r.percentage is not None and r.weight_percent is not None
        )
        return (weighted_sum / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
