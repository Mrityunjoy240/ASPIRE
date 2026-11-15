#!/usr/bin/env python
"""Preflight checks before applying the migrations to a managed Postgres.

The project was developed against a local PostgreSQL 16 cluster where the
bootstrap login is a superuser. Supabase's default ``postgres`` role is not a
superuser, so three things must be verified before migration 0001 is trusted:

* the required extensions are installable;
* the login can create roles;
* an existing owner role can be impersonated (needed for ``OWNER TO``).

Usage (PowerShell)::

    python database/supabase_preflight.py --url "postgresql://postgres:...@..."

This tool only reads the catalog and runs one rolled-back ``CREATE ROLE``
probe. It writes nothing. It never prints the DSN.
"""

from __future__ import annotations

import argparse
import secrets
import sys

import psycopg
from psycopg import sql

REQUIRED_EXTENSIONS = (
    "btree_gist",
    "pg_trgm",
    "unaccent",
    "pgcrypto",
    "pg_stat_statements",
)

OWNER_ROLES = (
    "owner_iam",
    "owner_core",
    "owner_academic",
    "owner_student",
    "owner_attendance",
    "owner_assessment",
    "owner_exam",
    "owner_faculty",
    "owner_finance",
    "owner_services",
    "owner_doc",
    "owner_knowledge",
    "owner_cip",
    "owner_policy",
    "owner_integration",
    "owner_ops",
    "owner_api",
)


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def ok(self, message: str) -> None:
        print(f"PASS  {message}")

    def warn(self, message: str) -> None:
        self.warnings += 1
        print(f"WARN  {message}")

    def fail(self, message: str) -> None:
        self.failures += 1
        print(f"FAIL  {message}")


def check_identity(connection: psycopg.Connection, report: Report) -> None:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT current_user,
                   r.rolsuper,
                   r.rolcreaterole,
                   r.rolcreatedb,
                   r.rolbypassrls,
                   current_setting('server_version')
            FROM pg_roles r
            WHERE r.rolname = current_user
            """
        )
        user, is_super, can_create_role, can_create_db, bypass_rls, version = (
            cur.fetchone()
        )

    print(f"INFO  server {version}; login {user}")
    print(
        f"INFO  superuser={is_super} createrole={can_create_role} "
        f"createdb={can_create_db} bypassrls={bypass_rls}"
    )

    if is_super or can_create_role:
        report.ok("login can create the schema-owner and runtime roles")
    else:
        report.fail(
            "login cannot create roles; migration 0001 will fail. Use the "
            "Supabase 'postgres' role or grant CREATEROLE."
        )

    if bypass_rls:
        report.warn(
            "login bypasses RLS. It must never be used as a runtime DSN; "
            "APP_DB_ERP_DSN must log in as app_erp."
        )


def check_extensions(connection: psycopg.Connection, report: Report) -> None:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT a.name, a.installed_version, a.default_version,
                   n.nspname
            FROM pg_available_extensions a
            LEFT JOIN pg_extension e ON e.extname = a.name
            LEFT JOIN pg_namespace n ON n.oid = e.extnamespace
            WHERE a.name = ANY(%s)
            """,
            (list(REQUIRED_EXTENSIONS),),
        )
        rows = {row[0]: row for row in cur.fetchall()}

    for name in REQUIRED_EXTENSIONS:
        row = rows.get(name)
        if row is None:
            report.fail(f"extension {name} is not available on this server")
            continue
        _name, installed, default, schema = row
        if installed:
            report.ok(f"extension {name} installed (version {installed}, schema {schema})")
        else:
            report.warn(
                f"extension {name} is available but not installed; migration "
                "0001 will install it into the first writable schema on the "
                "search_path. On Supabase that is normally fine, but installing "
                "into the 'extensions' schema is preferred."
            )


def check_roles(connection: psycopg.Connection, report: Report) -> None:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
            (list(OWNER_ROLES) + ["app_erp", "migration_owner"],),
        )
        existing = {row[0] for row in cur.fetchall()}

    missing = [name for name in OWNER_ROLES if name not in existing]
    if not missing:
        report.ok("all schema-owner roles already exist")
    else:
        report.ok(
            f"{len(missing)} of {len(OWNER_ROLES)} owner roles will be created "
            "by migration 0001"
        )

    if "app_erp" not in existing:
        report.ok("app_erp will be created by migration 0001 (set its password afterwards)")
    else:
        report.ok("app_erp already exists")

    if "owner_core" in existing:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_has_role(current_user, 'owner_core', 'SET')")
            can_set = cur.fetchone()[0]
        if can_set:
            report.ok("login can SET ROLE owner_core (needed for OWNER TO)")
        else:
            report.fail(
                "login cannot SET ROLE owner_core. Run, as an administrator: "
                "GRANT owner_core TO <login> WITH SET TRUE; or apply future "
                "migrations as migration_owner."
            )
    else:
        report.warn(
            "owner_core does not exist yet. After 0001, the migration login "
            "must be able to SET ROLE to every owner_* role. Applying the rest "
            "of the migrations as migration_owner is the supported path."
        )


def check_create_role(connection: psycopg.Connection, report: Report) -> None:
    probe = f"bcrec_preflight_{secrets.token_hex(6)}"
    try:
        with connection.transaction(force_rollback=True):
            with connection.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(probe))
                )
        report.ok("CREATE ROLE succeeded and was rolled back")
    except psycopg.errors.InsufficientPrivilege:
        report.fail("CREATE ROLE was refused; migration 0001 cannot bootstrap")
    except psycopg.Error as exc:
        report.fail(f"CREATE ROLE probe failed: {type(exc).__name__}: {exc}")


def check_row_security(connection: psycopg.Connection, report: Report) -> None:
    with connection.cursor() as cur:
        cur.execute("SHOW row_security")
        value = cur.fetchone()[0]
    if value == "on":
        report.ok("row_security is on")
    else:
        report.fail("row_security is off; RLS cannot protect tenant data")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Supabase/managed-Postgres preflight")
    parser.add_argument("--url", required=True, help="administrator connection URL")
    args = parser.parse_args(argv)

    report = Report()
    try:
        with psycopg.connect(args.url, connect_timeout=15) as connection:
            # DDL probes must be able to roll back.
            connection.autocommit = False
            check_identity(connection, report)
            check_extensions(connection, report)
            check_roles(connection, report)
            check_create_role(connection, report)
            check_row_security(connection, report)
    except psycopg.OperationalError as exc:
        print(f"FAIL  cannot connect: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print()
    if report.failures:
        print(
            f"{report.failures} blocker(s), {report.warnings} warning(s). "
            "Do not apply the migrations until every blocker is resolved."
        )
        return 1
    print(f"OK: no blockers, {report.warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
