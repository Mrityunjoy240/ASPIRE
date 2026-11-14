-- ===========================================================================
-- 0019_w7_api_keys.sql
-- W7 / Phase 9B: scoped API-key authentication for machine clients.
--
-- Approved scope: AUTH-BOOT-lite for API access. This migration adds machine
-- credentials, not interactive user authentication and not institutional
-- permissions. A key authenticates a *client project*; it never maps to a
-- person, account, role, or role assignment.
--
-- Security properties:
--   * only a SHA-256 hash of the secret half is stored;
--   * the public prefix is stored separately and is not secret;
--   * keys carry explicit scope codes, an optional expiry, and a revoke time;
--   * runtime roles have no table or column privileges on the three tables;
--   * the only runtime entry point is iam.authenticate_api_key(), which is
--     SECURITY DEFINER, owned by owner_iam, with a pinned search_path;
--   * RLS is enabled and forced on all three tables.
--
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

CREATE TABLE iam.api_client (
    client_id     uuid        NOT NULL DEFAULT gen_random_uuid(),
    client_code   text        NOT NULL,
    name          text        NOT NULL,
    description   text        NULL,
    is_active     boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    uuid        NULL,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    updated_by    uuid        NULL,
    row_version   integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_api_client PRIMARY KEY (client_id),
    CONSTRAINT fk_api_client_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_api_client_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_api_client_code_length CHECK (char_length(client_code) BETWEEN 1 AND 50),
    CONSTRAINT ck_api_client_code_format CHECK (client_code ~ '^[a-z0-9][a-z0-9_.-]*$'),
    CONSTRAINT ck_api_client_name_length CHECK (char_length(name) BETWEEN 1 AND 200),
    CONSTRAINT ck_api_client_description_length CHECK (
        description IS NULL OR char_length(description) <= 1000
    )
);
ALTER TABLE iam.api_client OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_api_client_code_lower ON iam.api_client (lower(client_code));
CREATE INDEX ix_api_client_created_by ON iam.api_client (created_by);
CREATE INDEX ix_api_client_updated_by ON iam.api_client (updated_by);

CREATE TABLE iam.api_key (
    api_key_id            uuid        NOT NULL DEFAULT gen_random_uuid(),
    client_id             uuid        NOT NULL,
    key_prefix            text        NOT NULL,
    secret_hash           bytea       NOT NULL,
    label                 text        NULL,
    rate_limit_per_minute integer     NOT NULL DEFAULT 60,
    expires_at            timestamptz NULL,
    revoked_at            timestamptz NULL,
    last_used_at          timestamptz NULL,
    created_at            timestamptz NOT NULL DEFAULT now(),
    created_by            uuid        NULL,
    updated_at            timestamptz NOT NULL DEFAULT now(),
    updated_by            uuid        NULL,
    row_version           integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_api_key PRIMARY KEY (api_key_id),
    CONSTRAINT fk_api_key_client FOREIGN KEY (client_id)
        REFERENCES iam.api_client (client_id) ON DELETE RESTRICT,
    CONSTRAINT fk_api_key_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_api_key_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_api_key_prefix_format CHECK (key_prefix ~ '^[0-9a-f]{12}$'),
    CONSTRAINT ck_api_key_secret_hash_length CHECK (octet_length(secret_hash) = 32),
    CONSTRAINT ck_api_key_label_length CHECK (label IS NULL OR char_length(label) <= 100),
    CONSTRAINT ck_api_key_rate_limit CHECK (rate_limit_per_minute BETWEEN 1 AND 6000),
    CONSTRAINT ck_api_key_expiry CHECK (expires_at IS NULL OR expires_at > created_at)
);
ALTER TABLE iam.api_key OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_api_key_prefix ON iam.api_key (key_prefix);
CREATE INDEX ix_api_key_client ON iam.api_key (client_id);
CREATE INDEX ix_api_key_live ON iam.api_key (expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE iam.api_key_scope (
    api_key_id  uuid        NOT NULL,
    scope_code  text        NOT NULL,
    granted_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_api_key_scope PRIMARY KEY (api_key_id, scope_code),
    CONSTRAINT fk_api_key_scope_key FOREIGN KEY (api_key_id)
        REFERENCES iam.api_key (api_key_id) ON DELETE RESTRICT,
    CONSTRAINT ck_api_key_scope_format CHECK (scope_code ~ '^[a-z][a-z0-9_.-]{0,63}$')
);
ALTER TABLE iam.api_key_scope OWNER TO owner_iam;

CREATE INDEX ix_api_key_scope_scope ON iam.api_key_scope (scope_code);

COMMENT ON TABLE iam.api_client IS
    'A machine client project that may hold one or more API keys. Not a person or an institutional role.';
COMMENT ON TABLE iam.api_key IS
    'Hashed machine credential. The plaintext key is shown once at creation and is never stored.';
COMMENT ON TABLE iam.api_key_scope IS
    'Explicit capability codes granted to an API key. Scope codes are API capabilities, not institutional permissions.';
COMMENT ON COLUMN iam.api_key.key_prefix IS
    'Public lookup prefix. It is not a secret; possession of the prefix alone grants nothing.';
COMMENT ON COLUMN iam.api_key.secret_hash IS
    'SHA-256 digest of the high-entropy secret half. The plaintext secret is never stored.';

-- ---------------------------------------------------------------------------
-- 2. Row-level security
-- ---------------------------------------------------------------------------
-- Runtime roles receive no policy at all, so they are denied by default. The
-- owner policy exists so the SECURITY DEFINER function (which runs as
-- owner_iam) can read and touch the rows under FORCE ROW LEVEL SECURITY.

ALTER TABLE iam.api_client ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.api_client FORCE ROW LEVEL SECURITY;
ALTER TABLE iam.api_key ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.api_key FORCE ROW LEVEL SECURITY;
ALTER TABLE iam.api_key_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.api_key_scope FORCE ROW LEVEL SECURITY;

CREATE POLICY p_api_client_owner_all ON iam.api_client
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);
CREATE POLICY p_api_key_owner_all ON iam.api_key
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);
CREATE POLICY p_api_key_scope_owner_all ON iam.api_key_scope
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 3. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON TABLE iam.api_client, iam.api_key, iam.api_key_scope FROM PUBLIC;
REVOKE ALL ON TABLE iam.api_client, iam.api_key, iam.api_key_scope
    FROM app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;

