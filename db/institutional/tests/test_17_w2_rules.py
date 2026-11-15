"""W2 rule enforcement: uniques, checks, exclusions, triggers, composite FKs."""

from __future__ import annotations

from datetime import timedelta

import psycopg

from w1a_support import (
    TERM,
    TODAY,
    VERSION_CONFIDENTIAL,
    expect_error,
    w1a_base,
)
from w1b_support import (
    BATCH,
    OFFERING,
    PROGRAMME,
    SECTION_A,
    SECTION_B,
    w1b_base,
)
from w2_support import (
    APPLICATION,
    ELIGIBILITY,
    GUARDIAN,
    P3,
    P4,
    SECTION_ASSIGNMENT,
    SEMESTER_ONE,
    SEMESTER_TWO,
    START,
    STATUS_HISTORY,
    STUDENT_ONE,
    STUDENT_TWO,
    w2_base,
)

P6 = "11111111-1111-1111-1111-111111111116"
APPLICATION_2 = "a3a3a3a3-a3a3-a3a3-a3a3-a3a3a3a3a3a3"
GUARDIAN_2 = "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c2"
BATCH_2 = "f2f2f2f2-f2f2-f2f2-f2f2-f2f2f2f2f2f2"
SECTION_C = "f3f3f3f3-f3f3-f3f3-f3f3-f3f3f3f3f3f3"
LATER = START + timedelta(days=20)


def _insert_application(
    conn: psycopg.Connection,
    *,
    application_id: str,
    person_id: str,
    application_no: str,
    admission_year: int = 2026,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.admission_application
                (application_id, person_id, programme_id, application_no,
                 admission_year)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (application_id, person_id, PROGRAMME, application_no, admission_year),
        )


def test_application_numbers_are_unique_within_an_admission_year(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.admission_application
            (person_id, programme_id, application_no, admission_year)
        VALUES (%s, %s, 'APP-2026-001', 2026)
        """,
        (P4, PROGRAMME),
        contains="duplicate key",
    )

    _insert_application(
        conn,
        application_id=APPLICATION_2,
        person_id=P4,
        application_no="APP-2026-001",
        admission_year=2027,
    )


def test_admission_application_rejects_an_unknown_category(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.admission_application
            (person_id, programme_id, application_no, admission_year, category)
        VALUES (%s, %s, 'APP-2026-009', 2026, 'special')
        """,
        (P4, PROGRAMME),
        contains="check",
    )


def test_one_offer_per_application_and_acceptance_order(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.admission_offer
            (application_id, offer_no, offered_at, accepted_at)
        VALUES (%s, 'OFF-2026-002', now(), now())
        """,
        (APPLICATION,),
        contains="duplicate key",
    )

    _insert_application(
        conn,
        application_id=APPLICATION_2,
        person_id=P4,
        application_no="APP-2026-002",
    )
    expect_error(
        conn,
        """
        INSERT INTO student.admission_offer
            (application_id, offer_no, offered_at, accepted_at)
        VALUES (%s, 'OFF-2026-003', now(), now() - interval '1 day')
        """,
        (APPLICATION_2,),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.admission_offer
                (application_id, offer_no, offered_at, accepted_at)
            VALUES (%s, 'OFF-2026-003', now() - interval '1 day', now())
            """,
            (APPLICATION_2,),
        )


def test_student_identity_uniques_and_checks(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO iam.person (person_id, legal_name, date_of_birth) "
            "VALUES (%s, 'Student Three', DATE '2006-03-03')",
            (P6,),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.student
            (person_id, batch_id, college_roll_no, admission_year,
             date_of_admission)
        VALUES (%s, %s, 'BCREC/2026/001', 2026, %s)
        """,
        (P6, BATCH, START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.student
            (person_id, batch_id, college_roll_no, admission_year,
             date_of_admission)
        VALUES (%s, %s, 'BCREC/2026/003', 2026, %s)
        """,
        (P3, BATCH, START),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.student
            (person_id, batch_id, college_roll_no, admission_year,
             date_of_admission, expected_completion_year)
        VALUES (%s, %s, 'BCREC/2026/004', 2026, %s, 2025)
        """,
        (P6, BATCH, START),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.student
            (person_id, batch_id, college_roll_no, admission_year,
             date_of_admission, photo_uri)
        VALUES (%s, %s, 'BCREC/2026/005', 2026, %s, 'not-a-uri')
        """,
        (P6, BATCH, START),
        contains="check",
    )


