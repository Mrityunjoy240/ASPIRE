"""Shared baseline data for W5 exam results and notices.

Builds on :mod:`w4_base`: one result import, one approved result set, one
published result record/revision for student one, one draft revision for
student two, a result-input trace, a published grade card with one composition
row, and one published notice with a programme audience.
"""

from __future__ import annotations

import pytest

from w1a_support import ORG_CHILD, P1, TERM, w1a_base
from w1b_support import BATCH, COURSE_VERSION, OFFERING, PROGRAMME, w1b_base
from w2_support import STUDENT_ONE, STUDENT_TWO, w2_base
from w3_support import w3_base
from w4_support import MARK_VERSION_ONE, w4_base

SHA_ONE = "a" * 64

RESULT_IMPORT = "aa01aa01-aa01-aa01-aa01-aa01aa01aa01"
RESULT_SET = "aa02aa02-aa02-aa02-aa02-aa02aa02aa02"
RESULT_RECORD_ONE = "aa03aa03-aa03-aa03-aa03-aa03aa03aa03"
RESULT_RECORD_TWO = "aa04aa04-aa04-aa04-aa04-aa04aa04aa04"
RESULT_REVISION_ONE = "aa05aa05-aa05-aa05-aa05-aa05aa05aa05"
RESULT_REVISION_TWO = "aa06aa06-aa06-aa06-aa06-aa06aa06aa06"
RESULT_INPUT = "aa07aa07-aa07-aa07-aa07-aa07aa07aa07"
GRADE_CARD = "aa08aa08-aa08-aa08-aa08-aa08aa08aa08"
GRADE_CARD_RESULT = "aa09aa09-aa09-aa09-aa09-aa09aa09aa09"
NOTICE = "aa10aa10-aa10-aa10-aa10-aa10aa10aa10"
NOTICE_VERSION = "aa11aa11-aa11-aa11-aa11-aa11aa11aa11"
NOTICE_AUDIENCE = "aa12aa12-aa12-aa12-aa12-aa12aa12aa12"


@pytest.fixture()
def w5_base(w4_base):
    conn = w4_base
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exam.result_import
                (result_import_id, term_id, programme_id, source_label,
                 file_name, sha256, imported_by, row_count, error_count, status)
            VALUES (%s, %s, %s, 'MAKAUT', 'even-2025-26.xlsx', %s, %s,
                    2, 0, 'imported')
            """,
            (RESULT_IMPORT, TERM, PROGRAMME, SHA_ONE, P1),
        )
        cur.execute(
            """
            INSERT INTO exam.result_set
                (result_set_id, term_id, programme_id, batch_id, import_id,
                 exam_label, result_type, status, approved_by, approved_at)
            VALUES (%s, %s, %s, %s, %s, 'Even 2025-26', 'regular', 'approved',
                    %s, now() - interval '2 hours')
            """,
            (RESULT_SET, TERM, PROGRAMME, BATCH, RESULT_IMPORT, P1),
        )
        cur.execute(
            """
            INSERT INTO exam.result_record
                (result_record_id, student_id, course_version_id,
                 course_offering_id, result_set_id, attempt_no, is_backlog,
                 year_of_study, current_revision_no, status)
            VALUES (%s, %s, %s, %s, %s, 1, FALSE, 3, 1, 'pass'),
                   (%s, %s, %s, %s, %s, 1, FALSE, 3, 1, 'fail')
            """,
            (
                RESULT_RECORD_ONE, STUDENT_ONE, COURSE_VERSION, OFFERING,
                RESULT_SET,
                RESULT_RECORD_TWO, STUDENT_TWO, COURSE_VERSION, OFFERING,
                RESULT_SET,
            ),
        )
        cur.execute(
            """
            INSERT INTO exam.result_revision
                (result_revision_id, result_record_id, revision_no, cia_total,
                 ese_total, total_marks, grade, grade_point, result_status,
                 published_at, computed_by)
            VALUES (%s, %s, 1, 30.00, 46.00, 76.00, 'A', 8.00, 'P',
                    now() - interval '1 hour', %s),
                   (%s, %s, 1, 12.00, 18.00, 30.00, 'F', 0.00, 'X',
                    NULL, %s)
            """,
            (
                RESULT_REVISION_ONE, RESULT_RECORD_ONE, P1,
                RESULT_REVISION_TWO, RESULT_RECORD_TWO, P1,
            ),
        )
        cur.execute(
            """
            INSERT INTO exam.result_input
                (result_input_id, result_revision_id, mark_entry_version_id,
                 component_code, marks_used, max_marks_snapshot)
            VALUES (%s, %s, %s, 'CIA1', 30.00, 40.00)
            """,
            (RESULT_INPUT, RESULT_REVISION_ONE, MARK_VERSION_ONE),
        )
        cur.execute(
            """
            INSERT INTO exam.grade_card
                (grade_card_id, student_id, term_id, result_set_id, version_no,
                 sgpa, ygpa, cgpa, credits_registered, credits_earned, status,
                 published_at, is_current)
            VALUES (%s, %s, %s, %s, 1, 8.00, 8.00, 8.00, 22.0, 22.0,
                    'published', now() - interval '30 minutes', TRUE)
            """,
            (GRADE_CARD, STUDENT_ONE, TERM, RESULT_SET),
        )
        cur.execute(
            """
            INSERT INTO exam.grade_card_result
                (grade_card_result_id, grade_card_id, result_record_id,
                 result_revision_id, included)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            (GRADE_CARD_RESULT, GRADE_CARD, RESULT_RECORD_ONE, RESULT_REVISION_ONE),
        )

        cur.execute(
            """
            INSERT INTO doc.notice
                (notice_id, notice_no, category, issuing_org_unit_id,
                 owner_person_id, status)
            VALUES (%s, 'BCREC/NOT/2026/001', 'academic', %s, %s, 'active')
            """,
            (NOTICE, ORG_CHILD, P1),
        )
        cur.execute(
            """
            INSERT INTO doc.notice_version
                (notice_version_id, notice_id, version_no, title, body_markdown,
                 publish_at, effective_from, status, approved_by, approved_at)
            VALUES (%s, %s, 1, 'Even semester schedule',
                    'The even semester begins as scheduled.', now() - interval '1 hour',
                    now() - interval '1 hour', 'published', %s,
                    now() - interval '2 hours')
            """,
            (NOTICE_VERSION, NOTICE, P1),
        )
        cur.execute(
            """
            INSERT INTO doc.notice_audience
                (notice_audience_id, notice_version_id, audience_type,
                 programme_id)
            VALUES (%s, %s, 'programme', %s)
            """,
            (NOTICE_AUDIENCE, NOTICE_VERSION, PROGRAMME),
        )

    try:
        yield conn
    finally:
        conn.rollback()
