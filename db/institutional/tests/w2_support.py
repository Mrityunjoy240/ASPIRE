"""Shared baseline data for W2 student-record tests.

Builds on :mod:`w1b_base`: one admitted applicant (P3), a second student in a
different section (P4), a consenting guardian (P5), registration records,
a current exam roll number, a status history, and an eligibility decision.
P1 is the class teacher of section A, P2 is the allocated instructor of the
offering, so the RLS matrix can exercise every implemented arm.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from w1a_support import (
    ASSIGNMENT,
    INSTITUTION,
    P1,
    P2,
    TERM,
    TODAY,
    VERSION_CONFIDENTIAL,
    VERSION_PUBLIC,
    w1a_base,
)
from w1b_support import (
    BATCH,
    COURSE_VERSION,
    OFFERING,
    PROGRAMME,
    SECTION_A,
    SECTION_B,
    w1b_base,
)

P3 = "11111111-1111-1111-1111-111111111113"
P4 = "11111111-1111-1111-1111-111111111114"
P5 = "11111111-1111-1111-1111-111111111115"

APPLICATION = "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"
OFFER = "a2a2a2a2-a2a2-a2a2-a2a2-a2a2a2a2a2a2"
STUDENT_ONE = "b1b1b1b1-b1b1-b1b1-b1b1-b1b1b1b1b1b1"
STUDENT_TWO = "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"
GUARDIAN = "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1"
STUDENT_GUARDIAN = "c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2"
STUDENT_DOCUMENT = "c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3"
UNIVERSITY_REGISTRATION = "c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4"
EXAM_ROLL = "c5c5c5c5-c5c5-c5c5-c5c5-c5c5c5c5c5c5"
SEMESTER_ONE = "c6c6c6c6-c6c6-c6c6-c6c6-c6c6c6c6c6c6"
SEMESTER_TWO = "c7c7c7c7-c7c7-c7c7-c7c7-c7c7c7c7c7c7"
COURSE_REGISTRATION = "c8c8c8c8-c8c8-c8c8-c8c8-c8c8c8c8c8c8"
STATUS_HISTORY = "c9c9c9c9-c9c9-c9c9-c9c9-c9c9c9c9c9c9"
ELIGIBILITY = "d1d1d1d1-d1d1-d1d1-d1d1-d1d1d1d1d1d1"
SECTION_ASSIGNMENT = "d2d2d2d2-d2d2-d2d2-d2d2-d2d2d2d2d2d2"

START = TODAY - timedelta(days=60)
ROLL_NUMBER = "120100264001"


@pytest.fixture()
def w2_base(w1b_base):
    conn = w1b_base
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.person (person_id, legal_name, date_of_birth)
            VALUES (%s, 'Student One', DATE '2006-01-01'),
                   (%s, 'Student Two', DATE '2006-02-02'),
                   (%s, 'Guardian One', DATE '1975-03-03')
            """,
            (P3, P4, P5),
        )
        cur.execute(
            """
            INSERT INTO student.admission_application
                (application_id, person_id, programme_id, batch_id,
                 application_no, admission_year, counselling_authority,
                 category, eligibility_status, application_status,
                 submitted_at, verified_by, verified_at)
            VALUES (%s, %s, %s, %s, 'APP-2026-001', 2026, 'WBJEE',
                    'general', 'eligible', 'admitted', now(), %s, now())
            """,
            (APPLICATION, P3, PROGRAMME, BATCH, P1),
        )
        cur.execute(
            """
            INSERT INTO student.admission_offer
                (offer_id, application_id, offer_no, offered_at, accepted_at,
                 admission_confirmed_at, fee_receipt_reference, confirmed_by,
                 status)
            VALUES (%s, %s, 'OFF-2026-001', now() - interval '2 days', now(),
                    now(), 'FEE-2026-001', %s, 'confirmed')
            """,
            (OFFER, APPLICATION, P1),
        )
        cur.execute(
            """
            INSERT INTO student.student
                (student_id, person_id, batch_id, section_id,
                 admission_application_id, college_roll_no, admission_year,
                 entry_mode, category, date_of_admission,
                 expected_completion_year, current_status, photo_uri)
            VALUES (%s, %s, %s, %s, %s, 'BCREC/2026/001', 2026,
                    'regular', 'general', %s, 2030, 'active',
                    's3://bucket/photo-one.jpg'),
                   (%s, %s, %s, %s, NULL, 'BCREC/2026/002', 2026,
                    'regular', 'general', %s, 2030, 'active', NULL)
            """,
            (
                STUDENT_ONE, P3, BATCH, SECTION_A, APPLICATION, START,
                STUDENT_TWO, P4, BATCH, SECTION_B, START,
            ),
        )
        cur.execute(
            """
            INSERT INTO student.guardian
                (guardian_id, person_id, occupation, education,
                 annual_income_band, is_alumni)
            VALUES (%s, %s, 'Engineer', 'B.Tech', '3l_5l', false)
            """,
            (GUARDIAN, P5),
        )
        cur.execute(
            """
            INSERT INTO student.student_guardian
                (student_guardian_id, student_id, guardian_id, relation,
                 is_primary, consent_status, consent_recorded_at, valid_from)
            VALUES (%s, %s, %s, 'father', true, 'granted', now(), %s)
            """,
            (STUDENT_GUARDIAN, STUDENT_ONE, GUARDIAN, START),
        )
        cur.execute(
            """
            INSERT INTO student.student_document
                (student_document_id, student_id, document_version_id,
                 document_type, verification_status, verified_by, verified_at)
            VALUES (%s, %s, %s, 'id_proof', 'verified', %s, now())
            """,
            (STUDENT_DOCUMENT, STUDENT_ONE, VERSION_CONFIDENTIAL, P1),
        )
        cur.execute(
            """
            INSERT INTO student.university_registration
                (university_registration_id, student_id, registration_number,
                 registration_year, status, uploaded_at, confirmed_at,
                 proof_document_version_id)
            VALUES (%s, %s, 'MAKAUT-2026-0001', 2026, 'confirmed', now(), now(), %s)
            """,
            (UNIVERSITY_REGISTRATION, STUDENT_ONE, VERSION_PUBLIC),
        )
        cur.execute(
            """
            INSERT INTO student.exam_roll_number
                (exam_roll_number_id, student_id, programme_id, roll_number,
                 college_code, programme_code, registration_year,
                 course_duration_years, serial_no, issued_on, is_current, status)
            VALUES (%s, %s, %s, %s, '120', '100', 26, 4, 1, %s, true, 'active')
            """,
            (EXAM_ROLL, STUDENT_ONE, PROGRAMME, ROLL_NUMBER, TODAY),
        )
        cur.execute(
            """
            INSERT INTO student.semester_registration
                (semester_registration_id, student_id, term_id, registration_no,
                 submitted_at, approved_by, approved_at, status)
            VALUES (%s, %s, %s, 'SEM-2026-001', now() - interval '2 days',
                    %s, now() - interval '1 day', 'approved'),
                   (%s, %s, %s, 'SEM-2026-002', now(), %s, now(), 'approved')
            """,
            (
                SEMESTER_ONE, STUDENT_ONE, TERM, P1,
                SEMESTER_TWO, STUDENT_TWO, TERM, P1,
            ),
        )
        cur.execute(
            """
            INSERT INTO student.course_registration
                (course_registration_id, student_id, semester_registration_id,
                 course_offering_id, registration_type, credits, status)
            VALUES (%s, %s, %s, %s, 'regular', 4.0, 'registered')
            """,
            (COURSE_REGISTRATION, STUDENT_ONE, SEMESTER_ONE, OFFERING),
        )
        cur.execute(
            """
            INSERT INTO student.status_history
                (status_history_id, student_id, status, effective_from,
                 recorded_by)
            VALUES (%s, %s, 'active', %s, %s)
            """,
            (STATUS_HISTORY, STUDENT_ONE, START, P1),
        )
        cur.execute(
            """
            INSERT INTO student.eligibility_determination
                (eligibility_determination_id, student_id, term_id, gate_code,
                 scope_type, scope_id, status, source, evidence_json, determined_by)
            VALUES (%s, %s, %s, 'ATTENDANCE', 'term', %s, 'pass', 'computed',
                    '{}'::jsonb, %s)
            """,
            (ELIGIBILITY, STUDENT_ONE, TERM, TERM, P1),
        )
        cur.execute(
            """
            INSERT INTO student.section_assignment
                (section_assignment_id, student_id, section_id, batch_id,
                 effective_from, assignment_reason, status, approved_by,
                 authority_role_assignment_id, source_document_version_id)
            VALUES (%s, %s, %s, %s, %s, 'initial_allotment', 'active', %s, %s, %s)
            """,
            (
                SECTION_ASSIGNMENT, STUDENT_ONE, SECTION_A, BATCH, START,
                P1, ASSIGNMENT, VERSION_PUBLIC,
            ),
        )

    try:
        yield conn
    finally:
        conn.rollback()
