"""W6 rule enforcement: chunk provenance, CIP integrity, and append-only seals."""

from __future__ import annotations

import psycopg

from w1a_support import ORG_CHILD, P1, expect_error, w1a_base
from w1b_support import w1b_base
from w2_support import P3, P4, w2_base
from w3_support import w3_base
from w4_support import w4_base
from w5_support import w5_base
from w6_support import (
    CALL_SESSION,
    CHUNK_CONFIDENTIAL,
    CHUNK_INTERNAL,
    CHUNK_PUBLIC,
    CITATION,
    CONVERSATION_ANON,
    CONVERSATION_P3,
    CONVERSATION_P4,
    ESCALATION,
    EVAL_CASE,
    EVAL_RESULT,
    EVAL_RUN,
    FEEDBACK,
    INGESTION_RUN,
    MESSAGE_ANON_USER,
    MESSAGE_P3_ASSISTANT,
    MESSAGE_P3_USER,
    MESSAGE_P4_USER,
    RETRIEVAL_HIT,
    RETRIEVAL_LOG,
    TEXT_HASH_PUBLIC,
    VERSION_CONFIDENTIAL,
    VERSION_GROUP,
    VERSION_PUBLIC,
    VERSION_RESTRICTED,
    w6_base,
)


def test_chunk_rejects_restricted_source_documents(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 0, 'Restricted chunk.', 3, %s)
        """,
        (VERSION_RESTRICTED, "9" * 64),
        contains="classified r",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 0, 'Group chunk.', 3, %s)
        """,
        (VERSION_GROUP, "9" * 64),
        contains="classified g",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 0, 'Missing source.', 3, %s)
        """,
        ("cd00cd00-cd00-cd00-cd00-cd00cd00cd00", "9" * 64),
        contains="not found",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO knowledge.document_chunk
                (document_version_id, sequence_no, chunk_text, token_count,
                 text_hash)
            VALUES (%s, 1, 'Confidential chunk is allowed to exist.', 5, %s)
            """,
            (VERSION_CONFIDENTIAL, "9" * 64),
        )


def test_chunk_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 0, 'Duplicate sequence.', 3, %s)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="duplicate key",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, -1, 'Negative sequence.', 3, %s)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 2, '', 3, %s)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 2, %s, 3, %s)
        """,
        (VERSION_PUBLIC, "x" * 20001, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash, page_from)
        VALUES (%s, 2, 'Bad page.', 3, %s, 0)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash, page_from, page_to)
        VALUES (%s, 2, 'Bad page window.', 3, %s, 5, 4)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 2, 'Zero tokens.', 0, %s)
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash)
        VALUES (%s, 2, 'Short hash.', 3, %s)
        """,
        (VERSION_PUBLIC, "9" * 63),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash, language)
        VALUES (%s, 2, 'Bad language.', 3, %s, 'fr')
        """,
        (VERSION_PUBLIC, "9" * 64),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash, chunking_profile)
        VALUES (%s, 2, 'Bad profile.', 3, %s, %s)
        """,
        (VERSION_PUBLIC, "9" * 64, "p" * 51),
        contains="check",
    )

    expect_error(
        conn,
        """
        INSERT INTO knowledge.document_chunk
            (document_version_id, sequence_no, chunk_text, token_count,
             text_hash, section_path)
        VALUES (%s, 2, 'Long path.', 3, %s, %s)
        """,
        (VERSION_PUBLIC, "9" * 64, "s" * 1001),
        contains="check",
    )


def test_chunk_is_append_only(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        "UPDATE knowledge.document_chunk SET chunk_text = 'edited' "
        "WHERE chunk_id = %s",
        (CHUNK_PUBLIC,),
        contains="append-only",
    )
    expect_error(
        conn,
        "DELETE FROM knowledge.document_chunk WHERE chunk_id = %s",
        (CHUNK_INTERNAL,),
        contains="append-only",
    )


