"""W3 security posture: the mentor arm, column boundaries, and grants."""

from __future__ import annotations

from datetime import timedelta

import psycopg

from w1a_support import P2, TERM, TODAY, expect_error, w1a_base
from w1b_support import w1b_base
from w2_support import P3, STUDENT_ONE, STUDENT_TWO, w2_base
from w3_support import (
    MENTOR_P2,
    MENTOR_P7,
    P7,
    w3_base,
)

APP_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)


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


def test_the_mentor_helper_arms(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, P7)
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is True, "P7 mentors student two"
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is False, "P7 does not mentor student one"

        _set_person(cur, P2)
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is True

        _set_person(cur, P3)
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is False

        _set_person(cur, None)
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is False

        cur.execute("RESET ROLE")


def test_mentor_is_the_only_arm_for_p7(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, P7)
        assert _visible_student_ids(cur) == [STUDENT_TWO], "mentor arm only"
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is True
        cur.execute("SELECT iam.can_access_student(%s)", (STUDENT_ONE,))
        assert cur.fetchone()[0] is False

        cur.execute("RESET ROLE")


def test_ended_mentor_assignment_closes_access(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty.mentor_assignment SET status = 'ended' "
            "WHERE mentor_assignment_id = %s",
            (MENTOR_P7,),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P7)
        assert _visible_student_ids(cur) == []
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is False
        cur.execute("RESET ROLE")


def test_expired_mentor_assignment_closes_access(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty.mentor_assignment SET valid_to = %s "
            "WHERE mentor_assignment_id = %s",
            (TODAY - timedelta(days=1), MENTOR_P7),
        )
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P7)
        assert _visible_student_ids(cur) == []
        cur.execute("SELECT iam.is_mentor_of(%s)", (STUDENT_TWO,))
        assert cur.fetchone()[0] is False
        cur.execute("RESET ROLE")


def test_notes_visibility_is_outside_the_application_projection(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P7)

        expect_error(
            conn,
            "SELECT notes_visibility FROM faculty.mentor_assignment",
            contains="permission denied",
        )
        expect_error(
            conn,
            """
            INSERT INTO faculty.mentor_assignment
                (mentor_person_id, student_id, term_id, notes_visibility)
            VALUES (%s, %s, %s, 'mentor_only')
            """,
            (P7, STUDENT_ONE, TERM),
            contains="permission denied",
        )
        expect_error(
            conn,
            "UPDATE faculty.mentor_assignment SET notes_visibility = 'hod_and_mentor' "
            "WHERE mentor_assignment_id = %s",
            (MENTOR_P7,),
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_app_erp_cannot_write_mentor_assignments(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    """Phase 9B IAM-SEP: mentor assignment is an authority write.

    ``iam.is_mentor_of(uuid)`` is SECURITY DEFINER and reads this table, so a
    runtime insert would let app_erp grant itself student read access. The
    whole write surface is revoked; the read projection is unchanged.
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)

        expect_error(
            conn,
            """
            INSERT INTO faculty.mentor_assignment
                (mentor_person_id, student_id, term_id, valid_from, status,
                 assigned_by)
            VALUES (%s, %s, %s, %s, 'ended', %s)
            """,
            (P7, STUDENT_ONE, TERM, TODAY, P2),
            contains="permission denied",
        )

        expect_error(
            conn,
            """
            UPDATE faculty.mentor_assignment
            SET valid_to = %s, updated_at = now()
            WHERE mentor_assignment_id = %s
            """,
            (TODAY + timedelta(days=30), MENTOR_P7),
            contains="permission denied",
        )

        cur.execute("RESET ROLE")


def test_app_erp_cannot_delete_mentor_assignments(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)
        expect_error(
            conn,
            "DELETE FROM faculty.mentor_assignment WHERE mentor_assignment_id = %s",
            (MENTOR_P2,),
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_app_cip_has_no_faculty_access(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        for table in (
            "faculty.faculty_profile",
            "faculty.staff_profile",
            "faculty.mentor_assignment",
        ):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")


def test_owner_iam_reads_only_the_mentor_assignment_table(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE owner_iam")
        cur.execute("SELECT count(*) FROM faculty.mentor_assignment")
        assert cur.fetchone()[0] >= 2
        for table in ("faculty.faculty_profile", "faculty.staff_profile"):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")


def test_the_trigger_function_is_not_executable_by_application_roles(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        for role in APP_ROLES:
            cur.execute(
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
                (role, "faculty.enforce_mentor_active_profile()"),
            )
            assert cur.fetchone()[0] is False, role

        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)
        expect_error(
            conn,
            "SELECT faculty.enforce_mentor_active_profile()",
            contains="permission denied",
        )
        cur.execute("RESET ROLE")


def test_faculty_profiles_remain_readable_to_their_owners_and_erp(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        cur.execute(
            "SELECT employee_id, status FROM faculty.faculty_profile "
            "ORDER BY employee_id"
        )
        assert cur.fetchall() == [("EMP-001", "active"), ("EMP-002", "active")]
        cur.execute("RESET ROLE")

        cur.execute("SET LOCAL ROLE owner_faculty")
        cur.execute("SELECT count(*) FROM faculty.faculty_profile")
        assert cur.fetchone()[0] == 2
        cur.execute("RESET ROLE")
