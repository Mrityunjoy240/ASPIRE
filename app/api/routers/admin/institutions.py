# app/api/routers/admin/institutions.py
# Admin router — Institution management and rule configuration.
# Multi-tenant control: each Institution has its own InstitutionRule rows
# (key-value JSONB pairs in institution_rules, per 05 §9, migration 012/013).
# Authorization: ADMIN role only (07 §2 permission matrix).

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_context, get_session, log_audit, require_roles
from app.api.schemas import (
    InstitutionCreateRequest,
    InstitutionResponse,
    InstitutionRulesUpdate,
    InstitutionUpdateRequest,
)
from app.models.enums import UserRole
from app.models.institutions import Institution
from app.models.rules import InstitutionRule

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


async def _get_rules_summary(
    session: AsyncSession, institution_id: UUID
) -> InstitutionRulesUpdate | None:
    """Read active rule values for an institution into a flat summary."""
    rules_result = await session.execute(
        select(InstitutionRule).where(
            InstitutionRule.institution_id == institution_id,
            InstitutionRule.status == "ACTIVE",
        )
    )
    rule_rows = rules_result.scalars().all()
    if not rule_rows:
        return None

    rules_dict: dict = {}
    for row in rule_rows:
        if row.rule_id == "attendance_threshold" and isinstance(row.value, dict):
            rules_dict["attendance_threshold"] = row.value.get("threshold")
        elif row.rule_id == "grade_threshold" and isinstance(row.value, dict):
            rules_dict["grade_threshold"] = row.value.get("threshold")
        elif row.rule_id == "ai_enabled" and isinstance(row.value, dict):
            rules_dict["ai_enabled"] = row.value.get("enabled")
        elif row.rule_id == "escalation_days" and isinstance(row.value, dict):
            rules_dict["escalation_days"] = row.value.get("days")

    return InstitutionRulesUpdate(**rules_dict) if rules_dict else None


@router.get("/institutions", response_model=List[InstitutionResponse])
async def list_institutions(
    session: AsyncSession = Depends(get_session),
) -> List[InstitutionResponse]:
    """List all registered institutions (System Admin view).

    Returns slug, name, and status for each tenant.
    """
    result = await session.execute(select(Institution).order_by(Institution.name))
    institutions = result.scalars().all()
    return [
        InstitutionResponse(
            id=inst.id,
            name=inst.name,
            slug=inst.slug,
            status=inst.status,
            rules=None,
        )
        for inst in institutions
    ]


@router.post(
    "/institutions",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_institution(
    request: InstitutionCreateRequest,
    auth=Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
) -> InstitutionResponse:
    """Onboard a new college/institution into the ASPIRE platform."""
    # Check for existing slug
    existing = await session.execute(
        select(Institution).where(Institution.slug == request.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Institution slug '{request.slug}' already exists",
        )

    now = datetime.now(timezone.utc)
    institution = Institution(
        name=request.name,
        slug=request.slug,
        status="ACTIVE",
        created_at=now,
    )
    session.add(institution)
    await session.flush()

    # Seed default attendance and grade thresholds for the new college
    default_rules = [
        ("attendance_threshold", {"threshold": 75.0}),
        ("grade_threshold", {"threshold": 60.0}),
        ("ai_enabled", {"enabled": True}),
        ("escalation_days", {"days": 7}),
    ]
    for rule_id, val in default_rules:
        rule_row = InstitutionRule(
            institution_id=institution.id,
            rule_id=rule_id,
            scope_level="INSTITUTION",
            scope_id=None,
            value=val,
            effective_from=now,
            version=1,
            status="ACTIVE",
            updated_by=auth.user_id,
            created_at=now,
            updated_at=now,
        )
        session.add(rule_row)

    await log_audit(
        session,
        actor_id=auth.user_id,
        actor_type="USER",
        action_type="INSTITUTION_CREATED",
        entity_table="institutions",
        entity_id=institution.id,
        previous_state=None,
        new_state={"name": institution.name, "slug": institution.slug, "status": "ACTIVE"},
        source_system="ADMIN_WEB",
    )
    await session.commit()

    rules = await _get_rules_summary(session, institution.id)
    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        status=institution.status,
        rules=rules,
    )


@router.get("/institutions/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> InstitutionResponse:
    """Get a single institution with its current active rule values."""
    result = await session.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    rules = await _get_rules_summary(session, institution.id)
    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        status=institution.status,
        rules=rules,
    )


@router.patch("/institutions/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: UUID,
    request: InstitutionUpdateRequest,
    auth=Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
) -> InstitutionResponse:
    """Update institution details or status (e.g. SUSPENDED / ACTIVE)."""
    result = await session.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    previous_state = {"name": institution.name, "status": institution.status}
    if request.name is not None:
        institution.name = request.name
    if request.status is not None:
        institution.status = request.status

    await log_audit(
        session,
        actor_id=auth.user_id,
        actor_type="USER",
        action_type="INSTITUTION_UPDATED",
        entity_table="institutions",
        entity_id=institution.id,
        previous_state=previous_state,
        new_state={"name": institution.name, "status": institution.status},
        source_system="ADMIN_WEB",
    )
    await session.commit()

    rules = await _get_rules_summary(session, institution.id)
    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        status=institution.status,
        rules=rules,
    )


@router.patch(
    "/institutions/{institution_id}/rules",
    response_model=InstitutionResponse,
    summary="Update institution-specific rules and thresholds",
)
async def update_institution_rules(
    institution_id: UUID,
    request: InstitutionRulesUpdate,
    auth=Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
) -> InstitutionResponse:
    """Update active rule values for an institution with audit trail.

    Enables Mother System to configure custom attendance cutoffs (e.g. 75% vs 80%),
    grade thresholds, AI agent enablement, and escalation timelines per college.
    """
    result = await session.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    now = datetime.now(timezone.utc)
    updates_map = {}
    if request.attendance_threshold is not None:
        updates_map["attendance_threshold"] = {"threshold": request.attendance_threshold}
    if request.grade_threshold is not None:
        updates_map["grade_threshold"] = {"threshold": request.grade_threshold}
    if request.ai_enabled is not None:
        updates_map["ai_enabled"] = {"enabled": request.ai_enabled}
    if request.escalation_days is not None:
        updates_map["escalation_days"] = {"days": request.escalation_days}

    for rule_id, val in updates_map.items():
        existing_res = await session.execute(
            select(InstitutionRule).where(
                InstitutionRule.institution_id == institution_id,
                InstitutionRule.rule_id == rule_id,
                InstitutionRule.scope_level == "INSTITUTION",
                InstitutionRule.status == "ACTIVE",
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            existing.value = val
            existing.updated_by = auth.user_id
            existing.updated_at = now
        else:
            new_rule = InstitutionRule(
                institution_id=institution_id,
                rule_id=rule_id,
                scope_level="INSTITUTION",
                scope_id=None,
                value=val,
                effective_from=now,
                version=1,
                status="ACTIVE",
                updated_by=auth.user_id,
                created_at=now,
                updated_at=now,
            )
            session.add(new_rule)

    await log_audit(
        session,
        actor_id=auth.user_id,
        actor_type="USER",
        action_type="INSTITUTION_RULES_UPDATED",
        entity_table="institution_rules",
        entity_id=institution.id,
        previous_state=None,
        new_state=updates_map,
        source_system="ADMIN_WEB",
    )
    await session.commit()

    rules = await _get_rules_summary(session, institution.id)
    return InstitutionResponse(
        id=institution.id,
        name=institution.name,
        slug=institution.slug,
        status=institution.status,
        rules=rules,
    )
