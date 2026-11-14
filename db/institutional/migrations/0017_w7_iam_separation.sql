-- ===========================================================================
-- 0017_w7_iam_separation.sql
-- W7 / Phase 9B: runtime/admin privilege separation (IAM-SEP)
--
-- Findings: DB-01, DB-02, DB-03, DB-04 (Phase 9 Stage A).
-- Design basis: POSTGRES_ARCHITECTURE.md sections 4.1, 4.2, 9.1-9.5, 10.2.
--
-- app_erp must not modify the IAM privilege catalogue, academic offering
-- allocation, mentor assignment, governance membership, or policy authority.
-- These tables have no application write policy, so the table and column
-- grants were the only protection and they were too broad.
--
-- This migration revokes writes only. SELECT is preserved, including the
-- column-level SELECT grants on faculty.mentor_assignment. No replacement
-- administrative role or function is created: administrative operations stay
-- unavailable until an approved authorization and audit contract exists.
--
-- Column-level grants are independent of table-level grants in PostgreSQL, so
-- both are revoked. Columns are enumerated at apply time so a column added by
-- any migration in the same install cannot escape the boundary.
--
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Non-policy authority tables.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    target record;
    column_list text;
BEGIN
    FOR target IN
        SELECT v.schema_name, v.table_name
        FROM (VALUES
            ('iam', 'role'),
            ('iam', 'permission'),
            ('iam', 'role_permission'),
            ('iam', 'delegation'),
            ('academic', 'offering_faculty'),
            ('faculty', 'mentor_assignment'),
            ('core', 'governance_membership')
        ) AS v(schema_name, table_name)
    LOOP
        IF to_regclass(format('%I.%I', target.schema_name, target.table_name)) IS NULL THEN
            RAISE EXCEPTION '0017: expected table %.% is missing',
                target.schema_name, target.table_name;
        END IF;

        SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY a.attnum)
        INTO column_list
        FROM pg_attribute a
        WHERE a.attrelid = format('%I.%I', target.schema_name, target.table_name)::regclass
          AND a.attnum > 0
          AND NOT a.attisdropped;

        EXECUTE format(
            'REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE %I.%I '
            'FROM app_erp, g_erp, PUBLIC',
            target.schema_name, target.table_name
        );

        IF column_list IS NOT NULL THEN
            EXECUTE format(
                'REVOKE INSERT (%1$s), UPDATE (%1$s) ON TABLE %2$I.%3$I '
                'FROM app_erp, g_erp, PUBLIC',
                column_list, target.schema_name, target.table_name
            );
        END IF;
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 2. Every base table in the policy schema.
--
-- This loop is intentionally schema-wide rather than a fixed list: a policy
-- table added before this migration must not retain a broad write grant.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    target record;
    column_list text;
BEGIN
    FOR target IN
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'policy'
          AND c.relkind IN ('r', 'p')
        ORDER BY c.relname
    LOOP
        SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY a.attnum)
        INTO column_list
        FROM pg_attribute a
        WHERE a.attrelid = format('%I.%I', target.schema_name, target.table_name)::regclass
          AND a.attnum > 0
          AND NOT a.attisdropped;

        EXECUTE format(
            'REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE %I.%I '
            'FROM app_erp, g_erp, PUBLIC',
            target.schema_name, target.table_name
        );

        IF column_list IS NOT NULL THEN
            EXECUTE format(
                'REVOKE INSERT (%1$s), UPDATE (%1$s) ON TABLE %2$I.%3$I '
                'FROM app_erp, g_erp, PUBLIC',
                column_list, target.schema_name, target.table_name
            );
        END IF;
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Self-verification. Abort the migration if any effective write remains,
--    whether granted at table level, at column level, or through inheritance.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    offending text;
    targets_sql text := $sql$
        SELECT * FROM (VALUES
            ('iam', 'role'),
            ('iam', 'permission'),
            ('iam', 'role_permission'),
            ('iam', 'delegation'),
            ('academic', 'offering_faculty'),
            ('faculty', 'mentor_assignment'),
            ('core', 'governance_membership')
        ) AS v(schema_name, table_name)
        UNION ALL
        SELECT 'policy', c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'policy'
          AND c.relkind IN ('r', 'p')
    $sql$;
BEGIN
    EXECUTE format($q$
        SELECT string_agg(format('%%I.%%I', schema_name, table_name), ', ' ORDER BY schema_name, table_name)
        FROM (%s) AS t
        WHERE has_table_privilege('app_erp', format('%%I.%%I', schema_name, table_name), 'INSERT')
           OR has_table_privilege('app_erp', format('%%I.%%I', schema_name, table_name), 'UPDATE')
           OR has_table_privilege('g_erp', format('%%I.%%I', schema_name, table_name), 'INSERT')
           OR has_table_privilege('g_erp', format('%%I.%%I', schema_name, table_name), 'UPDATE')
    $q$, targets_sql)
    INTO offending;

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0017: table-level write privilege still effective on %', offending;
    END IF;

    EXECUTE format($q$
        SELECT string_agg(format('%%I.%%I.%%I', t.schema_name, t.table_name, a.attname), ', '
                          ORDER BY t.schema_name, t.table_name, a.attnum)
        FROM (%s) AS t
        JOIN pg_attribute a
          ON a.attrelid = format('%%I.%%I', t.schema_name, t.table_name)::regclass
         AND a.attnum > 0
         AND NOT a.attisdropped
        WHERE has_column_privilege('app_erp', a.attrelid, a.attname, 'INSERT')
           OR has_column_privilege('app_erp', a.attrelid, a.attname, 'UPDATE')
           OR has_column_privilege('g_erp', a.attrelid, a.attname, 'INSERT')
           OR has_column_privilege('g_erp', a.attrelid, a.attname, 'UPDATE')
    $q$, targets_sql)
    INTO offending;

    IF offending IS NOT NULL THEN
        RAISE EXCEPTION '0017: column-level write privilege still effective on %', offending;
    END IF;
END
$$;
