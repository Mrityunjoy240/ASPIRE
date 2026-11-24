-- 0001_bootstrap.sql
-- Phase 1 foundation for the BCREC Central database.
--
-- Source of truth:
--   docs/architecture/database-design-v1/POSTGRES_ARCHITECTURE.md
--     section 2   cluster topology
--     section 3.1 schemas and owner roles
--     section 3.2 extensions
--     section 4   roles, grants, multi-application access
--     section 9.4 FORCE ROW LEVEL SECURITY and separate policies
--     section 17  migration and change management
--
-- This migration creates infrastructure only. It creates no domain table and
-- no data. It is idempotent so a partially provisioned cluster can be repaired,
-- but the migration runner records it exactly once.

-- ---------------------------------------------------------------------------
-- 1. Required extensions (POSTGRES_ARCHITECTURE section 3.2)
-- ---------------------------------------------------------------------------
-- pg_stat_statements requires shared_preload_libraries; see
-- database/config/postgresql.conf.snippet. If the server was not started with
-- the library, this file fails loudly rather than silently omitting a control.
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- pgvector is intentionally absent: knowledge.embedding is blocked by OD-06 and
-- may not be created until the embedding dimension is decided.

-- ---------------------------------------------------------------------------
-- 2. Schema owner roles (POSTGRES_ARCHITECTURE section 3.1, 4.1)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'owner_iam', 'owner_core', 'owner_academic', 'owner_student',
        'owner_attendance', 'owner_assessment', 'owner_exam', 'owner_faculty',
        'owner_finance', 'owner_services', 'owner_doc', 'owner_knowledge',
        'owner_cip', 'owner_policy', 'owner_integration', 'owner_ops',
        'owner_api'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
                role_name
            );
        END IF;
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Group roles and application login roles (POSTGRES_ARCHITECTURE section 4.1)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'g_erp', 'g_cip', 'g_integration', 'g_worker', 'g_reporting'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE',
                role_name
            );
        END IF;
    END LOOP;

    FOREACH role_name IN ARRAY ARRAY[
        'app_erp', 'app_cip', 'app_integration', 'app_worker', 'app_reporting',
        'audit_writer', 'migration_owner', 'dba'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            -- No password is set here. Passwords are provisioned from the
            -- environment by the DBA (or migrate.py provision-dev-roles locally).
            EXECUTE format(
                'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE',
                role_name
            );
        END IF;
    END LOOP;
END
$$;

GRANT g_erp TO app_erp;
GRANT g_cip TO app_cip;
GRANT g_integration TO app_integration;
GRANT g_worker TO app_worker;
GRANT g_reporting TO app_reporting;

-- migration_owner owns no object directly; it can SET ROLE to each schema owner
-- so that every object is owned by the documented owner_<schema> role.
GRANT owner_iam, owner_core, owner_academic, owner_student, owner_attendance,
      owner_assessment, owner_exam, owner_faculty, owner_finance, owner_services,
      owner_doc, owner_knowledge, owner_cip, owner_policy, owner_integration,
      owner_ops, owner_api
TO migration_owner;

-- Documented statement and transaction guardrails (section 4.2, 8.4).
ALTER ROLE app_cip SET statement_timeout = '8s';
ALTER ROLE app_erp SET statement_timeout = '30s';
ALTER ROLE app_erp SET lock_timeout = '5s';
ALTER ROLE app_worker SET lock_timeout = '30s';
ALTER ROLE app_erp SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_cip SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_integration SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_worker SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app_erp SET idle_session_timeout = '10min';
ALTER ROLE app_cip SET idle_session_timeout = '10min';
ALTER ROLE app_integration SET idle_session_timeout = '10min';
ALTER ROLE app_worker SET idle_session_timeout = '10min';
ALTER ROLE app_reporting SET idle_session_timeout = '10min';

-- ---------------------------------------------------------------------------
-- 4. Schema namespaces (POSTGRES_ARCHITECTURE section 3.1)
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS iam         AUTHORIZATION owner_iam;
CREATE SCHEMA IF NOT EXISTS core        AUTHORIZATION owner_core;
CREATE SCHEMA IF NOT EXISTS academic    AUTHORIZATION owner_academic;
CREATE SCHEMA IF NOT EXISTS student     AUTHORIZATION owner_student;
CREATE SCHEMA IF NOT EXISTS attendance  AUTHORIZATION owner_attendance;
CREATE SCHEMA IF NOT EXISTS assessment  AUTHORIZATION owner_assessment;
CREATE SCHEMA IF NOT EXISTS exam        AUTHORIZATION owner_exam;
CREATE SCHEMA IF NOT EXISTS faculty     AUTHORIZATION owner_faculty;
CREATE SCHEMA IF NOT EXISTS finance     AUTHORIZATION owner_finance;
CREATE SCHEMA IF NOT EXISTS services    AUTHORIZATION owner_services;
CREATE SCHEMA IF NOT EXISTS doc         AUTHORIZATION owner_doc;
CREATE SCHEMA IF NOT EXISTS knowledge   AUTHORIZATION owner_knowledge;
CREATE SCHEMA IF NOT EXISTS cip         AUTHORIZATION owner_cip;
CREATE SCHEMA IF NOT EXISTS policy      AUTHORIZATION owner_policy;
CREATE SCHEMA IF NOT EXISTS integration AUTHORIZATION owner_integration;
CREATE SCHEMA IF NOT EXISTS ops         AUTHORIZATION owner_ops;
CREATE SCHEMA IF NOT EXISTS api         AUTHORIZATION owner_api;

-- PUBLIC has no privileges on any application schema (section 4.2).
REVOKE ALL ON SCHEMA iam, core, academic, student, attendance, assessment, exam,
    faculty, finance, services, doc, knowledge, cip, policy, integration, ops, api
FROM PUBLIC;

-- Schema usage only for the roles that need it. Table and column grants are
-- added by the wave that creates each table so that no R/G column is ever
-- exposed by a broad schema grant.
GRANT USAGE ON SCHEMA iam, core, academic, student, attendance, assessment, exam,
    faculty, doc, policy, api TO app_erp;

GRANT USAGE ON SCHEMA doc, academic, policy, knowledge, cip, api TO app_cip;

GRANT USAGE ON SCHEMA integration, api TO app_integration;
GRANT USAGE ON SCHEMA integration, api TO app_worker;
GRANT USAGE ON SCHEMA api TO app_reporting;
GRANT USAGE ON SCHEMA ops TO audit_writer;

GRANT USAGE ON SCHEMA iam, core, academic, student, attendance, assessment, exam,
    faculty, finance, services, doc, knowledge, cip, policy, integration, ops, api
TO dba;

-- ---------------------------------------------------------------------------
-- 5. Migration history (infrastructure, excluded from the 108-entity count)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.schema_migration (
    version    text        PRIMARY KEY,
    name       text        NOT NULL,
    checksum   text        NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    applied_by text        NOT NULL DEFAULT current_user
);

REVOKE ALL ON public.schema_migration FROM PUBLIC;
