"""W4 structural validation against the approved design."""

from __future__ import annotations

import re

import psycopg

from design import (
    TYPE_MAP,
    W4_ENTITIES,
    W4_TABLES,
    W4_TRIGGERS,
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
    ("attendance.session", "uq_session_offering_date_start"):
        ("course_offering_id", "session_date", "start_time"),
    ("attendance.session", "uq_session_offering_target"):
        ("session_id", "course_offering_id"),
    ("attendance.record", "uq_attendance_record_session_student"):
        ("session_id", "student_id"),
    ("attendance.summary", "uq_attendance_summary_asof"):
        ("student_id", "course_offering_id", "as_of"),
    ("attendance.eligibility_assessment", "uq_attendance_eligibility_variant"):
        ("student_id", "term_id", "rule_variant", "computed_at"),
    ("attendance.condonation_case", "uq_condonation_student_term"):
        ("student_id", "term_id"),
    ("assessment.scheme", "uq_assessment_scheme"):
        ("course_version_id", "name", "effective_from_term_id"),
    ("assessment.component", "uq_assessment_component_code"):
        ("scheme_id", "component_code"),
    ("assessment.schedule", "uq_assessment_schedule"):
        ("component_id", "course_offering_id", "schedule_type"),
    ("assessment.mark_entry", "uq_assessment_mark_entry"):
        ("student_id", "component_id", "course_offering_id"),
    ("assessment.mark_entry_version", "uq_assessment_mark_version"):
        ("mark_entry_id", "version_no"),
    ("assessment.conflict_declaration", "uq_assessment_conflict"):
        ("faculty_person_id", "course_offering_id", "student_id"),
}

DOCUMENTED_INDEXES = (
    ("attendance.session", ("course_offering_id", "session_date")),
    ("attendance.session", ("session_date", "status")),
    ("attendance.record", ("student_id", "session_id")),
    ("attendance.record", ("session_id", "status")),
    ("attendance.record", ("course_registration_id",)),
    ("attendance.record", ("course_offering_id",)),
    ("attendance.correction", ("attendance_record_id",)),
    ("attendance.correction", ("status", "requested_at")),
    ("attendance.summary", ("student_id", "course_offering_id", "as_of")),
    ("attendance.summary", ("course_offering_id",)),
    ("attendance.eligibility_assessment",
     ("student_id", "term_id", "computed_at")),
    ("attendance.eligibility_assessment", ("outcome",)),
    ("attendance.condonation_case", ("term_id", "status")),
    ("attendance.condonation_case", ("student_id",)),
    ("assessment.scheme", ("course_version_id", "status")),
    ("assessment.scheme", ("effective_from_term_id",)),
    ("assessment.component", ("scheme_id", "sequence_no")),
    ("assessment.component", ("parent_component_id",)),
    ("assessment.schedule", ("course_offering_id", "scheduled_start")),
    ("assessment.mark_entry", ("course_offering_id", "component_id")),
    ("assessment.mark_entry", ("student_id",)),
    ("assessment.mark_entry_version", ("mark_entry_id", "version_no")),
    ("assessment.mark_entry_version", ("entered_by",)),
    ("assessment.mark_correction", ("mark_entry_id", "requested_at")),
    ("assessment.mark_correction", ("status",)),
    ("assessment.conflict_declaration", ("course_offering_id", "status")),
    ("assessment.conflict_declaration", ("faculty_person_id",)),
)

DOCUMENTED_CHECKS = {
    "attendance.session": {
        "ck_session_end_time": ("end_time", "start_time"),
    },
    "attendance.correction": {
        "ck_correction_new_status": ("new_status", "old_status"),
    },
    "attendance.summary": {
        "ck_summary_sessions_attended": (
            "sessions_attended", "sessions_conducted"
        ),
    },
    "assessment.scheme": {
        "ck_scheme_effective_window": (
            "effective_to_term_id", "effective_from_term_id"
        ),
    },
    "assessment.component": {
        "ck_component_parent_component_id": (
            "parent_component_id", "component_id"
        ),
    },
    "assessment.mark_entry_version": {
        "ck_mark_entry_version_marks_obtained": (
            "marks_obtained", "max_marks_snapshot"
        ),
    },
    "assessment.mark_correction": {
        "ck_mark_correction_to_version_id": (
            "to_version_id", "from_version_id"
        ),
    },
    "assessment.conflict_declaration": {
        "ck_conflict_declaration_reassigned_to_person_id": (
            "reassigned_to_person_id", "faculty_person_id"
        ),
    },
}


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_w4_has_thirteen_documented_entities() -> None:
    assert len(W4_ENTITIES) == 13


