"""W7 / Phase 9B IAM-SEP regression: app_erp must not write authority tables.

Every negative test executes as the real ``app_erp`` role. No permission check
is mocked. The catalog checks use ``has_table_privilege`` and
``has_column_privilege`` so an inherited or column-level grant cannot hide.
"""

from __future__ import annotations

import psycopg
import pytest

from w1a_support import (
    ASSIGNMENT,
    PERMISSION,
    P1,
    ROLE,
    TERM,
    expect_error,
    w1a_base,
)

_ = w1a_base  # imported fixture

RUNTIME_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)

AUTHORITY_TABLES = (
    ("iam", "role"),
    ("iam", "permission"),
    ("iam", "role_permission"),
    ("iam", "delegation"),
    ("academic", "offering_faculty"),
    ("faculty", "mentor_assignment"),
    ("core", "governance_membership"),
    ("policy", "policy_bundle"),
    ("policy", "policy_bundle_member"),
    ("policy", "policy_bundle_version"),
    ("policy", "rule"),
    ("policy", "rule_conflict"),
    ("policy", "rule_scope"),
    ("policy", "rule_version"),
)

POLICY_TABLES = tuple(target for target in AUTHORITY_TABLES if target[0] == "policy")


def _as_app_erp(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")


def _reset_role(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("RESET ROLE")


def test_app_erp_cannot_write_iam_catalogue(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    statements = (
        (
            "INSERT INTO iam.role (role_id, role_code, name, category) "
            "VALUES (gen_random_uuid(), 'ESCALATED_ROLE', 'Escalated', 'system')",
            (),
        ),
        (
            "UPDATE iam.role SET name = 'changed' WHERE role_id = %s",
            (ROLE,),
        ),
        (
            "INSERT INTO iam.permission "
            "(permission_id, permission_code, resource, action) "
            "VALUES (gen_random_uuid(), 'escalated.write', 'escalated', 'write')",
            (),
        ),
        (
            "UPDATE iam.permission SET is_active = false WHERE permission_id = %s",
            (PERMISSION,),
        ),
        (
            "INSERT INTO iam.role_permission (role_id, permission_id) "
            "VALUES (%s, %s)",
            (ROLE, PERMISSION),
        ),
        (
            "INSERT INTO iam.delegation "
            "(from_assignment_id, to_assignment_id, reason, valid_to) "
            "VALUES (%s, %s, 'escalate', now() + interval '1 day')",
            (ASSIGNMENT, ASSIGNMENT),
        ),
    )

    _as_app_erp(conn)
    try:
        for statement, params in statements:
            expect_error(conn, statement, params, contains="permission denied")
    finally:
        _reset_role(conn)


def test_app_erp_cannot_write_authority_tables(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    statements = (
        (
            "INSERT INTO academic.offering_faculty "
            "(course_offering_id, person_id) VALUES (gen_random_uuid(), %s)",
            (P1,),
        ),
        (
            "UPDATE academic.offering_faculty SET role_in_offering = 'instructor'",
            (),
        ),
        (
            "INSERT INTO faculty.mentor_assignment "
            "(mentor_person_id, student_id, term_id) "
            "VALUES (%s, gen_random_uuid(), %s)",
            (P1, TERM),
        ),
        (
            "UPDATE faculty.mentor_assignment SET status = 'inactive'",
            (),
        ),
        (
            "INSERT INTO core.governance_membership "
            "(governance_body_id, person_id, valid_from) "
            "VALUES (gen_random_uuid(), %s, CURRENT_DATE)",
            (P1,),
        ),
        (
            "UPDATE core.governance_membership SET status = 'inactive'",
            (),
        ),
    )

    _as_app_erp(conn)
    try:
        for statement, params in statements:
            expect_error(conn, statement, params, contains="permission denied")
    finally:
        _reset_role(conn)


@pytest.mark.parametrize(("schema", "table"), POLICY_TABLES)
def test_app_erp_cannot_write_policy_tables(
    conn: psycopg.Connection,
    w1a_base: psycopg.Connection,
    schema: str,
    table: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT quote_ident(column_name)
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND is_generated = 'NEVER'
            ORDER BY ordinal_position
            LIMIT 1
            """,
            (schema, table),
        )
        column = cur.fetchone()[0]

    statements = (
        (f"INSERT INTO {schema}.{table} DEFAULT VALUES", ()),
        (f"UPDATE {schema}.{table} SET {column} = {column}", ()),
    )

    _as_app_erp(conn)
    try:
        for statement, params in statements:
            expect_error(conn, statement, params, contains="permission denied")
    finally:
        _reset_role(conn)


def test_no_table_level_write_privileges_remain(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        for schema, table in AUTHORITY_TABLES:
            name = f"{schema}.{table}"
            cur.execute(
                "SELECT has_table_privilege('app_erp', %s, 'INSERT'), "
                "has_table_privilege('app_erp', %s, 'UPDATE')",
                (name, name),
            )
            assert cur.fetchone() == (False, False), name


def test_no_column_level_write_privileges_remain(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        for schema, table in AUTHORITY_TABLES:
            cur.execute(
                """
                SELECT a.attname
                FROM pg_attribute a
                WHERE a.attrelid = %s::regclass
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                  AND (
                        has_column_privilege('app_erp', a.attrelid, a.attname, 'INSERT')
                     OR has_column_privilege('app_erp', a.attrelid, a.attname, 'UPDATE')
                  )
                """,
                (f"{schema}.{table}",),
            )
            assert cur.fetchall() == [], f"{schema}.{table}"


def test_no_inherited_write_path(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH RECURSIVE closure(roleid) AS (
                SELECT oid FROM pg_roles WHERE rolname = 'app_erp'
                UNION
                SELECT am.roleid
                FROM pg_auth_members am
                JOIN closure c ON c.roleid = am.member
            )
            SELECT r.rolname
            FROM closure
            JOIN pg_roles r ON r.oid = closure.roleid
            ORDER BY 1
            """
        )
        roles = [row[0] for row in cur.fetchall()]
        assert set(roles) == {"app_erp", "g_erp"}, roles

        for role in roles:
            for schema, table in AUTHORITY_TABLES:
                name = f"{schema}.{table}"
                cur.execute(
                    "SELECT has_table_privilege(%s, %s, 'INSERT'), "
                    "has_table_privilege(%s, %s, 'UPDATE')",
                    (role, name, role, name),
                )
                assert cur.fetchone() == (False, False), f"{role} -> {name}"


def test_read_behavior_preserved(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        for schema, table in AUTHORITY_TABLES:
            name = f"{schema}.{table}"
            cur.execute(
                """
                SELECT has_table_privilege('app_erp', %s, 'SELECT')
                    OR EXISTS (
                        SELECT 1
                        FROM pg_attribute a
                        WHERE a.attrelid = %s::regclass
                          AND a.attnum > 0
                          AND NOT a.attisdropped
                          AND has_column_privilege(
                                'app_erp', a.attrelid, a.attname, 'SELECT'
                          )
                    )
                """,
                (name, name),
            )
            assert cur.fetchone()[0] is True, name

        for signature in (
            "iam.has_permission(text,text,uuid)",
            "iam.can_access_student(uuid)",
            "iam.can_access_offering(uuid)",
            "iam.is_allocated_to_offering(uuid)",
            "iam.is_mentor_of(uuid)",
        ):
            cur.execute(
                "SELECT has_function_privilege('app_erp', %s, 'EXECUTE')",
                (signature,),
            )
            assert cur.fetchone()[0] is True, signature


def test_runtime_roles_are_not_privileged(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole
            FROM pg_roles
            WHERE rolname = ANY(%s)
            """,
            (list(RUNTIME_ROLES),),
        )
        rows = cur.fetchall()
        assert len(rows) == len(RUNTIME_ROLES)
        for row in rows:
            assert row[1:] == (False, False, False, False), row

        cur.execute(
            """
            SELECT nspname, pg_get_userbyid(nspowner)
            FROM pg_namespace
            WHERE nspname NOT LIKE 'pg\\_%'
              AND nspname <> 'information_schema'
            """
        )
        for schema, owner in cur.fetchall():
            assert owner not in RUNTIME_ROLES, f"{schema} owned by {owner}"


def test_no_replacement_admin_role_or_function(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM pg_roles
            WHERE rolname IN (
                'app_admin', 'admin', 'erp_admin', 'runtime_admin', 'app_superuser'
            )
            """
        )
        assert cur.fetchone()[0] == 0

        cur.execute(
            """
            SELECT count(*)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname IN (
                'academic', 'assessment', 'attendance', 'cip', 'core', 'doc',
                'exam', 'faculty', 'iam', 'integration', 'knowledge', 'ops',
                'policy', 'student'
            )
              AND (
                    p.proname ILIKE '%admin%'
                 OR p.proname ILIKE '%grant_role%'
                 OR p.proname ILIKE '%assign_permission%'
              )
            """
        )
        assert cur.fetchone()[0] == 0
