-- ===========================================================================
-- 0020_w7_api_key_function_fix.sql
-- W7 / Phase 9B: correct the PL/pgSQL name collision in 0019.
--
-- ``RETURNS TABLE (api_key_id ...)`` creates an output variable named
-- api_key_id. The unqualified ``WHERE api_key_id = ...`` in the last_used_at
-- UPDATE was therefore ambiguous. This migration replaces the function body
-- with an aliased UPDATE. It changes no table, grant, policy, or contract.
--
-- Forward-only. Does not edit the applied 0019 file.
-- ===========================================================================

SET client_min_messages = warning;

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

    UPDATE iam.api_key AS k
    SET last_used_at = now()
    WHERE k.api_key_id = v_key.api_key_id
      AND (k.last_used_at IS NULL OR k.last_used_at < now() - interval '1 hour');

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

DO $$
DECLARE
    offending text;
BEGIN
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
        RAISE EXCEPTION '0020: authenticate_api_key is unsafe: %', offending;
    END IF;

    IF NOT has_function_privilege(
        'app_erp', 'iam.authenticate_api_key(text, bytea)', 'EXECUTE'
    ) THEN
        RAISE EXCEPTION '0020: app_erp cannot execute authenticate_api_key';
    END IF;
END
$$;
