"""Checkpoint 1 plus W1a: a clean database can be created from scratch.

Every assertion here is derived from the approved design, not from the
implementation: schema/owner map (POSTGRES_ARCHITECTURE 3.1), required
extensions (3.2), role model (4.1), and the W1a wave boundary
(MVP_DEPENDENCY_MAP 8.1).
"""

from __future__ import annotations

import psycopg

from design import IMPLEMENTED_TABLES

EXPECTED_SCHEMA_OWNERS = {
    "iam": "owner_iam",
    "core": "owner_core",
    "academic": "owner_academic",
    "student": "owner_student",
    "attendance": "owner_attendance",
    "assessment": "owner_assessment",
    "exam": "owner_exam",
    "faculty": "owner_faculty",
    "finance": "owner_finance",
    "services": "owner_services",
    "doc": "owner_doc",
    "knowledge": "owner_knowledge",
    "cip": "owner_cip",
    "policy": "owner_policy",
    "integration": "owner_integration",
    "ops": "owner_ops",
    "api": "owner_api",
}

REQUIRED_EXTENSIONS = {
    "btree_gist",
    "pg_trgm",
    "unaccent",
    "pgcrypto",
    "pg_stat_statements",
}

OWNER_ROLES = set(EXPECTED_SCHEMA_OWNERS.values())
GROUP_ROLES = {"g_erp", "g_cip", "g_integration", "g_worker", "g_reporting"}
APP_ROLES = {"app_erp", "app_cip", "app_integration", "app_worker", "app_reporting"}
SPECIAL_LOGIN_ROLES = {"audit_writer", "migration_owner", "dba"}


def _rows(conn: psycopg.Connection, query: str, params=None) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def test_server_version_is_supported(conn: psycopg.Connection) -> None:
    [(version_num,)] = _rows(conn, "SHOW server_version_num")
    major = int(version_num) // 10000
    assert major in (16, 17), f"PostgreSQL {major} is outside the approved 16/17 target"


def test_required_extensions_are_installed(conn: psycopg.Connection) -> None:
    installed = {row[0] for row in _rows(conn, "SELECT extname FROM pg_extension")}
    assert REQUIRED_EXTENSIONS <= installed, REQUIRED_EXTENSIONS - installed


def test_pgvector_is_not_installed(conn: psycopg.Connection) -> None:
    installed = {row[0] for row in _rows(conn, "SELECT extname FROM pg_extension")}
    assert "vector" not in installed, "OD-06 is open; the vector extension must not be installed"


def test_all_design_schemas_exist_with_documented_owners(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT nspname, pg_get_userbyid(nspowner)
        FROM pg_namespace
        WHERE nspname = ANY(%s)
        """,
        (list(EXPECTED_SCHEMA_OWNERS),),
    )
    actual = dict(rows)
    assert actual == EXPECTED_SCHEMA_OWNERS


def test_schema_owner_roles_are_nologin(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        "SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname = ANY(%s)",
        (list(OWNER_ROLES),),
    )
    assert {r[0] for r in rows} == OWNER_ROLES
    for role, can_login, is_super in rows:
        assert can_login is False, f"{role} must not be a login role"
        assert is_super is False, f"{role} must not be a superuser"


def test_group_roles_are_nologin(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        "SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = ANY(%s)",
        (list(GROUP_ROLES),),
    )
    assert {r[0] for r in rows} == GROUP_ROLES
    assert all(can_login is False for _role, can_login in rows)


def test_application_roles_are_login_and_not_superuser(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        "SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname = ANY(%s)",
        (list(APP_ROLES | SPECIAL_LOGIN_ROLES),),
    )
    assert {r[0] for r in rows} == APP_ROLES | SPECIAL_LOGIN_ROLES
    for role, can_login, is_super in rows:
        assert can_login is True, f"{role} must be a login role"
        assert is_super is False, f"{role} must not be a superuser"


def test_application_roles_inherit_their_group_role(conn: psycopg.Connection) -> None:
    expected = {
        "app_erp": "g_erp",
        "app_cip": "g_cip",
        "app_integration": "g_integration",
        "app_worker": "g_worker",
        "app_reporting": "g_reporting",
    }
    rows = _rows(
        conn,
        """
        SELECT member.rolname, parent.rolname
        FROM pg_auth_members m
        JOIN pg_roles member ON member.oid = m.member
        JOIN pg_roles parent ON parent.oid = m.roleid
        WHERE member.rolname = ANY(%s)
        """,
        (list(expected),),
    )
    actual = dict(rows)
    for app_role, group_role in expected.items():
        assert actual.get(app_role) == group_role


def test_migration_owner_can_assume_every_schema_owner(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT parent.rolname
        FROM pg_auth_members m
        JOIN pg_roles member ON member.oid = m.member
        JOIN pg_roles parent ON parent.oid = m.roleid
        WHERE member.rolname = 'migration_owner'
        """,
    )
    granted = {row[0] for row in rows}
    assert OWNER_ROLES <= granted, OWNER_ROLES - granted


