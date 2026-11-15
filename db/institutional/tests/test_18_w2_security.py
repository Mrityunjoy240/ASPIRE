"""W2 security posture: the documented RLS arms, helper functions, and grants."""

from __future__ import annotations

from datetime import timedelta

import psycopg

from w1a_support import P1, P2, TODAY, expect_error, w1a_base
from w1b_support import OFFERING, SECTION_A, SECTION_B, w1b_base
from w2_support import (
    APPLICATION,
    GUARDIAN,
    P3,
    P4,
    P5,
    SECTION_ASSIGNMENT,
    STUDENT_DOCUMENT,
    STUDENT_GUARDIAN,
    STUDENT_ONE,
    STUDENT_TWO,
    w2_base,
)

P6 = "11111111-1111-1111-1111-111111111116"


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def _set_person(cur: psycopg.Cursor, person_id: str | None) -> None:
    cur.execute(
        "SELECT set_config('app.person_id', %s, true)",
        (person_id or "",),
    )


def _visible_student_ids(cur: psycopg.Cursor) -> list[str]:
    cur.execute("SELECT student_id::text FROM student.student ORDER BY student_id")
    return [row[0] for row in cur.fetchall()]


def test_the_student_policy_arms(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, None)
        assert _visible_student_ids(cur) == [], "no context must yield no rows"

        _set_person(cur, P3)
        assert _visible_student_ids(cur) == [STUDENT_ONE], "self arm"

        _set_person(cur, P4)
        assert _visible_student_ids(cur) == [STUDENT_TWO], "other student's self arm"

        _set_person(cur, P5)
        assert _visible_student_ids(cur) == [STUDENT_ONE], "consenting guardian arm"

        _set_person(cur, P1)
        assert _visible_student_ids(cur) == [STUDENT_ONE], "class teacher arm"

        _set_person(cur, P2)
        assert _visible_student_ids(cur) == [STUDENT_ONE], "allocated faculty arm"

        cur.execute("RESET ROLE")


def test_denied_guardian_consent_closes_the_arm(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE student.student_guardian
            SET consent_status = 'denied'
            WHERE student_guardian_id = %s
            """,
            (STUDENT_GUARDIAN,),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P5)
        assert _visible_student_ids(cur) == []
        cur.execute("RESET ROLE")


def test_expired_guardian_consent_closes_the_arm(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE student.student_guardian
            SET valid_to = %s
            WHERE student_guardian_id = %s
            """,
            (TODAY - timedelta(days=1), STUDENT_GUARDIAN),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P5)
        assert _visible_student_ids(cur) == []
        cur.execute("RESET ROLE")


def test_closed_section_teacher_and_faculty_arms(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE academic.section_teacher_assignment
            SET valid_from = %s, valid_to = %s, status = 'ended'
            WHERE section_id = %s
            """,
            (TODAY - timedelta(days=10), TODAY - timedelta(days=1), SECTION_A),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)
        assert _visible_student_ids(cur) == []
        cur.execute("RESET ROLE")

        cur.execute(
            """
            UPDATE academic.offering_faculty
            SET valid_from = %s, valid_to = %s
            WHERE course_offering_id = %s
            """,
            (TODAY - timedelta(days=10), TODAY - timedelta(days=1), OFFERING),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)
        assert _visible_student_ids(cur) == []
        cur.execute("RESET ROLE")


def test_section_assignment_visibility(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, None)
        cur.execute("SELECT count(*) FROM student.section_assignment")
        assert cur.fetchone()[0] == 0

        _set_person(cur, P3)
        cur.execute(
            "SELECT section_assignment_id::text FROM student.section_assignment"
        )
        assert cur.fetchall() == [(SECTION_ASSIGNMENT,)], "self arm"

        _set_person(cur, P1)
        cur.execute(
            "SELECT section_assignment_id::text FROM student.section_assignment"
        )
        assert cur.fetchall() == [(SECTION_ASSIGNMENT,)], "class teacher arm"

        for person in (P2, P4, P5):
            _set_person(cur, person)
            cur.execute("SELECT count(*) FROM student.section_assignment")
            assert cur.fetchone()[0] == 0, person

        cur.execute("RESET ROLE")


def test_section_assignment_arm_closes_with_the_teacher_assignment(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE academic.section_teacher_assignment
            SET valid_from = %s, valid_to = %s, status = 'ended'
            WHERE section_id = %s
            """,
            (TODAY - timedelta(days=10), TODAY - timedelta(days=1), SECTION_A),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)
        cur.execute("SELECT count(*) FROM student.section_assignment")
        assert cur.fetchone()[0] == 0
        cur.execute("RESET ROLE")


