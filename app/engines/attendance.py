# app/engines/attendance.py
# Attendance Rule Engine — deterministic, pure Python (no LLM, no I/O).
# Calculates attendance percentage, risk bands, recovery math.
# Engines calculate. Agents propose. Humans approve.

from dataclasses import dataclass
from datetime import UTC
from decimal import ROUND_HALF_UP, Decimal

from app.models.attendance import AttendanceRecord
from app.models.enums import AttendanceStatus


@dataclass(frozen=True)
class AttendanceConfig:
    """Configuration-driven thresholds (from institution_rules)."""
    threshold_percent: Decimal  # e.g., Decimal("75.00")
    warning_margin: Decimal = Decimal("5.00")  # threshold - margin = warning zone
    critical_margin: Decimal = Decimal("2.00")  # threshold - critical_margin = critical zone


@dataclass(frozen=True)
class DerivedState:
    """Deterministic engine output — no LLM involvement."""
    student_id: str
    course_run_id: str
    classes_conducted: int
    classes_attended: int
    attendance_percentage: Decimal | None  # None if conducted == 0
    risk_band: str  # SAFE | WARNING | CRITICAL | DATA_CONFLICT
    required_to_recover: int | None  # classes needed to reach threshold
    computed_at: str  # ISO timestamp


class AttendanceEngine:
    """Pure deterministic attendance calculation engine."""

    def __init__(self, config: AttendanceConfig):
        self.config = config

    def compute(self, records: list[AttendanceRecord]) -> DerivedState:
        """Compute derived state from VERIFIED records only."""
        if not records:
            raise ValueError("No attendance records provided")

        student_id = str(records[0].student_id)
        course_run_id = str(records[0].course_run_id)

        # Only VERIFIED records count (Constitution: deterministic engines only)
        verified = [r for r in records if r.record_status == "VERIFIED"]
        conducted = len(verified)
        attended = sum(1 for r in verified if r.status == AttendanceStatus.PRESENT)

        # Attendance percentage
        if conducted == 0:
            percentage: Decimal | None = None
        else:
            percentage = Decimal(attended) / Decimal(conducted) * Decimal("100")
            percentage = percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Risk band
        if conducted == 0:
            risk_band = "DATA_CONFLICT"
        elif percentage is None:
            risk_band = "DATA_CONFLICT"
        elif percentage >= self.config.threshold_percent:
            risk_band = "SAFE"
        elif percentage >= self.config.threshold_percent - self.config.warning_margin:
            risk_band = "WARNING"
        else:
            risk_band = "CRITICAL"

        # Recovery math: (attended + x) / (conducted + x) >= threshold
        if conducted == 0 or percentage is None or percentage >= self.config.threshold_percent:
            required_to_recover = 0
        else:
            # Solve: (attended + x) / (conducted + x) >= threshold
            # attended + x >= threshold * (conducted + x)
            # attended + x >= threshold * conducted + threshold * x
            # x - threshold * x >= threshold * conducted - attended
            # x * (1 - threshold) >= threshold * conducted - attended
            # x >= (threshold * conducted - attended) / (1 - threshold)
            threshold_decimal = self.config.threshold_percent / Decimal("100")
            numerator = threshold_decimal * Decimal(conducted) - Decimal(attended)
            denominator = Decimal("1") - threshold_decimal
            if denominator <= 0:
                required_to_recover = None  # Impossible to recover
            else:
                x = (numerator / denominator).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                required_to_recover = max(0, int(x))

        from datetime import datetime
        computed_at = datetime.now(UTC).isoformat()

        return DerivedState(
            student_id=student_id,
            course_run_id=course_run_id,
            classes_conducted=conducted,
            classes_attended=attended,
            attendance_percentage=percentage,
            risk_band=risk_band,
            required_to_recover=required_to_recover,
            computed_at=computed_at,
        )

    def what_if(self, current_state: DerivedState, future_present: int) -> DerivedState:
        """Project attendance if student attends `future_present` more classes."""
        if current_state.attendance_percentage is None:
            raise ValueError("Cannot project from null percentage")

        new_conducted = current_state.classes_conducted + future_present
        new_attended = current_state.classes_attended + future_present

        new_pct = Decimal(new_attended) / Decimal(new_conducted) * Decimal("100")
        new_pct = new_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Re-evaluate risk band
        if new_pct >= self.config.threshold_percent:
            new_risk = "SAFE"
        elif new_pct >= self.config.threshold_percent - self.config.warning_margin:
            new_risk = "WARNING"
        else:
            new_risk = "CRITICAL"

        # New recovery
        threshold_decimal = self.config.threshold_percent / Decimal("100")
        numerator = threshold_decimal * Decimal(new_conducted) - Decimal(new_attended)
        denominator = Decimal("1") - threshold_decimal
        if denominator <= 0 or new_pct >= self.config.threshold_percent:
            new_required = 0
        else:
            x = (numerator / denominator).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            new_required = max(0, int(x))

        from datetime import datetime
        return DerivedState(
            student_id=current_state.student_id,
            course_run_id=current_state.course_run_id,
            classes_conducted=new_conducted,
            classes_attended=new_attended,
            attendance_percentage=new_pct,
            risk_band=new_risk,
            required_to_recover=new_required,
            computed_at=datetime.now(UTC).isoformat(),
        )
