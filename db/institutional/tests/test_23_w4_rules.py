"""W4 rule enforcement: attendance integrity, marks, and conflict guards."""

from __future__ import annotations

import psycopg

from w1a_support import P1, P2, TERM, TODAY, expect_error, w1a_base
from w1b_support import COURSE_VERSION, OFFERING, w1b_base
from w2_support import (
    COURSE_REGISTRATION,
    SEMESTER_ONE,
    STUDENT_ONE,
    STUDENT_TWO,
    w2_base,
)
from w3_support import w3_base
from w4_support import (
    COMPONENT_CIA1,
    COMPONENT_CIA2,
    COMPONENT_ESE,
    COURSE_REG_TWO,
    ELIGIBILITY,
    MARK_ENTRY_ONE,
    MARK_ENTRY_TWO,
    MARK_VERSION_ONE,
    MARK_VERSION_TWO,
    RECORD_ONE,
    RECORD_TWO,
    SCHEME,
    SESSION_ONE,
    SESSION_TWO,
    w4_base,
)

OFFERING_TWO = "e8e8e8e8-e8e8-e8e8-e8e8-e8e8e8e8e8e8"
COURSE_REGISTRATION_TWO = "e9e9e9e9-e9e9-e9e9-e9e9-e9e9e9e9e9e9"
MARK_VERSION_THREE = "a9d9a9d9-a9d9-a9d9-a9d9-a9d9a9d9a9d9"


def test_session_time_and_uniqueness_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO attendance.session
            (course_offering_id, session_date, start_time, end_time)
        VALUES (%s, %s, TIME '09:00', TIME '08:30')
        """,
        (OFFERING, TODAY),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.session
            (course_offering_id, session_date, start_time, end_time)
        VALUES (%s, %s, TIME '09:00', TIME '10:00')
        """,
        (OFFERING, TODAY),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.session
            (course_offering_id, session_date, start_time, end_time,
             session_type)
        VALUES (%s, %s, TIME '13:00', TIME '14:00', 'seminar')
        """,
        (OFFERING, TODAY),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO attendance.session
                (course_offering_id, session_date, start_time, end_time)
            VALUES (%s, %s, TIME '13:00', TIME '14:00')
            """,
            (OFFERING, TODAY),
        )