def test_the_helper_functions_return_the_documented_answers(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, P3)
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is True
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is False

        _set_person(cur, P4)
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is False

        _set_person(cur, P5)
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is True

        _set_person(cur, P1)
        cur.execute("SELECT iam.is_section_teacher(%s)", (SECTION_A,))
        assert cur.fetchone()[0] is True
        cur.execute("SELECT iam.is_section_teacher(%s)", (SECTION_B,))
        assert cur.fetchone()[0] is False

        _set_person(cur, P2)
        cur.execute("SELECT iam.is_allocated_to_offering(%s)", (OFFERING,))
        assert cur.fetchone()[0] is True
        cur.execute("SELECT iam.can_access_offering(%s)", (OFFERING,))
        assert cur.fetchone()[0] is True

        _set_person(cur, P4)
        cur.execute("SELECT iam.is_allocated_to_offering(%s)", (OFFERING,))
        assert cur.fetchone()[0] is False
        cur.execute("SELECT iam.can_access_offering(%s)", (OFFERING,))
        assert cur.fetchone()[0] is False

        _set_person(cur, None)
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is False
        cur.execute("SELECT iam.current_person_id() IS NULL")
        assert cur.fetchone()[0] is True

        cur.execute("RESET ROLE")


def test_app_erp_cannot_insert_a_student_or_section_assignment(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO iam.person (person_id, legal_name, date_of_birth) "
            "VALUES (%s, 'Student Six', DATE '2006-06-06')",
            (P6,),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)

        expect_error(
            conn,
            """
            INSERT INTO student.student
                (person_id, batch_id, college_roll_no, admission_year,
                 date_of_admission)
            VALUES (%s, %s, 'BCREC/2026/006', 2026, %s)
            """,
            (P6, "d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4", TODAY),
            contains="row-level security",
        )

        expect_error(
            conn,
            """
            INSERT INTO student.section_assignment
                (student_id, section_id, batch_id, effective_from)
            VALUES (%s, %s, %s, %s)
            """,
            (
                STUDENT_TWO,
                SECTION_B,
                "d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4",
                TODAY,
            ),
            contains="row-level security",
        )

        cur.execute("RESET ROLE")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM student.student WHERE person_id = %s",
            (P6,),
        )
        assert cur.fetchone()[0] == 0


def test_app_erp_cannot_update_student_rows(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P3)
        cur.execute(
            """
            UPDATE student.student
            SET current_status = 'detained'
            WHERE student_id = %s
            RETURNING student_id
            """,
            (STUDENT_ONE,),
        )
        assert cur.fetchall() == [], "no UPDATE policy must affect zero rows"
        cur.execute("RESET ROLE")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT current_status FROM student.student WHERE student_id = %s",
            (STUDENT_ONE,),
        )
        assert cur.fetchone() == ("active",)


def test_app_erp_cannot_delete_student_rows(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P3)
        expect_error(
            conn,
            "DELETE FROM student.student WHERE student_id = %s",
            (STUDENT_ONE,),
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_sensitive_columns_and_documents_are_outside_erp_reads(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P3)

        for table, column in (
            ("student.student", "category"),
            ("student.admission_application", "category"),
            ("student.guardian", "annual_income_band"),
            ("student.student_guardian", "consent_status"),
            ("student.status_history", "reason"),
        ):
            expect_error(
                conn,
                f"SELECT {column} FROM {table}",
                contains="permission denied",
            )

        expect_error(
            conn,
            "SELECT count(*) FROM student.student_document",
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_app_cip_has_no_direct_student_access(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        expect_error(
            conn,
            "SELECT count(*) FROM student.student",
            contains="permission denied",
        )
        expect_error(
            conn,
            "SELECT count(*) FROM student.section_assignment",
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_the_owner_policy_sees_every_student_row(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE owner_student")
        cur.execute("SELECT count(*) FROM student.student")
        assert cur.fetchone()[0] == 2
        cur.execute("RESET ROLE")


def test_rls_policy_definitions_match_the_documented_arms(
    conn: psycopg.Connection,
) -> None:
    [(definition,)] = _rows(
        conn,
        """
        SELECT pg_get_expr(pol.polqual, pol.polrelid)
        FROM pg_policy pol
        JOIN pg_class c ON c.oid = pol.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'student' AND c.relname = 'student'
          AND pol.polname = 'p_student_access_select'
        """,
    )
    assert "can_access_student" in definition

    [(definition,)] = _rows(
        conn,
        """
        SELECT pg_get_expr(pol.polqual, pol.polrelid)
        FROM pg_policy pol
        JOIN pg_class c ON c.oid = pol.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'student' AND c.relname = 'section_assignment'
          AND pol.polname = 'p_section_assignment_access_select'
        """,
    )
    assert "is_section_teacher" in definition
    assert "current_person_id" in definition
