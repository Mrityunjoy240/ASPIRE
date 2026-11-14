#!/usr/bin/env python
"""Operator CLI for scoped API clients and keys.

This is an administrative tool. It is never exposed through the HTTP API.

Usage (PowerShell)::

    python database/api_keys.py create-client --code demo --name "Demo"
    python database/api_keys.py create-key --client demo --label "friend-1" \
        --scope public.read --expires-days 90
    python database/api_keys.py list
    python database/api_keys.py revoke --prefix 0123456789ab

The plaintext key is printed exactly once, at creation. Only its SHA-256
digest is stored. If the key is lost, revoke it and create a new one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import sys
from pathlib import Path

import psycopg

DATABASE_DIR = Path(__file__).resolve().parent
ENV_FILE = DATABASE_DIR / "config" / ".env"
SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
KEY_TOKEN_PREFIX = "bcrec_ak_"


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
        sys.exit(
            "ERROR: DATABASE_URL is not set. Pass --url or configure "
            "database/config/.env."
        )
    return url


def _enter_owner(cur: psycopg.Cursor) -> None:
    """Run DDL writes as the documented table owner, not the admin login."""

    try:
        cur.execute("SET LOCAL ROLE owner_iam")
    except psycopg.errors.InsufficientPrivilege:
        # A superuser or an administrator with ADMIN on owner_iam can set the
        # role. Anything else must fail rather than silently bypass RLS.
        raise SystemExit(
            "ERROR: the database login cannot SET ROLE owner_iam; use an "
            "administrator login or grant ADMIN on owner_iam."
        ) from None


def cmd_create_client(args: argparse.Namespace) -> int:
    url = resolve_url(args.url)
    with psycopg.connect(url) as connection:
        with connection.cursor() as cur:
            _enter_owner(cur)
            cur.execute(
                """
                INSERT INTO iam.api_client (client_code, name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (lower(client_code)) DO UPDATE
                   SET name = EXCLUDED.name,
                       description = EXCLUDED.description,
                       is_active = true,
                       updated_at = now(),
                       row_version = api_client.row_version + 1
                RETURNING client_id
                """,
                (args.code.strip().lower(), args.name, args.description),
            )
            client_id = cur.fetchone()[0]
        connection.commit()
    print(f"OK: client '{args.code.strip().lower()}' is {client_id}")
    return 0


def cmd_create_key(args: argparse.Namespace) -> int:
    scopes = tuple(dict.fromkeys(args.scope or ()))
    for scope in scopes:
        if not SCOPE_PATTERN.fullmatch(scope):
            sys.exit(f"ERROR: invalid scope code: {scope!r}")

    if not scopes:
        print(
            "WARNING: no --scope was supplied; the key will authenticate but "
            "will not authorize any policy.",
            file=sys.stderr,
        )

    expires_days = int(args.expires_days)
    if expires_days < 0:
        sys.exit("ERROR: --expires-days must be zero or greater")
    if expires_days > 3650:
        sys.exit("ERROR: --expires-days must not exceed 3650")
    if not 1 <= int(args.rate_limit) <= 6000:
        sys.exit("ERROR: --rate-limit must be between 1 and 6000")

    prefix = secrets.token_hex(6)
    secret = secrets.token_hex(32)
    digest = hashlib.sha256(secret.encode("ascii")).digest()

    url = resolve_url(args.url)
    with psycopg.connect(url) as connection:
        with connection.cursor() as cur:
            _enter_owner(cur)
            cur.execute(
                "SELECT client_id FROM iam.api_client "
                "WHERE lower(client_code) = lower(%s) AND is_active",
                (args.client,),
            )
            row = cur.fetchone()
            if row is None:
                sys.exit(f"ERROR: no active client with code {args.client!r}")
            client_id = row[0]

            if expires_days == 0:
                expires_at_sql = "NULL"
                params = (
                    client_id,
                    prefix,
                    digest,
                    args.label,
                    int(args.rate_limit),
                )
            else:
                expires_at_sql = f"now() + interval '{expires_days} days'"
                params = (
                    client_id,
                    prefix,
                    digest,
                    args.label,
                    int(args.rate_limit),
                )

            cur.execute(
                f"""
                INSERT INTO iam.api_key
                    (client_id, key_prefix, secret_hash, label,
                     rate_limit_per_minute, expires_at)
                VALUES (%s, %s, %s, %s, %s, {expires_at_sql})
                RETURNING api_key_id
                """,
                params,
            )
            key_id = cur.fetchone()[0]

            for scope in scopes:
                cur.execute(
                    "INSERT INTO iam.api_key_scope (api_key_id, scope_code) "
                    "VALUES (%s, %s)",
                    (key_id, scope),
                )
        connection.commit()

    token = f"{KEY_TOKEN_PREFIX}{prefix}.{secret}"
    print("OK: API key created. It is shown once and cannot be recovered.")
    print(f"  key_id : {key_id}")
    print(f"  client : {args.client.strip().lower()}")
    print(f"  scopes : {', '.join(scopes) if scopes else '(none)'}")
    print(f"  expires: {'never' if expires_days == 0 else f'{expires_days} days'}")
    print(f"  secret : {token}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    url = resolve_url(args.url)
    with psycopg.connect(url) as connection:
        with connection.cursor() as cur:
            _enter_owner(cur)
            cur.execute(
                """
                SELECT k.key_prefix,
                       c.client_code,
                       coalesce(k.label, ''),
                       coalesce(array_to_string(
                           array_agg(s.scope_code ORDER BY s.scope_code)
                               FILTER (WHERE s.scope_code IS NOT NULL),
                           ','), ''),
                       k.expires_at,
                       k.revoked_at,
                       k.last_used_at
                FROM iam.api_key k
                JOIN iam.api_client c ON c.client_id = k.client_id
                LEFT JOIN iam.api_key_scope s ON s.api_key_id = k.api_key_id
                WHERE (%s::text IS NULL OR lower(c.client_code) = lower(%s))
                GROUP BY k.api_key_id, c.client_code
                ORDER BY k.created_at DESC
                """,
                (args.client, args.client),
            )
            rows = cur.fetchall()
    if not rows:
        print("no API keys")
        return 0
    for prefix, client, label, scopes, expires_at, revoked_at, last_used_at in rows:
        state = "revoked" if revoked_at else "active"
        expiry = "never" if expires_at is None else expires_at.isoformat()
        used = "never" if last_used_at is None else last_used_at.isoformat()
        print(
            f"{prefix}  {client:<20}  {state:<8}  expires={expiry}  "
            f"last_used={used}  scopes={scopes or '-'}  label={label or '-'}"
        )
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    url = resolve_url(args.url)
    with psycopg.connect(url) as connection:
        with connection.cursor() as cur:
            _enter_owner(cur)
            cur.execute(
                "UPDATE iam.api_key SET revoked_at = now() "
                "WHERE key_prefix = %s AND revoked_at IS NULL",
                (args.prefix,),
            )
            changed = cur.rowcount
        connection.commit()
    if changed == 0:
        sys.exit(f"ERROR: no active key with prefix {args.prefix!r}")
    print(f"OK: revoked key {args.prefix}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BCREC scoped API-key operator CLI")
    parser.add_argument("--url", help="PostgreSQL connection URL (defaults to DATABASE_URL)")
    sub = parser.add_subparsers(dest="command", required=True)

    client = sub.add_parser("create-client", help="create or update a client project")
    client.add_argument("--code", required=True)
    client.add_argument("--name", required=True)
    client.add_argument("--description", default=None)
    client.add_argument("--url", default=argparse.SUPPRESS)
    client.set_defaults(handler=cmd_create_client)

    key = sub.add_parser("create-key", help="create a scoped API key")
    key.add_argument("--client", required=True)
    key.add_argument("--label", default=None)
    key.add_argument("--scope", action="append", default=[])
    key.add_argument("--expires-days", default="90")
    key.add_argument("--rate-limit", default="60")
    key.add_argument("--url", default=argparse.SUPPRESS)
    key.set_defaults(handler=cmd_create_key)

    listing = sub.add_parser("list", help="list keys without secrets")
    listing.add_argument("--client", default=None)
    listing.add_argument("--url", default=argparse.SUPPRESS)
    listing.set_defaults(handler=cmd_list)

    revoke = sub.add_parser("revoke", help="revoke a key by prefix")
    revoke.add_argument("--prefix", required=True)
    revoke.add_argument("--url", default=argparse.SUPPRESS)
    revoke.set_defaults(handler=cmd_revoke)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
