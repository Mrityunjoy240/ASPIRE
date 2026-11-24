"""W6 structural validation against the approved design."""

from __future__ import annotations

import re

import psycopg

from design import (
    DEFERRED_ENTITIES,
    TYPE_MAP,
    W6_ENTITIES,
    W6_IMPLEMENTED_ENTITIES,
    W6_TABLES,
    W6_TRIGGERS,
    documented_enum_checks,
    expected_columns,
    expected_primary_key,
    normalise_default,
)

APP_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)

DOCUMENTED_UNIQUES = {
    ("knowledge.document_chunk", "uq_document_chunk_version_profile_seq"):
        ("document_version_id", "chunking_profile", "sequence_no"),
    ("cip.call_session", "uq_call_session_provider"):
        ("provider", "provider_call_id"),
    ("cip.message", "uq_message_conversation_seq"):
        ("conversation_id", "sequence_no"),
    ("cip.retrieval_hit", "uq_retrieval_hit_rank"):
        ("retrieval_log_id", "rank"),
    ("cip.citation", "uq_citation_message_chunk_pages"):
        ("message_id", "chunk_id", "page_from", "page_to"),
    ("cip.eval_result", "uq_eval_result_run_case"):
        ("eval_run_id", "eval_case_id"),
}

DOCUMENTED_INDEXES = (
    ("knowledge.document_chunk", ("document_version_id", "sequence_no")),
    ("knowledge.document_chunk", ("language",)),
    ("knowledge.ingestion_run", ("started_at",)),
    ("knowledge.ingestion_run", ("status",)),
    ("cip.conversation", ("person_id", "started_at")),
    ("cip.conversation", ("channel", "started_at")),
    ("cip.call_session", ("conversation_id",)),
    ("cip.call_session", ("started_at",)),
    ("cip.message", ("conversation_id", "sequence_no")),
    ("cip.message", ("intent_code",)),
    ("cip.retrieval_log", ("message_id",)),
    ("cip.retrieval_log", ("created_at",)),
    ("cip.retrieval_log", ("strategy",)),
    ("cip.retrieval_hit", ("retrieval_log_id", "rank")),
    ("cip.retrieval_hit", ("chunk_id",)),
    ("cip.citation", ("message_id",)),
    ("cip.citation", ("document_version_id",)),
    ("cip.feedback", ("message_id",)),
    ("cip.feedback", ("rating", "created_at")),
    ("cip.escalation", ("status", "created_at")),
    ("cip.escalation", ("assigned_org_unit_id",)),
    ("cip.eval_case", ("category", "is_active")),
    ("cip.eval_run", ("started_at",)),
    ("cip.eval_result", ("eval_run_id", "pass")),
    ("cip.eval_result", ("eval_case_id",)),
)

DOCUMENTED_CHECKS = {
    "knowledge.document_chunk": {
        "ck_document_chunk_page_to": ("page_to", "page_from"),
        "ck_document_chunk_token_count": ("token_count", "> 0"),
        "ck_document_chunk_text_hash": ("text_hash", "= 64"),
    },
    "knowledge.ingestion_run": {
        "ck_ingestion_run_finished_at": ("finished_at", "started_at"),
    },
    "cip.conversation": {
        "ck_conversation_ended_at": ("ended_at", "started_at"),
    },
    "cip.call_session": {
        "ck_call_session_ended_at": ("ended_at", "started_at"),
        "ck_call_session_duration_sec": ("duration_sec", ">= 0"),
    },
    "cip.message": {
        "ck_message_sequence_no": ("sequence_no", ">= 1"),
        "ck_message_confidence": ("confidence", ">= (0)", "<= (1)"),
    },
    "cip.retrieval_log": {
        "ck_retrieval_log_top_k": ("top_k", "> 0"),
        "ck_retrieval_log_result_count": ("result_count", ">= 0"),
    },
    "cip.citation": {
        "ck_citation_page_to": ("page_to", "page_from"),
        "ck_citation_confidence": ("confidence", ">= (0)", "<= (1)"),
    },
    "cip.escalation": {
        "ck_escalation_resolved_at": ("resolved_at", "created_at"),
    },
    "cip.eval_case": {
        "ck_eval_case_question_not_empty": ("question", "> 0"),
    },
    "cip.eval_run": {
        "ck_eval_run_finished_at": ("finished_at", "started_at"),
    },
    "cip.eval_result": {
        "ck_eval_result_latency_ms": ("latency_ms", ">= 0"),
    },
}


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_w6_accounts_for_every_documented_entity() -> None:
    assert len(W6_ENTITIES) == 14
    assert len([e for e in W6_ENTITIES if e.startswith("KNW")]) == 3
    assert len([e for e in W6_ENTITIES if e.startswith("CIP")]) == 11
    assert DEFERRED_ENTITIES == {"KNW-02": "knowledge.embedding"}
    assert len(W6_IMPLEMENTED_ENTITIES) == 13
    assert len(W6_TABLES) == 13


