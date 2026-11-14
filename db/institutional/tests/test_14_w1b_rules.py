"""W1b rule enforcement: exclusions, triggers, partial uniques, and checks."""

from __future__ import annotations

from datetime import date, timedelta

import psycopg

from w1a_support import (
    ASSIGNMENT,
    INSTITUTION,
    ORG_ROOT,
    P1,
    P2,
    TODAY,
    expect_error,
    w1a_base,
)
from w1b_support import (
    BATCH,
    COURSE,
    COURSE_VERSION,
    DEPARTMENT,
    OFFERING,
    PROGRAMME,
    PROGRAMME_VERSION,
    SECTION_A,
    SECTION_B,
    SECTION_TEACHER,
    TIMETABLE_SLOT,
    w1b_base,
)

TOMORROW = TODAY + timedelta(days=1)
LATER = TODAY + timedelta(days=12)

BATCH_2 = "f2f2f2f2-f2f2-f2f2-f2f2-f2f2f2f2f2f2"
SECTION_C = "f3f3f3f3-f3f3-f3f3-f3f3-f3f3f3f3f3f3"
COURSE_2 = "f4f4f4f4-f4f4-f4f4-f4f4-f4f4f4f4f4f4"
COURSE_VERSION_2 = "f5f5f5f5-f5f5-f5f5-f5f5-f5f5f5f5f5f5"
OFFERING_2 = "f6f6f6f6-f6f6-f6f6-f6f6-f6f6f6f6f6f6"
INSTITUTION_2 = "f7f7f7f7-f7f7-f7f7-f7f7-f7f7f7f7f7f7"


def test_programme_version_year_ranges_cannot_overlap(conn: psycopg.Connection, w1b_base) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE academic.programme_version
            SET effective_to_admission_year = 2026
            WHERE programme_version_id = %s
            """,
            (PROGRAMME_VERSION,),
        )
        cur.execute(
            """
            INSERT INTO academic.programme_version
                (programme_version_id, programme_id, version_no, regulation_name,
                 effective_from_admission_year, effective_to_admission_year,
                 total_credits, status)
            VALUES ('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', %s, 2, 'R2027', 2027, 2028, 160, 'draft')
            """,
            (PROGRAMME,),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.programme_version
            (programme_version_id, programme_id, version_no, regulation_name,
             effective_from_admission_year, effective_to_admission_year,
             total_credits, status)
        VALUES ('a2a2a2a2-a2a2-a2a2-a2a2-a2a2a2a2a2a2', %s, 3, 'R2028', 2028, 2030, 160, 'draft')
        """,
        (PROGRAMME,),
        contains="exclusion",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.programme_version
                (programme_version_id, programme_id, version_no, regulation_name,
                 effective_from_admission_year, total_credits, status)
            VALUES ('a3a3a3a3-a3a3-a3a3-a3a3-a3a3a3a3a3a3', %s, 4, 'R2029', 2029, 160, 'draft')
            """,
            (PROGRAMME,),
        )


def test_programme_version_end_year_cannot_precede_start(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        """
        UPDATE academic.programme_version
        SET effective_to_admission_year = 2025
        WHERE programme_version_id = %s
        """,
        (PROGRAMME_VERSION,),
        contains="check",
    )


def test_expected_graduation_year_cannot_precede_admission_year(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO academic.batch
            (batch_id, programme_id, programme_version_id, admission_year,
             entry_mode, expected_graduation_year)
        VALUES (%s, %s, %s, 2027, 'lateral', 2026)
        """,
        (BATCH_2, PROGRAMME, PROGRAMME_VERSION),
        contains="check",
    )


