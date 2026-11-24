"""Shared fixtures for the BCREC Central database test suite.

The suite never touches the configured development database. It creates a
unique database named ``bcrec_test_<suffix>`` from ``BCREC_MAINTENANCE_URL``,
applies every migration to it, and drops only that database afterwards.

Credentials are read from the environment or from the git-ignored
``database/config/.env``. Nothing is hard-coded.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

DATABASE_DIR = Path(__file__).resolve().parents[1]
MIGRATE = DATABASE_DIR / "migrate.py"
ENV_FILE = DATABASE_DIR / "config" / ".env"
TEST_DB_PREFIX = "bcrec_test_"


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def _database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


def _maintenance_url(base_url: str) -> str:
    explicit = os.environ.get("BCREC_MAINTENANCE_URL")
    if explicit:
        return explicit
    params = conninfo_to_dict(base_url)
    params["dbname"] = "postgres"
    return make_conninfo(**params)


def _with_dbname(url: str, dbname: str) -> str:
    params = conninfo_to_dict(url)
    params["dbname"] = dbname
    return make_conninfo(**params)


def run_migrate(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MIGRATE), "--url", url, *args],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )


@pytest.fixture(scope="session")
def fresh_db_url() -> str:
    base_url = _database_url()
    if not base_url:
        pytest.skip(
            "DATABASE_URL is not set; configure database/config/.env to run the database suite"
        )
    admin_url = _maintenance_url(base_url)
    name = f"{TEST_DB_PREFIX}{uuid.uuid4().hex[:12]}"
    test_url = _with_dbname(base_url, name)

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    try:
        result = run_migrate(test_url, "apply")
        if result.returncode != 0:
            raise AssertionError(
                "migration apply failed on a fresh database:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        yield test_url
    finally:
        # Guard: only ever drop a database this fixture created.
        assert name.startswith(TEST_DB_PREFIX)
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture()
def empty_db_url() -> str:
    """A clean database that no migration has touched yet."""
    base_url = _database_url()
    if not base_url:
        pytest.skip(
            "DATABASE_URL is not set; configure database/config/.env to run the database suite"
        )
    admin_url = _maintenance_url(base_url)
    name = f"{TEST_DB_PREFIX}{uuid.uuid4().hex[:12]}"
    url = _with_dbname(base_url, name)

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield url
    finally:
        assert name.startswith(TEST_DB_PREFIX)
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture()
def conn(fresh_db_url: str):
    with psycopg.connect(fresh_db_url) as connection:
        yield connection