def test_w4_tables_exist(conn: psycopg.Connection) -> None:
    actual = {
        row[0]
        for row in _rows(
            conn,
            """
            SELECT n.nspname || '.' || c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname IN ('attendance', 'assessment')
            """,
        )
    }
    assert actual == W4_TABLES, {
        "missing": sorted(W4_TABLES - actual),
        "unexpected": sorted(actual - W4_TABLES),
    }


def test_w4_columns_match_the_data_dictionary(conn: psycopg.Connection) -> None:
    mismatches: list[str] = []
    for table in sorted(W4_TABLES):
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


def test_w4_primary_keys_match_the_dictionary(conn: psycopg.Connection) -> None:
    for table in sorted(W4_TABLES):
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


def test_w4_documented_single_column_foreign_keys_exist(
    conn: psycopg.Connection,
) -> None:
    for table in sorted(W4_TABLES):
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


def test_w4_composite_foreign_keys_are_enforced(conn: psycopg.Connection) -> None:
    expected = {
        (
            "attendance.record",
            ("course_registration_id", "student_id", "course_offering_id"),
            "student.course_registration",
            ("course_registration_id", "student_id", "course_offering_id"),
        ),
        (
            "attendance.record",
            ("session_id", "course_offering_id"),
            "attendance.session",
            ("session_id", "course_offering_id"),
        ),
    }
    actual = set()
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || t.relname AS source,
               array_agg(a.attname ORDER BY k.ord) AS source_columns,
               cn.nspname || '.' || ct.relname AS target,
               array_agg(ca.attname ORDER BY k.ord) AS target_columns
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class ct ON ct.oid = c.confrelid
        JOIN pg_namespace cn ON cn.oid = ct.relnamespace
        JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN unnest(c.confkey) WITH ORDINALITY AS fk(attnum, ord)
          ON fk.ord = k.ord
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        JOIN pg_attribute ca ON ca.attrelid = ct.oid AND ca.attnum = fk.attnum
        WHERE c.contype = 'f'
          AND n.nspname IN ('attendance', 'assessment')
          AND array_length(c.conkey, 1) > 1
        GROUP BY c.oid, n.nspname, t.relname, cn.nspname, ct.relname
        """,
    )
    for source, source_columns, target, target_columns in rows:
        actual.add((source, tuple(source_columns), target, tuple(target_columns)))
    assert actual == expected, {
        "missing": sorted(expected - actual),
        "unexpected": sorted(actual - expected),
    }


def test_w4_documented_unique_constraints_exist(conn: psycopg.Connection) -> None:
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
          AND n.nspname IN ('attendance', 'assessment')
        GROUP BY c.oid, n.nspname, t.relname, c.conname
        """,
    ):
        actual[(row[0], row[1])] = tuple(row[2])
    assert actual == DOCUMENTED_UNIQUES, {
        "missing": sorted(set(DOCUMENTED_UNIQUES) - set(actual)),
        "unexpected": sorted(set(actual) - set(DOCUMENTED_UNIQUES)),
        "wrong": {
            key: (DOCUMENTED_UNIQUES[key], actual[key])
            for key in set(actual) & set(DOCUMENTED_UNIQUES)
            if actual[key] != DOCUMENTED_UNIQUES[key]
        },
    }


def test_w4_documented_checks_are_enforced(conn: psycopg.Connection) -> None:
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
                missing.append((table, constraint, pieces := fragments, definition))
    assert missing == [], f"missing documented checks: {missing}"


def test_w4_enum_checks_are_enforced(conn: psycopg.Connection) -> None:
    missing = []
    for table in sorted(W4_TABLES):
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


