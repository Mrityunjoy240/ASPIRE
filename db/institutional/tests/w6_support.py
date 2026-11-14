"""Shared baseline data for W6 knowledge chunks and CIP conversations.

Builds on :mod:`w5_base`: one completed ingestion run, three chunks (public,
internal, confidential), two restricted documents (R and G) with no chunks, one
conversation for each of two students, one anonymous conversation, and one row
in every remaining CIP table.
"""

from __future__ import annotations

import pytest

from w1a_support import (
    DOC_CONFIDENTIAL,
    DOC_INTERNAL,
    DOC_PUBLIC,
    ORG_CHILD,
    P1,
    VERSION_CONFIDENTIAL,
    VERSION_INTERNAL,
    VERSION_PUBLIC,
    w1a_base,
)
from w1b_support import w1b_base
from w2_support import P3, P4, w2_base
from w3_support import w3_base
from w4_support import w4_base
from w5_support import w5_base

INGESTION_RUN = "cc01cc01-cc01-cc01-cc01-cc01cc01cc01"
CHUNK_PUBLIC = "cc02cc02-cc02-cc02-cc02-cc02cc02cc02"
CHUNK_INTERNAL = "cc03cc03-cc03-cc03-cc03-cc03cc03cc03"
CHUNK_CONFIDENTIAL = "cc04cc04-cc04-cc04-cc04-cc04cc04cc04"

DOC_RESTRICTED = "cc10cc10-cc10-cc10-cc10-cc10cc10cc10"
DOC_GROUP = "cc11cc11-cc11-cc11-cc11-cc11cc11cc11"
VERSION_RESTRICTED = "cc12cc12-cc12-cc12-cc12-cc12cc12cc12"
VERSION_GROUP = "cc13cc13-cc13-cc13-cc13-cc13cc13cc13"

CONVERSATION_P3 = "cc20cc20-cc20-cc20-cc20-cc20cc20cc20"
CONVERSATION_P4 = "cc21cc21-cc21-cc21-cc21-cc21cc21cc21"
CONVERSATION_ANON = "cc22cc22-cc22-cc22-cc22-cc22cc22cc22"

CALL_SESSION = "cc30cc30-cc30-cc30-cc30-cc30cc30cc30"
MESSAGE_P3_USER = "cc31cc31-cc31-cc31-cc31-cc31cc31cc31"
MESSAGE_P3_ASSISTANT = "cc32cc32-cc32-cc32-cc32-cc32cc32cc32"
MESSAGE_P4_USER = "cc33cc33-cc33-cc33-cc33-cc33cc33cc33"
MESSAGE_ANON_USER = "cc34cc34-cc34-cc34-cc34-cc34cc34cc34"

RETRIEVAL_LOG = "cc40cc40-cc40-cc40-cc40-cc40cc40cc40"
RETRIEVAL_HIT = "cc41cc41-cc41-cc41-cc41-cc41cc41cc41"
CITATION = "cc42cc42-cc42-cc42-cc42-cc42cc42cc42"
FEEDBACK = "cc43cc43-cc43-cc43-cc43-cc43cc43cc43"
ESCALATION = "cc44cc44-cc44-cc44-cc44-cc44cc44cc44"

EVAL_CASE = "cc50cc50-cc50-cc50-cc50-cc50cc50cc50"
EVAL_RUN = "cc51cc51-cc51-cc51-cc51-cc51cc51cc51"
EVAL_RESULT = "cc52cc52-cc52-cc52-cc52-cc52cc52cc52"

TEXT_HASH_PUBLIC = "1" * 64
TEXT_HASH_INTERNAL = "2" * 64
TEXT_HASH_CONFIDENTIAL = "3" * 64


