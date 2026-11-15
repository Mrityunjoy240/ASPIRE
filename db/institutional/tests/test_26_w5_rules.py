"""W5 rule enforcement: result integrity, seals, and notice rules."""

from __future__ import annotations

import psycopg

from w1a_support import P1, expect_error, w1a_base
from w1b_support import BATCH, PROGRAMME, w1b_base
from w2_support import STUDENT_ONE, STUDENT_TWO, w2_base
from w3_support import w3_base
from w4_support import w4_base
from w5_support import (
    GRADE_CARD,
    GRADE_CARD_RESULT,
    NOTICE,
    NOTICE_VERSION,
    RESULT_IMPORT,
    RESULT_INPUT,
    RESULT_RECORD_ONE,
    RESULT_RECORD_TWO,
    RESULT_REVISION_ONE,
    RESULT_REVISION_TWO,
    RESULT_SET,
    SHA_ONE,
    w5_base,
)

SHA_ZERO = "0" * 64


def test_result_import_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.result_import
            (term_id, programme_id, source_label, file_name, sha256,
             imported_by)
        VALUES ((SELECT term_id FROM exam.result_import WHERE result_import_id = %s),
                (SELECT programme_id FROM exam.result_import WHERE result_import_id = %s),
                'MAKAUT', 'short-hash.xlsx', %s, %s)
        """,
        (RESULT_IMPORT, RESULT_IMPORT, "0" * 63, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_import
            (term_id, programme_id, source_label, file_name, sha256,
             imported_by, row_count)
        VALUES ((SELECT term_id FROM exam.result_import WHERE result_import_id = %s),
                (SELECT programme_id FROM exam.result_import WHERE result_import_id = %s),
                'MAKAUT', 'negative.xlsx', %s, %s, -1)
        """,
        (RESULT_IMPORT, RESULT_IMPORT, SHA_ZERO, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_import
            (term_id, programme_id, source_label, file_name, sha256,
             imported_by, status)
        VALUES ((SELECT term_id FROM exam.result_import WHERE result_import_id = %s),
                (SELECT programme_id FROM exam.result_import WHERE result_import_id = %s),
                'MAKAUT', 'bad-status.xlsx', %s, %s, 'unknown')
        """,
        (RESULT_IMPORT, RESULT_IMPORT, SHA_ZERO, P1),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_import
            (term_id, programme_id, source_label, file_name, sha256,
             imported_by)
        VALUES ((SELECT term_id FROM exam.result_import WHERE result_import_id = %s),
                (SELECT programme_id FROM exam.result_import WHERE result_import_id = %s),
                'MAKAUT', 'duplicate.xlsx', %s, %s)
        """,
        (RESULT_IMPORT, RESULT_IMPORT, SHA_ONE, P1),
        contains="duplicate key",
    )


def test_result_set_publication_gate(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.result_set
            (term_id, programme_id, batch_id, exam_label, status)
        VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                %s, 'Unattributed publication', 'published')
        """,
        (RESULT_SET, RESULT_SET, BATCH),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_set
            (term_id, programme_id, batch_id, exam_label, status,
             approved_by)
        VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                %s, 'Half attribution', 'published', %s)
        """,
        (RESULT_SET, RESULT_SET, BATCH, P1),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exam.result_set
                (term_id, programme_id, batch_id, exam_label, status,
                 external_publication_ref)
            VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                    (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                    %s, 'External publication', 'published',
                    'WBMAKAUT/2026/001')
            """,
            (RESULT_SET, RESULT_SET, BATCH),
        )
        cur.execute(
            """
            INSERT INTO exam.result_set
                (term_id, programme_id, batch_id, exam_label, status,
                 approved_by, approved_at)
            VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                    (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                    %s, 'Internal publication', 'published', %s, now())
            """,
            (RESULT_SET, RESULT_SET, BATCH, P1),
        )


def test_result_set_publication_cannot_precede_approval(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.result_set
            (term_id, programme_id, batch_id, exam_label, status,
             approved_by, approved_at, published_at)
        VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                %s, 'Backdated publication', 'approved', %s, now(),
                now() - interval '1 hour')
        """,
        (RESULT_SET, RESULT_SET, BATCH, P1),
        contains="check",
    )


def test_result_set_uniqueness_treats_a_null_batch_as_equal(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exam.result_set
                (term_id, programme_id, batch_id, exam_label, result_type)
            VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                    (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                    NULL, 'Cross-batch set', 'regular')
            """,
            (RESULT_SET, RESULT_SET),
        )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_set
            (term_id, programme_id, batch_id, exam_label, result_type)
        VALUES ((SELECT term_id FROM exam.result_set WHERE result_set_id = %s),
                (SELECT programme_id FROM exam.result_set WHERE result_set_id = %s),
                NULL, 'Cross-batch set', 'regular')
        """,
        (RESULT_SET, RESULT_SET),
        contains="duplicate key",
    )