def test_w6_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname IN ('knowledge', 'cip')
            """,
        )
    }
    assert actual == W6_TABLES, {
        "missing": sorted(W6_TABLES - actual),
        "unexpected": sorted(actual - W6_TABLES),
    }


def test_knw02_embedding_is_absent(conn: psycopg.Connection) -> None:
    [(regclass,)] = _rows(conn, "SELECT to_regclass('knowledge.embedding')")
    assert regclass is None
    rows = _rows(
        conn,
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'knowledge' AND column_name = 'embedding'
        """,
    )
    assert rows == []
    comment = _rows(
        conn,
        "SELECT obj_description(oid, 'pg_namespace') "
        "FROM pg_namespace WHERE nspname = 'knowledge'",
    )[0][0]
    assert "OD-06" in comment


def test_w6_table_and_column_counts(conn: psycopg.Connection) -> None:
    [(knowledge_tables,)] = _rows(
        conn,
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n "
        "ON n.oid = c.relnamespace WHERE c.relkind = 'r' "
        "AND n.nspname = 'knowledge'",
    )
    assert knowledge_tables == 2
    [(knowledge_columns,)] = _rows(
        conn,
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema = 'knowledge'",
    )
    assert knowledge_columns == 33
    [(cip_tables,)] = _rows(
        conn,
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n "
        "ON n.oid = c.relnamespace WHERE c.relkind = 'r' "
        "AND n.nspname = 'cip'",
    )
    assert cip_tables == 11
    [(cip_columns,)] = _rows(
        conn,
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema = 'cip'",
    )
    assert cip_columns == 132


def test_w6_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W6_TABLES):
        schema, name = table.split(".")
        actual = _rows(
            conn,
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, name),
        )
        expected = expected_columns(table)
        if len(actual) != len(expected):
            mismatches.append(
                f"{table}: expected {len(expected)} columns, found {len(actual)}"
            )
        actual_map = {row[0]: row for row in actual}
        expected_names = {column["name"] for column in expected}
        for column in expected:
            actual_column = actual_map.get(column["name"])
            if actual_column is None:
                mismatches.append(f"{table}.{column['name']}: missing")
                continue
            _, actual_type, actual_nullable, actual_default = actual_column
            expected_type = TYPE_MAP[column["type"]]
            if actual_type != expected_type:
                mismatches.append(
                    f"{table}.{column['name']}: type {actual_type} != {expected_type}"
                )
            if actual_nullable != column["null"]:
                mismatches.append(
                    f"{table}.{column['name']}: nullability {actual_nullable} "
                    f"!= {column['null']}"
                )
            if normalise_default(column["default"]) != normalise_default(actual_default):
                mismatches.append(
                    f"{table}.{column['name']}: default {actual_default!r} "
                    f"!= {column['default']!r}"
                )
        for extra in actual_map.keys() - expected_names:
            mismatches.append(f"{table}.{extra}: not in the dictionary")
    assert mismatches == []


def test_w6_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W6_TABLES):
        expected = expected_primary_key(table)
        rows = _rows(
            conn,
            """
            SELECT a.attname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN unnest(c.conkey) AS k(attnum) ON true
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
            WHERE c.contype = 'p' AND n.nspname = %s AND t.relname = %s
            """,
            tuple(table.split(".")),
        )
        assert [row[0] for row in rows] == [expected], f"{table}: wrong primary key"


