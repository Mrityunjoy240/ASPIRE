"""W3 structural validation against the approved design."""

from __future__ import annotations

import re

import psycopg

from design import (
    TYPE_MAP,
    W3_ENTITIES,
    W3_TABLES,
    W3_TRIGGERS,
    W3_UNIQUE_INDEXES,
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


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_w3_has_the_three_documented_entities() -> None:
    assert len(W3_ENTITIES) == 3


def test_w3_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = 'faculty'
            """,
        )
    }
    assert actual == W3_TABLES, {
        "missing": sorted(W3_TABLES - actual),
        "unexpected": sorted(actual - W3_TABLES),
    }


def test_w3_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W3_TABLES):
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


def test_w3_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W3_TABLES):
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


def test_w3_foreign_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W3_TABLES):
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
                """,
                tuple(table.split(".")),
            )
        }
        assert actual == expected, (
            f"{table}: foreign keys differ\n"
            f"missing/wrong: {sorted(set(expected.items()) - set(actual.items()))}\n"
            f"unexpected/wrong: {sorted(set(actual.items()) - set(expected.items()))}"
        )


def test_w3_documented_unique_keys_exist(conn: psycopg.Connection) -> None:
    definitions: dict[str, list[str]] = {}
    for table in W3_TABLES:
        definitions[table] = [
            row[0].lower()
            for row in _rows(
                conn,
                """
                SELECT pg_get_indexdef(i.indexrelid)
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE i.indisunique AND n.nspname || '.' || t.relname = %s
                """,
                (table,),
            )
        ]

    missing = []
    for table, keys, predicates in W3_UNIQUE_INDEXES:
        found = False
        for definition in definitions[table]:
            if " unique " not in f" {definition} ":
                continue
            if not all(key.lower() in definition for key in keys):
                continue
            if not all(predicate.lower() in definition for predicate in predicates):
                continue
            found = True
            break
        if not found:
            missing.append((table, keys, predicates))
    assert missing == [], f"missing documented unique indexes: {missing}"


def test_w3_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W3_TABLES):
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


def test_w3_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal AND n.nspname = 'faculty'
            """,
        )
    }
    assert rows == W3_TRIGGERS, {
        "missing": sorted(W3_TRIGGERS - rows),
        "unexpected": sorted(rows - W3_TRIGGERS),
    }


def test_every_w3_foreign_key_has_a_leading_index(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname, a.attname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f' AND n.nspname = 'faculty'
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_faculty_tables_are_not_in_the_documented_rls_list(
    conn: psycopg.Connection,
) -> None:
    """DATA_DICTIONARY 1.6 lists student, attendance, assessment, exam, finance,
    services, doc, knowledge, cip, and four iam tables. Faculty is absent, so
    the design does not authorize an invented policy here; mentor access is
    governed through iam.can_access_student.
    """
    rows = _rows(
        conn,
        """
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'faculty'
        ORDER BY c.relname
        """,
    )
    assert len(rows) == 3
    assert all(not enabled and not forced for _, enabled, forced in rows), rows
    [(policies,)] = _rows(
        conn,
        "SELECT count(*) FROM pg_policies WHERE schemaname = 'faculty'",
    )
    assert policies == 0


def test_w3_helper_functions_are_security_definer_and_owner_owned(
    conn: psycopg.Connection,
) -> None:
    for function in ("iam.is_mentor_of(uuid)", "iam.can_access_student(uuid)"):
        rows = _rows(
            conn,
            """
            SELECT p.prosecdef, r.rolname
            FROM pg_proc p
            JOIN pg_roles r ON r.oid = p.proowner
            WHERE p.oid = to_regprocedure(%s)::oid
            """,
            (function,),
        )
        assert rows == [(True, "owner_iam")], f"{function}: {rows}"

        [(public_execute,)] = _rows(
            conn,
            "SELECT has_function_privilege('public', %s, 'EXECUTE')",
            (function,),
        )
        assert public_execute is False, f"PUBLIC can execute {function}"

    [(definition,)] = _rows(
        conn,
        """
        SELECT pg_get_functiondef(p.oid)
        FROM pg_proc p
        WHERE p.oid = to_regprocedure('iam.can_access_student(uuid)')::oid
        """,
    )
    assert "is_mentor_of" in definition


def test_w3_grant_boundaries(conn: psycopg.Connection) -> None:
    for table in ("faculty.faculty_profile", "faculty.staff_profile"):
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

    [(any_select,)] = _rows(
        conn,
        "SELECT has_any_column_privilege('app_erp', 'faculty.mentor_assignment', 'SELECT')",
    )
    assert any_select is True

    [(notes_visibility,)] = _rows(
        conn,
        """
        SELECT has_column_privilege(
            'app_erp', 'faculty.mentor_assignment', 'notes_visibility', 'SELECT'
        )
        """,
    )
    assert notes_visibility is False, "notes_visibility is class R"

    [(owner_iam_select,)] = _rows(
        conn,
        """
        SELECT has_table_privilege(
            'owner_iam', 'faculty.mentor_assignment', 'SELECT'
        )
        """,
    )
    assert owner_iam_select is True

    for role in APP_ROLES:
        for table in sorted(W3_TABLES):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                [(allowed,)] = _rows(
                    conn,
                    "SELECT has_table_privilege(%s, %s, %s)",
                    (role, table, privilege),
                )
                if role == "app_erp":
                    continue
                assert allowed is False, f"{role} has {privilege} on {table}"


def test_trigger_function_is_not_executable_by_application_roles(
    conn: psycopg.Connection,
) -> None:
    for role in APP_ROLES:
        [(actual,)] = _rows(
            conn,
            "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
            (role, "faculty.enforce_mentor_active_profile()"),
        )
        assert actual is False, f"{role} can execute the trigger function"
