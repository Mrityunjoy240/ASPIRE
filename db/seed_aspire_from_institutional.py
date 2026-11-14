# db/seed_aspire_from_institutional.py
"""
Seeds ASPIRE Core Platform with institutional data derived from BCREC Central
(db/institutional/seed/public_catalog.json).
"""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.institutions import Institution
from app.models.rules import InstitutionRule
from app.models.academic import Batch, Course
from app.models.users import User
from app.models.student import StudentProfile

CATALOG_PATH = Path(__file__).parent / "institutional" / "seed" / "public_catalog.json"

async def seed():
    if not CATALOG_PATH.exists():
        print(f"Catalog not found at {CATALOG_PATH}")
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    inst_data = catalog.get("institution", {})
    legal_name = inst_data.get("legal_name", "Dr. B. C. Roy Engineering College, Durgapur")
    short_name = inst_data.get("short_name", "BCREC").lower()

    async with async_session_factory() as session:
        # 1. Institution
        res = await session.execute(select(Institution).where(Institution.slug == short_name))
        inst = res.scalar_one_or_none()
        if not inst:
            inst = Institution(
                id=uuid4(),
                name=legal_name,
                slug=short_name,
                status="ACTIVE",
            )
            session.add(inst)
            await session.flush()
            print(f"Created institution: {inst.name} ({inst.slug})")
        else:
            print(f"Institution exists: {inst.name}")

        # 2. Institution Rules
        rules = [
            ("attendance_threshold", 75.0),
            ("grade_threshold", 60.0),
            ("escalation_days", 7),
            ("ai_enabled", True),
        ]
        for rule_id, default_val in rules:
            r_res = await session.execute(
                select(InstitutionRule).where(
                    InstitutionRule.institution_id == inst.id,
                    InstitutionRule.rule_id == rule_id,
                )
            )
            existing_rule = r_res.scalar_one_or_none()
            if not existing_rule:
                session.add(
                    InstitutionRule(
                        id=uuid4(),
                        institution_id=inst.id,
                        rule_id=rule_id,
                        scope_level="INSTITUTION",
                        scope_id=inst.id,
                        value={"threshold": default_val} if isinstance(default_val, (int, float)) else {"enabled": default_val},
                        status="ACTIVE",
                    )
                )
                print(f"Created rule: {rule_id} -> {default_val}")

        await session.commit()
        print("Seeding from institutional catalog completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())

