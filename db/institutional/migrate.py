#!/usr/bin/env python
"""Forward-only SQL migration runner for the BCREC Central database.

Design basis: docs/architecture/database-design-v1/POSTGRES_ARCHITECTURE.md
section 17 (forward-only, one logical change per migration, tested).

The runner is infrastructure, not a domain framework. It applies the numbered
SQL files in ``database/migrations`` in lexical order, one transaction per
file, and records a SHA-256 checksum in ``public.schema_migration``.

Usage (PowerShell):

    python database/migrate.py status
    python database/migrate.py apply
    python database/migrate.py verify
    python database/migrate.py provision-dev-roles   # dev only, needs BCREC_ROLE_PASSWORD

A DATABASE_URL environment variable is required unless --url is supplied. The
optional ``database/config/.env`` file is read first; it is git-ignored and must
never contain a committed credential.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

DATABASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = DATABASE_DIR / "migrations"
ENV_FILE = DATABASE_DIR / "config" / ".env"
HISTORY_TABLE = "public.schema_migration"
ADVISORY_LOCK_KEY = 0x4243524543  # "BCREC"

# Roles created by 0001_bootstrap.sql. Keep this list in sync with that file.
LOGIN_ROLES = (
    "app_erp",
    "app_cip",
    "app_integration",
    "app_worker",
    "app_reporting",
    "audit_writer",
    "migration_owner",
    "dba",
)


def load_env_file() -> None:
    """Load simple KEY=VALUE lines from config/.env without overriding the shell."""
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    load_env_file()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "ERROR: DATABASE_URL is not set. Copy database/config/.env.example to "
            "database/config/.env and fill it in, or pass --url."
        )
    return url


def discover_migrations(directory: Path) -> list[tuple[str, str, Path]]:
    if not directory.is_dir():
        sys.exit(f"ERROR: migration directory not found: {directory}")
    items: list[tuple[str, str, Path]] = []
    seen: dict[str, Path] = {}
    for path in sorted(directory.glob("*.sql")):
        version, sep, name = path.stem.partition("_")
        if not sep or not version.isdigit():
            sys.exit(f"ERROR: migration name must be NNNN_description.sql: {path.name}")
        if version in seen:
            sys.exit(f"ERROR: duplicate migration version {version}: {seen[version].name} and {path.name}")
        seen[version] = path
        items.append((version, name, path))
    return items


def resolve_migrations_dir(args: argparse.Namespace) -> Path:
    explicit = getattr(args, "migrations_dir", None)
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("BCREC_MIGRATIONS_DIR")
    if env:
        return Path(env).resolve()
    return MIGRATIONS_DIR


def ensure_history_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} (
                version    text        PRIMARY KEY,
                name       text        NOT NULL,
                checksum   text        NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now(),
                applied_by text        NOT NULL DEFAULT current_user
            )
            """
        )
    conn.commit()


def applied_migrations(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT version, checksum FROM {HISTORY_TABLE}")
        return dict(cur.fetchall())


def cmd_apply(args: argparse.Namespace) -> int:
    url = resolve_url(args.url)
    conn = psycopg.connect(url)
    try:
        ensure_history_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
        conn.commit()

        applied = applied_migrations(conn)
        pending = 0
        migrations_dir = resolve_migrations_dir(args)
        for version, name, path in discover_migrations(migrations_dir):
            payload = path.read_bytes()
            checksum = hashlib.sha256(payload).hexdigest()
            if version in applied:
                if applied[version] != checksum:
                    print(
                        f"ERROR: checksum mismatch for {path.name}. "
                        "An applied migration must never be edited; add a new migration.",
                        file=sys.stderr,
                    )
                    return 1
                print(f"skip    {path.name} (already applied)")
                continue
            sql = payload.decode("utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    f"INSERT INTO {HISTORY_TABLE} (version, name, checksum) VALUES (%s, %s, %s)",
                    (version, name, checksum),
                )
            conn.commit()
            pending += 1
            print(f"applied {path.name}")
        print(f"OK: {pending} migration(s) applied.")
        return 0
    except Exception as exc:  # noqa: BLE001 - surface the database error verbatim
        conn.rollback()
        print(f"ERROR: migration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))
            conn.commit()
        except Exception:  # noqa: BLE001 - connection may already be broken
            pass
        conn.close()


def cmd_status(args: argparse.Namespace) -> int:
    url = resolve_url(args.url)
    with psycopg.connect(url) as conn:
        ensure_history_table(conn)
        applied = applied_migrations(conn)
        rows = []
        migrations_dir = resolve_migrations_dir(args)
        for version, name, path in discover_migrations(migrations_dir):
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            if version not in applied:
                state = "pending"
            elif applied[version] != checksum:
                state = "CHECKSUM-MISMATCH"
            else:
                state = "applied"
            rows.append((version, path.name, state))
        width = max((len(r[1]) for r in rows), default=10)
        for version, filename, state in rows:
            print(f"{version}  {filename:<{width}}  {state}")
        if not rows:
            print("no migrations discovered")
        return 1 if any(r[2] == "CHECKSUM-MISMATCH" for r in rows) else 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Fail unless every discovered migration is applied with a matching checksum."""
    url = resolve_url(args.url)
    with psycopg.connect(url) as conn:
        ensure_history_table(conn)
        applied = applied_migrations(conn)
        problems = []
        migrations_dir = resolve_migrations_dir(args)
        discovered = discover_migrations(migrations_dir)
        for version, _name, path in discovered:
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            if version not in applied:
                problems.append(f"pending migration: {path.name}")
            elif applied[version] != checksum:
                problems.append(f"checksum mismatch: {path.name}")
        extra = sorted(set(applied) - {v for v, _n, _p in discovered})
        for version in extra:
            problems.append(f"applied migration not present in the repository: {version}")
        if problems:
            for problem in problems:
                print(f"FAIL: {problem}", file=sys.stderr)
            return 1
        print(f"OK: {len(applied)} migration(s) applied and checksums match.")
        return 0


def cmd_provision_dev_roles(args: argparse.Namespace) -> int:
    """Development convenience: give login roles a password from the environment.

    Never run this in production. The password is read from BCREC_ROLE_PASSWORD
    and is never stored in the repository.
    """
    password = os.environ.get("BCREC_ROLE_PASSWORD")
    if not password:
        print("ERROR: BCREC_ROLE_PASSWORD is not set.", file=sys.stderr)
        return 1
    url = resolve_url(args.url)
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for role in LOGIN_ROLES:
                cur.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(role),
                        sql.Literal(password),
                    )
                )
                print(f"password set for {role}")
    print("OK: development role passwords set.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BCREC Central database migration runner")
    parser.add_argument("--url", help="PostgreSQL connection URL (defaults to DATABASE_URL)")
    parser.add_argument(
        "--migrations-dir",
        help="Directory of NNNN_*.sql files (defaults to database/migrations)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("apply", "status", "verify", "provision-dev-roles"):
        child = sub.add_parser(name)
        # Accept --url after the subcommand as well as before it.
        child.add_argument("--url", default=argparse.SUPPRESS)
        child.add_argument("--migrations-dir", default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    handlers = {
        "apply": cmd_apply,
        "status": cmd_status,
        "verify": cmd_verify,
        "provision-dev-roles": cmd_provision_dev_roles,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
