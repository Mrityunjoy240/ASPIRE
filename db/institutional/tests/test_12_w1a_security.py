"""W1a security: RLS boundaries, session helpers, and role grants."""

from __future__ import annotations

import psycopg

from design import RLS_TABLES, W1A_SCHEMAS, W1A_TABLES
from w1a_support import (
    A1,
    ASSIGNMENT,
    DOC_CONFIDENTIAL,
    DOC_INTERNAL,
    DOC_PUBLIC,
    INSTITUTION,
    ORG_ROOT,
    P1,
    P2,
    ROLE,
    RULE,
    VERSION_CONFIDENTIAL,
    VERSION_INTERNAL,
    VERSION_PUBLIC,
    expect_error,
    w1a_base,
)

_ = w1a_base  # imported fixture

APP_ROLES = ("app_erp", "app_cip", "app_integration", "app_worker", "app_reporting")


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def _ids(rows: list[tuple]) -> list[str]:
    return [str(row[0]) for row in rows]


def _set_session(conn: psycopg.Connection, person: str | None, account: str | None = None,
                 assignment: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.person_id', %s, true)", (person or "",))
        cur.execute("SELECT set_config('app.account_id', %s, true)", (account or "",))
        cur.execute(
            "SELECT set_config('app.role_assignment_id', %s, true)", (assignment or "",)
        )


def test_session_helpers_read_the_documented_settings(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT iam.current_person_id(),
                   iam.current_account_id(),
                   iam.current_role_assignment_id()
            """
        )
        assert tuple(str(value) for value in cur.fetchone()) == (P1, A1, ASSIGNMENT)


def test_same_institution_checks_existence(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT iam.same_institution(%s)", (INSTITUTION,))
        assert cur.fetchone() == (True,)
        cur.execute("SELECT iam.same_institution(%s)", ("99999999-9999-9999-9999-999999999999",))
        assert cur.fetchone() == (False,)


def test_has_permission_requires_an_active_assignment_and_exact_scope(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT iam.has_permission('test.read', 'institution', %s)", (INSTITUTION,)
        )
        assert cur.fetchone() == (True,)
        cur.execute(
            "SELECT iam.has_permission('test.read', 'institution', %s)",
            ("99999999-9999-9999-9999-999999999999",),
        )
        assert cur.fetchone() == (False,)
        cur.execute(
            "SELECT iam.has_permission('other.read', 'institution', %s)", (INSTITUTION,)
        )
        assert cur.fetchone() == (False,)
        cur.execute("SELECT iam.has_permission('test.read', 'org_unit', %s)", (ORG_ROOT,))
        assert cur.fetchone() == (False,)

        cur.execute(
            """
            INSERT INTO iam.role_assignment
                (role_assignment_id, person_id, role_id, scope_type, scope_key,
                 org_unit_id, valid_from, valid_to, status)
            VALUES ('66666666-6666-6666-6666-666666666662', %s, %s, 'org_unit', %s,
                    %s, CURRENT_DATE - 10, CURRENT_DATE - 1, 'active')
            """,
            (P1, ROLE, ORG_ROOT, ORG_ROOT),
        )
        cur.execute("SELECT set_config('app.role_assignment_id', '66666666-6666-6666-6666-666666666662', true)")
        cur.execute("SELECT iam.has_permission('test.read', 'org_unit', %s)", (ORG_ROOT,))
        assert cur.fetchone() == (False,), "an expired assignment must not grant permission"

        cur.execute(
            """
            UPDATE iam.permission SET is_active = false WHERE permission_code = 'test.read'
            """
        )
        cur.execute("SELECT set_config('app.role_assignment_id', %s, true)", (ASSIGNMENT,))
        cur.execute(
            "SELECT iam.has_permission('test.read', 'institution', %s)", (INSTITUTION,)
        )
        assert cur.fetchone() == (False,), "an inactive permission must not grant access"


def test_self_rls_limits_person_account_and_assignment_visibility(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.person_contact (person_id, contact_type, value)
            VALUES (%s, 'email', 'one@example.com'), (%s, 'email', 'two@example.com')
            """,
            (P1, P2),
        )

    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
        cur.execute("SELECT person_id FROM iam.person ORDER BY person_id")
        assert _ids(cur.fetchall()) == [P1]
        cur.execute("SELECT account_id FROM iam.identity_account ORDER BY account_id")
        assert _ids(cur.fetchall()) == [A1]
        cur.execute(
            "SELECT role_assignment_id FROM iam.role_assignment ORDER BY role_assignment_id"
        )
        assert _ids(cur.fetchall()) == [ASSIGNMENT]
        cur.execute("SELECT person_id FROM iam.person_contact ORDER BY person_id")
        assert _ids(cur.fetchall()) == [P1]
        cur.execute("RESET ROLE")


def test_document_rls_applies_the_classification_ladder(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        cur.execute("SELECT document_id FROM doc.document ORDER BY document_id")
        assert _ids(cur.fetchall()) == [DOC_PUBLIC, DOC_INTERNAL]
        cur.execute(
            "SELECT document_version_id FROM doc.document_version ORDER BY document_version_id"
        )
        assert _ids(cur.fetchall()) == [VERSION_PUBLIC, VERSION_INTERNAL]
        cur.execute("SELECT set_config('app.person_id', '', true)")
        cur.execute("SELECT document_id FROM doc.document ORDER BY document_id")
        assert _ids(cur.fetchall()) == [DOC_PUBLIC], (
            "an unauthenticated session must see only P-classified documents"
        )
        cur.execute("RESET ROLE")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM doc.document WHERE document_id = %s",
            (DOC_CONFIDENTIAL,),
        )
        assert cur.fetchone() == (1,), "the confidential document still exists for its owners"
        cur.execute(
            "SELECT count(*) FROM doc.document_version WHERE document_version_id = %s",
            (VERSION_CONFIDENTIAL,),
        )
        assert cur.fetchone() == (1,)


def test_document_relation_rls_requires_both_endpoints_to_be_visible(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO doc.document_relation
                (from_version_id, to_version_id, relation_type)
            VALUES (%s, %s, 'attachment'),
                   (%s, %s, 'attachment')
            """,
            (VERSION_PUBLIC, VERSION_INTERNAL, VERSION_PUBLIC, VERSION_CONFIDENTIAL),
        )

    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
        cur.execute(
            """
            SELECT from_version_id, to_version_id
            FROM doc.document_relation
            ORDER BY to_version_id
            """
        )
        assert [tuple(str(value) for value in row) for row in cur.fetchall()] == [
            (VERSION_PUBLIC, VERSION_INTERNAL)
        ], "a relation is visible only when both endpoint versions are visible"

        cur.execute("SELECT set_config('app.person_id', '', true)")
        cur.execute("SELECT count(*) FROM doc.document_relation")
        assert cur.fetchone() == (0,), (
            "an unauthenticated session must not see relations to non-public versions"
        )
        cur.execute("RESET ROLE")


def test_rls_denies_writes_when_no_write_policy_exists(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    _set_session(conn, P1, A1, ASSIGNMENT)
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
    expect_error(
        conn,
        "INSERT INTO iam.person (legal_name) VALUES ('Unauthorised')",
        contains="row-level security",
    )
    with conn.cursor() as cur:
        cur.execute("UPDATE iam.person SET legal_name = 'Changed' WHERE person_id = %s", (P1,))
        assert cur.rowcount == 0, "an UPDATE without a policy must affect no row"
        cur.execute("RESET ROLE")
        cur.execute("SELECT legal_name FROM iam.person WHERE person_id = %s", (P1,))
        assert cur.fetchone() == ("Person One",)


def test_audit_writer_can_insert_but_cannot_read(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE audit_writer")
        cur.execute(
            "INSERT INTO ops.audit_event (action, record_hash) VALUES ('audit.test', %s)",
            ("a" * 64,),
        )
    expect_error(
        conn,
        "SELECT count(*) FROM ops.audit_event",
        contains="permission denied",
    )
    with conn.cursor() as cur:
        cur.execute("RESET ROLE")


def test_cip_cannot_write_documents(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_cip")
    expect_error(
        conn,
        """
        INSERT INTO doc.document (title, document_type, issuer_name, document_date)
        VALUES ('Unauthorised', 'other', 'CIP', CURRENT_DATE)
        """,
        contains="permission denied",
    )
    with conn.cursor() as cur:
        cur.execute("RESET ROLE")


def test_grants_follow_the_documented_application_boundary(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    checks = {
        ("app_erp", "iam.person", "INSERT"): False,
        ("app_erp", "iam.person", "UPDATE"): False,
        ("app_erp", "iam.person", "DELETE"): False,
        ("app_erp", "ops.audit_event", "SELECT"): False,
        ("app_erp", "integration.sync_run", "SELECT"): False,
        ("app_cip", "doc.document", "SELECT"): True,
        ("app_cip", "doc.document", "INSERT"): False,
        ("app_cip", "policy.rule", "SELECT"): True,
        ("app_cip", "ops.audit_event", "SELECT"): False,
        ("app_integration", "integration.sync_run", "INSERT"): True,
        ("app_integration", "integration.sync_run", "DELETE"): False,
        ("app_integration", "iam.person", "SELECT"): False,
        ("app_worker", "integration.outbox_event", "SELECT"): True,
        ("app_worker", "integration.outbox_event", "INSERT"): False,
        ("audit_writer", "ops.audit_event", "INSERT"): True,
        ("audit_writer", "ops.audit_event", "SELECT"): False,
        ("audit_writer", "ops.audit_event", "UPDATE"): False,
        ("audit_writer", "ops.audit_event", "DELETE"): False,
        ("app_reporting", "iam.person", "SELECT"): False,
    }
    for (role, table, privilege), expected in checks.items():
        [(actual,)] = _rows(
            conn,
            "SELECT has_table_privilege(%s, %s, %s)",
            (role, table, privilege),
        )
        assert actual is expected, f"{role} {privilege} on {table}: {actual} != {expected}"

    # Column-level grants protect the high-sensitivity person fields.
    for role, table, column, privilege, expected in (
        ("app_erp", "iam.person", "legal_name", "SELECT", True),
        ("app_erp", "iam.person", "legal_name", "INSERT", True),
        ("app_erp", "iam.person", "legal_name", "UPDATE", True),
        ("app_erp", "iam.person", "gender", "SELECT", False),
        ("app_erp", "iam.person", "gender", "INSERT", False),
        ("app_erp", "iam.person", "gender", "UPDATE", False),
        ("app_erp", "iam.person", "blood_group", "SELECT", False),
        ("app_erp", "iam.person", "blood_group", "INSERT", False),
        ("app_erp", "iam.person", "blood_group", "UPDATE", False),
        ("app_erp", "iam.person", "notes", "SELECT", False),
        ("app_erp", "iam.person", "notes", "INSERT", False),
        ("app_erp", "iam.person", "notes", "UPDATE", False),
        ("app_erp", "iam.identity_account", "disabled_reason", "SELECT", False),
        ("app_erp", "iam.identity_account", "disabled_reason", "INSERT", False),
        ("app_erp", "iam.identity_account", "disabled_reason", "UPDATE", False),
        ("app_erp", "iam.identity_account", "email", "INSERT", True),
        ("app_erp", "iam.identity_account", "email", "UPDATE", True),
        ("app_worker", "integration.outbox_event", "status", "UPDATE", True),
        ("app_worker", "integration.outbox_event", "event_type", "UPDATE", False),
    ):
        [(actual,)] = _rows(
            conn,
            "SELECT has_column_privilege(%s, %s, %s, %s)",
            (role, table, column, privilege),
        )
        assert actual is expected, f"{role} {privilege} {table}.{column}: {actual} != {expected}"

    # No runtime application role may delete W1a data.
    for role in (*APP_ROLES, "audit_writer"):
        for table in sorted(W1A_TABLES):
            [(actual,)] = _rows(
                conn,
                "SELECT has_table_privilege(%s, %s, 'DELETE')",
                (role, table),
            )
            assert actual is False, f"{role} unexpectedly has DELETE on {table}"


def test_app_erp_cannot_directly_write_sensitive_columns(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    """Review remediation: the R/G columns are denied at the grant level.

    RLS also has no write policy for app_erp, but these assertions prove the
    denial is a privilege failure, not only a row-level-security side effect.
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")

    attempts = (
        (
            "UPDATE iam.person SET gender = 'female' WHERE person_id = %s",
            (P1,),
        ),
        (
            "UPDATE iam.person SET blood_group = 'A+' WHERE person_id = %s",
            (P1,),
        ),
        (
            "UPDATE iam.person SET notes = 'sensitive' WHERE person_id = %s",
            (P1,),
        ),
        (
            "INSERT INTO iam.person (legal_name, date_of_birth, gender) "
            "VALUES ('Denied Person', DATE '2000-01-01', 'female')",
            None,
        ),
        (
            "INSERT INTO iam.person (legal_name, date_of_birth, notes) "
            "VALUES ('Denied Person', DATE '2000-01-01', 'sensitive')",
            None,
        ),
        (
            "UPDATE iam.identity_account SET disabled_reason = 'sensitive' "
            "WHERE account_id = %s",
            (A1,),
        ),
    )
    for statement, params in attempts:
        expect_error(conn, statement, params, contains="permission denied")

    with conn.cursor() as cur:
        cur.execute("RESET ROLE")


def test_only_owner_roles_have_all_command_policies(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT schemaname || '.' || tablename, policyname, roles, cmd
        FROM pg_policies
        WHERE schemaname = ANY(%s)
        """,
        (list(W1A_SCHEMAS),),
    )
    assert {f"{schema}.{table}" for schema, table in (r[0].split(".") for r in rows)} >= RLS_TABLES
    application_all = [
        row for row in rows if row[3] == "ALL" and not set(row[2]) <= {
            f"owner_{row[0].split('.')[0]}"
        }
    ]
    assert application_all == [], (
        f"application roles must not receive ALL policies: {application_all}"
    )
    for table in RLS_TABLES:
        table_rows = [row for row in rows if row[0] == table]
        assert any(row[3] == "ALL" for row in table_rows), f"{table}: owner policy missing"
        assert any(row[3] == "SELECT" for row in table_rows), f"{table}: SELECT policy missing"
