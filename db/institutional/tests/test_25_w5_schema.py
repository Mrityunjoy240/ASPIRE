"""W5 structural validation against the approved design."""

from __future__ import annotations

import re

import psycopg

from design import (
    TYPE_MAP,
    W5_ENTITIES,
    W5_TABLES,
    W5_TRIGGERS,
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
    ("exam.result_import", "uq_result_import"):
        ("term_id", "programme_id", "sha256"),
    ("exam.result_set", "uq_result_set"):
        ("term_id", "programme_id", "batch_id", "exam_label", "result_type"),
    ("exam.result_record", "uq_result_record"):
        ("student_id", "course_version_id", "result_set_id"),
    ("exam.result_revision", "uq_result_revision"):
        ("result_record_id", "revision_no"),
    ("exam.result_input", "uq_result_input"):
        ("result_revision_id", "component_code"),
    ("exam.grade_card", "uq_grade_card"):
        ("student_id", "term_id", "version_no"),
    ("exam.grade_card_result", "uq_grade_card_result"):
        ("grade_card_id", "result_record_id"),
    ("doc.notice_version", "uq_notice_version"):
        ("notice_id", "version_no"),
    ("doc.notice_audience", "uq_notice_audience"):
        ("notice_version_id", "audience_type", "programme_id", "batch_id",
         "term_id", "role_id", "org_unit_id"),
}

DOCUMENTED_INDEXES = (
    ("exam.result_import", ("term_id", "programme_id")),
    ("exam.result_import", ("status", "imported_at")),
    ("exam.result_set", ("term_id", "programme_id", "status")),
    ("exam.result_set", ("published_at",)),
    ("exam.result_record", ("student_id", "course_version_id")),
    ("exam.result_record", ("result_set_id",)),
    ("exam.result_record", ("status",)),
    ("exam.result_revision", ("result_record_id", "revision_no")),
    ("exam.result_revision", ("result_status",)),
    ("exam.result_input", ("mark_entry_version_id",)),
    ("exam.grade_card", ("student_id", "term_id", "version_no")),
    ("exam.grade_card", ("result_set_id",)),
    ("exam.grade_card_result", ("result_record_id",)),
    ("doc.notice", ("category", "status")),
    ("doc.notice", ("issuing_org_unit_id",)),
    ("doc.notice_version", ("notice_id", "version_no")),
    ("doc.notice_version", ("publish_at", "status")),
    ("doc.notice_audience", ("notice_version_id",)),
    ("doc.notice_audience", ("programme_id", "batch_id")),
    ("doc.notice_audience", ("role_id",)),
)

DOCUMENTED_CHECKS = {
    "exam.result_set": {
        "ck_result_set_published_at": ("published_at", "approved_at"),
        "ck_result_set_published_gate": (
            "published", "approved_by", "approved_at",
            "external_publication_ref",
        ),
    },
    "exam.grade_card": {
        "ck_grade_card_credits_earned": (
            "credits_earned", "credits_registered"
        ),
    },
    "doc.notice_version": {
        "ck_notice_version_effective_to": ("effective_to", "effective_from"),
        "ck_notice_version_supersedes_version_id": (
            "supersedes_version_id", "notice_version_id"
        ),
        "ck_notice_version_publish_at_scheduled": ("publish_at", "scheduled"),
    },
    "doc.notice_audience": {
        "ck_notice_audience_target_required": (
            "audience_type", "all", "programme_id", "batch_id", "term_id",
            "role_id", "org_unit_id",
        ),
    },
}


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_w5_has_ten_documented_entities() -> None:
    assert len(W5_ENTITIES) == 10
    assert len([e for e in W5_ENTITIES if e.startswith("EXM")]) == 7
    assert len([e for e in W5_ENTITIES if e.startswith("DOC")]) == 3


def test_w5_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname IN ('exam')
            """,
        )
    }
    actual |= {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = 'doc'
            """,
        )
        if row[0] not in {"doc.document", "doc.document_version",
                          "doc.document_relation"}
    }
    assert actual == W5_TABLES, {
        "missing": sorted(W5_TABLES - actual),
        "unexpected": sorted(actual - W5_TABLES),
    }


def test_w5_table_and_column_counts(conn: psycopg.Connection) -> None:
    [(exam_tables,)] = _rows(
        conn,
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n "
        "ON n.oid = c.relnamespace WHERE c.relkind = 'r' AND n.nspname = 'exam'",
    )
    assert exam_tables == 7
    [(exam_columns,)] = _rows(
        conn,
        """
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'exam'
        """,
    )
    assert exam_columns == 100
    [(notice_columns,)] = _rows(
        conn,
        """
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'doc'
          AND table_name IN ('notice', 'notice_version', 'notice_audience')
        """,
    )
    assert notice_columns == 42


