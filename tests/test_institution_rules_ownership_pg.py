# tests/test_institution_rules_ownership_pg.py
# DEC-02 (approved): every institution_rules row belongs to an institution.
# - migration 013 preflight REFUSES to enforce NOT NULL while NULL-ownership
#   rows exist (no silent delete/reassign/invent) and leaves the column
#   untouched after the aborted transaction;
# - migration 013 applies on an empty table and enforces NOT NULL afterwards;
# - institution-owned rows insert/query fine, NULL ownership cannot persist;
# - the UNIQUE constraint from 012 remains intact.
# DSN guard + throwaway schema conventions: tests/conftest.py.

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.rules import InstitutionRule

pytestmark = pytest.mark.integration

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"
MIGRATION_013 = "013_institution_rules_require_institution.sql"


def _require_dsn() -> str:
    """Copy of the tests/conftest.py guard for the self-contained fixture
    below (a partial migration chain cannot use the pg_engine fixture)."""
    dsn = os.environ.get("ASPIRE_TEST_PG_DSN")
    if not dsn:
        pytest.skip("ASPIRE_TEST_PG_DSN not set — PostgreSQL integration test not executed")
    database = dsn.rsplit("/", 1)[-1].split("?")[0]
    if not database.endswith("_test"):
        pytest.fail(f"refusing to run against database '{database}'")
    return dsn


async def test_migration_preflight_refuses_null_ownership():
    """013 must abort (with an actionable message) while a NULL-ownership row
    exists, and must NOT alter the column or touch the row on failure."""
    dsn = _require_dsn()
    schema = f"aspire_it_{uuid.uuid4().hex[:10]}"
    engine = create_async_engine(
        dsn,
        poolclass=NullPool,
        future=True,
        connect_args={"options": f"-c search_path={schema},public"},
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        # Full chain EXCEPT 013 (applied manually below).
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name == MIGRATION_013:
                continue
            async with engine.begin() as conn:
                await conn.execute(text(path.read_text(encoding="utf-8")))

        # Arrange: one rule row without institution ownership (NULL bypasses
        # the FK, so no institutions row is required).
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO institution_rules "
                    "(institution_id, rule_id, scope_level, scope_id, value, effective_from) "
                    "VALUES (NULL, 'attendance_threshold', 'INSTITUTION', NULL, "
                    "'{\"threshold\": 75}'::jsonb, now())"
                )
            )

        sql_013 = (MIGRATIONS_DIR / MIGRATION_013).read_text(encoding="utf-8")
        with pytest.raises(Exception) as excinfo:
            async with engine.begin() as conn:
                await conn.execute(text(sql_013))
        assert "DEC-02 preflight failed" in str(excinfo.value)

        # Aborted transaction: column still nullable, the row still there.
        async with engine.begin() as conn:
            notnull = (
                await conn.execute(
                    text(
                        "SELECT a.attnotnull FROM pg_attribute a "
                        "WHERE a.attrelid = CAST('institution_rules' AS regclass) "
                        "AND a.attname = 'institution_id'"
                    )
                )
            ).scalar_one()
            null_rows = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM institution_rules "
                        "WHERE institution_id IS NULL"
                    )
                )
            ).scalar_one()
        assert notnull is False, "013 must not flip NOT NULL after preflight failure"
        assert null_rows == 1, "the NULL-ownership row must not be deleted"
    finally:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            await engine.dispose()


async def _institution_id_column_notnull(engine) -> bool:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                text(
                    "SELECT a.attnotnull FROM pg_attribute a "
                    "WHERE a.attrelid = CAST('institution_rules' AS regclass) "
                    "AND a.attname = 'institution_id'"
                )
            )
        ).scalar_one()


async def test_full_chain_enforces_not_null(pg_engine):
    """With zero NULL rows the full chain (incl. 013) sets NOT NULL."""
    assert await _institution_id_column_notnull(pg_engine) is True


async def test_null_ownership_insert_rejected(pg_engine):
    """After 013, a NULL-institution rule cannot persist (IntegrityError)."""
    with pytest.raises(IntegrityError):
        async with pg_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO institution_rules "
                    "(institution_id, rule_id, scope_level, scope_id, value, effective_from) "
                    "VALUES (NULL, 'attendance_threshold', 'INSTITUTION', NULL, "
                    "'{\"threshold\": 75}'::jsonb, now())"
                )
            )


async def test_institution_owned_rule_insert_and_query(pg_engine, pg_seed):
    """Institution-owned rules insert through the ORM and are queryable by
    institution_id (the attendance-router lookup shape)."""
    now = datetime.now(UTC)
    rule = InstitutionRule(
        institution_id=pg_seed.institution_id,
        rule_id="attendance_threshold",
        scope_level="INSTITUTION",
        scope_id=None,
        value={"threshold": 80.0},
        effective_from=now,
        version=1,
        status="ACTIVE",
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(rule)
        await session.commit()

    async with AsyncSession(pg_engine) as session:
        rows = (
            await session.execute(
                select(InstitutionRule).where(
                    InstitutionRule.institution_id == pg_seed.institution_id
                )
            )
        ).scalars().all()
    assert len(rows) == 1
    assert rows[0].value == {"threshold": 80.0}


async def test_unique_constraint_remains_intact(pg_engine, pg_seed):
    """013 must not drop/alter 012's UNIQUE constraint: a duplicate
    (institution, rule, scope, version) insert fails, and the constraint is
    still registered in pg_constraint."""
    now = datetime.now(UTC)
    scope_id = uuid.uuid4()
    dup = dict(
        institution_id=pg_seed.institution_id,
        rule_id="assessment_scheme",
        scope_level="SEMESTER",
        scope_id=scope_id,
        value={"weight": 100},
        effective_from=now,
        version=1,
        status="ACTIVE",
    )
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        session.add(InstitutionRule(**dup))
        await session.commit()

    with pytest.raises(IntegrityError):
        async with AsyncSession(pg_engine) as session:
            session.add(InstitutionRule(**dup))
            await session.flush()

    # The constraint survives: a unique constraint over the five key columns
    # is still registered. (Note: 012's inline UNIQUE (...) is unnamed, so
    # PostgreSQL auto-generated a name — the ORM's declared name
    # "unique_institution_rule" only exists in model metadata. Behavior,
    # not naming, is the DEC-02 contract here.)
    async with AsyncSession(pg_engine) as session:
        unique_constraints = (
            await session.execute(
                text(
                    "SELECT c.conname, array_length(c.conkey, 1) "
                    "FROM pg_constraint c "
                    "WHERE c.conrelid = CAST('institution_rules' AS regclass) "
                    "AND c.contype = 'u'"
                )
            )
        ).all()
    assert len(unique_constraints) == 1, "exactly one unique constraint on the table"
    conname, column_count = unique_constraints[0]
    assert column_count == 5, f"unique key must cover 5 columns, got {column_count}"
    assert conname
