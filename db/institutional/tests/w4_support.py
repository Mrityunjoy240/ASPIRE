"""Shared baseline data for W4 attendance and assessment tests.

Builds on :mod:`w3_base`: a second course registration for student two, two
sessions and attendance records, a correction, a summary, an eligibility
assessment, a condonation case, a complete assessment scheme, a schedule, two
mark entries and versions, and two conflict declarations. P2 has an unresolved
declaration for student two; P1 has a resolved one for student one.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from w1a_support import P1, P2, TERM, TODAY, w1a_base
from w1b_support import COURSE_VERSION, OFFERING, SECTION_A, w1b_base
from w2_support import (
    COURSE_REGISTRATION,
    SEMESTER_TWO,
    STUDENT_ONE,
    STUDENT_TWO,
    w2_base,
)
from w3_support import w3_base

SESSION_ONE = "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1"
SESSION_TWO = "d2d2d2d2-d2d2-d2d2-d2d2-d2d2d2d2d2d2"
RECORD_ONE = "e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1"
RECORD_TWO = "e2e2e2e2-e2e2-e2e2-e2e2-e2e2e2e2e2e2"
CORRECTION = "e3e3e3e3-e3e3-e3e3-e3e3-e3e3e3e3e3e3"
SUMMARY = "e4e4e4e4-e4e4-e4e4-e4e4-e4e4e4e4e4e4"
ELIGIBILITY = "e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5"
CONDONATION = "e6e6e6e6-e6e6-e6e6-e6e6-e6e6e6e6e6e6"
COURSE_REG_TWO = "e7e7e7e7-e7e7-e7e7-e7e7-e7e7e7e7e7e7"

SCHEME = "f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1"
COMPONENT_CIA1 = "f2f2f2f2-f2f2-f2f2-f2f2-f2f2f2f2f2f2"
COMPONENT_CIA2 = "f3f3f3f3-f3f3-f3f3-f3f3-f3f3f3f3f3f3"
COMPONENT_ESE = "f4f4f4f4-f4f4-f4f4-f4f4-f4f4f4f4f4f4"
SCHEDULE = "f5f5f5f5-f5f5-f5f5-f5f5-f5f5f5f5f5f5"
MARK_ENTRY_ONE = "a7a7a7a7-a7a7-a7a7-a7a7-a7a7a7a7a7a7"
MARK_ENTRY_TWO = "a8a8a8a8-a8a8-a8a8-a8a8-a8a8a8a8a8a8"
MARK_VERSION_ONE = "a9b9a9b9-a9b9-a9b9-a9b9-a9b9a9b9a9b9"
MARK_VERSION_TWO = "a9c9a9c9-a9c9-a9c9-a9c9-a9c9a9c9a9c9"
CONFLICT_ONE = "b7b7b7b7-b7b7-b7b7-b7b7-b7b7b7b7b7b7"
CONFLICT_TWO = "b8b8b8b8-b8b8-b8b8-b8b8-b8b8b8b8b8b8"


@pytest.fixture()
def w4_base(w3_base):
    conn = w3_base
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.course_registration
                (course_registration_id, student_id, semester_registration_id,
                 course_offering_id, registration_type, credits, status)
            VALUES (%s, %s, %s, %s, 'regular', 4.0, 'registered')
            """,
            (COURSE_REG_TWO, STUDENT_TWO, SEMESTER_TWO, OFFERING),
        )
        cur.execute(
            """
            INSERT INTO attendance.session
                (session_id, course_offering_id, session_date, start_time,
                 end_time, session_type, status, held_by_person_id)
            VALUES (%s, %s, %s, '09:00', '10:00', 'theory', 'held', %s),
                   (%s, %s, %s, '11:00', '12:00', 'theory', 'held', %s)
            """,
            (
                SESSION_ONE, OFFERING, TODAY, P1,
                SESSION_TWO, OFFERING, TODAY + timedelta(days=1), P1,
            ),
        )
        cur.execute(
            """
            INSERT INTO attendance.record
                (attendance_record_id, session_id, student_id,
                 course_registration_id, course_offering_id, status, source,
                 marked_by)
            VALUES (%s, %s, %s, %s, %s, 'present', 'faculty_manual', %s),
                   (%s, %s, %s, %s, %s, 'absent', 'faculty_manual', %s)
            """,
            (
                RECORD_ONE, SESSION_ONE, STUDENT_ONE,
                COURSE_REGISTRATION, OFFERING, P1,
                RECORD_TWO, SESSION_TWO, STUDENT_TWO,
                COURSE_REG_TWO, OFFERING, P1,
            ),
        )
        cur.execute(
            """
            INSERT INTO attendance.correction
                (correction_id, attendance_record_id, old_status, new_status,
                 reason, requested_by, status)
            VALUES (%s, %s, 'absent', 'present', 'Marked absent by mistake',
                    %s, 'requested')
            """,
            (CORRECTION, RECORD_TWO, P1),
        )
        cur.execute(
            """
            INSERT INTO attendance.summary
                (summary_id, student_id, course_offering_id,
                 sessions_conducted, sessions_attended, attendance_pct,
                 as_of, calculation_version)
            VALUES (%s, %s, %s, 10, 8, 80.00, now() - interval '1 hour', 'v1')
            """,
            (SUMMARY, STUDENT_ONE, OFFERING),
        )
        cur.execute(
            """
            INSERT INTO attendance.eligibility_assessment
                (eligibility_assessment_id, student_id, term_id, rule_variant,
                 aggregate_pct, theory_pct, outcome)
            VALUES (%s, %s, %s, 'aggregate', 80.00, 80.00, 'eligible')
            """,
            (ELIGIBILITY, STUDENT_ONE, TERM),
        )
        cur.execute(
            """
            INSERT INTO attendance.condonation_case
                (condonation_case_id, student_id, term_id,
                 eligibility_assessment_id, shortfall_pct, grounds, status)
            VALUES (%s, %s, %s, %s, 5.00, 'Medical evidence', 'opened')
            """,
            (CONDONATION, STUDENT_ONE, TERM, ELIGIBILITY),
        )

        cur.execute(
            """
            INSERT INTO assessment.scheme
                (scheme_id, course_version_id, name, effective_from_term_id,
                 status, approved_by)
            VALUES (%s, %s, 'Theory CIA+ESE', %s, 'active', %s)
            """,
            (SCHEME, COURSE_VERSION, TERM, P1),
        )
        cur.execute(
            """
            INSERT INTO assessment.component
                (component_id, scheme_id, component_code, name, component_type,
                 max_marks, weight_pct, sequence_no)
            VALUES (%s, %s, 'CIA1', 'Class Internal Assessment 1', 'internal',
                    40.00, 40.00, 1),
                   (%s, %s, 'CIA2', 'Class Internal Assessment 2', 'internal',
                    40.00, 40.00, 2),
                   (%s, %s, 'ESE', 'End Semester Examination', 'external',
                    60.00, 20.00, 3)
            """,
            (
                COMPONENT_CIA1, SCHEME,
                COMPONENT_CIA2, SCHEME,
                COMPONENT_ESE, SCHEME,
            ),
        )
        cur.execute(
            """
            INSERT INTO assessment.schedule
                (schedule_id, component_id, course_offering_id, schedule_type,
                 scheduled_start, scheduled_end, duration_min, venue_text,
                 status)
            VALUES (%s, %s, %s, 'regular', now() + interval '7 days',
                    now() + interval '7 days 1 hour', 60, 'Room 101', 'planned')
            """,
            (SCHEDULE, COMPONENT_CIA1, OFFERING),
        )
        cur.execute(
            """
            INSERT INTO assessment.mark_entry
                (mark_entry_id, student_id, component_id, course_offering_id,
                 current_version_no, status)
            VALUES (%s, %s, %s, %s, 1, 'draft'),
                   (%s, %s, %s, %s, 1, 'draft')
            """,
            (
                MARK_ENTRY_ONE, STUDENT_ONE, COMPONENT_CIA1, OFFERING,
                MARK_ENTRY_TWO, STUDENT_TWO, COMPONENT_CIA1, OFFERING,
            ),
        )
        cur.execute(
            """
            INSERT INTO assessment.conflict_declaration
                (conflict_declaration_id, faculty_person_id,
                 course_offering_id, student_id, relationship_type, action_taken,
                 status)
            VALUES (%s, %s, %s, %s, 'other', 'none', 'declared'),
                   (%s, %s, %s, %s, 'other', 'recused', 'resolved')
            """,
            (
                CONFLICT_ONE, P2, OFFERING, STUDENT_TWO,
                CONFLICT_TWO, P1, OFFERING, STUDENT_ONE,
            ),
        )
        cur.execute(
            """
            INSERT INTO assessment.mark_entry_version
                (mark_entry_version_id, mark_entry_id, version_no,
                 marks_obtained, max_marks_snapshot, status, entered_by)
            VALUES (%s, %s, 1, 30.00, 40.00, 'draft', %s),
                   (%s, %s, 1, 25.00, 40.00, 'draft', %s)
            """,
            (
                MARK_VERSION_ONE, MARK_ENTRY_ONE, P1,
                MARK_VERSION_TWO, MARK_ENTRY_TWO, P1,
            ),
        )

    try:
        yield conn
    finally:
        conn.rollback()
