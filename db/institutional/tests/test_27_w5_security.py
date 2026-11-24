"""W5 security posture: published-revision RLS, deny-by-default, and seals."""

from __future__ import annotations

import psycopg

from w1a_support import P1, TERM, expect_error, w1a_base
from w1b_support import PROGRAMME, w1b_base
from w2_support import P3, P4, w2_base
from w3_support import P7, w3_base
from w4_support import w4_base
from w5_support import (
    NOTICE,
    NOTICE_AUDIENCE,
    NOTICE_VERSION,
    RESULT_IMPORT,
    RESULT_RECORD_ONE,
    RESULT_RECORD_TWO,
    RESULT_REVISION_ONE,
    RESULT_SET,
    w5_base,
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
    "exam.enforce_result_revision_seal()",
    "exam.enforce_result_input_append_only()",
    "exam.enforce_grade_card_result_append_only()",
    "exam.enforce_grade_card_result_revision()",
)


def _set_person(cur: psycopg.Cursor, person_id: str | None) -> None:
    cur.execute(
        "SELECT set_config('app.person_id', %s, true)",
        (person_id or "",),
    )


def _ids(cur: psycopg.Cursor, table: str, column: str) -> list[str]:
    cur.execute(f"SELECT {column}::text FROM {table} ORDER BY {column}")
    return [row[0] for row in cur.fetchall()]


def test_student_sees_only_their_published_result_revision(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, None)
        assert _ids(cur, "exam.result_revision", "result_revision_id") == []

        _set_person(cur, P3)
        assert _ids(cur, "exam.result_revision", "result_revision_id") == [
            RESULT_REVISION_ONE
        ]

        _set_person(cur, P4)
        assert _ids(cur, "exam.result_revision", "result_revision_id") == [], (
            "a draft revision must not be visible to the student"
        )

        for person in (P1, P7):
            _set_person(cur, person)
            assert _ids(cur, "exam.result_revision", "result_revision_id") == [], (
                "the COE/faculty arm is deferred under A-01"
            )

        cur.execute("RESET ROLE")


def test_result_record_support_policy_is_self_only(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

        _set_person(cur, P3)
        assert _ids(cur, "exam.result_record", "result_record_id") == [
            RESULT_RECORD_ONE
        ]

        _set_person(cur, P4)
        assert _ids(cur, "exam.result_record", "result_record_id") == [
            RESULT_RECORD_TWO
        ]

        _set_person(cur, P1)
        assert _ids(cur, "exam.result_record", "result_record_id") == []

        cur.execute("RESET ROLE")


def test_every_other_exam_table_is_deny_by_default(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)

        for table in (
            "exam.result_import",
            "exam.result_set",
            "exam.result_input",
            "exam.grade_card",
            "exam.grade_card_result",
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == 0, table

        cur.execute("RESET ROLE")


def test_notice_tables_are_deny_by_default(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    for role in ("app_erp", "app_cip"):
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL ROLE {role}")
            _set_person(cur, P1)
            for table in (
                "doc.notice",
                "doc.notice_version",
                "doc.notice_audience",
            ):
                cur.execute(f"SELECT count(*) FROM {table}")
                assert cur.fetchone()[0] == 0, (role, table)
            cur.execute("RESET ROLE")


def test_exam_writes_are_denied_to_the_application_role(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P3)

        expect_error(
            conn,
            """
            INSERT INTO exam.result_import
                (term_id, programme_id, source_label, file_name, sha256,
                 imported_by)
            VALUES (%s, %s, 'MAKAUT', 'blocked.xlsx', %s, %s)
            """,
            (TERM, PROGRAMME, "b" * 64, P1),
            contains="row-level security",
        )

        cur.execute(
            """
            UPDATE exam.result_revision SET grade = 'F'
            WHERE result_revision_id = %s RETURNING grade
            """,
            (RESULT_REVISION_ONE,),
        )
        assert cur.fetchall() == [], (
            "no UPDATE policy means a visible row still cannot be changed"
        )

        expect_error(
            conn,
            "DELETE FROM exam.result_input WHERE mark_entry_version_id IS NULL",
            contains="permission denied",
        )

        expect_error(
            conn,
            """
            INSERT INTO doc.notice (notice_no, category)
            VALUES ('BCREC/NOT/2026/999', 'general')
            """,
            contains="row-level security",
        )

        cur.execute("RESET ROLE")


def test_app_cip_cannot_read_exam_tables(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        _set_person(cur, P3)
        for table in (
            "exam.result_import",
            "exam.result_set",
            "exam.result_record",
            "exam.result_revision",
            "exam.result_input",
            "exam.grade_card",
            "exam.grade_card_result",
        ):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")


def test_owner_roles_see_every_w5_row(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE owner_exam")
        for table, expected in (
            ("exam.result_import", 1),
            ("exam.result_set", 1),
            ("exam.result_record", 2),
            ("exam.result_revision", 2),
            ("exam.result_input", 1),
            ("exam.grade_card", 1),
            ("exam.grade_card_result", 1),
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")

        cur.execute("SET LOCAL ROLE owner_doc")
        for table, expected in (
            ("doc.notice", 1),
            ("doc.notice_version", 1),
            ("doc.notice_audience", 1),
        ):
            cur.execute(f"SELECT count(*) FROM {table} WHERE " + {
                "doc.notice": f"notice_id = '{NOTICE}'",
                "doc.notice_version": (
                    f"notice_version_id = '{NOTICE_VERSION}'"
                ),
                "doc.notice_audience": (
                    f"notice_audience_id = '{NOTICE_AUDIENCE}'"
                ),
            }[table])
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")


def test_w5_trigger_functions_are_not_executable_by_application_roles(
    conn: psycopg.Connection,
    w5_base,
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
        _set_person(cur, P1)
        for function in TRIGGER_FUNCTIONS:
            expect_error(
                conn,
                f"SELECT {function}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")