def test_w5_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W5_TABLES):
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


def test_w5_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W5_TABLES):
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


def test_w5_documented_single_column_foreign_keys_exist(
    conn: psycopg.Connection,
) -> None:
    for table in sorted(W5_TABLES):
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


def test_w5_documented_unique_constraints_exist(conn: psycopg.Connection) -> None:
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
          AND n.nspname IN ('exam', 'doc')
        GROUP BY c.oid, n.nspname, t.relname, c.conname
        """,
    ):
        table = row[0]
        if table in W5_TABLES:
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


def test_w5_documented_unique_indexes_exist(conn: psycopg.Connection) -> None:
    definitions = {
        row[0]: row[1]
        for row in _rows(
            conn,
            """
            SELECT indexname, indexdef FROM pg_indexes
            WHERE schemaname IN ('exam', 'doc')
            """,
        )
    }
    current = definitions.get("uq_grade_card_current", "").lower()
    assert "unique index" in current
    assert "where is_current" in current
    notice_no = definitions.get("uq_notice_no_lower", "").lower()
    assert "unique index" in notice_no
    assert "lower(notice_no)" in notice_no


def test_w5_documented_checks_are_enforced(conn: psycopg.Connection) -> None:
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


def test_w5_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W5_TABLES):
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


def test_w5_documented_indexes_exist(conn: psycopg.Connection) -> None:
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
        WHERE n.nspname IN ('exam', 'doc') AND k.ord > 0
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


def test_w5_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal AND n.nspname IN ('exam', 'doc')
              AND (n.nspname || '.' || t.relname) = ANY(%s)
            """,
            (sorted(W5_TABLES),),
        )
    }
    assert rows == W5_TRIGGERS, {
        "missing": sorted(W5_TRIGGERS - rows),
        "unexpected": sorted(rows - W5_TRIGGERS),
    }


def test_every_w5_foreign_key_has_a_leading_index(
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
          AND n.nspname IN ('exam', 'doc')
          AND t.relname NOT IN ('document', 'document_version',
                                'document_relation')
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_all_w5_tables_are_rls_enabled_and_forced(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || c.relname, c.relrowsecurity,
               c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname IN ('exam', 'doc')
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
            WHERE schemaname IN ('exam', 'doc')
            """,
        )
    }
    for table in sorted(W5_TABLES):
        schema, name = table.split(".")
        matching = [
            policy
            for entry_schema, entry_table, policy in policies
            if entry_schema == schema
            and entry_table == name
            and policy.endswith("_owner_all")
        ]
        assert matching, f"{table}: missing owner policy"

    assert ("exam", "result_record", "p_result_record_access_select") in policies
    assert (
        "exam", "result_revision", "p_result_revision_access_select"
    ) in policies


def test_w5_grant_boundaries(conn: psycopg.Connection) -> None:
    exam_tables = sorted(t for t in W5_TABLES if t.startswith("exam."))
    notice_tables = sorted(t for t in W5_TABLES if t.startswith("doc."))

    for table in exam_tables:
        for privilege in ("SELECT", "INSERT", "UPDATE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_erp', %s, %s)",
                (table, privilege),
            )
            assert allowed is True, f"app_erp lacks {privilege} on {table}"
        [(delete_allowed,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_erp', %s, 'DELETE')",
            (table,),
        )
        assert delete_allowed is False, f"app_erp can delete {table}"
        [(cip_select,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_cip', %s, 'SELECT')",
            (table,),
        )
        assert cip_select is False, f"app_cip can read {table}"

    for table in notice_tables:
        for privilege in ("SELECT", "INSERT", "UPDATE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_erp', %s, %s)",
                (table, privilege),
            )
            assert allowed is True, f"app_erp lacks {privilege} on {table}"
        [(delete_allowed,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_erp', %s, 'DELETE')",
            (table,),
        )
        assert delete_allowed is False, f"app_erp can delete {table}"
        [(cip_select,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_cip', %s, 'SELECT')",
            (table,),
        )
        assert cip_select is True, f"app_cip lacks SELECT on {table}"
        for privilege in ("INSERT", "UPDATE", "DELETE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_cip', %s, %s)",
                (table, privilege),
            )
            assert allowed is False, f"app_cip has {privilege} on {table}"

    for role in APP_ROLES:
        if role in ("app_erp", "app_cip"):
            continue
        for table in sorted(W5_TABLES):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                [(allowed,)] = _rows(
                    conn,
                    "SELECT has_table_privilege(%s, %s, %s)",
                    (role, table, privilege),
                )
                assert allowed is False, f"{role} has {privilege} on {table}"