@pytest.fixture()
def w6_base(w5_base):
    conn = w5_base
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge.ingestion_run
                (ingestion_run_id, triggered_by, source_type, source_uri,
                 started_at, finished_at, status, documents_seen,
                 versions_created, chunks_created, embeddings_created,
                 error_count, parser_version, chunker_version)
            VALUES (%s, %s, 'file_upload', 's3://docs/batch-1/',
                    now() - interval '2 days', now() - interval '1 day',
                    'completed', 3, 0, 3, 0, 0, 'parser-1.0', 'chunker-1.0')
            """,
            (INGESTION_RUN, P1),
        )
        cur.execute(
            """
            INSERT INTO knowledge.document_chunk
                (chunk_id, document_version_id, ingestion_run_id, sequence_no,
                 chunk_text, section_path, page_from, page_to, token_count,
                 language, chunking_profile, text_hash)
            VALUES
                (%s, %s, %s, 0, 'The even semester begins as scheduled.',
                 '1. Calendar', 1, 1, 8, 'en', 'default', %s),
                (%s, %s, %s, 0, 'Internal staff guidance for the semester.',
                 '1. Guidance', 1, 2, 7, 'en', 'default', %s),
                (%s, %s, %s, 0, 'Restricted committee deliberation minutes.',
                 '1. Minutes', 1, 1, 6, 'en', 'default', %s)
            """,
            (
                CHUNK_PUBLIC, VERSION_PUBLIC, INGESTION_RUN, TEXT_HASH_PUBLIC,
                CHUNK_INTERNAL, VERSION_INTERNAL, INGESTION_RUN,
                TEXT_HASH_INTERNAL,
                CHUNK_CONFIDENTIAL, VERSION_CONFIDENTIAL, INGESTION_RUN,
                TEXT_HASH_CONFIDENTIAL,
            ),
        )

        cur.execute(
            """
            INSERT INTO doc.document
                (document_id, title, document_type, issuer_name, document_date,
                 classification)
            VALUES
                (%s, 'Restricted document', 'minutes', 'BCREC', current_date,
                 'R'),
                (%s, 'Group document', 'minutes', 'BCREC', current_date, 'G')
            """,
            (DOC_RESTRICTED, DOC_GROUP),
        )
        cur.execute(
            """
            INSERT INTO doc.document_version
                (document_version_id, document_id, version_no, file_uri,
                 mime_type, sha256, status)
            VALUES
                (%s, %s, 1, 's3://docs/restricted.pdf', 'application/pdf',
                 %s, 'draft'),
                (%s, %s, 1, 's3://docs/group.pdf', 'application/pdf',
                 %s, 'draft')
            """,
            (
                VERSION_RESTRICTED, DOC_RESTRICTED, "d" * 64,
                VERSION_GROUP, DOC_GROUP, "e" * 64,
            ),
        )

        cur.execute(
            """
            INSERT INTO cip.conversation
                (conversation_id, person_id, channel, language, started_at,
                 ended_at, outcome, escalation_flag, consent_recording)
            VALUES
                (%s, %s, 'web', 'en', now() - interval '4 hours',
                 now() - interval '3 hours', 'resolved', FALSE, NULL),
                (%s, %s, 'voice', 'en', now() - interval '3 hours',
                 now() - interval '2 hours', 'escalated', TRUE, TRUE),
                (%s, NULL, 'kiosk', 'en', now() - interval '1 hour',
                 NULL, 'open', FALSE, NULL)
            """,
            (
                CONVERSATION_P3, P3,
                CONVERSATION_P4, P4,
                CONVERSATION_ANON,
            ),
        )
        cur.execute(
            """
            INSERT INTO cip.call_session
                (call_session_id, conversation_id, provider, provider_call_id,
                 direction, from_number_masked, to_number_masked, started_at,
                 ended_at, duration_sec, recording_consent, status)
            VALUES (%s, %s, 'test-provider', 'CALL-001', 'inbound',
                    'XXXXXX1234', 'XXXXXX5678', now() - interval '3 hours',
                    now() - interval '2 hours', 3600, TRUE, 'completed')
            """,
            (CALL_SESSION, CONVERSATION_P4),
        )
        cur.execute(
            """
            INSERT INTO cip.message
                (message_id, conversation_id, sequence_no, role, content_text,
                 content_redacted, language, intent_code, confidence,
                 model_name, model_version, latency_ms, token_count)
            VALUES
                (%s, %s, 1, 'user',
                 'When does the even semester begin?',
                 'When does the term begin?', 'en', NULL, NULL, NULL, NULL,
                 NULL, NULL),
                (%s, %s, 2, 'assistant',
                 'The even semester begins as scheduled.',
                 'The term begins as scheduled.', 'en',
                 'academic_calendar', 0.950, 'test-model', '1.0', 120, 10),
                (%s, %s, 1, 'user',
                 'I cannot find my result.',
                 'I cannot find my result.', 'en', NULL, NULL, NULL, NULL,
                 NULL, NULL),
                (%s, %s, 1, 'user',
                 'What are the office hours?',
                 'What are the office hours?', 'en', NULL, NULL, NULL, NULL,
                 NULL, NULL)
            """,
            (
                MESSAGE_P3_USER, CONVERSATION_P3,
                MESSAGE_P3_ASSISTANT, CONVERSATION_P3,
                MESSAGE_P4_USER, CONVERSATION_P4,
                MESSAGE_ANON_USER, CONVERSATION_ANON,
            ),
        )
        cur.execute(
            """
            INSERT INTO cip.retrieval_log
                (retrieval_log_id, message_id, query_text, normalized_query,
                 strategy, filters_json, top_k, latency_ms, result_count,
                 fallback_used)
            VALUES (%s, %s, 'when does the even semester begin?',
                    'when does the even semester begin?', 'hybrid', '{}',
                    5, 50, 1, FALSE)
            """,
            (RETRIEVAL_LOG, MESSAGE_P3_ASSISTANT),
        )
        cur.execute(
            """
            INSERT INTO cip.retrieval_hit
                (retrieval_hit_id, retrieval_log_id, chunk_id, rank,
                 vector_score, lexical_score, rerank_score)
            VALUES (%s, %s, %s, 1, 0.900000, 0.500000, 0.800000)
            """,
            (RETRIEVAL_HIT, RETRIEVAL_LOG, CHUNK_PUBLIC),
        )
        cur.execute(
            """
            INSERT INTO cip.citation
                (citation_id, message_id, chunk_id, document_version_id,
                 page_from, page_to, quote, confidence, displayed)
            VALUES (%s, %s, %s, %s, 1, 1,
                    'The even semester begins as scheduled.', 0.900, TRUE)
            """,
            (CITATION, MESSAGE_P3_ASSISTANT, CHUNK_PUBLIC, VERSION_PUBLIC),
        )
        cur.execute(
            """
            INSERT INTO cip.feedback
                (feedback_id, message_id, person_id, rating, reason_code,
                 comment)
            VALUES (%s, %s, %s, 'up', 'helpful', 'Clear answer.')
            """,
            (FEEDBACK, MESSAGE_P3_ASSISTANT, P3),
        )
        cur.execute(
            """
            INSERT INTO cip.escalation
                (escalation_id, conversation_id, message_id,
                 assigned_org_unit_id, reason_code, status)
            VALUES (%s, %s, %s, %s, 'no_answer', 'open')
            """,
            (ESCALATION, CONVERSATION_P4, MESSAGE_P4_USER, ORG_CHILD),
        )
        cur.execute(
            """
            INSERT INTO cip.eval_case
                (eval_case_id, case_code, category, question, expected_answer,
                 expected_citation, language, is_active)
            VALUES (%s, 'EVAL-001', 'golden',
                    'When does the even semester begin?',
                    'The even semester begins as scheduled.',
                    'Public document p.1', 'en', TRUE)
            """,
            (EVAL_CASE,),
        )
        cur.execute(
            """
            INSERT INTO cip.eval_run
                (eval_run_id, created_by, started_at, finished_at,
                 corpus_version, model_name, status)
            VALUES (%s, %s, now() - interval '1 day',
                    now() - interval '23 hours', 'v1', 'test-model',
                    'completed')
            """,
            (EVAL_RUN, P1),
        )
        cur.execute(
            """
            INSERT INTO cip.eval_result
                (eval_result_id, eval_run_id, eval_case_id, actual_answer,
                 citation_correct, answer_correct, latency_ms, pass, notes)
            VALUES (%s, %s, %s, 'The even semester begins as scheduled.',
                    TRUE, TRUE, 100, TRUE, 'matched')
            """,
            (EVAL_RESULT, EVAL_RUN, EVAL_CASE),
        )

    try:
        yield conn
    finally:
        conn.rollback()