def test_w6_documented_single_column_foreign_keys_exist(
    conn: psycopg.Connection,
) -> None:
    for table in sorted(W6_TABLES):
        expected = {}
        for column in expected_columns(table):
            match = re.search(r"FK\s*→\s*([a-z_]+\.[a-z_]+)", column["key_check"])
            if match:
                expected[column["name"]] = (
                    match.group(1),
                    expected_primary_key(match.group(1)),
                )
        actual = {
            row[0]: (row[1], row[2])
            for row in _rows(
                conn,
                """
                SELECT a.attname,
                       cn.nspname || '.' || ct.relname,
                       ca.attname
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
                JOIN pg_class ct ON ct.oid = c.confrelid
                JOIN pg_namespace cn ON cn.oid = ct.relnamespace
                JOIN pg_attribute ca ON ca.attrelid = ct.oid AND ca.attnum = c.confkey[1]
                WHERE c.contype = 'f' AND n.nspname = %s AND t.relname = %s
                  AND array_length(c.conkey, 1) = 1
                """,
                tuple(table.split(".")),
            )
        }
        assert actual == expected, (
            f"{table}: single-column foreign keys differ\n"
            f"missing/wrong: {sorted(set(expected.items()) - set(actual.items()))}\n"
            f"unexpected/wrong: {sorted(set(actual.items()) - set(expected.items()))}"
        )


def test_w6_documented_unique_constraints_exist(conn: psycopg.Connection) -> None:
    actual = {}
    for row in _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname,
               array_agg(a.attname ORDER BY k.ord)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE c.contype = 'u'
          AND n.nspname IN ('knowledge', 'cip')
        GROUP BY c.oid, n.nspname, t.relname, c.conname
        """,
    ):
        table = row[0]
        if table in W6_TABLES:
            actual[(table, row[1])] = tuple(row[2])
    assert actual == DOCUMENTED_UNIQUES, {
        "missing": sorted(set(DOCUMENTED_UNIQUES) - set(actual)),
        "unexpected": sorted(set(actual) - set(DOCUMENTED_UNIQUES)),
        "wrong": {
            key: (DOCUMENTED_UNIQUES[key], actual[key])
            for key in set(actual) & set(DOCUMENTED_UNIQUES)
            if actual[key] != DOCUMENTED_UNIQUES[key]
        },
    }


def test_w6_documented_unique_indexes_exist(conn: psycopg.Connection) -> None:
    definitions = {
        row[0]: row[1].lower()
        for row in _rows(
            conn,
            """
            SELECT indexname, indexdef FROM pg_indexes
            WHERE schemaname IN ('knowledge', 'cip')
            """,
        )
    }
    feedback = definitions.get("uq_feedback_message_person", "")
    assert "unique index" in feedback
    assert "(message_id, person_id)" in feedback
    assert "where (person_id is not null)" in feedback
    eval_case = definitions.get("uq_eval_case_code_lower", "")
    assert "unique index" in eval_case
    assert "lower(case_code)" in eval_case
    citation = definitions.get("uq_citation_message_chunk_pages", "")
    assert "nulls not distinct" in citation


def test_w6_documented_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table, wanted in DOCUMENTED_CHECKS.items():
        schema, name = table.split(".")
        checks = {
            row[0]: row[1].lower()
            for row in _rows(
                conn,
                """
                SELECT c.conname, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE c.contype = 'c' AND n.nspname = %s AND t.relname = %s
                """,
                (schema, name),
            )
        }
        for constraint, fragments in wanted.items():
            definition = checks.get(constraint, "")
            if not definition or not all(
                fragment.lower() in definition for fragment in fragments
            ):
                missing.append((table, constraint, fragments, definition))
    assert missing == [], f"missing documented checks: {missing}"


def test_w6_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W6_TABLES):
        schema, name = table.split(".")
        checks = [
            row[0].lower()
            for row in _rows(
                conn,
                """
                SELECT pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE c.contype = 'c' AND n.nspname = %s AND t.relname = %s
                """,
                (schema, name),
            )
        ]
        for column, values in documented_enum_checks(table):
            matching = [
                check
                for check in checks
                if re.search(rf"\b{column}\b", check)
                and all(f"'{value.lower()}'" in check for value in values)
            ]
            if not matching:
                missing.append((table, column, values))
    assert missing == [], f"missing documented enum checks: {missing}"


def test_w6_documented_indexes_exist(conn: psycopg.Connection) -> None:
    definitions: dict[str, set[tuple[str, ...]]] = {}
    for row in _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname,
               array_agg(a.attname ORDER BY k.ord)
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE n.nspname IN ('knowledge', 'cip') AND k.ord > 0
        GROUP BY i.indexrelid, n.nspname, t.relname
        """,
    ):
        definitions.setdefault(row[0], set()).add(tuple(row[1]))

    missing = []
    for table, columns in DOCUMENTED_INDEXES:
        found = any(
            definition[: len(columns)] == columns
            for definition in definitions.get(table, set())
        )
        if not found:
            missing.append((table, columns))
    assert missing == [], f"missing documented indexes: {missing}"

    fts = [
        row[0].lower()
        for row in _rows(
            conn,
            """
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'knowledge' AND tablename = 'document_chunk'
            """,
        )
    ]
    assert any(
        "using gin" in definition
        and "to_tsvector" in definition
        and "chunk_text" in definition
        for definition in fts
    ), fts


