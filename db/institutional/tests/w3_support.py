"""Shared baseline data for W3 faculty and mentoring tests.

Builds on :mod:`w2_base`: two faculty profiles for P2 and P7, one staff
profile for P6, and two active mentor assignments. P7 is deliberately not a
class teacher, allocated instructor, guardian, or student, so P7's access to
student two can only come from the mentor arm.
"""

from __future__ import annotations

import pytest

from w1a_support import ORG_CHILD, P1, P2, TERM, w1a_base
from w1b_support import DEPARTMENT, w1b_base
from w2_support import START, STUDENT_ONE, STUDENT_TWO, w2_base

P6 = "11111111-1111-1111-1111-111111111116"
P7 = "11111111-1111-1111-1111-111111111117"

FACULTY_P2 = "a9a9a9a9-a9a9-a9a9-a9a9-a9a9a9a9a9a1"
FACULTY_P7 = "a9a9a9a9-a9a9-a9a9-a9a9-a9a9a9a9a9a2"
STAFF_P6 = "a9a9a9a9-a9a9-a9a9-a9a9-a9a9a9a9a9a3"
MENTOR_P2 = "a9a9a9a9-a9a9-a9a9-a9a9-a9a9a9a9a9a4"
MENTOR_P7 = "a9a9a9a9-a9a9-a9a9-a9a9-a9a9a9a9a9a5"


@pytest.fixture()
def w3_base(w2_base):
    conn = w2_base
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO iam.person (person_id, legal_name, date_of_birth) "
            "VALUES (%s, 'Staff Six', DATE '1980-06-06'), "
            "       (%s, 'Faculty Seven', DATE '1982-07-07')",
            (P6, P7),
        )
        cur.execute(
            """
            INSERT INTO faculty.faculty_profile
                (faculty_profile_id, person_id, employee_id, designation,
                 department_id, joining_date, employment_type,
                 highest_qualification, specialization, workload_category,
                 status)
            VALUES (%s, %s, 'EMP-001', 'Assistant Professor', %s, %s,
                    'permanent', 'Ph.D.', 'Artificial Intelligence',
                    'assistant_professor', 'active'),
                   (%s, %s, 'EMP-002', 'Assistant Professor', %s, %s,
                    'permanent', 'Ph.D.', 'Databases',
                    'assistant_professor', 'active')
            """,
            (
                FACULTY_P2, P2, DEPARTMENT, START,
                FACULTY_P7, P7, DEPARTMENT, START,
            ),
        )
        cur.execute(
            """
            INSERT INTO faculty.staff_profile
                (staff_profile_id, person_id, employee_id, designation,
                 org_unit_id, reporting_to_person_id, joining_date,
                 employment_type, status)
            VALUES (%s, %s, 'STF-001', 'Lab Assistant', %s, %s, %s,
                    'permanent', 'active')
            """,
            (STAFF_P6, P6, ORG_CHILD, P2, START),
        )
        cur.execute(
            """
            INSERT INTO faculty.mentor_assignment
                (mentor_assignment_id, mentor_person_id, student_id, term_id,
                 valid_from, status, assigned_by, notes_visibility)
            VALUES (%s, %s, %s, %s, %s, 'active', %s, 'mentor_only'),
                   (%s, %s, %s, %s, %s, 'active', %s, 'mentor_only')
            """,
            (
                MENTOR_P2, P2, STUDENT_ONE, TERM, START, P1,
                MENTOR_P7, P7, STUDENT_TWO, TERM, START, P1,
            ),
        )

    try:
        yield conn
    finally:
        conn.rollback()
