"""W1b structural validation against the approved design.

Expectations come from ``DATA_DICTIONARY.md`` and ``MVP_DEPENDENCY_MAP.md``.
The tests inspect the catalog, not the migration text.
"""

from __future__ import annotations

import re

import psycopg

from design import (
    TYPE_MAP,
    W1B_ENTITIES,
    W1B_TRIGGERS,
    W1B_TABLES,
    W1B_UNIQUE_INDEXES,
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


def test_w1b_has_the_thirteen_documented_entities() -> None:
    assert len(W1B_ENTITIES) == 13
    assert "ACD-13" not in W1B_ENTITIES


def test_w1b_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = 'academic'
            """,
        )
    }
    assert actual == W1B_TABLES, {
        "missing": sorted(W1B_TABLES - actual),
        "unexpected": sorted(actual - W1B_TABLES),
    }


def test_w1b_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W1B_TABLES):
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


def test_w1b_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W1B_TABLES):
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


def test_w1b_foreign_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W1B_TABLES):
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


def test_w1b_documented_unique_keys_exist(conn: psycopg.Connection) -> None:
    definitions: dict[str, list[str]] = {}
    for table in W1B_TABLES:
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
    for table, keys, predicates in W1B_UNIQUE_INDEXES:
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


def test_w1b_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W1B_TABLES):
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


def test_w1b_exclusion_constraints_exist(conn: psycopg.Connection) -> None:
    rows = dict(
        _rows(
            conn,
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.contype = 'x' AND n.nspname = 'academic'
            """,
        )
    )
    assert set(rows) == {"ex_programme_version_years", "ex_section_teacher_overlap"}
    assert "int4range" in rows["ex_programme_version_years"]
    overlap = rows["ex_section_teacher_overlap"]
    assert "daterange" in overlap and "class_teacher" in overlap


def test_w1b_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal AND n.nspname = 'academic'
            """,
        )
    }
    assert rows == W1B_TRIGGERS, {
        "missing": sorted(W1B_TRIGGERS - rows),
        "unexpected": sorted(rows - W1B_TRIGGERS),
    }


def test_every_w1b_foreign_key_has_a_leading_index(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname, a.attname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f' AND n.nspname = 'academic'
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_course_offering_unique_treats_null_sections_as_equal(
    conn: psycopg.Connection,
) -> None:
    [(definition,)] = _rows(
        conn,
        """
        SELECT pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE c.conname = 'uq_course_offering' AND n.nspname = 'academic'
        """,
    )
    assert "NULLS NOT DISTINCT" in definition.upper()


def test_timetable_slot_has_no_room_id(conn: psycopg.Connection) -> None:
    [(count,)] = _rows(
        conn,
        """
        SELECT count(*)
        FROM information_schema.columns
        WHERE table_schema = 'academic' AND table_name = 'timetable_slot'
          AND column_name = 'room_id'
        """,
    )
    assert count == 0, "the V1 timetable slot is a pattern, not a room allocation"


def test_no_application_role_can_delete_w1b_data(conn: psycopg.Connection) -> None:
    for role in APP_ROLES:
        for table in sorted(W1B_TABLES):
            [(actual,)] = _rows(
                conn,
                "SELECT has_table_privilege(%s, %s, 'DELETE')",
                (role, table),
            )
            assert actual is False, f"{role} unexpectedly has DELETE on {table}"