def test_guardian_profile_and_consent_rules(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.student_guardian
            (student_id, guardian_id, relation, is_primary, consent_status)
        VALUES (%s, %s, 'father', false, 'granted')
        """,
        (STUDENT_ONE, GUARDIAN),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO iam.person (person_id, legal_name, date_of_birth) "
            "VALUES (%s, 'Guardian Two', DATE '1970-01-01')",
            (P6,),
        )
        cur.execute(
            """
            INSERT INTO student.guardian (guardian_id, person_id)
            VALUES (%s, %s)
            """,
            (GUARDIAN_2, P6),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.student_guardian
            (student_id, guardian_id, relation, is_primary, consent_status)
        VALUES (%s, %s, 'guardian', true, 'granted')
        """,
        (STUDENT_ONE, GUARDIAN_2),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.student_guardian
            (student_id, guardian_id, relation, is_primary, consent_status,
             valid_from, valid_to)
        VALUES (%s, %s, 'guardian', false, 'pending', %s, %s)
        """,
        (STUDENT_TWO, GUARDIAN_2, START, START),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.student_guardian
                (student_id, guardian_id, relation, is_primary, consent_status)
            VALUES (%s, %s, 'guardian', false, 'pending')
            """,
            (STUDENT_TWO, GUARDIAN_2),
        )


def test_student_document_uniqueness_and_type_check(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.student_document
            (student_id, document_version_id, document_type)
        VALUES (%s, %s, 'id_proof')
        """,
        (STUDENT_ONE, VERSION_CONFIDENTIAL),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.student_document
            (student_id, document_version_id, document_type)
        VALUES (%s, %s, 'unknown_document')
        """,
        (STUDENT_TWO, VERSION_CONFIDENTIAL),
        contains="check",
    )


def test_university_registration_uniques_and_year_range(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.university_registration
            (student_id, registration_number, registration_year)
        VALUES (%s, 'MAKAUT-2026-9999', 2026)
        """,
        (STUDENT_ONE,),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.university_registration
            (student_id, registration_number, registration_year)
        VALUES (%s, 'makaut-2026-0001', 2026)
        """,
        (STUDENT_TWO,),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.university_registration
            (student_id, registration_number, registration_year)
        VALUES (%s, 'MAKAUT-2026-0002', 1999)
        """,
        (STUDENT_TWO,),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.university_registration
                (student_id, registration_number, registration_year)
            VALUES (%s, 'MAKAUT-2026-0002', 2026)
            """,
            (STUDENT_TWO,),
        )


def test_exam_roll_numbers_reconcile_and_are_unique(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.exam_roll_number
            (student_id, programme_id, roll_number, college_code,
             programme_code, registration_year, course_duration_years,
             serial_no)
        VALUES (%s, %s, '120100264099', '120', '100', 26, 4, 2)
        """,
        (STUDENT_TWO, PROGRAMME),
        contains="components",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.exam_roll_number
            (student_id, programme_id, roll_number, college_code,
             programme_code, registration_year, course_duration_years,
             serial_no)
        VALUES (%s, %s, '120100264001', '120', '100', 26, 4, 1)
        """,
        (STUDENT_TWO, PROGRAMME),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.exam_roll_number
                (student_id, programme_id, roll_number, college_code,
                 programme_code, registration_year, course_duration_years,
                 serial_no)
            VALUES (%s, %s, '120100264002', '120', '100', 26, 4, 2)
            """,
            (STUDENT_TWO, PROGRAMME),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.exam_roll_number
            (student_id, programme_id, roll_number, college_code,
             programme_code, registration_year, course_duration_years,
             serial_no, is_current)
        VALUES (%s, %s, '120100264003', '120', '100', 26, 4, 3, true)
        """,
        (STUDENT_TWO, PROGRAMME),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.exam_roll_number
                (student_id, programme_id, roll_number, college_code,
                 programme_code, registration_year, course_duration_years,
                 serial_no, is_current)
            VALUES (%s, %s, '120100264004', '120', '100', 26, 4, 4, false)
            """,
            (STUDENT_TWO, PROGRAMME),
        )


def test_semester_registration_uniques_and_approval_order(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.semester_registration (student_id, term_id)
        VALUES (%s, %s)
        """,
        (STUDENT_ONE, TERM),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        UPDATE student.semester_registration
        SET approved_at = submitted_at - interval '1 day'
        WHERE semester_registration_id = %s
        """,
        (SEMESTER_TWO,),
        contains="check",
    )

    expect_error(
        conn,
        """
        UPDATE student.semester_registration
        SET registration_no = 'SEM-2026-001'
        WHERE semester_registration_id = %s
        """,
        (SEMESTER_TWO,),
        contains="duplicate key",
    )


def test_course_registration_composite_student_anchor(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.course_registration
            (student_id, semester_registration_id, course_offering_id)
        VALUES (%s, %s, %s)
        """,
        (STUDENT_ONE, SEMESTER_TWO, OFFERING),
        contains="foreign key",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.course_registration
            (student_id, semester_registration_id, course_offering_id, credits)
        VALUES (%s, %s, %s, -1)
        """,
        (STUDENT_TWO, SEMESTER_TWO, OFFERING),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.course_registration
            (student_id, semester_registration_id, course_offering_id,
             registered_at, dropped_at)
        VALUES (%s, %s, %s, now(), now() - interval '1 day')
        """,
        (STUDENT_TWO, SEMESTER_TWO, OFFERING),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.course_registration
                (student_id, semester_registration_id, course_offering_id, credits)
            VALUES (%s, %s, %s, 4.0)
            """,
            (STUDENT_TWO, SEMESTER_TWO, OFFERING),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.course_registration
            (student_id, semester_registration_id, course_offering_id)
        VALUES (%s, %s, %s)
        """,
        (STUDENT_ONE, SEMESTER_ONE, OFFERING),
        contains="duplicate key",
    )


