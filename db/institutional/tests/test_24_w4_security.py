"""W4 security posture: RLS arms, write denial, and column boundaries."""

from __future__ import annotations

import psycopg

from w1a_support import P1, P2, expect_error, w1a_base
from w1b_support import OFFERING, w1b_base
from w2_support import P3, P4, STUDENT_ONE, STUDENT_TWO, w2_base
from w3_support import P7, w3_base
from w4_support import (
    CORRECTION,
    COURSE_REG_TWO,
    MARK_ENTRY_ONE,
    MARK_ENTRY_TWO,
    MARK_VERSION_ONE,
    MARK_VERSION_TWO,
    RECORD_ONE,
    RECORD_TWO,
    SESSION_ONE,
    w4_base,
)

APP_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)

TRIGGER_FUNCTIONS = (
    "assessment.enforce_component_immutable()",
    "assessment.enforce_component_weight_sum()",
    "assessment.enforce_mark_version_immutable()",
    "assessment.enforce_mark_correction_versions()",
    "assessment.enforce_mark_conflict()",
    "assessment.enforce_attendance_conflict()",
)


def _set_person(cur: psycopg.Cursor, person_id: str | None) -> None:
    cur.execute(
        "SELECT set_config('app.person_id', %s, true)",
        (person_id or "",),
    )


def _visible_record_ids(cur: psycopg.Cursor) -> list[str]:
    cur.execute(
        "SELECT attendance_record_id::text FROM attendance.record "
        "ORDER BY attendance_record_id"
    )
    return [row[0] for row in cur.fetchall()]


def _visible_mark_entry_ids(cur: psycopg.Cursor) -> list[str]:
    cur.execute(
        "SELECT mark_entry_id::text FROM assessment.mark_entry "
        "ORDER BY mark_entry_id"
    )
    return [row[0] for row in cur.fetchall()]


def _visible_mark_version_ids(cur: psycopg.Cursor) -> list[str]:
    cur.execute(
        "SELECT mark_entry_version_id::text FROM assessment.mark_entry_version "
        "ORDER BY mark_entry_version_id"
    )
    return [row[0] for row in cur.fetchall()]


def test_attendance_record_rls_arms(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, None)
        assert _visible_record_ids(cur) == []

        _set_person(cur, P3)
        assert _visible_record_ids(cur) == [RECORD_ONE], "self arm"

        _set_person(cur, P4)
        assert _visible_record_ids(cur) == [RECORD_TWO], "self arm"

        _set_person(cur, P7)
        assert _visible_record_ids(cur) == [RECORD_TWO], "mentor arm"

        _set_person(cur, P1)
        assert _visible_record_ids(cur) == [RECORD_ONE], "section teacher arm"

        _set_person(cur, P2)
        assert _visible_record_ids(cur) == [RECORD_ONE, RECORD_TWO], (
            "allocated faculty arm"
        )

        cur.execute("RESET ROLE")


def test_allocated_faculty_sees_marks_but_the_section_teacher_does_not(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, P2)
        assert _visible_mark_entry_ids(cur) == [MARK_ENTRY_ONE, MARK_ENTRY_TWO]
        assert _visible_mark_version_ids(cur) == [
            MARK_VERSION_ONE,
            MARK_VERSION_TWO,
        ]

        for person in (P1, P3, P4, P7, None):
            _set_person(cur, person)
            assert _visible_mark_entry_ids(cur) == [], person
            assert _visible_mark_version_ids(cur) == [], person

        cur.execute("RESET ROLE")


def test_attendance_writes_are_denied_to_the_application_role(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)

        expect_error(
            conn,
            """
            INSERT INTO attendance.record
                (session_id, student_id, course_registration_id,
                 course_offering_id, status, marked_by)
            VALUES (%s, %s, %s, %s, 'present', %s)
            """,
            (SESSION_ONE, STUDENT_TWO, COURSE_REG_TWO, OFFERING, P1),
            contains="row-level security",
        )

        cur.execute(
            "UPDATE attendance.record SET status = 'late' "
            "WHERE attendance_record_id = %s RETURNING status",
            (RECORD_ONE,),
        )
        assert cur.fetchall() == [], "no UPDATE policy means zero rows"

        expect_error(
            conn,
            "DELETE FROM attendance.record WHERE attendance_record_id = %s",
            (RECORD_ONE,),
            contains="permission denied",
        )

        cur.execute("RESET ROLE")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM attendance.record WHERE attendance_record_id = %s",
            (RECORD_ONE,),
        )
        assert cur.fetchone() == ("present",)