def test_result_record_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    result_set_two = "bb02bb02-bb02-bb02-bb02-bb02bb02bb02"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exam.result_set
                (result_set_id, term_id, programme_id, batch_id, exam_label)
            SELECT %s, term_id, programme_id, batch_id, 'Rule checks'
            FROM exam.result_set WHERE result_set_id = %s
            """,
            (result_set_two, RESULT_SET),
        )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_record
            (student_id, course_version_id, course_offering_id, result_set_id,
             attempt_no, year_of_study)
        VALUES ((SELECT student_id FROM exam.result_record
                 WHERE result_record_id = %s),
                (SELECT course_version_id FROM exam.result_record
                 WHERE result_record_id = %s),
                (SELECT course_offering_id FROM exam.result_record
                 WHERE result_record_id = %s),
                %s, 1, 3)
        """,
        (RESULT_RECORD_ONE, RESULT_RECORD_ONE, RESULT_RECORD_ONE, RESULT_SET),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_record
            (student_id, course_version_id, result_set_id, attempt_no,
             year_of_study)
        VALUES ((SELECT student_id FROM exam.result_record
                 WHERE result_record_id = %s),
                (SELECT course_version_id FROM exam.result_record
                 WHERE result_record_id = %s),
                %s, 0, 3)
        """,
        (RESULT_RECORD_TWO, RESULT_RECORD_TWO, result_set_two),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_record
            (student_id, course_version_id, result_set_id, attempt_no,
             year_of_study, status)
        VALUES ((SELECT student_id FROM exam.result_record
                 WHERE result_record_id = %s),
                (SELECT course_version_id FROM exam.result_record
                 WHERE result_record_id = %s),
                %s, 2, 6, 'unknown')
        """,
        (RESULT_RECORD_TWO, RESULT_RECORD_TWO, result_set_two),
        contains="check",
    )


def test_result_revision_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.result_revision
            (result_record_id, revision_no, total_marks)
        VALUES (%s, 1, 10.00)
        """,
        (RESULT_RECORD_ONE,),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_revision
            (result_record_id, revision_no, total_marks)
        VALUES (%s, 0, 10.00)
        """,
        (RESULT_RECORD_TWO,),
        contains="check",
    )

    for column, value in (
        ("grade", "'Z'"),
        ("grade_point", "10.50"),
        ("total_marks", "-1.00"),
        ("result_status", "'Q'"),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO exam.result_revision
                (result_record_id, revision_no, {column})
            VALUES (%s, 2, {value})
            """,
            (RESULT_RECORD_TWO,),
            contains="check",
        )


def test_published_result_revision_is_sealed(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        UPDATE exam.result_revision SET cia_total = 31.00
        WHERE result_revision_id = %s
        """,
        (RESULT_REVISION_ONE,),
        contains="immutable",
    )

    expect_error(
        conn,
        "DELETE FROM exam.result_revision WHERE result_revision_id = %s",
        (RESULT_REVISION_ONE,),
        contains="immutable",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE exam.result_revision SET grade = 'D'
            WHERE result_revision_id = %s
            """,
            (RESULT_REVISION_TWO,),
        )


def test_result_input_rules_and_append_only_seal(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.result_input
            (result_revision_id, component_code, marks_used,
             max_marks_snapshot)
        VALUES (%s, 'CIA1', 10.00, 40.00)
        """,
        (RESULT_REVISION_ONE,),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_input
            (result_revision_id, component_code, marks_used,
             max_marks_snapshot)
        VALUES (%s, 'ESE', -1.00, 60.00)
        """,
        (RESULT_REVISION_ONE,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.result_input
            (result_revision_id, component_code, marks_used,
             max_marks_snapshot)
        VALUES (%s, 'ESE', 45.00, 0.00)
        """,
        (RESULT_REVISION_ONE,),
        contains="check",
    )

    expect_error(
        conn,
        """
        UPDATE exam.result_input SET marks_used = 31.00
        WHERE result_input_id = %s
        """,
        (RESULT_INPUT,),
        contains="append-only",
    )

    expect_error(
        conn,
        "DELETE FROM exam.result_input WHERE result_input_id = %s",
        (RESULT_INPUT,),
        contains="append-only",
    )


