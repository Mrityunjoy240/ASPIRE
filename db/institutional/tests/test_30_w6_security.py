"""W6 security posture: chunk inheritance, person-own conversations, deny-by-default."""

from __future__ import annotations

import psycopg

from w1a_support import P1, TERM, expect_error, w1a_base
from w1b_support import PROGRAMME, w1b_base
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
    VERSION_PUBLIC,
    w6_base,
)

APP_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)

OTHER_CIP_TABLES = (
    "cip.call_session",
    "cip.message",
    "cip.retrieval_log",
    "cip.retrieval_hit",
    "cip.citation",
    "cip.feedback",
    "cip.escalation",
    "cip.eval_case",
    "cip.eval_run",
    "cip.eval_result",
)


def _set_person(cur: psycopg.Cursor, person_id: str | None) -> None:
    cur.execute(
        "SELECT set_config('app.person_id', %s, true)",
        (person_id or "",),
    )


def _ids(cur: psycopg.Cursor, table: str, column: str) -> list[str]:
    cur.execute(f"SELECT {column}::text FROM {table} ORDER BY {column}")
    return [row[0] for row in cur.fetchall()]


def test_chunk_classification_is_inherited(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")

        _set_person(cur, None)
        assert _ids(cur, "knowledge.document_chunk", "chunk_id") == [
            CHUNK_PUBLIC
        ], "an unauthenticated session sees only public chunks"

        for person in (P1, P3, P4):
            _set_person(cur, person)
            assert _ids(cur, "knowledge.document_chunk", "chunk_id") == [
                CHUNK_PUBLIC,
                CHUNK_INTERNAL,
            ], "an authenticated session sees P and I chunks"

        assert CHUNK_CONFIDENTIAL not in _ids(
            cur, "knowledge.document_chunk", "chunk_id"
        ), "the confidential arm waits for A-01"

        cur.execute("RESET ROLE")


def test_conversation_person_own_policy(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")

        _set_person(cur, P3)
        assert _ids(cur, "cip.conversation", "conversation_id") == [
            CONVERSATION_P3
        ]

        _set_person(cur, P4)
        assert _ids(cur, "cip.conversation", "conversation_id") == [
            CONVERSATION_P4
        ]

        _set_person(cur, P1)
        assert _ids(cur, "cip.conversation", "conversation_id") == []

        _set_person(cur, None)
        assert _ids(cur, "cip.conversation", "conversation_id") == [], (
            "anonymous rows are visible to no application role"
        )
        assert CONVERSATION_ANON not in _ids(
            cur, "cip.conversation", "conversation_id"
        )

        cur.execute("RESET ROLE")


def test_every_other_w6_table_is_deny_by_default(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        _set_person(cur, P3)

        for table in OTHER_CIP_TABLES:
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == 0, table

        cur.execute("SELECT count(*) FROM knowledge.ingestion_run")
        assert cur.fetchone()[0] == 0

        cur.execute("RESET ROLE")


def test_app_erp_cannot_read_w6_tables(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        _set_person(cur, P1)
        for table in (
            "knowledge.document_chunk",
            "knowledge.ingestion_run",
            "cip.conversation",
            "cip.call_session",
            "cip.message",
            "cip.retrieval_log",
            "cip.retrieval_hit",
            "cip.citation",
            "cip.feedback",
            "cip.escalation",
            "cip.eval_case",
            "cip.eval_run",
            "cip.eval_result",
        ):
            expect_error(
                conn,
                f"SELECT count(*) FROM {table}",
                contains="permission denied",
            )
        cur.execute("RESET ROLE")


def test_app_cip_writes_are_deny_by_default(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        _set_person(cur, P3)

        expect_error(
            conn,
            "INSERT INTO cip.conversation (person_id) VALUES (%s)",
            (P3,),
            contains="row-level security",
        )

        expect_error(
            conn,
            """
            INSERT INTO knowledge.document_chunk
                (document_version_id, sequence_no, chunk_text, token_count,
                 text_hash)
            VALUES (%s, 5, 'Blocked chunk.', 3, %s)
            """,
            (VERSION_PUBLIC, "9" * 64),
            contains="row-level security",
        )

        expect_error(
            conn,
            "INSERT INTO knowledge.ingestion_run (source_type) "
            "VALUES ('file_upload')",
            contains="row-level security",
        )

        cur.execute(
            "UPDATE cip.conversation SET outcome = 'abandoned' "
            "WHERE conversation_id = %s RETURNING outcome",
            (CONVERSATION_P3,),
        )
        assert cur.fetchall() == [], (
            "no UPDATE policy means a visible row still cannot be changed"
        )

        expect_error(
            conn,
            "DELETE FROM cip.conversation WHERE conversation_id = %s",
            (CONVERSATION_P3,),
            contains="permission denied",
        )

        cur.execute("RESET ROLE")


def test_owner_roles_see_every_w6_row(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE owner_knowledge")
        for table, expected in (
            ("knowledge.document_chunk", 3),
            ("knowledge.ingestion_run", 1),
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")

        cur.execute("SET LOCAL ROLE owner_cip")
        for table, expected in (
            ("cip.conversation", 3),
            ("cip.call_session", 1),
            ("cip.message", 4),
            ("cip.retrieval_log", 1),
            ("cip.retrieval_hit", 1),
            ("cip.citation", 1),
            ("cip.feedback", 1),
            ("cip.escalation", 1),
            ("cip.eval_case", 1),
            ("cip.eval_run", 1),
            ("cip.eval_result", 1),
        ):
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] == expected, table
        cur.execute("RESET ROLE")


def test_w6_trigger_functions_are_not_executable_by_application_roles(
    conn: psycopg.Connection,
    w6_base,
) -> None:
    protection_function = "knowledge.enforce_chunk_source_classification()"
    with conn.cursor() as cur:
        for role in APP_ROLES:
            cur.execute(
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
                (role, protection_function),
            )
            assert cur.fetchone()[0] is False, role

        cur.execute("SET LOCAL ROLE app_cip")
        _set_person(cur, P1)
        expect_error(
            conn,
            f"SELECT {protection_function}",
            contains="permission denied",
        )
        cur.execute("RESET ROLE")

        # The classification helper is deliberately callable by the ingestion
        # service only (app_cip); every other application role is excluded.
        cur.execute(
            "SELECT has_function_privilege('app_cip', "
            "'doc.classification_of(uuid)', 'EXECUTE')"
        )
        assert cur.fetchone()[0] is True
        for role in APP_ROLES:
            if role == "app_cip":
                continue
            cur.execute(
                "SELECT has_function_privilege(%s, "
                "'doc.classification_of(uuid)', 'EXECUTE')",
                (role,),
            )
            assert cur.fetchone()[0] is False, role