def test_w6_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal AND n.nspname IN ('knowledge', 'cip')
              AND (n.nspname || '.' || t.relname) = ANY(%s)
            """,
            (sorted(W6_TABLES),),
        )
    }
    assert rows == W6_TRIGGERS, {
        "missing": sorted(W6_TRIGGERS - rows),
        "unexpected": sorted(rows - W6_TRIGGERS),
    }


def test_every_w6_foreign_key_has_a_leading_index(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname, a.attname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f'
          AND n.nspname IN ('knowledge', 'cip')
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_all_w6_tables_are_rls_enabled_and_forced(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || c.relname, c.relrowsecurity,
               c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname IN ('knowledge', 'cip')
        ORDER BY 1
        """,
    )
    assert len(rows) == 13
    assert all(enabled and forced for _, enabled, forced in rows), rows

    policies = {
        (row[0], row[1], row[2])
        for row in _rows(
            conn,
            """
            SELECT schemaname, tablename, policyname
            FROM pg_policies
            WHERE schemaname IN ('knowledge', 'cip')
            """,
        )
    }
    for table in sorted(W6_TABLES):
        schema, name = table.split(".")
        matching = [
            policy
            for entry_schema, entry_table, policy in policies
            if entry_schema == schema
            and entry_table == name
            and policy.endswith("_owner_all")
        ]
        assert matching, f"{table}: missing owner policy"

    assert (
        "knowledge", "document_chunk", "p_document_chunk_classification_select"
    ) in policies
    assert ("cip", "conversation", "p_conversation_person_select") in policies
    assert len(policies) == 15


def test_w6_grant_boundaries(conn: psycopg.Connection) -> None:
    for table in sorted(W6_TABLES):
        for privilege in ("SELECT", "INSERT", "UPDATE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_cip', %s, %s)",
                (table, privilege),
            )
            assert allowed is True, f"app_cip lacks {privilege} on {table}"
        [(delete_allowed,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_cip', %s, 'DELETE')",
            (table,),
        )
        assert delete_allowed is False, f"app_cip can delete {table}"

        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            [(erp_allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_erp', %s, %s)",
                (table, privilege),
            )
            assert erp_allowed is False, f"app_erp has {privilege} on {table}"

    for role in APP_ROLES:
        if role == "app_cip":
            continue
        for table in sorted(W6_TABLES):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                [(allowed,)] = _rows(
                    conn,
                    "SELECT has_table_privilege(%s, %s, %s)",
                    (role, table, privilege),
                )
                assert allowed is False, f"{role} has {privilege} on {table}"