def test_ingestion_run_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO knowledge.ingestion_run
            (source_type, started_at, finished_at, status)
        VALUES ('file_upload', now(), now() - interval '1 hour', 'completed')
        """,
        contains="check",
    )

    for column in (
        "documents_seen",
        "versions_created",
        "chunks_created",
        "embeddings_created",
        "error_count",
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO knowledge.ingestion_run (source_type, {column})
            VALUES ('file_upload', -1)
            """,
            contains="check",
        )

    expect_error(
        conn,
        "INSERT INTO knowledge.ingestion_run (source_type, status) "
        "VALUES ('file_upload', 'unknown')",
        contains="check",
    )
    expect_error(
        conn,
        "INSERT INTO knowledge.ingestion_run (source_type) "
        "VALUES ('ftp')",
        contains="check",
    )

    for column, value in (
        ("source_uri", "u" * 2001),
        ("error_summary", "e" * 5001),
        ("parser_version", "p" * 51),
        ("ocr_engine", "o" * 51),
        ("chunker_version", "c" * 51),
        ("embedding_model", "m" * 101),
    ):
        expect_error(
            conn,
            f"INSERT INTO knowledge.ingestion_run (source_type, {column}) "
            "VALUES ('file_upload', %s)",
            (value,),
            contains="check",
        )


def test_conversation_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.conversation (person_id, started_at, ended_at)
        VALUES (%s, now(), now() - interval '1 hour')
        """,
        (P1,),
        contains="check",
    )
    for column, value in (
        ("channel", "sms"),
        ("outcome", "unknown"),
        ("language", "fr"),
    ):
        expect_error(
            conn,
            f"INSERT INTO cip.conversation (person_id, {column}) "
            "VALUES (%s, %s)",
            (P1, value),
            contains="check",
        )


def test_call_session_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.call_session
            (conversation_id, provider, provider_call_id)
        VALUES (%s, 'test-provider', 'CALL-001')
        """,
        (CONVERSATION_P3,),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.call_session
            (conversation_id, provider, provider_call_id, duration_sec)
        VALUES (%s, 'other-provider', 'CALL-002', -1)
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    for column, value in (
        ("direction", "sideways"),
        ("status", "unknown"),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.call_session
                (conversation_id, provider, {column})
            VALUES (%s, 'other-provider', %s)
            """,
            (CONVERSATION_P3, value),
            contains="check",
        )
    for column in ("from_number_masked", "to_number_masked"):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.call_session
                (conversation_id, provider, {column})
            VALUES (%s, 'other-provider', %s)
            """,
            (CONVERSATION_P3, "1" * 21),
            contains="check",
        )
    expect_error(
        conn,
        """
        INSERT INTO cip.call_session
            (conversation_id, provider, recording_uri)
        VALUES (%s, 'other-provider', 'not-a-uri')
        """,
        (CONVERSATION_P3,),
        contains="check",
    )


