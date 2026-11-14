-- 0006_w1a_has_permission.sql
-- Phase 2 / Wave W1a: fix parameter/column name resolution in
-- iam.has_permission(text, text, uuid).
--
-- The function parameters were named permission_code, scope_type, and
-- scope_id. Inside the SQL body, permission_code and scope_type collide with
-- columns of the joined tables, so PostgreSQL resolved them as column
-- references. The predicate became p.permission_code = p.permission_code,
-- which granted any active assignment any permission code.
--
-- Positional parameters remove the ambiguity. Ownership, SECURITY DEFINER,
-- and the pinned search_path are retained. The signature is unchanged.

CREATE OR REPLACE FUNCTION iam.has_permission(
    permission_code text,
    scope_type text,
    scope_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM iam.role_assignment ra
        JOIN iam.role_permission rp ON rp.role_id = ra.role_id
        JOIN iam.permission p ON p.permission_id = rp.permission_id
        WHERE ra.role_assignment_id = iam.current_role_assignment_id()
          AND ra.status = 'active'
          AND ra.valid_from <= current_date
          AND (ra.valid_to IS NULL OR ra.valid_to >= current_date)
          AND p.is_active
          AND lower(p.permission_code) = lower($1)
          AND ra.scope_type = $2
          AND ra.scope_key = $3
    )
$$;

ALTER FUNCTION iam.has_permission(text, text, uuid) OWNER TO owner_iam;
