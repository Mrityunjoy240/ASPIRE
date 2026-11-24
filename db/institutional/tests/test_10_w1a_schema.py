"""W1a structural validation against the approved design.

Every expectation is derived from ``DATA_DICTIONARY.md``, ``ENTITY_CATALOG.md``,
``MVP_DEPENDENCY_MAP.md``, and ``POSTGRES_ARCHITECTURE.md``. The tests check the
database the migrations actually create, not the migration text.
"""

from __future__ import annotations

import psycopg

from design import (
    IMPLEMENTED_TABLES,
    RLS_TABLES,
    STAGED_FOREIGN_KEYS,
    UNIQUE_INDEXES,
    W1A_ENTITIES,
    W1A_SCHEMAS,
    W1A_TABLES,
    W7_RLS_TABLES,
    documented_enum_checks,
    expected_columns,
    expected_primary_key,
    normalise_default,
    TYPE_MAP,
)

EXPECTED_TRIGGERS = {
    ("iam", "person", "trg_person_date_of_birth"),
    ("iam", "role", "trg_role_protect_system"),
    ("iam", "role_assignment", "trg_role_assignment_scope"),
    ("core", "org_unit", "trg_org_unit_path"),
    ("core", "org_unit", "trg_org_unit_descendant_paths"),
    ("policy", "rule_version", "trg_rule_version_current"),
    ("policy", "rule_version", "trg_rule_version_seal"),
    ("doc", "document", "trg_document_classification_no_downgrade"),
    ("doc", "document_version", "trg_document_version_seal"),
    ("policy", "policy_bundle_version", "trg_policy_bundle_version_append_only"),
    ("integration", "sync_record", "trg_sync_record_append_only"),
    ("integration", "sync_run", "trg_sync_run_seal"),
    ("ops", "audit_event", "trg_audit_event_append_only"),
}


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def _domain_tables(conn: psycopg.Connection) -> set[str]:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'public')
        """,
    )
    return {row[0] for row in rows}


def test_database_has_exactly_the_implemented_documented_tables(conn: psycopg.Connection) -> None:
    actual = _domain_tables(conn)
    assert actual == IMPLEMENTED_TABLES, {
        "missing": sorted(IMPLEMENTED_TABLES - actual),
        "unexpected": sorted(actual - IMPLEMENTED_TABLES),
    }
    assert len(W1A_ENTITIES) == 42


def test_w1a_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W1A_TABLES):
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
        for name in actual_map.keys() - expected_names:
            mismatches.append(f"{table}.{name}: not in the dictionary")

    assert mismatches == []


def test_every_table_has_the_documented_primary_key(conn: psycopg.Connection) -> None:
    for table in sorted(W1A_TABLES):
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


def test_foreign_keys_never_point_outside_the_implemented_waves(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname,
               cn.nspname || '.' || ct.relname,
               c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class ct ON ct.oid = c.confrelid
        JOIN pg_namespace cn ON cn.oid = ct.relnamespace
        WHERE c.contype = 'f' AND n.nspname = ANY(%s)
        """,
        (list(W1A_SCHEMAS),),
    )
    outside = sorted(
        (source, target, name)
        for source, target, name in rows
        if target not in IMPLEMENTED_TABLES
    )
    assert outside == [], f"active foreign keys point outside implemented waves: {outside}"


def test_the_seven_staged_foreign_keys_are_present_and_validated(
    conn: psycopg.Connection,
) -> None:
    names = [item[0] for item in STAGED_FOREIGN_KEYS]
    rows = _rows(
        conn,
        "SELECT conname, convalidated FROM pg_constraint WHERE conname = ANY(%s)",
        (names,),
    )
    assert len(rows) == len(names), f"OD-12 staged foreign keys missing: {rows}"
    assert all(validated for _, validated in rows), (
        f"OD-12 staged foreign keys must be validated: {rows}"
    )


def test_only_the_documented_cycle_foreign_key_is_deferrable(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT c.conname, c.condeferrable, c.condeferred, c.convalidated
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE c.contype = 'f' AND n.nspname = ANY(%s)
        """,
        (list(W1A_SCHEMAS),),
    )
    deferrable = {name for name, deferrable, _, _ in rows if deferrable}
    assert deferrable == {"fk_role_assignment_source_membership"}, deferrable
    assert all(
        deferred for name, _, deferred, _ in rows
        if name == "fk_role_assignment_source_membership"
    )
    assert all(validated for _, _, _, validated in rows), "unvalidated W1a foreign key"


def test_every_foreign_key_column_has_a_leading_index(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, a.attname, c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN unnest(c.conkey) AS k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE c.contype = 'f' AND n.nspname = ANY(%s)
          AND NOT EXISTS (
              SELECT 1 FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
        (list(W1A_SCHEMAS),),
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_documented_unique_keys_exist(conn: psycopg.Connection) -> None:
    definitions: dict[str, list[str]] = {}
    for table in W1A_TABLES:
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
    for table, keys, predicates in UNIQUE_INDEXES:
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


def test_documented_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W1A_TABLES):
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
            column_pattern = rf"\b{column}\b"
            matching = [
                check
                for check in checks
                if __import__("re").search(column_pattern, check)
                and all(f"'{value.lower()}'" in check for value in values)
            ]
            if not matching:
                missing.append((table, column, values))
    assert missing == [], f"missing documented enum checks: {missing}"


def test_documented_triggers_exist(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname, t.relname, trg.tgname
        FROM pg_trigger trg
        JOIN pg_class t ON t.oid = trg.tgrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE NOT trg.tgisinternal AND n.nspname = ANY(%s)
        """,
        (list(W1A_SCHEMAS),),
    )
    assert set(rows) == EXPECTED_TRIGGERS, {
        "missing": sorted(EXPECTED_TRIGGERS - set(rows)),
        "unexpected": sorted(set(rows) - EXPECTED_TRIGGERS),
    }


def test_rls_is_enabled_and_forced_on_the_documented_tables(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, t.relrowsecurity, t.relforcerowsecurity
        FROM pg_class t
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE t.relkind = 'r'
          AND n.nspname = ANY(%s)
          AND (t.relrowsecurity OR t.relforcerowsecurity)
        """,
        (list(W1A_SCHEMAS),),
    )
    actual = {row[0] for row in rows}
    assert RLS_TABLES <= actual, {
        "missing": sorted(RLS_TABLES - actual),
    }
    # W1a owns no later doc tables; W5 adds RLS to doc.notice* by design, and
    # W7 adds forced RLS to the three API-key tables.
    unexpected = {
        table
        for table in actual - RLS_TABLES - W7_RLS_TABLES
        if not table.startswith("doc.")
    }
    assert unexpected == set(), {
        "unexpected": sorted(unexpected),
    }
    assert all(
        enabled and forced for _, enabled, forced in rows
    ), "every RLS table must use ENABLE and FORCE"


def test_w1a_has_no_exclusion_constraint(conn: psycopg.Connection) -> None:
    """The documented exclusion constraints all belong to W1b or later waves."""
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname, c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE c.contype = 'x' AND n.nspname = ANY(%s)
        """,
        (list(W1A_SCHEMAS),),
    )
    assert rows == []