def test_message_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.message (conversation_id, sequence_no, role)
        VALUES (%s, 1, 'user')
        """,
        (CONVERSATION_P3,),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.message (conversation_id, sequence_no, role)
        VALUES (%s, 0, 'user')
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.message (conversation_id, sequence_no, role)
        VALUES (%s, 3, 'narrator')
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.message
            (conversation_id, sequence_no, role, confidence)
        VALUES (%s, 3, 'user', 1.500)
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    for column, value in (
        ("latency_ms", -1),
        ("token_count", -1),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.message
                (conversation_id, sequence_no, role, {column})
            VALUES (%s, 3, 'user', %s)
            """,
            (CONVERSATION_P3, value),
            contains="check",
        )
    for column, value in (
        ("language", "fr"),
        ("intent_code", "i" * 51),
        ("model_name", "m" * 101),
        ("model_version", "v" * 51),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.message
                (conversation_id, sequence_no, role, {column})
            VALUES (%s, 3, 'user', %s)
            """,
            (CONVERSATION_P3, value),
            contains="check",
        )


def test_message_retrieval_tables_are_append_only(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    for table, id_column, row_id in (
        ("cip.message", "message_id", MESSAGE_P3_ASSISTANT),
        ("cip.retrieval_log", "retrieval_log_id", RETRIEVAL_LOG),
        ("cip.retrieval_hit", "retrieval_hit_id", RETRIEVAL_HIT),
        ("cip.citation", "citation_id", CITATION),
    ):
        expect_error(
            conn,
            f"UPDATE {table} SET created_at = created_at "
            f"WHERE {id_column} = %s",
            (row_id,),
            contains="append-only",
        )
        expect_error(
            conn,
            f"DELETE FROM {table} WHERE {id_column} = %s",
            (row_id,),
            contains="append-only",
        )


def test_retrieval_log_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log (message_id, query_text, top_k)
        VALUES (%s, 'query', 0)
        """,
        (MESSAGE_P4_USER,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log (message_id, query_text, result_count)
        VALUES (%s, 'query', -1)
        """,
        (MESSAGE_P4_USER,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log (message_id, query_text, latency_ms)
        VALUES (%s, 'query', -1)
        """,
        (MESSAGE_P4_USER,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log (message_id, query_text, strategy)
        VALUES (%s, 'query', 'magic')
        """,
        (MESSAGE_P4_USER,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log (message_id, query_text)
        VALUES (%s, %s)
        """,
        (MESSAGE_P4_USER, "q" * 2001),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_log
            (message_id, query_text, normalized_query)
        VALUES (%s, 'query', %s)
        """,
        (MESSAGE_P4_USER, "n" * 2001),
        contains="check",
    )


def test_retrieval_hit_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_hit (retrieval_log_id, chunk_id, rank)
        VALUES (%s, %s, 1)
        """,
        (RETRIEVAL_LOG, CHUNK_INTERNAL),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.retrieval_hit (retrieval_log_id, chunk_id, rank)
        VALUES (%s, %s, 0)
        """,
        (RETRIEVAL_LOG, CHUNK_INTERNAL),
        contains="check",
    )


def test_citation_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.citation
            (message_id, chunk_id, document_version_id, page_from, page_to)
        VALUES (%s, %s, %s, 1, 1)
        """,
        (MESSAGE_P3_ASSISTANT, CHUNK_PUBLIC, VERSION_PUBLIC),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.citation
            (message_id, chunk_id, page_from, page_to)
        VALUES (%s, %s, 5, 4)
        """,
        (MESSAGE_P3_ASSISTANT, CHUNK_INTERNAL),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.citation (message_id, chunk_id, page_from)
        VALUES (%s, %s, 0)
        """,
        (MESSAGE_P3_ASSISTANT, CHUNK_INTERNAL),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.citation (message_id, chunk_id, confidence)
        VALUES (%s, %s, 1.500)
        """,
        (MESSAGE_P3_ASSISTANT, CHUNK_INTERNAL),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.citation (message_id, chunk_id, quote)
        VALUES (%s, %s, %s)
        """,
        (MESSAGE_P3_ASSISTANT, CHUNK_INTERNAL, "q" * 2001),
        contains="check",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cip.citation (message_id) VALUES (%s)
            """,
            (MESSAGE_P4_USER,),
        )
    expect_error(
        conn,
        "INSERT INTO cip.citation (message_id) VALUES (%s)",
        (MESSAGE_P4_USER,),
        contains="duplicate key",
    )


def test_feedback_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.feedback (message_id, person_id, rating)
        VALUES (%s, %s, 'down')
        """,
        (MESSAGE_P3_ASSISTANT, P3),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.feedback (message_id, person_id, rating)
        VALUES (%s, %s, 'sideways')
        """,
        (MESSAGE_P4_USER, P4),
        contains="check",
    )
    for column, value in (
        ("reason_code", "r" * 51),
        ("comment", "c" * 2001),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.feedback (message_id, person_id, rating, {column})
            VALUES (%s, %s, 'up', %s)
            """,
            (MESSAGE_P4_USER, P4, value),
            contains="check",
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cip.feedback (message_id, person_id, rating)
            VALUES (%s, %s, 'down'), (%s, NULL, 'up'), (%s, NULL, 'down')
            """,
            (MESSAGE_P4_USER, P4, MESSAGE_P4_USER, MESSAGE_P4_USER),
        )


def test_escalation_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.escalation
            (conversation_id, reason_code, created_at, resolved_at)
        VALUES (%s, 'no_answer', now(), now() - interval '1 hour')
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.escalation (conversation_id, reason_code, status)
        VALUES (%s, 'no_answer', 'unknown')
        """,
        (CONVERSATION_P3,),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.escalation (conversation_id, reason_code)
        VALUES (%s, %s)
        """,
        (CONVERSATION_P3, "r" * 51),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.escalation
            (conversation_id, reason_code, resolution_note)
        VALUES (%s, 'no_answer', %s)
        """,
        (CONVERSATION_P3, "n" * 2001),
        contains="check",
    )


def test_eval_case_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_case (case_code, question)
        VALUES ('eval-001', 'Duplicate code.')
        """,
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_case (case_code, question)
        VALUES ('EVAL-002', '')
        """,
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_case (case_code, question)
        VALUES ('EVAL-002', %s)
        """,
        ("q" * 2001,),
        contains="check",
    )
    for column, value in (
        ("category", "unknown"),
        ("language", "fr"),
    ):
        expect_error(
            conn,
            f"""
            INSERT INTO cip.eval_case (case_code, question, {column})
            VALUES ('EVAL-002', 'Question?', %s)
            """,
            (value,),
            contains="check",
        )
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_case (case_code, question, expected_citation)
        VALUES ('EVAL-002', 'Question?', %s)
        """,
        ("c" * 501,),
        contains="check",
    )
    expect_error(
        conn,
        "INSERT INTO cip.eval_case (case_code, question) VALUES (%s, 'Q?')",
        ("c" * 51,),
        contains="check",
    )


def test_eval_run_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_run (started_at, finished_at)
        VALUES (now(), now() - interval '1 hour')
        """,
        contains="check",
    )
    expect_error(
        conn,
        "INSERT INTO cip.eval_run (status) VALUES ('unknown')",
        contains="check",
    )
    for column, value in (
        ("corpus_version", "c" * 51),
        ("model_name", "m" * 101),
    ):
        expect_error(
            conn,
            f"INSERT INTO cip.eval_run ({column}) VALUES (%s)",
            (value,),
            contains="check",
        )


def test_eval_result_rules(conn: psycopg.Connection, w6_base) -> None:
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_result (eval_run_id, eval_case_id)
        VALUES (%s, %s)
        """,
        (EVAL_RUN, EVAL_CASE),
        contains="duplicate key",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_result
            (eval_run_id, eval_case_id, latency_ms)
        VALUES (%s, %s, -1)
        """,
        (EVAL_RUN, EVAL_CASE),
        contains="check",
    )
    expect_error(
        conn,
        """
        INSERT INTO cip.eval_result (eval_run_id, eval_case_id, notes)
        VALUES (%s, %s, %s)
        """,
        (EVAL_RUN, EVAL_CASE, "n" * 2001),
        contains="check",
    )


def test_fixture_identities_are_distinct(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    """Guard the fixture itself against silent duplication or missing rows."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM knowledge.document_chunk")
        assert cur.fetchone()[0] == 3
        cur.execute("SELECT count(*) FROM cip.conversation")
        assert cur.fetchone()[0] == 3
        cur.execute("SELECT count(*) FROM cip.message")
        assert cur.fetchone()[0] == 4
        cur.execute("SELECT person_id FROM cip.conversation WHERE conversation_id = %s", (CONVERSATION_ANON,))
        assert cur.fetchone()[0] is None
        for message_id in (MESSAGE_P3_USER, MESSAGE_P4_USER, MESSAGE_ANON_USER):
            cur.execute("SELECT count(*) FROM cip.message WHERE message_id = %s", (message_id,))
            assert cur.fetchone()[0] == 1