def test_status_history_ranges_cannot_overlap(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.status_history
            (student_id, status, effective_from)
        VALUES (%s, 'detained', %s)
        """,
        (STUDENT_ONE, START + timedelta(days=1)),
        contains="exclusion",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.status_history
            (student_id, status, effective_from, effective_to)
        VALUES (%s, 'detained', %s, %s)
        """,
        (STUDENT_ONE, START, START),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE student.status_history
            SET effective_to = %s
            WHERE status_history_id = %s
            """,
            (START + timedelta(days=10), STATUS_HISTORY),
        )
        cur.execute(
            """
            INSERT INTO student.status_history
                (student_id, status, effective_from, effective_to)
            VALUES (%s, 'detained', %s, %s)
            """,
            (STUDENT_ONE, START + timedelta(days=11), START + timedelta(days=15)),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.status_history
            (student_id, status, effective_from, effective_to)
        VALUES (%s, 'active', %s, %s)
        """,
        (STUDENT_ONE, START + timedelta(days=12), START + timedelta(days=20)),
        contains="exclusion",
    )


def test_eligibility_scope_population_and_append_only(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.eligibility_determination
            (student_id, term_id, gate_code, scope_type, scope_id)
        VALUES (%s, %s, 'FEE_CLEARANCE', 'term', NULL)
        """,
        (STUDENT_TWO, TERM),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.eligibility_determination
            (student_id, term_id, gate_code, scope_type, scope_id)
        VALUES (%s, %s, 'FEE_CLEARANCE', 'institution', %s)
        """,
        (STUDENT_TWO, TERM, TERM),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.eligibility_determination
                (student_id, term_id, gate_code, scope_type, scope_id, status)
            VALUES (%s, %s, 'FEE_CLEARANCE', 'institution', NULL, 'pass')
            """,
            (STUDENT_TWO, TERM),
        )

    expect_error(
        conn,
        """
        UPDATE student.eligibility_determination
        SET status = 'fail'
        WHERE eligibility_determination_id = %s
        """,
        (ELIGIBILITY,),
        contains="append-only",
    )

    expect_error(
        conn,
        """
        DELETE FROM student.eligibility_determination
        WHERE eligibility_determination_id = %s
        """,
        (ELIGIBILITY,),
        contains="append-only",
    )


def test_section_assignment_overlap_and_open_rows(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, effective_from, effective_to)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (STUDENT_ONE, SECTION_B, BATCH, TODAY, TODAY + timedelta(days=30)),
        contains="exclusion",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, effective_from, effective_to)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (STUDENT_TWO, SECTION_B, BATCH, START, START),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE student.section_assignment
            SET effective_to = %s
            WHERE section_assignment_id = %s
            """,
            (START + timedelta(days=10), SECTION_ASSIGNMENT),
        )
        cur.execute(
            """
            INSERT INTO student.section_assignment
                (student_id, section_id, batch_id, effective_from,
                 assignment_reason, status)
            VALUES (%s, %s, %s, %s, 'transfer', 'active')
            """,
            (STUDENT_ONE, SECTION_B, BATCH, LATER),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, effective_from, status)
        VALUES (%s, %s, %s, %s, 'active')
        """,
        (STUDENT_ONE, SECTION_A, BATCH, LATER + timedelta(days=1)),
        contains="exclusion",
    )


def test_section_assignment_rejects_a_cross_batch_section(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO academic.batch
                (batch_id, programme_id, programme_version_id, admission_year,
                 entry_mode)
            SELECT %s, %s, programme_version_id, 2027, 'regular'
            FROM academic.batch WHERE batch_id = %s
            """,
            (BATCH_2, PROGRAMME, BATCH),
        )
        cur.execute(
            """
            INSERT INTO academic.section (section_id, batch_id, section_code)
            VALUES (%s, %s, 'C')
            """,
            (SECTION_C, BATCH_2),
        )

    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, effective_from)
        VALUES (%s, %s, %s, %s)
        """,
        (STUDENT_TWO, SECTION_C, BATCH, START),
        contains="foreign key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO student.section_assignment
                (student_id, section_id, batch_id, effective_from)
            VALUES (%s, %s, %s, %s)
            """,
            (STUDENT_TWO, SECTION_B, BATCH, START),
        )


def test_section_assignment_reason_and_status_are_controlled(
    conn: psycopg.Connection,
    w2_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, assignment_reason)
        VALUES (%s, %s, %s, 'unknown_reason')
        """,
        (STUDENT_TWO, SECTION_B, BATCH),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO student.section_assignment
            (student_id, section_id, batch_id, status)
        VALUES (%s, %s, %s, 'pending')
        """,
        (STUDENT_TWO, SECTION_B, BATCH),
        contains="check",
    )