-- ---------------------------------------------------------------------------
-- 4. Authentication function
-- ---------------------------------------------------------------------------
-- The only runtime entry point. It returns zero rows for any invalid, expired,
-- revoked, or inactive credential. It deliberately does not distinguish the
-- failure modes to the caller.
--
-- The function updates last_used_at at most once per hour to bound write load.
-- Callers must therefore invoke it in a read-write transaction; the backend
-- authenticator does so before any read-only unit of work.

CREATE OR REPLACE FUNCTION iam.authenticate_api_key(
    p_key_prefix text,
    p_secret_hash bytea
)
RETURNS TABLE (
    api_key_id            uuid,
    client_id             uuid,
    client_code           text,
    scopes                text[],
    rate_limit_per_minute integer,
    expires_at            timestamptz
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_key    iam.api_key%ROWTYPE;
    v_client iam.api_client%ROWTYPE;
BEGIN
    IF p_key_prefix IS NULL OR p_secret_hash IS NULL THEN
        RETURN;
    END IF;

    SELECT k.* INTO v_key
    FROM iam.api_key k
    WHERE k.key_prefix = p_key_prefix;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    IF v_key.secret_hash IS DISTINCT FROM p_secret_hash THEN
        RETURN;
    END IF;

    IF v_key.revoked_at IS NOT NULL THEN
        RETURN;
    END IF;

    IF v_key.expires_at IS NOT NULL AND v_key.expires_at <= now() THEN
        RETURN;
    END IF;

    SELECT c.* INTO v_client
    FROM iam.api_client c
    WHERE c.client_id = v_key.client_id
      AND c.is_active;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    UPDATE iam.api_key
    SET last_used_at = now()
    WHERE api_key_id = v_key.api_key_id
      AND (last_used_at IS NULL OR last_used_at < now() - interval '1 hour');

    RETURN QUERY
    SELECT
        v_key.api_key_id,
        v_key.client_id,
        v_client.client_code,
        COALESCE(
            (
                SELECT array_agg(s.scope_code ORDER BY s.scope_code)
                FROM iam.api_key_scope s
                WHERE s.api_key_id = v_key.api_key_id
            ),
            ARRAY[]::text[]
        ),
        v_key.rate_limit_per_minute,
        v_key.expires_at;
END
$$;
ALTER FUNCTION iam.authenticate_api_key(text, bytea) OWNER TO owner_iam;

REVOKE ALL ON FUNCTION iam.authenticate_api_key(text, bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION iam.authenticate_api_key(text, bytea) TO app_erp;

-- ---------------------------------------------------------------------------
-- 5. Self-verification
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    found integer;
    offending text;
BEGIN
    SELECT count(*)
    INTO found
    FROM (VALUES
        ('iam', 'api_client'),
        ('iam', 'api_key'),
        ('iam', 'api_key_scope')
    ) AS t(schema_name, table_name)
    WHERE to_regclass(format('%I.%I', t.schema_name, t.table_name)) IS NULL;

    IF found <> 0 THEN
        RAISE EXCEPTION '0019: expected three API-key tables, % are missing', found;
    END IF;

    SELECT string_agg(format('%I.%I', t.schema_name, t.table_name), ', ')
    INTO offending
    FROM (VALUES
        ('iam', 'api_client'),
        ('iam', 'api_key'),
        ('iam', 'api_key_scope')
    ) AS t(schema_name, table_name)
    JOIN pg_class c
      ON c.oid = to_regclass(format('%I.%I', t.schema_name, t.table_name))
    WHERE NOT c.relrowsecurity
       OR NOT c.relforcerowsecurity;

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0019: RLS is not enabled and forced on %', offending;
    END IF;

    SELECT string_agg(
        format('%s has %s on %I.%I', r.rolname, p.privilege, t.schema_name, t.table_name),
        ', '
    )
    INTO offending
    FROM (VALUES
        ('iam', 'api_client'),
        ('iam', 'api_key'),
        ('iam', 'api_key_scope')
    ) AS t(schema_name, table_name)
    CROSS JOIN (VALUES
        ('app_erp'), ('app_cip'), ('app_integration'),
        ('app_worker'), ('app_reporting'), ('audit_writer')
    ) AS r(rolname)
    CROSS JOIN (VALUES ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE')) AS p(privilege)
    WHERE has_table_privilege(
        r.rolname,
        format('%I.%I', t.schema_name, t.table_name),
        p.privilege
    );

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0019: runtime table privileges were not removed: %', offending;
    END IF;

    SELECT string_agg(
        format('%s has column %s on %I.%I.%I',
               r.rolname, p.privilege, t.schema_name, t.table_name, a.attname),
        ', '
    )
    INTO offending
    FROM (VALUES
        ('iam', 'api_client'),
        ('iam', 'api_key'),
        ('iam', 'api_key_scope')
    ) AS t(schema_name, table_name)
    JOIN pg_attribute a
      ON a.attrelid = to_regclass(format('%I.%I', t.schema_name, t.table_name))
     AND a.attnum > 0
     AND NOT a.attisdropped
    CROSS JOIN (VALUES
        ('app_erp'), ('app_cip'), ('app_integration'),
        ('app_worker'), ('app_reporting'), ('audit_writer')
    ) AS r(rolname)
    CROSS JOIN (VALUES ('INSERT'), ('UPDATE')) AS p(privilege)
    WHERE has_column_privilege(
        r.rolname,
        a.attrelid,
        a.attname,
        p.privilege
    );

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0019: runtime column privileges were not removed: %', offending;
    END IF;

    SELECT string_agg(format('%I.%I()', n.nspname, p.proname), ', ')
    INTO offending
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'iam'
      AND p.proname = 'authenticate_api_key'
      AND p.pronargs = 2
      AND (
          NOT p.prosecdef
          OR pg_get_userbyid(p.proowner) <> 'owner_iam'
          OR p.proconfig IS NULL
          OR NOT EXISTS (
              SELECT 1 FROM unnest(p.proconfig) AS c
              WHERE c LIKE 'search_path=%'
          )
          OR EXISTS (
              SELECT 1
              FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
              WHERE a.grantee = 0
                AND a.privilege_type = 'EXECUTE'
          )
      );

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0019: authenticate_api_key is unsafe: %', offending;
    END IF;

    IF NOT has_function_privilege(
        'app_erp', 'iam.authenticate_api_key(text, bytea)', 'EXECUTE'
    ) THEN
        RAISE EXCEPTION '0019: app_erp cannot execute authenticate_api_key';
    END IF;
END
$$;
