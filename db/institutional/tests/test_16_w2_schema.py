"""W2 structural validation against the approved design.

Expectations come from ``DATA_DICTIONARY.md`` and ``MVP_DEPENDENCY_MAP.md``.
The tests inspect the catalog, not the migration text.
"""

from __future__ import annotations

import re

import psycopg

from design import (
    TYPE_MAP,
    W2_ENTITIES,
    W2_TABLES,
    W2_TRIGGERS,
    W2_UNIQUE_INDEXES,
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

HELPER_FUNCTIONS = (
    "iam.is_section_teacher(uuid)",
    "iam.is_allocated_to_offering(uuid)",
    "iam.can_access_student(uuid)",
    "iam.can_access_offering(uuid)",
)


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_w2_has_the_thirteen_documented_entities() -> None:
    assert len(W2_ENTITIES) == 13
    assert "STU-13" not in W2_ENTITIES
    assert "STU-14" not in W2_ENTITIES


def test_w2_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = 'student'
            """,
        )
    }
    assert actual == W2_TABLES, {
        "missing": sorted(W2_TABLES - actual),
        "unexpected": sorted(actual - W2_TABLES),
    }


def test_w2_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W2_TABLES):
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


def test_w2_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W2_TABLES):
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


def test_w2_documented_foreign_keys_exist(conn: psycopg.Connection) -> None:
    """Every dictionary arrow must resolve; composite keys are checked below."""
    missing: list[str] = []
    for table in sorted(W2_TABLES):
        actual = {
            (row[0], row[1])
            for row in _rows(
                conn,
                """
                SELECT a.attname,
                       cn.nspname || '.' || ct.relname
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
                JOIN pg_class ct ON ct.oid = c.confrelid
                JOIN pg_namespace cn ON cn.oid = ct.relnamespace
                WHERE c.contype = 'f' AND array_length(c.conkey, 1) = 1
                  AND n.nspname = %s AND t.relname = %s
                """,
                tuple(table.split(".")),
            )
        }
        for column in expected_columns(table):
            match = re.search(r"FK\s*→\s*([a-z_]+\.[a-z_]+)", column["key_check"])
            if match and (column["name"], match.group(1)) not in actual:
                missing.append(f"{table}.{column['name']} -> {match.group(1)}")
    assert missing == [], f"missing documented foreign keys: {missing}"


def test_w2_composite_foreign_keys_are_enforced(conn: psycopg.Connection) -> None:
    expected = {
        (
            "student.course_registration",
            ("semester_registration_id", "student_id"),
            "student.semester_registration",
            ("semester_registration_id", "student_id"),
        ),
        (
            "student.section_assignment",
            ("student_id", "batch_id"),
            "student.student",
            ("student_id", "batch_id"),
        ),
        (
            "student.section_assignment",
            ("section_id", "batch_id"),
            "academic.section",
            ("section_id", "batch_id"),
        ),
    }
    actual = set()
    for row in _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname AS child,
               (SELECT array_agg(a.attname ORDER BY k.ord)
                FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum),
               cn.nspname || '.' || ct.relname AS parent,
               (SELECT array_agg(a.attname ORDER BY k.ord)
                FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord)
                JOIN pg_attribute a ON a.attrelid = ct.oid AND a.attnum = k.attnum)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class ct ON ct.oid = c.confrelid
        JOIN pg_namespace cn ON cn.oid = ct.relnamespace
        WHERE c.contype = 'f' AND n.nspname = 'student'
          AND array_length(c.conkey, 1) > 1
        """,
    ):
        actual.add((row[0], tuple(row[1]), row[2], tuple(row[3])))
    assert actual == expected, {
        "missing": sorted(expected - actual),
        "unexpected": sorted(actual - expected),
    }


def test_w2_documented_unique_keys_exist(conn: psycopg.Connection) -> None:
    definitions: dict[str, list[str]] = {}
    for table in W2_TABLES:
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
    for table, keys, predicates in W2_UNIQUE_INDEXES:
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


def test_w2_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W2_TABLES):
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


