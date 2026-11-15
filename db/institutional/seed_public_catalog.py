#!/usr/bin/env python
"""Seed the public institutional catalogue.

This script loads ``database/seed/public_catalog.json`` and upserts exactly the
public catalogue graph the read-only ``GET /v1/programmes`` endpoint serves:

    core.institution -> core.org_unit -> academic.department -> academic.programme

It is idempotent: the natural keys are ``lower(college_code)``,
``(institution_id, code)`` for org units, ``lower(code)`` for departments, and
``(institution_id, bcrec_code)`` for programmes.

Writes run as the documented table owners, ``owner_core`` and
``owner_academic``, not as the administrative login. The login must be able to
``SET ROLE`` to them (a superuser, or a role holding ADMIN on them).

Usage (PowerShell)::

    python database/seed_public_catalog.py --dry-run
    python database/seed_public_catalog.py
    python database/seed_public_catalog.py --verify

No person, contact, student, staff, attendance, assessment, or document record
is ever written by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

DATABASE_DIR = Path(__file__).resolve().parent
ENV_FILE = DATABASE_DIR / "config" / ".env"
DEFAULT_SEED = DATABASE_DIR / "seed" / "public_catalog.json"

LEVELS = {"UG", "PG", "diploma", "certificate"}
INSTITUTION_STATUSES = {"active", "inactive"}
AUTONOMY_STATUSES = {"autonomous", "affiliated", "transitional"}


class SeedError(Exception):
    """The seed file is malformed or inconsistent."""


def load_env_file() -> None:
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
        raise SeedError(
            "DATABASE_URL is not set. Pass --url or configure database/config/.env."
        )
    return url


def load_seed(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SeedError(f"seed file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SeedError(f"seed file is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise SeedError("seed document must be a JSON object")
    return document


def validate(document: dict[str, Any]) -> None:
    """Reject a malformed seed before any database write happens."""

    institution = document.get("institution")
    if not isinstance(institution, dict):
        raise SeedError("'institution' must be an object")
    for field in ("college_code", "legal_name", "short_name"):
        value = institution.get(field)
        if not isinstance(value, str) or not value.strip():
            raise SeedError(f"institution.{field} is required and must be text")
    if len(institution["college_code"]) != 3:
        raise SeedError("institution.college_code must be exactly 3 characters")
    if institution.get("status") not in INSTITUTION_STATUSES:
        raise SeedError("institution.status must be 'active' or 'inactive'")
    if institution.get("autonomy_status") not in AUTONOMY_STATUSES:
        raise SeedError(
            "institution.autonomy_status must be 'autonomous', 'affiliated', "
            "or 'transitional'"
        )

    departments = document.get("departments")
    if not isinstance(departments, list) or not departments:
        raise SeedError("'departments' must be a non-empty list")

    seen_departments: set[str] = set()
    for index, department in enumerate(departments):
        if not isinstance(department, dict):
            raise SeedError(f"departments[{index}] must be an object")
        code = department.get("code")
        name = department.get("name")
        if not isinstance(code, str) or not code.strip():
            raise SeedError(f"departments[{index}].code is required")
        if len(code) > 30:
            raise SeedError(f"departments[{index}].code exceeds 30 characters")
        if not isinstance(name, str) or not name.strip():
            raise SeedError(f"departments[{index}].name is required")
        if len(name) > 200:
            raise SeedError(f"departments[{index}].name exceeds 200 characters")
        key = code.strip().lower()
        if key in seen_departments:
            raise SeedError(f"duplicate department code: {code!r}")
        seen_departments.add(key)

    programmes = document.get("programmes")
    if not isinstance(programmes, list) or not programmes:
        raise SeedError("'programmes' must be a non-empty list")

    seen_codes: set[str] = set()
    for index, programme in enumerate(programmes):
        if not isinstance(programme, dict):
            raise SeedError(f"programmes[{index}] must be an object")
        for field in ("programme_code", "bcrec_code", "name", "department_code"):
            value = programme.get(field)
            if not isinstance(value, str) or not value.strip():
                raise SeedError(f"programmes[{index}].{field} is required")
        if len(programme["programme_code"]) > 20:
            raise SeedError(f"programmes[{index}].programme_code exceeds 20 characters")
        if len(programme["bcrec_code"]) > 20:
            raise SeedError(f"programmes[{index}].bcrec_code exceeds 20 characters")
        if len(programme["name"]) > 200:
            raise SeedError(f"programmes[{index}].name exceeds 200 characters")
        if programme.get("level") not in LEVELS:
            raise SeedError(
                f"programmes[{index}].level must be one of {sorted(LEVELS)}"
            )
        duration = programme.get("duration_years")
        if not isinstance(duration, int) or not 1 <= duration <= 6:
            raise SeedError(
                f"programmes[{index}].duration_years must be an integer from 1 to 6"
            )
        department_code = programme["department_code"].strip().lower()
        if department_code not in seen_departments:
            raise SeedError(
                f"programmes[{index}] references unknown department "
                f"{programme['department_code']!r}"
            )
        key = programme["bcrec_code"].strip().lower()
        if key in seen_codes:
            raise SeedError(f"duplicate bcrec_code: {programme['bcrec_code']!r}")
        seen_codes.add(key)


def _set_role(cur: psycopg.Cursor, role: str) -> None:
    try:
        cur.execute(f"SET LOCAL ROLE {role}")
    except psycopg.errors.InsufficientPrivilege:
        raise SeedError(
            f"the database login cannot SET ROLE {role}; use an administrator "
            "login or grant ADMIN on that role"
        ) from None


def seed(connection: psycopg.Connection, document: dict[str, Any]) -> dict[str, int]:
    institution = document["institution"]
    departments = document["departments"]
    programmes = document["programmes"]

    with connection.cursor() as cur:
        # ---- core -----------------------------------------------------------------
        _set_role(cur, "owner_core")
        cur.execute(
            """
            INSERT INTO core.institution AS i
                (legal_name, short_name, college_code, affiliation_university,
                 autonomy_status, address_line1, city, district, state,
                 postal_code, country, timezone, currency, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (lower(college_code)) DO UPDATE SET
                legal_name            = EXCLUDED.legal_name,
                short_name            = EXCLUDED.short_name,
                affiliation_university = EXCLUDED.affiliation_university,
                autonomy_status       = EXCLUDED.autonomy_status,
                address_line1         = EXCLUDED.address_line1,
                city                  = EXCLUDED.city,
                district              = EXCLUDED.district,
                state                 = EXCLUDED.state,
                postal_code           = EXCLUDED.postal_code,
                country               = EXCLUDED.country,
                timezone              = EXCLUDED.timezone,
                currency              = EXCLUDED.currency,
                status                = EXCLUDED.status,
                updated_at            = now(),
                row_version           = i.row_version + 1
            RETURNING institution_id
            """,
            (
                institution["legal_name"].strip(),
                institution["short_name"].strip(),
                institution["college_code"].strip(),
                institution.get("affiliation_university"),
                institution["autonomy_status"],
                institution.get("address_line1"),
                institution.get("city"),
                institution.get("district"),
                institution.get("state"),
                institution.get("postal_code"),
                institution.get("country"),
                institution.get("timezone", "Asia/Kolkata"),
                institution.get("currency", "INR"),
                institution["status"],
            ),
        )
        institution_id = cur.fetchone()[0]

        org_units: dict[str, Any] = {}
        for sort_order, department in enumerate(departments, start=1):
            code = department["code"].strip()
            cur.execute(
                """
                INSERT INTO core.org_unit AS ou
                    (institution_id, code, name, unit_type, sort_order)
                VALUES (%s, %s, %s, 'department', %s)
                ON CONFLICT (institution_id, code) DO UPDATE SET
                    name        = EXCLUDED.name,
                    unit_type   = EXCLUDED.unit_type,
                    sort_order  = EXCLUDED.sort_order,
                    is_active   = true,
                    updated_at  = now(),
                    row_version = ou.row_version + 1
                RETURNING org_unit_id
                """,
                (institution_id, code, department["name"].strip(), sort_order),
            )
            org_units[code.lower()] = cur.fetchone()[0]

        # ---- academic -------------------------------------------------------------
        _set_role(cur, "owner_academic")
        department_ids: dict[str, Any] = {}
        for department in departments:
            code = department["code"].strip()
            cur.execute(
                """
                INSERT INTO academic.department AS d (org_unit_id, code, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (lower(code)) DO UPDATE SET
                    org_unit_id = EXCLUDED.org_unit_id,
                    name        = EXCLUDED.name,
                    is_active   = true,
                    updated_at  = now(),
                    row_version = d.row_version + 1
                RETURNING department_id
                """,
                (org_units[code.lower()], code, department["name"].strip()),
            )
            department_ids[code.lower()] = cur.fetchone()[0]

        for programme in programmes:
            cur.execute(
                """
                INSERT INTO academic.programme AS p
                    (institution_id, department_id, programme_code, bcrec_code,
                     name, level, degree_awarded_by, duration_years, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
                ON CONFLICT (institution_id, bcrec_code) DO UPDATE SET
                    department_id    = EXCLUDED.department_id,
                    programme_code   = EXCLUDED.programme_code,
                    name             = EXCLUDED.name,
                    level            = EXCLUDED.level,
                    duration_years   = EXCLUDED.duration_years,
                    status           = EXCLUDED.status,
                    updated_at       = now(),
                    row_version      = p.row_version + 1
                RETURNING programme_id
                """,
                (
                    institution_id,
                    department_ids[programme["department_code"].strip().lower()],
                    programme["programme_code"].strip(),
                    programme["bcrec_code"].strip(),
                    programme["name"].strip(),
                    programme["level"],
                    programme.get("degree_awarded_by", "MAKAUT"),
                    programme["duration_years"],
                ),
            )
            cur.fetchone()

    return {
        "institutions": 1,
        "departments": len(departments),
        "programmes": len(programmes),
    }


def verify(connection: psycopg.Connection) -> None:
    """Print the same shape the catalogue endpoint will serve."""

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT p.programme_code, p.bcrec_code, p.level, p.name,
                   d.code AS department_code, i.short_name AS institution
            FROM academic.programme p
            JOIN academic.department d ON d.department_id = p.department_id
            JOIN core.institution i ON i.institution_id = p.institution_id
            WHERE p.status = 'active'
            ORDER BY p.level, p.name
            """
        )
        rows = cur.fetchall()

    if not rows:
        print("no active programmes")
        return
    for code, bcrec_code, level, name, department, institution in rows:
        print(
            f"{institution}  {department:<10}  {level:<3}  "
            f"{bcrec_code:<8}  {name}"
        )
    print(f"\n{len(rows)} active programme(s)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the public catalogue")
    parser.add_argument("--url", help="PostgreSQL URL (defaults to DATABASE_URL)")
    parser.add_argument(
        "--file", default=str(DEFAULT_SEED), help="seed JSON path"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate only; write nothing"
    )
    parser.add_argument(
        "--verify", action="store_true", help="print the seeded catalogue and exit"
    )
    args = parser.parse_args(argv)

    try:
        url = resolve_url(args.url)
        document = load_seed(Path(args.file))
        validate(document)
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = (
        f"institution={document['institution']['legal_name']} "
        f"departments={len(document['departments'])} "
        f"programmes={len(document['programmes'])}"
    )

    if args.dry_run:
        print(f"OK: seed file is valid ({summary}); nothing was written")
        withheld = document.get("withheld", {}).get("programmes", [])
        if withheld:
            print(f"note: {len(withheld)} PG programme(s) are withheld (no verified code)")
        return 0

    try:
        with psycopg.connect(url) as connection:
            if args.verify:
                verify(connection)
                return 0
            counts = seed(connection, document)
            connection.commit()
            verify(connection)
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        # Never echo the DSN; the exception text does not contain it.
        print(f"ERROR: database write failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: seeded {counts['institutions']} institution, "
        f"{counts['departments']} departments, {counts['programmes']} programmes"
    )
    withheld = document.get("withheld", {}).get("programmes", [])
    if withheld:
        print(
            f"note: {len(withheld)} PG programme(s) were withheld because the "
            "research corpus records no MAKAUT code for them"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