def test_assessment_writes_are_denied_to_the_application_role(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)

        cur.execute(
            "UPDATE assessment.mark_entry SET status = 'submitted' "
            "WHERE mark_entry_id = %s RETURNING status",
            (MARK_ENTRY_ONE,),
        )
        assert cur.fetchall() == [], "no UPDATE policy means zero rows"

        expect_error(
            conn,
            """
            INSERT INTO assessment.mark_entry_version
                (mark_entry_id, version_no, marks_obtained, max_marks_snapshot,
                 entered_by)
            VALUES (%s, 2, 30.00, 40.00, %s)
            """,
            (MARK_ENTRY_ONE, P1),
            contains="row-level security",
        )

        expect_error(
            conn,
            "DELETE FROM assessment.mark_entry WHERE mark_entry_id = %s",
            (MARK_ENTRY_ONE,),
            contains="permission denied",
        )

        cur.execute("RESET ROLE")


def test_class_r_columns_are_withheld_from_the_application_role(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)

        expect_error(
            conn,
            "SELECT reason FROM attendance.correction WHERE correction_id = %s",
            (CORRECTION,),
            contains="permission denied",
        )
        expect_error(
            conn,
            "SELECT evidence_document_version_id FROM attendance.correction",
            contains="permission denied",
        )
        expect_error(
            conn,
            """
            INSERT INTO attendance.correction
                (attendance_record_id, old_status, new_status, reason,
                 requested_by)
            VALUES (%s, 'absent', 'present', 'Direct insert attempt', %s)
            """,
            (RECORD_ONE, P1),
            contains="permission denied",
        )

        expect_error(
            conn,
            "SELECT reason FROM assessment.mark_correction",
            contains="permission denied",
        )
        expect_error(
            conn,
            """
            INSERT INTO assessment.mark_correction
                (mark_entry_id, from_version_id, to_version_id, reason,
                 requested_by)
            VALUES (%s, %s, %s, 'Direct insert attempt', %s)
            """,
            (MARK_ENTRY_ONE, MARK_VERSION_ONE, MARK_VERSION_TWO, P1),
            contains="permission denied",
        )

        cur.execute("RESET ROLE")


def test_restricted_case_tables_have_no_application_access(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)

        for table in (
            "attendance.condonation_case",
            "assessment.conflict_declaration",
        ):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )

        cur.execute("RESET ROLE")


def test_app_cip_has_no_w4_access(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        _set_person(cur, P2)
        for table in (
            "attendance.session",
            "attendance.record",
            "attendance.correction",
            "attendance.summary",
            "attendance.eligibility_assessment",
            "attendance.condonation_case",
            "assessment.scheme",
            "assessment.component",
            "assessment.schedule",
            "assessment.mark_entry",
            "assessment.mark_entry_version",
            "assessment.mark_correction",
            "assessment.conflict_declaration",
        ):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")


def test_owner_roles_see_every_w4_table(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE owner_attendance")
        for table, expected in (
            ("attendance.session", 2),
            ("attendance.record", 2),
            ("attendance.correction", 1),
            ("attendance.summary", 1),
            ("attendance.eligibility_assessment", 1),
            ("attendance.condonation_case", 1),
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")

        cur.execute("SET LOCAL ROLE owner_assessment")
        for table, expected in (
            ("assessment.scheme", 1),
            ("assessment.component", 3),
            ("assessment.schedule", 1),
            ("assessment.mark_entry", 2),
            ("assessment.mark_entry_version", 2),
            ("assessment.mark_correction", 0),
            ("assessment.conflict_declaration", 2),
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")


def test_w4_trigger_functions_are_not_executable_by_application_roles(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        for role in APP_ROLES:
            for function in TRIGGER_FUNCTIONS:
                cur.execute(
                    "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
                    (role, function),
                )
                assert cur.fetchone()[0] is False, (role, function)

        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P2)
        for function in TRIGGER_FUNCTIONS:
            expect_error(
                conn,
                f"SELECT {function}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")
