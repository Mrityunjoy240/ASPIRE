"""W7 / Phase 9B API-key regression: hashed, scoped, revocable machine keys.

Every privilege assertion runs as the real ``app_erp`` role or inspects the
real catalog. The credential fixtures are inserted as ``owner_iam`` and the
authentication function is called as ``app_erp``.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from w1a_support import expect_error

RUNTIME_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
)

CLIENT_ID = "aaaaaaaa-0000-0000-0000-0000000000c1"
KEY_ID = "bbbbbbbb-0000-0000-0000-0000000000c1"
PREFIX = "0123456789ab"
SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def _hash(conn: psycopg.Connection, secret: str) -> bytes:
    with conn.cursor() as cur:
        cur.execute("SELECT digest(%s, 'sha256')", (secret,))
        return cur.fetchone()[0]


def _as(conn: psycopg.Connection, role: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"SET LOCAL ROLE {role}")


def _reset(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("RESET ROLE")


@pytest.fixture()
def api_key_fixture(conn: psycopg.Connection):
    """Create one active client, key, and scope as owner_iam."""

    secret_hash = _hash(conn, SECRET)
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.api_client (client_id, client_code, name)
            VALUES (%s, 'demo', 'Demo client')
            """,
            (CLIENT_ID,),
        )
        cur.execute(
            """
            INSERT INTO iam.api_key
                (api_key_id, client_id, key_prefix, secret_hash, label,
                 rate_limit_per_minute, expires_at)
            VALUES (%s, %s, %s, %s, 'test key', 60, now() + interval '30 days')
            """,
            (KEY_ID, CLIENT_ID, PREFIX, secret_hash),
        )
        cur.execute(
            "INSERT INTO iam.api_key_scope (api_key_id, scope_code) VALUES (%s, 'public.read')",
            (KEY_ID,),
        )
    _reset(conn)
    try:
        yield secret_hash
    finally:
        # Match the W1a fixtures: never leave the fixture data committed.
        conn.rollback()


def _call(conn: psycopg.Connection, prefix: str, secret_hash: bytes):
    _as(conn, "app_erp")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT api_key_id, client_id, client_code, scopes,
                       rate_limit_per_minute, expires_at
                FROM iam.authenticate_api_key(%s, %s)
                """,
                (prefix, secret_hash),
            )
            return cur.fetchall()
    finally:
        _reset(conn)


def test_api_key_tables_exist_with_forced_rls(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'iam'
              AND c.relname IN ('api_client', 'api_key', 'api_key_scope')
            ORDER BY c.relname
            """
        )
        rows = cur.fetchall()
    assert len(rows) == 3
    for name, enabled, forced in rows:
        assert enabled, name
        assert forced, name