def test_public_has_no_usage_on_application_schemas(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname, a.privilege_type
        FROM pg_namespace n,
             aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
        WHERE n.nspname = ANY(%s)
          AND a.grantee = 0
        """,
        (list(EXPECTED_SCHEMA_OWNERS),),
    )
    assert rows == [], f"PUBLIC still has schema privileges: {rows}"


def test_schema_usage_follows_the_application_boundary(conn: psycopg.Connection) -> None:
    checks = {
        ("app_erp", "student"): True,
        ("app_erp", "api"): True,
        ("app_cip", "knowledge"): True,
        ("app_cip", "student"): False,
        ("app_cip", "exam"): False,
        ("app_reporting", "api"): True,
        ("app_reporting", "iam"): False,
        ("audit_writer", "ops"): True,
    }
    for (role, schema), expected in checks.items():
        [(actual,)] = _rows(
            conn, "SELECT has_schema_privilege(%s, %s, 'USAGE')", (role, schema)
        )
        assert actual is expected, f"{role} USAGE on {schema}: expected {expected}, got {actual}"


def test_database_contains_only_the_implemented_domain_tables(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        """
        SELECT n.nspname || '.' || c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'public')
        ORDER BY 1
        """,
    )
    actual = {row[0] for row in rows}
    assert actual == IMPLEMENTED_TABLES, {
        "missing": sorted(IMPLEMENTED_TABLES - actual),
        "unexpected": sorted(actual - IMPLEMENTED_TABLES),
    }


def test_migration_history_is_recorded(conn: psycopg.Connection) -> None:
    rows = _rows(
        conn,
        "SELECT version, name, checksum, applied_at, applied_by FROM public.schema_migration ORDER BY version",
    )
    assert [(row[0], row[1]) for row in rows] == [
        ("0001", "bootstrap"),
        ("0002", "w1a_schema"),
        ("0003", "w1a_security"),
        ("0004", "w1a_fk_index"),
        ("0005", "w1a_org_path_trigger"),
        ("0006", "w1a_has_permission"),
        ("0007", "w1a_review_remediation"),
        ("0008", "w1b_academic"),
        ("0009", "w2_student"),
        ("0010", "w3_faculty"),
        ("0011", "w4_attendance"),
        ("0012", "w4_assessment"),
        ("0013", "w5_exam"),
        ("0014", "w5_doc_notice"),
        ("0015", "w6_knowledge"),
        ("0016", "w6_cip"),
        ("0017", "w7_iam_separation"),
        ("0018", "w7_trigger_hardening"),
        ("0019", "w7_api_keys"),
        ("0020", "w7_api_key_function_fix"),
        ("0021", "w7_api_key_fk_indexes"),
    ]
    for version, name, checksum, applied_at, applied_by in rows:
        assert len(checksum) == 64, f"{version}: checksum is not SHA-256"
        assert applied_at is not None, f"{version}: applied_at is missing"
        assert applied_by, f"{version}: applied_by is missing"


def test_expected_migration_files_are_present() -> None:
    from pathlib import Path

    migrations = Path(__file__).resolve().parents[1] / "migrations"
    names = sorted(p.name for p in migrations.glob("*.sql"))
    assert names == [
        "0001_bootstrap.sql",
        "0002_w1a_schema.sql",
        "0003_w1a_security.sql",
        "0004_w1a_fk_index.sql",
        "0005_w1a_org_path_trigger.sql",
        "0006_w1a_has_permission.sql",
        "0007_w1a_review_remediation.sql",
        "0008_w1b_academic.sql",
        "0009_w2_student.sql",
        "0010_w3_faculty.sql",
        "0011_w4_attendance.sql",
        "0012_w4_assessment.sql",
        "0013_w5_exam.sql",
        "0014_w5_doc_notice.sql",
        "0015_w6_knowledge.sql",
        "0016_w6_cip.sql",
        "0017_w7_iam_separation.sql",
        "0018_w7_trigger_hardening.sql",
        "0019_w7_api_keys.sql",
        "0020_w7_api_key_function_fix.sql",
        "0021_w7_api_key_fk_indexes.sql",
    ]
