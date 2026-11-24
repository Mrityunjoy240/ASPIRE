"""W1b security posture: RLS on the class-teacher table and grant boundaries."""

from __future__ import annotations

import psycopg

from w1a_support import ASSIGNMENT, P1, P2, expect_error, w1a_base
from w1b_support import SECTION_A, SECTION_B, SECTION_TEACHER, w1b_base


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_the_class_teacher_table_uses_enable_and_force_rls(
    conn: psycopg.Connection,
) -> None:
    [(enabled, forced)] = _rows(
        conn,
        """
        SELECT relrowsecurity, relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'academic' AND c.relname = 'section_teacher_assignment'
        """,
    )
    assert enabled and forced


def test_only_the_owner_has_an_all_command_policy(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT tablename, policyname, roles, cmd
        FROM pg_policies
        WHERE schemaname = 'academic'
        ORDER BY policyname
        """,
    )
    # W1b created the owner policy and the self-select policy. W2 adds the
    # owner_iam helper-read policy used by iam.is_section_teacher.
    assert len(rows) == 3, rows
    application_all = [
        row for row in rows
        if row[3] == "ALL" and not set(row[2]) <= {"owner_academic"}
    ]
    assert application_all == [], application_all
    assert any(
        row[2] == ["owner_academic"] and row[3] == "ALL" for row in rows
    ), rows
    assert any(row[3] == "SELECT" for row in rows), rows
    assert any(row[2] == ["owner_iam"] and row[3] == "SELECT" for row in rows), rows


def test_a_class_teacher_sees_only_own_rows(
    conn: psycopg.Connection, w1b_base
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        cur.execute("SELECT count(*) FROM academic.section_teacher_assignment")
        assert cur.fetchone()[0] == 0, "no person context must yield no rows"

        cur.execute("SELECT set_config('app.person_id', %s, true)", (P1,))
        cur.execute(
            "SELECT section_teacher_assignment_id FROM academic.section_teacher_assignment"
        )
        rows = cur.fetchall()
        assert [str(row[0]) for row in rows] == [SECTION_TEACHER]

        cur.execute("SELECT set_config('app.person_id', %s, true)", (P2,))
        cur.execute("SELECT count(*) FROM academic.section_teacher_assignment")
        assert cur.fetchone()[0] == 0

        cur.execute("RESET ROLE")


def test_app_erp_cannot_write_the_rls_table(
    conn: psycopg.Connection, w1b_base
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        cur.execute("SELECT set_config('app.person_id', %s, true)", (P1,))

        expect_error(
            conn,
            """
            INSERT INTO academic.section_teacher_assignment
                (section_id, person_id, role_in_section, valid_from, status,
                 authority_role_assignment_id)
            VALUES (%s, %s, 'class_teacher', CURRENT_DATE, 'active', %s)
            """,
            (SECTION_B, P2, ASSIGNMENT),
            contains="row-level security",
        )

        # No UPDATE policy: the row is not visible to UPDATE, so the statement
        # affects zero rows rather than raising. Prove nothing changed.
        cur.execute(
            """
            UPDATE academic.section_teacher_assignment
            SET change_reason = 'unauthorised'
            WHERE section_teacher_assignment_id = %s
            RETURNING section_teacher_assignment_id
            """,
            (SECTION_TEACHER,),
        )
        assert cur.fetchall() == []

        cur.execute("RESET ROLE")
        cur.execute(
            "SELECT change_reason FROM academic.section_teacher_assignment WHERE section_teacher_assignment_id = %s",
            (SECTION_TEACHER,),
        )
        assert cur.fetchone() == (None,)


def test_cip_reads_the_catalogue_but_not_delivery_tables(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        cur.execute("SELECT count(*) FROM academic.programme")
        assert cur.fetchone()[0] == 1

        expect_error(
            conn,
            "SELECT count(*) FROM academic.course_offering",
            contains="permission denied",
        )
        expect_error(
            conn,
            "SELECT count(*) FROM academic.section_teacher_assignment",
            contains="permission denied",
        )
        expect_error(
            conn,
            """
            INSERT INTO academic.programme
                (institution_id, department_id, programme_code, bcrec_code, name, level)
            VALUES (gen_random_uuid(), gen_random_uuid(), 'X', 'X', 'X', 'UG')
            """,
            contains="permission denied",
        )

        cur.execute("RESET ROLE")


def test_integration_role_has_no_academic_grant(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_integration")
        expect_error(
            conn,
            "SELECT count(*) FROM academic.programme",
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_trigger_functions_are_not_executable_by_application_roles(
    conn: psycopg.Connection,
) -> None:
    for function in (
        "academic.reject_course_version_update()",
        "academic.enforce_course_offering_section_batch()",
    ):
        for role in ("app_erp", "app_cip", "app_integration", "app_worker", "audit_writer"):
            [(actual,)] = _rows(
                conn,
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
                (role, function),
            )
            assert actual is False, f"{role} can execute {function}"