def test_w2_exclusion_constraints_exist(conn: psycopg.Connection) -> None:
    rows = dict(
        _rows(
            conn,
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.contype = 'x' AND n.nspname = 'student'
            """,
        )
    )
    assert set(rows) == {"ex_status_history_overlap", "ex_section_assignment_overlap"}
    for name, definition in rows.items():
        assert "daterange" in definition, name
        assert " WITH &&" in definition or "&&" in definition, name


def test_w2_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal AND n.nspname = 'student'
            """,
        )
    }
    assert rows == W2_TRIGGERS, {
        "missing": sorted(W2_TRIGGERS - rows),
        "unexpected": sorted(rows - W2_TRIGGERS),
    }


def test_every_w2_foreign_key_has_a_leading_index(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname, a.attname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f' AND n.nspname = 'student'
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_all_w2_tables_use_enable_and_force_rls(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'student'
        ORDER BY c.relname
        """,
    )
    assert len(rows) == 13
    assert all(enabled and forced for _, enabled, forced in rows), rows


def test_only_documented_application_policies_exist(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT tablename, policyname, cmd, roles
        FROM pg_policies
        WHERE schemaname = 'student'
        ORDER BY tablename, policyname
        """,
    )

    owner_all = [row for row in rows if row[2] == "ALL"]
    assert len(owner_all) == 13
    assert all(set(row[3]) == {"owner_student"} for row in owner_all), owner_all

    application = [
        row for row in rows if not set(row[3]) <= {"owner_student", "owner_iam"}
    ]
    assert {
        (row[0], row[2]) for row in application
    } == {
        ("student", "SELECT"),
        ("section_assignment", "SELECT"),
    }, application

    helper = [row for row in rows if set(row[3]) == {"owner_iam"}]
    assert {row[0] for row in helper} == {
        "student",
        "student_guardian",
        "guardian",
        "course_registration",
    }, helper
    assert all(row[2] == "SELECT" for row in helper)


def test_w2_helper_functions_are_security_definer_and_owner_owned(
    conn: psycopg.Connection,
) -> None:
    for function in HELPER_FUNCTIONS:
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


def test_sensitive_w2_columns_are_outside_the_erp_projection(
    conn: psycopg.Connection,
) -> None:
    denied = [
        ("student.admission_application", "category"),
        ("student.student", "category"),
        ("student.guardian", "annual_income_band"),
        ("student.student_guardian", "consent_status"),
        ("student.status_history", "reason"),
        ("student.student_document", "document_type"),
    ]
    for table, column in denied:
        [(allowed,)] = _rows(
            conn,
            "SELECT has_column_privilege('app_erp', %s, %s, 'SELECT')",
            (table, column),
        )
        assert allowed is False, f"app_erp can read {table}.{column}"


def test_student_documents_have_no_application_grant(conn: psycopg.Connection) -> None:
    for role in APP_ROLES:
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege(%s, 'student.student_document', %s)",
                (role, privilege),
            )
            assert allowed is False, f"{role} has {privilege} on student.student_document"


def test_only_erp_has_direct_student_table_access(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT grantee, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE table_schema = 'student'
          AND grantee NOT IN ('owner_student', 'owner_iam', 'migration_owner')
        """,
    )
    assert rows, "app_erp should have documented table grants"
    assert {row[0] for row in rows} == {"app_erp"}, rows
    assert {row[2] for row in rows} <= {"SELECT", "INSERT", "UPDATE"}, rows
    assert not any(row[2] == "DELETE" for row in rows)


def test_app_cip_cannot_read_student_base_tables(conn: psycopg.Connection) -> None:
    for table in sorted(W2_TABLES):
        [(allowed,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_cip', %s, 'SELECT')",
            (table,),
        )
        assert allowed is False, f"app_cip can read {table} directly"


def test_trigger_functions_are_not_executable_by_application_roles(
    conn: psycopg.Connection,
) -> None:
    for function in (
        "student.enforce_exam_roll_number_format()",
        "student.seal_eligibility_determination()",
    ):
        for role in APP_ROLES:
            [(actual,)] = _rows(
                conn,
                "SELECT has_function_privilege(%s, %s, 'EXECUTE')",
                (role, function),
            )
            assert actual is False, f"{role} can execute {function}"
