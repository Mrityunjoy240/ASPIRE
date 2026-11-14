"""W3 rule enforcement: employee identities, employment dates, mentor rules."""

from __future__ import annotations

from datetime import timedelta

import psycopg

from w1a_support import P2, TERM, expect_error, w1a_base
from w1b_support import DEPARTMENT, w1b_base
from w2_support import START, STUDENT_ONE, STUDENT_TWO, w2_base
from w3_support import (
    FACULTY_P2,
    MENTOR_P2,
    MENTOR_P7,
    P6,
    P7,
    STAFF_P6,
    w3_base,
)

P3 = "11111111-1111-1111-1111-111111111113"
P4 = "11111111-1111-1111-1111-111111111114"


def _insert_faculty(
    conn: psycopg.Connection,
    *,
    person_id: str,
    employee_id: str,
    status: str = "active",
    employment_type: str = "permanent",
    joining_date=START,
    relieving_date=None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO faculty.faculty_profile
                (person_id, employee_id, designation, department_id,
                 joining_date, employment_type, status, relieving_date)
            VALUES (%s, %s, 'Assistant Professor', %s, %s, %s, %s, %s)
            """,
            (
                person_id, employee_id, DEPARTMENT, joining_date,
                employment_type, status, relieving_date,
            ),
        )


def test_faculty_identity_and_employment_checks(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO faculty.faculty_profile
            (person_id, employee_id, designation, department_id, joining_date)
        VALUES (%s, 'EMP-100', 'Professor', %s, %s)
        """,
        (P7, DEPARTMENT, START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.faculty_profile
            (person_id, employee_id, designation, department_id, joining_date)
        VALUES (%s, 'emp-001', 'Professor', %s, %s)
        """,
        (P6, DEPARTMENT, START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.faculty_profile
            (person_id, employee_id, designation, department_id, joining_date,
             relieving_date)
        VALUES (%s, 'EMP-101', 'Professor', %s, %s, %s)
        """,
        (P6, DEPARTMENT, START, START - timedelta(days=1)),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.faculty_profile
            (person_id, employee_id, designation, department_id, joining_date,
             employment_type)
        VALUES (%s, 'EMP-102', 'Professor', %s, %s, 'temporary')
        """,
        (P6, DEPARTMENT, START),
        contains="check",
    )

    _insert_faculty(conn, person_id=P6, employee_id="EMP-102")


def test_staff_identity_and_reporting_checks(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO faculty.staff_profile
            (person_id, employee_id, designation, org_unit_id, joining_date)
        VALUES (%s, 'STF-100', 'Clerk', %s, %s)
        """,
        (P6, "33333333-3333-3333-3333-333333333332", START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.staff_profile
            (person_id, employee_id, designation, org_unit_id, joining_date)
        VALUES (%s, 'stf-001', 'Clerk', %s, %s)
        """,
        (P7, "33333333-3333-3333-3333-333333333332", START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.staff_profile
            (person_id, employee_id, designation, org_unit_id,
             reporting_to_person_id, joining_date)
        VALUES (%s, 'STF-101', 'Clerk', %s, %s, %s)
        """,
        (P7, "33333333-3333-3333-3333-333333333332", P7, START),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.staff_profile
            (person_id, employee_id, designation, org_unit_id, joining_date,
             relieving_date)
        VALUES (%s, 'STF-102', 'Clerk', %s, %s, %s)
        """,
        (P7, "33333333-3333-3333-3333-333333333332", START,
         START - timedelta(days=1)),
        contains="check",
    )


def test_a_mentor_must_hold_an_active_faculty_profile(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty.mentor_assignment SET status = 'ended' "
            "WHERE mentor_assignment_id = %s",
            (MENTOR_P2,),
        )

    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, valid_from)
        VALUES (%s, %s, %s, %s)
        """,
        (P4, STUDENT_ONE, TERM, START),
        contains="no active faculty profile",
    )

    _insert_faculty(
        conn,
        person_id=P6,
        employee_id="EMP-200",
        status="relieved",
        relieving_date=START + timedelta(days=1),
    )
    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, valid_from)
        VALUES (%s, %s, %s, %s)
        """,
        (P6, STUDENT_ONE, TERM, START),
        contains="no active faculty profile",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO faculty.mentor_assignment
                (mentor_person_id, student_id, term_id, valid_from)
            VALUES (%s, %s, %s, %s)
            """,
            (P2, STUDENT_ONE, TERM, START),
        )


def test_one_active_mentor_per_student_and_term(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, valid_from)
        VALUES (%s, %s, %s, %s)
        """,
        (P2, STUDENT_TWO, TERM, START),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO faculty.mentor_assignment
                (mentor_person_id, student_id, term_id, valid_from, status)
            VALUES (%s, %s, %s, %s, 'ended')
            """,
            (P2, STUDENT_TWO, TERM, START),
        )

    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, valid_from, valid_to)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (P2, STUDENT_ONE, TERM, START, START),
        contains="check",
    )


def test_mentor_visibility_and_status_are_controlled(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, notes_visibility)
        VALUES (%s, %s, %s, 'public')
        """,
        (P2, STUDENT_ONE, TERM),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO faculty.mentor_assignment
            (mentor_person_id, student_id, term_id, status)
        VALUES (%s, %s, %s, 'pending')
        """,
        (P2, STUDENT_ONE, TERM),
        contains="check",
    )


def test_mentor_trigger_also_guards_mentor_changes(
    conn: psycopg.Connection,
    w3_base,
) -> None:
    expect_error(
        conn,
        """
        UPDATE faculty.mentor_assignment
        SET mentor_person_id = %s
        WHERE mentor_assignment_id = %s
        """,
        (P4, MENTOR_P7),
        contains="no active faculty profile",
    )

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty.mentor_assignment SET status = 'ended' "
            "WHERE mentor_assignment_id = %s",
            (MENTOR_P7,),
        )