def test_attendance_record_requires_the_registered_offering(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    # SESSION_TWO and STUDENT_ONE are individually valid, but the registration
    # belongs to STUDENT_TWO, so the composite FK must reject the row.
    expect_error(
        conn,
        """
        INSERT INTO attendance.record
            (session_id, student_id, course_registration_id,
             course_offering_id, status)
        VALUES (%s, %s, %s, %s, 'present')
        """,
        (SESSION_TWO, STUDENT_ONE, COURSE_REG_TWO, OFFERING),
        contains="foreign key",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.record
            (session_id, student_id, course_registration_id,
             course_offering_id, status)
        VALUES (%s, %s, %s, %s, 'present')
        """,
        (SESSION_ONE, STUDENT_ONE, COURSE_REGISTRATION, OFFERING),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.record
            (session_id, student_id, course_registration_id,
             course_offering_id, status)
        VALUES (%s, %s, %s, %s, 'unknown')
        """,
        (SESSION_ONE, STUDENT_TWO, COURSE_REG_TWO, OFFERING),
        contains="check",
    )


def test_attendance_record_rejects_a_session_from_another_offering(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.course_offering
                (course_offering_id, offering_code, course_version_id,
                 term_id, batch_id, section_id, capacity)
            VALUES (%s, 'CSE101-2026-B2', %s, %s,
                    'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', %s, 60)
            """,
            (OFFERING_TWO, COURSE_VERSION, TERM, "d6d6d6d6-d6d6-d6d6-d6d6-d6d6d6d6d6d6"),
        )
        cur.execute(
            """
            INSERT INTO student.course_registration
                (course_registration_id, student_id, semester_registration_id,
                 course_offering_id, registration_type, credits, status)
            VALUES (%s, %s, %s, %s, 'regular', 4.0, 'registered')
            """,
            (COURSE_REGISTRATION_TWO, STUDENT_ONE, SEMESTER_ONE, OFFERING_TWO),
        )

    expect_error(
        conn,
        """
        INSERT INTO attendance.record
            (session_id, student_id, course_registration_id,
             course_offering_id, status)
        VALUES (%s, %s, %s, %s, 'present')
        """,
        (SESSION_TWO, STUDENT_ONE, COURSE_REGISTRATION_TWO, OFFERING_TWO),
        contains="foreign key",
    )


def test_attendance_correction_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO attendance.correction
            (attendance_record_id, old_status, new_status, reason, requested_by)
        VALUES (%s, 'absent', 'absent', 'No change recorded', %s)
        """,
        (RECORD_ONE, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.correction
            (attendance_record_id, old_status, new_status, reason, requested_by)
        VALUES (%s, 'absent', 'present', 'bad', %s)
        """,
        (RECORD_ONE, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.correction
            (attendance_record_id, old_status, new_status, reason,
             requested_by, requested_at, approved_at)
        VALUES (%s, 'absent', 'present', 'Approved before request',
                %s, now(), now() - interval '1 hour')
        """,
        (RECORD_ONE, P1),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO attendance.correction
                (attendance_record_id, old_status, new_status, reason,
                 requested_by, requested_at, approved_by, approved_at, status)
            VALUES (%s, 'absent', 'present', 'Approved after review',
                    %s, now() - interval '2 hours', %s, now(), 'approved')
            """,
            (RECORD_ONE, P1, P2),
        )


def test_attendance_summary_bounds_and_snapshot_identity(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO attendance.summary
            (student_id, course_offering_id, sessions_conducted,
             sessions_attended, attendance_pct, as_of, calculation_version)
        VALUES (%s, %s, 10, 11, 80.00, now() - interval '2 hours', 'v1')
        """,
        (STUDENT_TWO, OFFERING),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.summary
            (student_id, course_offering_id, sessions_conducted,
             sessions_attended, attendance_pct, as_of, calculation_version)
        VALUES (%s, %s, 10, 8, 101.00, now() - interval '2 hours', 'v1')
        """,
        (STUDENT_TWO, OFFERING),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO attendance.summary
                (student_id, course_offering_id, sessions_conducted,
                 sessions_attended, attendance_pct, as_of, calculation_version)
            VALUES (%s, %s, 10, 8, 80.00, now() - interval '2 hours', 'v1')
            """,
            (STUDENT_TWO, OFFERING),
        )

    expect_error(
        conn,
        """
        INSERT INTO attendance.summary
            (student_id, course_offering_id, sessions_conducted,
             sessions_attended, attendance_pct, as_of, calculation_version)
        VALUES (%s, %s, 10, 8, 80.00, now() - interval '2 hours', 'v2')
        """,
        (STUDENT_TWO, OFFERING),
        contains="duplicate key",
    )


def test_both_attendance_eligibility_variants_are_stored(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO attendance.eligibility_assessment
                (student_id, term_id, rule_variant, theory_pct, practical_pct,
                 outcome)
            VALUES (%s, %s, 'split', 78.50, 91.00, 'eligible')
            """,
            (STUDENT_TWO, TERM),
        )

    expect_error(
        conn,
        """
        INSERT INTO attendance.eligibility_assessment
            (student_id, term_id, rule_variant, aggregate_pct, outcome)
        VALUES (%s, %s, 'weighted', 80.00, 'eligible')
        """,
        (STUDENT_TWO, TERM),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.eligibility_assessment
            (student_id, term_id, rule_variant, aggregate_pct, outcome)
        VALUES (%s, %s, 'aggregate', 80.00, 'maybe')
        """,
        (STUDENT_TWO, TERM),
        contains="check",
    )


def test_condonation_case_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO attendance.eligibility_assessment
                (student_id, term_id, rule_variant, aggregate_pct, outcome)
            VALUES (%s, %s, 'aggregate', 65.00, 'shortage')
            RETURNING eligibility_assessment_id
            """,
            (STUDENT_TWO, TERM),
        )
        [(student_two_eligibility,)] = cur.fetchall()

    expect_error(
        conn,
        """
        INSERT INTO attendance.condonation_case
            (student_id, term_id, eligibility_assessment_id, shortfall_pct,
             grounds, status)
        VALUES (%s, %s, %s, 101.00, 'Out of range', 'opened')
        """,
        (STUDENT_TWO, TERM, student_two_eligibility),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.condonation_case
            (student_id, term_id, eligibility_assessment_id, shortfall_pct,
             grounds, status)
        VALUES (%s, %s, %s, 5.00, 'Duplicate case', 'opened')
        """,
        (STUDENT_ONE, TERM, ELIGIBILITY),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.condonation_case
            (student_id, term_id, eligibility_assessment_id, shortfall_pct,
             grounds, status)
        VALUES (%s, %s, %s, 5.00, 'Invalid status', 'pending')
        """,
        (STUDENT_TWO, TERM, student_two_eligibility),
        contains="check",
    )


def test_assessment_scheme_and_component_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO assessment.scheme
            (course_version_id, name, effective_from_term_id,
             effective_to_term_id)
        VALUES (%s, 'Same term window', %s, %s)
        """,
        (COURSE_VERSION, TERM, TERM),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.scheme
            (course_version_id, name, effective_from_term_id, status)
        VALUES (%s, 'Theory CIA+ESE', %s, 'draft')
        """,
        (COURSE_VERSION, TERM),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.component
            (scheme_id, component_code, name, component_type, max_marks,
             weight_pct, sequence_no)
        VALUES (%s, 'CIA1', 'Zero marks', 'internal', 0, 50, 1)
        """,
        (SCHEME,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.component
            (component_id, scheme_id, component_code, name, component_type,
             max_marks, weight_pct, sequence_no, parent_component_id)
        VALUES (%s, %s, 'VIVA', 'Self parent', 'internal', 40, 50, 4, %s)
        """,
        ("f6f6f6f6-f6f6-f6f6-f6f6-f6f6f6f6f6f6", SCHEME,
         "f6f6f6f6-f6f6-f6f6-f6f6-f6f6f6f6f6f6"),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.component
            (scheme_id, component_code, name, component_type, max_marks,
             weight_pct, sequence_no)
        VALUES (%s, 'QUIZ', 'Unknown code', 'internal', 40, 50, 5)
        """,
        (SCHEME,),
        contains="check",
    )


def test_assessment_schedule_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO assessment.schedule
            (component_id, course_offering_id, schedule_type,
             scheduled_start, scheduled_end, duration_min)
        VALUES (%s, %s, 'regular', now(), now() + interval '1 hour', 60)
        """,
        (COMPONENT_CIA1, OFFERING),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.schedule
            (component_id, course_offering_id, schedule_type,
             scheduled_start, scheduled_end, duration_min)
        VALUES (%s, %s, 'makeup', now(), now() - interval '1 hour', 60)
        """,
        (COMPONENT_CIA1, OFFERING),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.schedule
            (component_id, course_offering_id, schedule_type,
             scheduled_start, scheduled_end, duration_min)
        VALUES (%s, %s, 'reassessment', now(), now() + interval '1 hour', 0)
        """,
        (COMPONENT_CIA2, OFFERING),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.schedule
                (component_id, course_offering_id, schedule_type,
                 scheduled_start, scheduled_end, duration_min, venue_text)
            VALUES (%s, %s, 'makeup', now() + interval '14 days',
                    now() + interval '14 days 1 hour', 60, 'Room 102')
            """,
            (COMPONENT_CIA1, OFFERING),
        )


def test_component_weights_must_total_one_hundred(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.scheme
                (scheme_id, course_version_id, name, effective_from_term_id)
            VALUES ('f7f7f7f7-f7f7-f7f7-f7f7-f7f7f7f7f7f7', %s,
                    'Incomplete weights', %s)
            """,
            (COURSE_VERSION, TERM),
        )
        cur.execute(
            """
            INSERT INTO assessment.component
                (scheme_id, component_code, name, component_type, max_marks,
                 weight_pct, sequence_no)
            VALUES ('f7f7f7f7-f7f7-f7f7-f7f7-f7f7f7f7f7f7',
                    'CIA1', 'Only component', 'internal', 40, 70, 1)
            """,
        )

    expect_error(
        conn,
        "SET CONSTRAINTS ALL IMMEDIATE",
        contains="sibling weight_pct",
    )


def test_component_weights_accept_a_complete_nested_scheme(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    parent = "f9f9f9f9-f9f9-f9f9-f9f9-f9f9f9f9f9f9"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.scheme
                (scheme_id, course_version_id, name, effective_from_term_id)
            VALUES ('fafafafa-fafa-fafa-fafa-fafafafafafa', %s,
                    'Nested weights', %s)
            """,
            (COURSE_VERSION, TERM),
        )
        cur.execute(
            """
            INSERT INTO assessment.component
                (component_id, scheme_id, component_code, name, component_type,
                 max_marks, weight_pct, sequence_no)
            VALUES (%s, 'fafafafa-fafa-fafa-fafa-fafafafafafa', 'ASSIGNMENT',
                    'Assignment group', 'sessional', 100, 100, 1)
            """,
            (parent,),
        )
        cur.execute(
            """
            INSERT INTO assessment.component
                (scheme_id, component_code, name, component_type, max_marks,
                 weight_pct, sequence_no, parent_component_id)
            VALUES ('fafafafa-fafa-fafa-fafa-fafafafafafa', 'CIA1',
                    'Assignment part one', 'internal', 40, 40, 2, %s),
                   ('fafafafa-fafa-fafa-fafa-fafafafafafa', 'CIA2',
                    'Assignment part two', 'internal', 60, 60, 3, %s)
            """,
            (parent, parent),
        )
    with conn.cursor() as cur:
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_component_fields_are_frozen_once_marks_exist(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        UPDATE assessment.component SET max_marks = 70
        WHERE component_id = %s
        """,
        (COMPONENT_ESE,),
        contains="frozen",
    )

    expect_error(
        conn,
        """
        UPDATE assessment.component SET weight_pct = 25
        WHERE component_id = %s
        """,
        (COMPONENT_CIA2,),
        contains="frozen",
    )

    # A scheme without mark entries can still be edited.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.scheme
                (scheme_id, course_version_id, name, effective_from_term_id)
            VALUES ('fbfbfbfb-fbfb-fbfb-fbfb-fbfbfbfbfbfb', %s,
                    'Editable scheme', %s)
            """,
            (COURSE_VERSION, TERM),
        )
        cur.execute(
            """
            INSERT INTO assessment.component
                (scheme_id, component_code, name, component_type, max_marks,
                 weight_pct, sequence_no)
            VALUES ('fbfbfbfb-fbfb-fbfb-fbfb-fbfbfbfbfbfb', 'CIA2',
                    'Editable component', 'internal', 40, 100, 1)
            """,
        )
        cur.execute(
            """
            UPDATE assessment.component SET max_marks = 50
            WHERE scheme_id = 'fbfbfbfb-fbfb-fbfb-fbfb-fbfbfbfbfbfb'
            """
        )


def test_mark_entry_and_version_checks(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_entry
            (student_id, component_id, course_offering_id,
             current_version_no)
        VALUES (%s, %s, %s, 0)
        """,
        (STUDENT_TWO, COMPONENT_CIA2, OFFERING),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_entry
            (student_id, component_id, course_offering_id)
        VALUES (%s, %s, %s)
        """,
        (STUDENT_ONE, COMPONENT_CIA1, OFFERING),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_entry_version
            (mark_entry_id, version_no, marks_obtained, max_marks_snapshot,
             entered_by)
        VALUES (%s, 2, 41.00, 40.00, %s)
        """,
        (MARK_ENTRY_ONE, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_entry_version
            (mark_entry_id, version_no, marks_obtained, max_marks_snapshot,
             entered_by, submitted_at, verified_at)
        VALUES (%s, 2, 30.00, 40.00, %s, now(), now() - interval '1 hour')
        """,
        (MARK_ENTRY_ONE, P1),
        contains="check",
    )


def test_verified_and_locked_mark_versions_are_sealed(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE assessment.mark_entry_version SET status = 'verified'
            WHERE mark_entry_version_id = %s
            """,
            (MARK_VERSION_ONE,),
        )
        cur.execute(
            """
            UPDATE assessment.mark_entry_version SET status = 'locked'
            WHERE mark_entry_version_id = %s
            """,
            (MARK_VERSION_TWO,),
        )

    expect_error(
        conn,
        """
        UPDATE assessment.mark_entry_version SET marks_obtained = 31.00
        WHERE mark_entry_version_id = %s
        """,
        (MARK_VERSION_ONE,),
        contains="immutable",
    )

    expect_error(
        conn,
        """
        DELETE FROM assessment.mark_entry_version
        WHERE mark_entry_version_id = %s
        """,
        (MARK_VERSION_ONE,),
        contains="immutable",
    )

    expect_error(
        conn,
        """
        UPDATE assessment.mark_entry_version SET status = 'draft'
        WHERE mark_entry_version_id = %s
        """,
        (MARK_VERSION_TWO,),
        contains="immutable",
    )


def test_mark_correction_versions_must_share_the_mark_entry(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.mark_entry_version
                (mark_entry_version_id, mark_entry_id, version_no,
                 marks_obtained, max_marks_snapshot, entered_by)
            VALUES (%s, %s, 2, 35.00, 40.00, %s)
            """,
            (MARK_VERSION_THREE, MARK_ENTRY_ONE, P1),
        )

    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_correction
            (mark_entry_id, from_version_id, to_version_id, reason,
             requested_by)
        VALUES (%s, %s, %s, 'Cross-entry correction', %s)
        """,
        (MARK_ENTRY_ONE, MARK_VERSION_ONE, MARK_VERSION_TWO, P1),
        contains="belong to mark entry",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.mark_correction
                (mark_entry_id, from_version_id, to_version_id, reason,
                 requested_by)
            VALUES (%s, %s, %s, 'Corrected after recheck', %s)
            """,
            (MARK_ENTRY_ONE, MARK_VERSION_ONE, MARK_VERSION_THREE, P1),
        )