def test_course_offering_rejects_a_section_from_another_batch(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.batch
                (batch_id, programme_id, programme_version_id, admission_year, entry_mode)
            VALUES (%s, %s, %s, 2027, 'regular')
            """,
            (BATCH_2, PROGRAMME, PROGRAMME_VERSION),
        )
        cur.execute(
            """
            INSERT INTO academic.section (section_id, batch_id, section_code)
            VALUES (%s, %s, 'A')
            """,
            (SECTION_C, BATCH_2),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.course_offering
            (course_offering_id, offering_code, course_version_id, term_id,
             batch_id, section_id)
        VALUES (%s, 'CSE101-2026-C', %s,
                (SELECT current_term_id FROM academic.batch WHERE batch_id = %s),
                %s, %s)
        """,
        ("a4a4a4a4-a4a4-a4a4-a4a4-a4a4a4a4a4a4", COURSE_VERSION, BATCH, BATCH, SECTION_C),
        contains="does not belong to batch",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (offering_code, course_version_id, term_id, batch_id, section_id)
            SELECT 'CSE101-2026-B', %s, b.current_term_id, b.batch_id, %s
            FROM academic.batch b WHERE b.batch_id = %s
            """,
            (COURSE_VERSION, SECTION_B, BATCH),
        )


def test_course_version_is_frozen_after_an_offering_exists(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        "UPDATE academic.course_version SET title = 'Changed' WHERE course_version_id = %s",
        (COURSE_VERSION,),
        contains="frozen",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.course
                (course_id, course_code, title, course_type, department_id)
            VALUES (%s, 'CSE102', 'Data Structures', 'theory', %s)
            """,
            (COURSE_2, DEPARTMENT),
        )
        cur.execute(
            """
            INSERT INTO academic.course_version
                (course_version_id, course_id, version_no, title, credits,
                 effective_from_admission_year, status)
            VALUES (%s, %s, 1, 'Data Structures', 3.0, 2026, 'draft')
            """,
            (COURSE_VERSION_2, COURSE_2),
        )
        cur.execute(
            "UPDATE academic.course_version SET title = 'Data Structures I' WHERE course_version_id = %s",
            (COURSE_VERSION_2,),
        )
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (course_offering_id, offering_code, course_version_id, term_id,
                 batch_id, section_id)
            SELECT %s, 'CSE102-2026-B', %s, b.current_term_id, b.batch_id, %s
            FROM academic.batch b WHERE b.batch_id = %s
            """,
            (OFFERING_2, COURSE_VERSION_2, SECTION_B, BATCH),
        )

    expect_error(
        conn,
        "UPDATE academic.course_version SET title = 'Changed again' WHERE course_version_id = %s",
        (COURSE_VERSION_2,),
        contains="frozen",
    )


def test_one_open_coordinator_per_offering(conn: psycopg.Connection, w1b_base) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.offering_faculty
                (course_offering_id, person_id, role_in_offering, valid_from)
            VALUES (%s, %s, 'coordinator', %s)
            """,
            (OFFERING, P1, TODAY),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.offering_faculty
            (course_offering_id, person_id, role_in_offering, valid_from)
        VALUES (%s, %s, 'coordinator', %s)
        """,
        (OFFERING, P2, TODAY),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.offering_faculty
                (course_offering_id, person_id, role_in_offering, valid_from, valid_to)
            VALUES (%s, %s, 'coordinator', %s, %s)
            """,
            (OFFERING, P2, TOMORROW, LATER),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.offering_faculty
            (course_offering_id, person_id, role_in_offering, valid_from, valid_to)
        VALUES (%s, %s, 'instructor', %s, %s)
        """,
        (OFFERING, P1, TODAY, TODAY),
        contains="check",
    )


def test_section_teacher_partial_unique_and_overlap(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO academic.section_teacher_assignment
            (section_id, person_id, role_in_section, valid_from, status,
             authority_role_assignment_id)
        VALUES (%s, %s, 'class_teacher', %s, 'active', %s)
        """,
        (SECTION_A, P2, TOMORROW, ASSIGNMENT),
        contains="exclusion",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.section_teacher_assignment
                (section_id, person_id, role_in_section, valid_from, status,
                 authority_role_assignment_id)
            VALUES (%s, %s, 'co_class_teacher', %s, 'active', %s)
            """,
            (SECTION_A, P2, TOMORROW, ASSIGNMENT),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.section_teacher_assignment
            (section_id, person_id, role_in_section, valid_from, status,
             authority_role_assignment_id)
        VALUES (%s, %s, 'class_teacher', %s, 'ended', %s)
        """,
        (SECTION_A, P2, TOMORROW, ASSIGNMENT),
        contains="exclusion",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE academic.section_teacher_assignment
            SET valid_to = %s
            WHERE section_teacher_assignment_id = %s
            """,
            (TODAY + timedelta(days=10), SECTION_TEACHER),
        )
        cur.execute(
            """
            INSERT INTO academic.section_teacher_assignment
                (section_id, person_id, role_in_section, valid_from, valid_to,
                 status, authority_role_assignment_id)
            VALUES (%s, %s, 'class_teacher', %s, %s, 'ended', %s)
            """,
            (SECTION_A, P2, LATER, LATER + timedelta(days=1), ASSIGNMENT),
        )
        cur.execute(
            """
            INSERT INTO academic.section_teacher_assignment
                (section_id, person_id, role_in_section, valid_from, status,
                 authority_role_assignment_id)
            VALUES (%s, %s, 'class_teacher', %s, 'active', %s)
            """,
            (SECTION_A, P1, LATER + timedelta(days=2), ASSIGNMENT),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.section_teacher_assignment
            (section_id, person_id, role_in_section, valid_from, valid_to, status,
             authority_role_assignment_id)
        VALUES (%s, %s, 'co_class_teacher', %s, %s, 'active', %s)
        """,
        (SECTION_A, P2, TODAY, TODAY, ASSIGNMENT),
        contains="check",
    )


