"""Shared baseline data for W1b academic-structure tests.

Builds on :mod:`w1a_support`: a department under the existing org unit, one
programme and version, a batch with two sections, a course and version, a
curriculum, an offering, one instructor, one timetable slot, and one class
teacher. The surrounding fixture rolls the whole transaction back.
"""

from __future__ import annotations

from datetime import date

import pytest

from w1a_support import (
    ASSIGNMENT,
    INSTITUTION,
    ORG_CHILD,
    P1,
    P2,
    TERM,
    TODAY,
    w1a_base,
)

DEPARTMENT = "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1"
PROGRAMME = "d2d2d2d2-d2d2-d2d2-d2d2-d2d2d2d2d2d2"
PROGRAMME_VERSION = "d3d3d3d3-d3d3-d3d3-d3d3-d3d3d3d3d3d3"
BATCH = "d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4"
SECTION_A = "d5d5d5d5-d5d5-d5d5-d5d5-d5d5d5d5d5d5"
SECTION_B = "d6d6d6d6-d6d6-d6d6-d6d6-d6d6d6d6d6d6"
CURRICULUM = "d7d7d7d7-d7d7-d7d7-d7d7-d7d7d7d7d7d7"
CURRICULUM_COURSE = "d8d8d8d8-d8d8-d8d8-d8d8-d8d8d8d8d8d8"
COURSE = "d9d9d9d9-d9d9-d9d9-d9d9-d9d9d9d9d9d9"
COURSE_VERSION = "e1e1e1e1-e1e1-e1e1-e1e1-e1e1e1e1e1e1"
OFFERING = "e2e2e2e2-e2e2-e2e2-e2e2-e2e2e2e2e2e2"
OFFERING_FACULTY = "e3e3e3e3-e3e3-e3e3-e3e3-e3e3e3e3e3e3"
TIMETABLE_SLOT = "e4e4e4e4-e4e4-e4e4-e4e4-e4e4e4e4e4e4"
SECTION_TEACHER = "e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5"


@pytest.fixture()
def w1b_base(w1a_base):
    conn = w1a_base
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.department
                (department_id, org_unit_id, code, name, short_name)
            VALUES (%s, %s, 'CSE', 'Computer Science and Engineering', 'CSE')
            """,
            (DEPARTMENT, ORG_CHILD),
        )
        cur.execute(
            """
            INSERT INTO academic.programme
                (programme_id, institution_id, department_id, programme_code,
                 bcrec_code, name, level, degree_awarded_by, duration_years)
            VALUES (%s, %s, %s, 'BTECH-CSE', '1001', 'B.Tech CSE', 'UG', 'MAKAUT', 4)
            """,
            (PROGRAMME, INSTITUTION, DEPARTMENT),
        )
        cur.execute(
            """
            INSERT INTO academic.programme_version
                (programme_version_id, programme_id, version_no, regulation_name,
                 effective_from_admission_year, total_credits, status)
            VALUES (%s, %s, 1, 'R2026', 2026, 160, 'draft')
            """,
            (PROGRAMME_VERSION, PROGRAMME),
        )
        cur.execute(
            """
            INSERT INTO academic.batch
                (batch_id, programme_id, programme_version_id, admission_year,
                 entry_mode, autonomy_status, current_term_id, expected_graduation_year)
            VALUES (%s, %s, %s, 2026, 'regular', 'transitional', %s, 2030)
            """,
            (BATCH, PROGRAMME, PROGRAMME_VERSION, TERM),
        )
        cur.execute(
            """
            INSERT INTO academic.section (section_id, batch_id, section_code, name, strength)
            VALUES (%s, %s, 'A', 'Section A', 60),
                   (%s, %s, 'B', 'Section B', 60)
            """,
            (SECTION_A, BATCH, SECTION_B, BATCH),
        )
        cur.execute(
            """
            INSERT INTO academic.course
                (course_id, course_code, title, course_type, department_id)
            VALUES (%s, 'CSE101', 'Programming Fundamentals', 'theory', %s)
            """,
            (COURSE, DEPARTMENT),
        )
        cur.execute(
            """
            INSERT INTO academic.course_version
                (course_version_id, course_id, version_no, title, credits,
                 contact_hours, course_outcomes_json,
                 effective_from_admission_year, status)
            VALUES (%s, %s, 1, 'Programming Fundamentals', 4.0, 48, '[]', 2026, 'draft')
            """,
            (COURSE_VERSION, COURSE),
        )
        cur.execute(
            """
            INSERT INTO academic.curriculum
                (curriculum_id, programme_version_id, term_no, version_no,
                 total_credits, status, effective_from_term_id)
            VALUES (%s, %s, 1, 1, 20, 'draft', %s)
            """,
            (CURRICULUM, PROGRAMME_VERSION, TERM),
        )
        cur.execute(
            """
            INSERT INTO academic.curriculum_course
                (curriculum_course_id, curriculum_id, course_version_id,
                 term_no, sequence_no, category, credits)
            VALUES (%s, %s, %s, 1, 1, 'core', 4.0)
            """,
            (CURRICULUM_COURSE, CURRICULUM, COURSE_VERSION),
        )
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (course_offering_id, offering_code, course_version_id, term_id,
                 batch_id, section_id, capacity, delivery_mode)
            VALUES (%s, 'CSE101-2026-A', %s, %s, %s, %s, 60, 'offline')
            """,
            (OFFERING, COURSE_VERSION, TERM, BATCH, SECTION_A),
        )
        cur.execute(
            """
            INSERT INTO academic.offering_faculty
                (offering_faculty_id, course_offering_id, person_id,
                 role_in_offering, is_assessor, valid_from, allocated_hours)
            VALUES (%s, %s, %s, 'instructor', true, %s, 48)
            """,
            (OFFERING_FACULTY, OFFERING, P2, TODAY),
        )
        cur.execute(
            """
            INSERT INTO academic.timetable_slot
                (timetable_slot_id, course_offering_id, day_of_week,
                 start_time, end_time, slot_type, venue_text, valid_from)
            VALUES (%s, %s, 1, TIME '09:00', TIME '10:00', 'theory', 'Room 101', %s)
            """,
            (TIMETABLE_SLOT, OFFERING, TODAY),
        )
        cur.execute(
            """
            INSERT INTO academic.section_teacher_assignment
                (section_teacher_assignment_id, section_id, person_id,
                 role_in_section, valid_from, status, assigned_by,
                 authority_role_assignment_id)
            VALUES (%s, %s, %s, 'class_teacher', %s, 'active', %s, %s)
            """,
            (SECTION_TEACHER, SECTION_A, P1, TODAY, P1, ASSIGNMENT),
        )

    try:
        yield conn
    finally:
        conn.rollback()
