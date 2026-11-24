-- ===========================================================================
-- 0018_w7_trigger_hardening.sql
-- W7 / Phase 9B: trigger-function execution hardening (TRG-EXEC)
--
-- Finding: DB-10 (Phase 9 Stage A).
--
-- All ten W1a trigger functions are SECURITY INVOKER, owned by the correct
-- owner_* role, and retained the default PUBLIC EXECUTE ACL. None of them is
-- meant to be called directly by a runtime role.
--
-- This migration revokes PUBLIC EXECUTE on exactly those ten functions. It
-- does not alter, disable, drop, or recreate any trigger. Trigger invocation
-- does not check the invoking role's EXECUTE privilege, so the 17 dependent
-- triggers continue to fire; this is proved by test_32.
--
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Revoke PUBLIC and runtime-role execution.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    fn record;
    signature text;
BEGIN
    FOR fn IN
        SELECT v.schema_name, v.function_name
        FROM (VALUES
            ('core', 'refresh_org_unit_descendant_paths'),
            ('core', 'set_org_unit_path'),
            ('doc', 'seal_document_version'),
            ('iam', 'check_person_date_of_birth'),
            ('iam', 'enforce_role_assignment_scope'),
            ('iam', 'reject_system_role_delete'),
            ('integration', 'seal_sync_run'),
            ('ops', 'reject_mutation'),
            ('policy', 'check_rule_version_current'),
            ('policy', 'seal_referenced_rule_version')
        ) AS v(schema_name, function_name)
    LOOP
        SELECT p.oid::regprocedure::text
        INTO signature
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = fn.schema_name
          AND p.proname = fn.function_name
          AND p.pronargs = 0;

        IF signature IS NULL THEN
            RAISE EXCEPTION '0018: expected function %.%() is missing',
                fn.schema_name, fn.function_name;
        END IF;

        EXECUTE format(
            'REVOKE ALL ON FUNCTION %s FROM PUBLIC, app_erp, app_cip, '
            'app_integration, app_worker, app_reporting, audit_writer',
            signature
        );
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 2. Self-verification. Abort if a function is missing, has changed owner,
--    has become SECURITY DEFINER, or is still executable by PUBLIC.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    found integer;
    offending text;
BEGIN
    SELECT count(*)
    INTO found
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (
        ('core', 'refresh_org_unit_descendant_paths'),
        ('core', 'set_org_unit_path'),
        ('doc', 'seal_document_version'),
        ('iam', 'check_person_date_of_birth'),
        ('iam', 'enforce_role_assignment_scope'),
        ('iam', 'reject_system_role_delete'),
        ('integration', 'seal_sync_run'),
        ('ops', 'reject_mutation'),
        ('policy', 'check_rule_version_current'),
        ('policy', 'seal_referenced_rule_version')
    )
      AND p.pronargs = 0;

    IF found <> 10 THEN
        RAISE EXCEPTION '0018: expected 10 trigger functions, found %', found;
    END IF;

    SELECT string_agg(format('%I.%I()', v.schema_name, v.function_name), ', ')
    INTO offending
    FROM (VALUES
        ('core', 'refresh_org_unit_descendant_paths', 'owner_core'),
        ('core', 'set_org_unit_path', 'owner_core'),
        ('doc', 'seal_document_version', 'owner_doc'),
        ('iam', 'check_person_date_of_birth', 'owner_iam'),
        ('iam', 'enforce_role_assignment_scope', 'owner_iam'),
        ('iam', 'reject_system_role_delete', 'owner_iam'),
        ('integration', 'seal_sync_run', 'owner_integration'),
        ('ops', 'reject_mutation', 'owner_ops'),
        ('policy', 'check_rule_version_current', 'owner_policy'),
        ('policy', 'seal_referenced_rule_version', 'owner_policy')
    ) AS v(schema_name, function_name, owner_name)
    JOIN pg_proc p
      ON p.proname = v.function_name
     AND p.pronargs = 0
     AND p.pronamespace = to_regnamespace(v.schema_name)
    WHERE p.prosecdef
       OR pg_get_userbyid(p.proowner) <> v.owner_name
       OR EXISTS (
            SELECT 1
            FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
            WHERE a.grantee = 0
              AND a.privilege_type = 'EXECUTE'
       );

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0018: trigger function hardening failed for %', offending;
    END IF;
END
$$;
