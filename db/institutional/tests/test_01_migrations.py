"""Checkpoint 1: migration ordering, repeatability, and checksum protection."""

from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

from conftest import run_migrate

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def test_migration_files_are_ordered_and_unique() -> None:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert files, "no migration files found"
    versions = []
    for path in files:
        version, sep, name = path.stem.partition("_")
        assert sep and name, f"bad migration name: {path.name}"
        assert version.isdigit() and len(version) == 4, f"bad migration version: {path.name}"
        versions.append(version)
    assert versions == sorted(versions)
    assert len(versions) == len(set(versions))


def test_apply_is_idempotent(fresh_db_url: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.schema_migration")
        before = cur.fetchone()[0]
    conn.rollback()

    result = run_migrate(fresh_db_url, "apply")
    assert result.returncode == 0, result.stderr
    assert "0 migration(s) applied" in result.stdout

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.schema_migration")
        after = cur.fetchone()[0]
    conn.rollback()
    assert before == after


def test_verify_passes_on_a_fresh_database(fresh_db_url: str) -> None:
    result = run_migrate(fresh_db_url, "verify")
    assert result.returncode == 0, result.stderr
    assert "checksums match" in result.stdout


def test_status_reports_applied(fresh_db_url: str) -> None:
    result = run_migrate(fresh_db_url, "status")
    assert result.returncode == 0, result.stderr
    assert "applied" in result.stdout
    assert "pending" not in result.stdout


def test_checksum_guard_rejects_an_edited_migration(
    fresh_db_url: str, conn: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT checksum FROM public.schema_migration WHERE version = '0001'")
        original = cur.fetchone()[0]
        cur.execute(
            "UPDATE public.schema_migration SET checksum = %s WHERE version = '0001'",
            ("0" * 64,),
        )
    conn.commit()

    try:
        result = run_migrate(fresh_db_url, "apply")
        assert result.returncode == 1
        assert "checksum mismatch" in result.stderr.lower()
    finally:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.schema_migration SET checksum = %s WHERE version = '0001'",
                (original,),
            )
        conn.commit()

    assert run_migrate(fresh_db_url, "verify").returncode == 0


def test_recorded_checksum_matches_the_file(conn: psycopg.Connection) -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem.split("_", 1)[0]
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT checksum FROM public.schema_migration WHERE version = %s",
                (version,),
            )
            row = cur.fetchone()
        conn.rollback()
        assert row is not None, f"{path.name} is not recorded in schema_migration"
        assert row[0] == expected, f"recorded checksum differs for {path.name}"


def test_failed_migration_rolls_back_atomically(empty_db_url: str, tmp_path) -> None:
    """Forward-only recovery: a failing file aborts its own transaction only."""
    (tmp_path / "0001_ok.sql").write_text(
        "CREATE TABLE public.t_ok (id integer PRIMARY KEY);\n", encoding="utf-8"
    )
    (tmp_path / "0002_bad.sql").write_text(
        "CREATE TABLE public.t_bad (id integer PRIMARY KEY);\n"
        "SELECT this_function_does_not_exist();\n",
        encoding="utf-8",
    )

    result = run_migrate(empty_db_url, "apply", "--migrations-dir", str(tmp_path))
    assert result.returncode == 1
    assert "migration failed" in result.stderr.lower()

    with psycopg.connect(empty_db_url) as check:
        with check.cursor() as cur:
            cur.execute("SELECT to_regclass('public.t_ok'), to_regclass('public.t_bad')")
            t_ok, t_bad = cur.fetchone()
            cur.execute("SELECT version FROM public.schema_migration ORDER BY version")
            applied = [row[0] for row in cur.fetchall()]
    assert t_ok is not None, "the migration before the failure must stay committed"
    assert t_bad is None, "the failed migration must roll back every statement in its file"
    assert applied == ["0001"]