def test_unresolved_conflict_blocks_marks_and_attendance(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO assessment.mark_entry_version
            (mark_entry_id, version_no, marks_obtained, max_marks_snapshot,
             entered_by)
        VALUES (%s, 2, 20.00, 40.00, %s)
        """,
        (MARK_ENTRY_TWO, P2),
        contains="unresolved conflict",
    )

    expect_error(
        conn,
        """
        UPDATE attendance.record SET marked_by = %s
        WHERE attendance_record_id = %s
        """,
        (P2, RECORD_TWO),
        contains="unresolved conflict",
    )

    expect_error(
        conn,
        """
        INSERT INTO attendance.record
            (session_id, student_id, course_registration_id,
             course_offering_id, status, marked_by)
        VALUES (%s, %s, %s, %s, 'present', %s)
        """,
        (SESSION_ONE, STUDENT_TWO, COURSE_REG_TWO, OFFERING, P2),
        contains="unresolved conflict",
    )

    # A resolved declaration does not block the same faculty member.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.mark_entry_version
                (mark_entry_id, version_no, marks_obtained, max_marks_snapshot,
                 entered_by)
            VALUES (%s, 2, 35.00, 40.00, %s)
            """,
            (MARK_ENTRY_ONE, P1),
        )


def test_conflict_declaration_rules(
    conn: psycopg.Connection,
    w4_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO assessment.conflict_declaration
            (faculty_person_id, course_offering_id, student_id,
             relationship_type, action_taken, reassigned_to_person_id)
        VALUES (%s, %s, %s, 'other', 'reassigned', %s)
        """,
        (P1, OFFERING, STUDENT_TWO, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.conflict_declaration
            (faculty_person_id, course_offering_id, student_id,
             relationship_type)
        VALUES (%s, %s, %s, 'friend')
        """,
        (P1, OFFERING, STUDENT_TWO),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO assessment.conflict_declaration
            (faculty_person_id, course_offering_id, student_id,
             relationship_type)
        VALUES (%s, %s, %s, 'other')
        """,
        (P2, OFFERING, STUDENT_TWO),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO assessment.conflict_declaration
                (faculty_person_id, course_offering_id, student_id,
                 relationship_type, action_taken, status)
            VALUES (%s, %s, %s, 'relative', 'recused', 'resolved')
            """,
            (P1, OFFERING, STUDENT_TWO),
        )
