# app/services/rules_reader.py
# Shared institution_rules readers (05 §12). Extracted from the attendance
# what-if endpoint so the follow-up improvement check (ADR-004) and the
# router use one resolver — no duplicated rule-query logic (one shared core).
#
# Resolution order mirrors the established pattern: institution scope first,
# then batch scope, then a documented fallback constant (attendance 75.00,
# follow-up window 7 days — ADR-004 §2.6). Every fallback is explicit; the
# scheduler/engine never invents thresholds (03 §8.3 business-rule ownership).

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rules import InstitutionRule

# Documented fallbacks (not silent defaults — cited in ADR-004 §2.6 and the
# attendance what-if contract).
DEFAULT_ATTENDANCE_THRESHOLD = Decimal("75.00")
DEFAULT_FOLLOWUP_EVALUATION_WINDOW_DAYS = 7

_RULE_ATTENDANCE_THRESHOLD = "attendance_threshold"
_RULE_FOLLOWUP_WINDOW = "followup_evaluation_window_days"


async def _student_institution_and_batch(
    session: AsyncSession, student_id: UUID
) -> tuple[UUID | None, UUID | None]:
    """Student -> institution ownership goes through the batch (003/004:
    student_profiles carry batch_id only — no institution_id column)."""
    from app.models.academic import Batch
    from app.models.student import StudentProfile

    result = await session.execute(
        select(Batch.institution_id, Batch.id)
        .join(StudentProfile, StudentProfile.batch_id == Batch.id)
        .where(StudentProfile.id == student_id)
    )
    row = result.first()
    if not row:
        return None, None
    return row[0], row[1]


async def _active_rule_value(
    session: AsyncSession,
    *,
    institution_id: UUID,
    rule_id: str,
    scope_level: str,
    scope_id: UUID | None,
) -> dict | None:
    stmt = select(InstitutionRule.value).where(
        InstitutionRule.institution_id == institution_id,
        InstitutionRule.rule_id == rule_id,
        InstitutionRule.scope_level == scope_level,
        InstitutionRule.status == "ACTIVE",
    )
    if scope_id is not None:
        stmt = stmt.where(InstitutionRule.scope_id == scope_id)
    stmt = stmt.order_by(InstitutionRule.version.desc()).limit(1)
    value = await session.execute(stmt)
    rule = value.scalar_one_or_none()
    if rule and isinstance(rule, dict):
        return rule
    return None


async def get_attendance_threshold(session: AsyncSession, student_id: UUID) -> Decimal:
    """Institution `attendance_threshold` rule (value {"threshold": N});
    batch scope honored; documented fallback 75.00 when no rule exists."""
    institution_id, batch_id = await _student_institution_and_batch(session, student_id)
    if institution_id is None:
        return DEFAULT_ATTENDANCE_THRESHOLD

    rule = await _active_rule_value(
        session,
        institution_id=institution_id,
        rule_id=_RULE_ATTENDANCE_THRESHOLD,
        scope_level="INSTITUTION",
        scope_id=None,
    )
    if rule and "threshold" in rule:
        return Decimal(str(rule["threshold"]))

    if batch_id:
        rule = await _active_rule_value(
            session,
            institution_id=institution_id,
            rule_id=_RULE_ATTENDANCE_THRESHOLD,
            scope_level="BATCH",
            scope_id=batch_id,
        )
        if rule and "threshold" in rule:
            return Decimal(str(rule["threshold"]))

    return DEFAULT_ATTENDANCE_THRESHOLD


async def get_followup_evaluation_window_days(
    session: AsyncSession, student_id: UUID
) -> int:
    """Institution `followup_evaluation_window_days` rule (value {"days": N});
    batch scope honored; documented fallback 7 days (ADR-004 §2.6)."""
    institution_id, batch_id = await _student_institution_and_batch(session, student_id)
    if institution_id is None:
        return DEFAULT_FOLLOWUP_EVALUATION_WINDOW_DAYS

    rule = await _active_rule_value(
        session,
        institution_id=institution_id,
        rule_id=_RULE_FOLLOWUP_WINDOW,
        scope_level="INSTITUTION",
        scope_id=None,
    )
    if rule and "days" in rule:
        return int(rule["days"])

    if batch_id:
        rule = await _active_rule_value(
            session,
            institution_id=institution_id,
            rule_id=_RULE_FOLLOWUP_WINDOW,
            scope_level="BATCH",
            scope_id=batch_id,
        )
        if rule and "days" in rule:
            return int(rule["days"])

    return DEFAULT_FOLLOWUP_EVALUATION_WINDOW_DAYS