def test_programme_codes_are_case_insensitively_unique_per_institution(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO academic.programme
            (institution_id, department_id, programme_code, bcrec_code, name, level)
        VALUES (%s, %s, 'btech-cse', '1002', 'Duplicate CSE', 'UG')
        """,
        (INSTITUTION, DEPARTMENT),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.institution
                (institution_id, legal_name, short_name, college_code)
            VALUES (%s, 'Other Institute', 'OI', '200')
            """,
            (INSTITUTION_2,),
        )
        cur.execute(
            """
            INSERT INTO academic.programme
                (institution_id, department_id, programme_code, bcrec_code, name, level)
            VALUES (%s, %s, 'BTECH-CSE', '2001', 'CSE at Other Institute', 'UG')
            """,
            (INSTITUTION_2, DEPARTMENT),
        )


def test_course_offering_treats_null_sections_as_equal(conn: psycopg.Connection, w1b_base) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (offering_code, course_version_id, term_id, batch_id)
            SELECT 'CSE101-2026-ALL', %s, b.current_term_id, b.batch_id
            FROM academic.batch b WHERE b.batch_id = %s
            """,
            (COURSE_VERSION, BATCH),
        )

    expect_error(
        conn,
        """
        INSERT INTO academic.course_offering
            (offering_code, course_version_id, term_id, batch_id)
        SELECT 'CSE101-2026-ALL-2', %s, b.current_term_id, b.batch_id
        FROM academic.batch b WHERE b.batch_id = %s
        """,
        (COURSE_VERSION, BATCH),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (offering_code, course_version_id, term_id, batch_id, section_id)
            SELECT 'CSE101-2026-B-2', %s, b.current_term_id, b.batch_id, %s
            FROM academic.batch b WHERE b.batch_id = %s
            """,
            (COURSE_VERSION, SECTION_B, BATCH),
        )


def test_timetable_slot_end_time_must_follow_start(conn: psycopg.Connection, w1b_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO academic.timetable_slot
            (course_offering_id, day_of_week, start_time, end_time, slot_type,
             valid_from)
        VALUES (%s, 2, TIME '11:00', TIME '11:00', 'theory', %s)
        """,
        (OFFERING, TODAY),
        contains="check",
    )


def test_department_establishment_date_cannot_be_in_the_future(
    conn: psycopg.Connection,
    w1b_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO academic.department
            (org_unit_id, code, name, established_on)
        VALUES (%s, 'ECE', 'Electronics', %s)
        """,
        (ORG_ROOT, TOMORROW),
        contains="check",
    )