def test_runtime_roles_have_no_api_key_table_privileges(
    conn: psycopg.Connection,
) -> None:
    with conn.cursor() as cur:
        for role in RUNTIME_ROLES:
            for table in ("api_client", "api_key", "api_key_scope"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    cur.execute(
                        "SELECT has_table_privilege(%s, %s, %s)",
                        (role, f"iam.{table}", privilege),
                    )
                    assert cur.fetchone()[0] is False, (role, table, privilege)

        for role in RUNTIME_ROLES:
            for table in ("api_client", "api_key", "api_key_scope"):
                cur.execute(
                    """
                    SELECT a.attname
                    FROM pg_attribute a
                    WHERE a.attrelid = to_regclass(%s)
                      AND a.attnum > 0
                      AND NOT a.attisdropped
                    """,
                    (f"iam.{table}",),
                )
                columns = [row[0] for row in cur.fetchall()]
                for column in columns:
                    for privilege in ("SELECT", "INSERT", "UPDATE"):
                        cur.execute(
                            "SELECT has_column_privilege(%s, %s, %s, %s)",
                            (role, f"iam.{table}", column, privilege),
                        )
                        assert cur.fetchone()[0] is False, (
                            role,
                            table,
                            column,
                            privilege,
                        )


def test_only_app_erp_can_execute_the_authentication_function(
    conn: psycopg.Connection,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT has_function_privilege('app_erp', "
            "'iam.authenticate_api_key(text, bytea)', 'EXECUTE')"
        )
        assert cur.fetchone()[0] is True

        for role in RUNTIME_ROLES:
            if role == "app_erp":
                continue
            cur.execute(
                "SELECT has_function_privilege(%s, "
                "'iam.authenticate_api_key(text, bytea)', 'EXECUTE')",
                (role,),
            )
            assert cur.fetchone()[0] is False, role

        cur.execute(
            """
            SELECT count(*)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            CROSS JOIN LATERAL aclexplode(
                coalesce(p.proacl, acldefault('f', p.proowner))
            ) a
            WHERE n.nspname = 'iam'
              AND p.proname = 'authenticate_api_key'
              AND a.grantee = 0
              AND a.privilege_type = 'EXECUTE'
            """
        )
        assert cur.fetchone()[0] == 0


def test_function_is_security_definer_with_pinned_search_path(
    conn: psycopg.Connection,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.prosecdef,
                   pg_get_userbyid(p.proowner),
                   p.proconfig
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'iam' AND p.proname = 'authenticate_api_key'
            """
        )
        prosecdef, owner, proconfig = cur.fetchone()
    assert prosecdef is True
    assert owner == "owner_iam"
    assert proconfig is not None
    assert any(item.startswith("search_path=") for item in proconfig)


def test_valid_key_authenticates_as_a_client(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    rows = _call(conn, PREFIX, api_key_fixture)
    assert len(rows) == 1
    api_key_id, client_id, client_code, scopes, rate_limit, expires_at = rows[0]
    assert str(api_key_id) == KEY_ID
    assert str(client_id) == CLIENT_ID
    assert client_code == "demo"
    assert scopes == ["public.read"]
    assert rate_limit == 60
    assert expires_at is not None


def test_wrong_secret_returns_no_rows(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    assert _call(conn, PREFIX, _hash(conn, "wrong-secret")) == []


def test_unknown_prefix_returns_no_rows(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    assert _call(conn, "ffffffffffff", api_key_fixture) == []


def test_expired_key_returns_no_rows(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        # The table correctly forbids a key whose expiry precedes its creation.
        # Simulate an aged key instead of violating that invariant.
        cur.execute(
            "UPDATE iam.api_key "
            "SET created_at = now() - interval '2 days', "
            "    expires_at = now() - interval '1 day' "
            "WHERE api_key_id = %s",
            (KEY_ID,),
        )
    _reset(conn)
    assert _call(conn, PREFIX, api_key_fixture) == []


def test_revoked_key_returns_no_rows(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE iam.api_key SET revoked_at = now() WHERE api_key_id = %s",
            (KEY_ID,),
        )
    _reset(conn)
    assert _call(conn, PREFIX, api_key_fixture) == []


def test_inactive_client_returns_no_rows(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE iam.api_client SET is_active = false WHERE client_id = %s",
            (CLIENT_ID,),
        )
    _reset(conn)
    assert _call(conn, PREFIX, api_key_fixture) == []


def test_key_without_scopes_authenticates_with_empty_scopes(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM iam.api_key_scope WHERE api_key_id = %s", (KEY_ID,)
        )
    _reset(conn)
    rows = _call(conn, PREFIX, api_key_fixture)
    assert len(rows) == 1
    assert rows[0][3] == []


def test_last_used_at_is_touched(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _call(conn, PREFIX, api_key_fixture)
    _as(conn, "owner_iam")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_used_at FROM iam.api_key WHERE api_key_id = %s",
            (KEY_ID,),
        )
        assert cur.fetchone()[0] is not None
    _reset(conn)


def test_app_erp_cannot_read_or_write_the_api_key_tables(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    _as(conn, "app_erp")
    try:
        expect_error(conn, "SELECT 1 FROM iam.api_key LIMIT 1", contains="permission denied")
        expect_error(
            conn,
            "INSERT INTO iam.api_client (client_code, name) VALUES ('x', 'X')",
            contains="permission denied",
        )
        expect_error(
            conn,
            "UPDATE iam.api_key SET label = 'x' WHERE api_key_id = %s",
            (KEY_ID,),
            contains="permission denied",
        )
        expect_error(
            conn,
            "DELETE FROM iam.api_key_scope WHERE api_key_id = %s",
            (KEY_ID,),
            contains="permission denied",
        )
    finally:
        _reset(conn)


@pytest.fixture()
def app_erp_conn(fresh_db_url: str):
    password = os.environ.get("BCREC_ROLE_PASSWORD")
    if not password:
        pytest.skip("BCREC_ROLE_PASSWORD is not set")
    params = conninfo_to_dict(fresh_db_url)
    params["user"] = "app_erp"
    params["password"] = password
    params["connect_timeout"] = 5
    dsn = make_conninfo(**params)
    with psycopg.connect(dsn, autocommit=True) as connection:
        yield connection


def test_app_erp_login_cannot_set_role_to_the_owner(
    app_erp_conn: psycopg.Connection,
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with app_erp_conn.cursor() as cur:
            cur.execute("SET ROLE owner_iam")


def test_expired_timestamp_is_utc_aware(
    conn: psycopg.Connection, api_key_fixture: bytes
) -> None:
    rows = _call(conn, PREFIX, api_key_fixture)
    expires_at = rows[0][5]
    assert expires_at.tzinfo is not None
    assert expires_at > datetime.now(UTC)
    assert expires_at < datetime.now(UTC) + timedelta(days=31)