def test_w4_documented_indexes_exist(conn: psycopg.Connection) -> None:
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
        WHERE n.nspname IN ('attendance', 'assessment') AND k.ord > 0
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


def test_w4_triggers_exist(conn: psycopg.Connection) -> None:
    rows = {
        tuple(row)
        for row in _rows(
            conn,
            """
            SELECT n.nspname, t.relname, trg.tgname
            FROM pg_trigger trg
            JOIN pg_class t ON t.oid = trg.tgrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE NOT trg.tgisinternal
              AND n.nspname IN ('attendance', 'assessment')
            """,
        )
    }
    assert rows == W4_TRIGGERS, {
        "missing": sorted(W4_TRIGGERS - rows),
        "unexpected": sorted(rows - W4_TRIGGERS),
    }

    [(deferrable, initially_deferred, is_constraint)] = _rows(
        conn,
        """
        SELECT trg.tgdeferrable, trg.tginitdeferred, trg.tgconstraint <> 0
        FROM pg_trigger trg
        JOIN pg_class t ON t.oid = trg.tgrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE NOT trg.tgisinternal AND n.nspname = 'assessment'
          AND t.relname = 'component' AND trg.tgname = 'trg_component_weight_sum'
        """,
    )
    assert (deferrable, initially_deferred, is_constraint) == (True, True, True)


def test_every_w4_foreign_key_has_a_leading_index(
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
          AND n.nspname IN ('attendance', 'assessment')
          AND NOT EXISTS (
              SELECT 1
              FROM pg_index i
              WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum
          )
        """,
    )
    assert rows == [], f"foreign keys without a leading index: {rows}"


def test_all_w4_tables_are_rls_enabled_and_forced(
    conn: psycopg.Connection,
) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || c.relname, c.relrowsecurity,
               c.relforcerowsecurity
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname IN ('attendance', 'assessment')
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
            WHERE schemaname IN ('attendance', 'assessment')
            """,
        )
    }
    for table in sorted(W4_TABLES):
        schema, name = table.split(".")
        matching = [
            policy
            for entry_schema, entry_table, policy in policies
            if entry_schema == schema
            and entry_table == name
            and policy.endswith("_owner_all")
        ]
        assert matching, f"{table}: missing owner policy"

    [(faculty_tables,)] = _rows(
        conn,
        """
        SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'faculty'
        """,
    )
    assert faculty_tables == 3


def test_w4_grant_boundaries(conn: psycopg.Connection) -> None:
    full_tables = (
        "attendance.session", "attendance.record", "attendance.summary",
        "attendance.eligibility_assessment", "assessment.scheme",
        "assessment.component", "assessment.schedule",
        "assessment.mark_entry", "assessment.mark_entry_version",
    )
    for table in full_tables:
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

    for table in ("attendance.correction", "assessment.mark_correction"):
        [(any_select,)] = _rows(
            conn,
            "SELECT has_any_column_privilege('app_erp', %s, 'SELECT')",
            (table,),
        )
        assert any_select is True
        [(reason,)] = _rows(
            conn,
            "SELECT has_column_privilege('app_erp', %s, 'reason', 'SELECT')",
            (table,),
        )
        assert reason is False, f"{table}.reason is class R"
        [(insert,)] = _rows(
            conn,
            "SELECT has_table_privilege('app_erp', %s, 'INSERT')",
            (table,),
        )
        assert insert is False

    for table in ("attendance.condonation_case", "assessment.conflict_declaration"):
        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            [(allowed,)] = _rows(
                conn,
                "SELECT has_table_privilege('app_erp', %s, %s)",
                (table, privilege),
            )
            assert allowed is False, f"app_erp has {privilege} on {table}"

    for role in APP_ROLES:
        if role == "app_erp":
            continue
        for table in sorted(W4_TABLES):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                [(allowed,)] = _rows(
                    conn,
                    "SELECT has_table_privilege(%s, %s, %s)",
                    (role, table, privilege),
                )
                assert allowed is False, f"{role} has {privilege} on {table}"