def test_grade_card_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 1)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 0)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no, sgpa, is_current)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 2, 10.50, FALSE)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no, credits_registered,
             credits_earned, is_current)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 2, 20.0, 21.0, FALSE)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no, status, is_current)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 2, 'unknown', FALSE)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card
            (student_id, term_id, version_no, is_current)
        VALUES ((SELECT student_id FROM exam.grade_card
                 WHERE grade_card_id = %s),
                (SELECT term_id FROM exam.grade_card
                 WHERE grade_card_id = %s), 2, TRUE)
        """,
        (GRADE_CARD, GRADE_CARD),
        contains="duplicate key",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exam.grade_card
                (student_id, term_id, version_no, is_current)
            VALUES ((SELECT student_id FROM exam.grade_card
                     WHERE grade_card_id = %s),
                    (SELECT term_id FROM exam.grade_card
                     WHERE grade_card_id = %s), 2, FALSE)
            """,
            (GRADE_CARD, GRADE_CARD),
        )


def test_grade_card_result_rules_and_append_only_seal(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card_result
            (grade_card_id, result_record_id, result_revision_id)
        VALUES (%s, %s, %s)
        """,
        (GRADE_CARD, RESULT_RECORD_ONE, RESULT_REVISION_ONE),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO exam.grade_card_result
            (grade_card_id, result_record_id, result_revision_id)
        VALUES (%s, %s, %s)
        """,
        (GRADE_CARD, RESULT_RECORD_TWO, RESULT_REVISION_ONE),
        contains="does not belong to result record",
    )

    expect_error(
        conn,
        """
        UPDATE exam.grade_card_result SET included = FALSE
        WHERE grade_card_result_id = %s
        """,
        (GRADE_CARD_RESULT,),
        contains="append-only",
    )

    expect_error(
        conn,
        "DELETE FROM exam.grade_card_result "
        "WHERE grade_card_result_id = %s",
        (GRADE_CARD_RESULT,),
        contains="append-only",
    )


def test_notice_identity_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO doc.notice (notice_no, category)
        VALUES ('bcrec/not/2026/001', 'academic')
        """,
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice (notice_no, category)
        VALUES (%s, 'academic')
        """,
        ("N" * 51,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice (notice_no, category)
        VALUES ('BCREC/NOT/2026/002', 'sports')
        """,
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice (notice_no, status)
        VALUES ('BCREC/NOT/2026/002', 'unknown')
        """,
        contains="check",
    )


def test_notice_version_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown)
        VALUES (%s, 1, 'Duplicate', 'Body')
        """,
        (NOTICE,),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown)
        VALUES (%s, 0, 'Zero version', 'Body')
        """,
        (NOTICE,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown)
        VALUES (%s, 2, %s, 'Body')
        """,
        (NOTICE, "T" * 301),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown)
        VALUES (%s, 2, 'Long body', %s)
        """,
        (NOTICE, "B" * 20001),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown, effective_from,
             effective_to)
        VALUES (%s, 2, 'Bad window', 'Body', now(), now())
        """,
        (NOTICE,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown, status)
        VALUES (%s, 2, 'Bad status', 'Body', 'unknown')
        """,
        (NOTICE,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_version_id, notice_id, version_no, title, body_markdown,
             supersedes_version_id)
        VALUES (%s, %s, 2, 'Self supersede', 'Body', %s)
        """,
        ("bb01bb01-bb01-bb01-bb01-bb01bb01bb01", NOTICE,
         "bb01bb01-bb01-bb01-bb01-bb01bb01bb01"),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_version
            (notice_id, version_no, title, body_markdown, status)
        VALUES (%s, 2, 'Unscheduled', 'Body', 'scheduled')
        """,
        (NOTICE,),
        contains="check",
    )


def test_notice_audience_rules(
    conn: psycopg.Connection,
    w5_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO doc.notice_audience
            (notice_version_id, audience_type, programme_id)
        VALUES (%s, 'programme', %s)
        """,
        (NOTICE_VERSION, PROGRAMME),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_audience
            (notice_version_id, audience_type)
        VALUES (%s, 'class')
        """,
        (NOTICE_VERSION,),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO doc.notice_audience
            (notice_version_id, audience_type)
        VALUES (%s, 'programme')
        """,
        (NOTICE_VERSION,),
        contains="check",
    )

    # DOC-06 lists audience_type=person but has no person_id column; the
    # documented target rule therefore rejects every person audience.
    expect_error(
        conn,
        """
        INSERT INTO doc.notice_audience
            (notice_version_id, audience_type)
        VALUES (%s, 'person')
        """,
        (NOTICE_VERSION,),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO doc.notice_audience
                (notice_version_id, audience_type)
            VALUES (%s, 'all')
            """,
            (NOTICE_VERSION,),
        )
        cur.execute(
            """
            INSERT INTO doc.notice_audience
                (notice_version_id, audience_type, batch_id)
            VALUES (%s, 'batch', %s)
            """,
            (NOTICE_VERSION, BATCH),
        )
