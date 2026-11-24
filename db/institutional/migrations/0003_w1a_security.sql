-- 0003_w1a_security.sql
-- Phase 2 / Wave W1a: security helpers, row-level security, and grants.
--
-- Design basis:
--   POSTGRES_ARCHITECTURE.md sections 4.1, 4.2, 9.1-9.5, 10.2
--   DATA_DICTIONARY.md sections 1.6 and 17
--   ERD_IDENTITY.md section 5
--   IMPLEMENTATION_PLAN.md section 7.4 (A-01)
--
-- Deliberate boundary: only documented predicates are implemented. Tables for
-- which the design states an RLS intent but no complete predicate remain
-- deny-by-default for non-owner roles. This is recorded in the W1a validation
-- report; it is not an invented policy.

-- ===========================================================================
-- 1. Session helpers
-- ===========================================================================

CREATE OR REPLACE FUNCTION iam.current_person_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('app.person_id', true), '')::uuid
$$;
ALTER FUNCTION iam.current_person_id() OWNER TO owner_iam;

CREATE OR REPLACE FUNCTION iam.current_account_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('app.account_id', true), '')::uuid
$$;
ALTER FUNCTION iam.current_account_id() OWNER TO owner_iam;

CREATE OR REPLACE FUNCTION iam.current_role_assignment_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('app.role_assignment_id', true), '')::uuid
$$;
ALTER FUNCTION iam.current_role_assignment_id() OWNER TO owner_iam;

-- Security-definer authority check. It deliberately requires the exact
-- assignment and the exact scope; a global permission without a scope is not
-- invented here.
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
          AND lower(p.permission_code) = lower(permission_code)
          AND ra.scope_type = scope_type
          AND ra.scope_key = scope_id
    )
$$;
ALTER FUNCTION iam.has_permission(text, text, uuid) OWNER TO owner_iam;

-- Institution scope check. The design notes that today this is always true for
-- BCREC; the implementation verifies that the identifier exists rather than
-- hard-coding the single institution.
CREATE OR REPLACE FUNCTION iam.same_institution(institution_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM core.institution i WHERE i.institution_id = $1
    )
$$;
ALTER FUNCTION iam.same_institution(uuid) OWNER TO owner_core;

REVOKE EXECUTE ON FUNCTION iam.current_person_id() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.current_account_id() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.current_role_assignment_id() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.has_permission(text, text, uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.same_institution(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION iam.current_person_id() TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.current_account_id() TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.current_role_assignment_id() TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.has_permission(text, text, uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.same_institution(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;

-- ===========================================================================
-- 2. Row-level security
-- ===========================================================================
-- FORCE ROW LEVEL SECURITY is used as required by POSTGRES_ARCHITECTURE 9.4.
-- The owner_<schema> role receives a documented all-rows policy so that
-- migrations and security-definer helpers can read the table. Application
-- roles do not inherit owner_<schema>; they therefore remain subject to the
-- application policies below.

ALTER TABLE iam.person ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.person FORCE ROW LEVEL SECURITY;
ALTER TABLE iam.person_contact ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.person_contact FORCE ROW LEVEL SECURITY;
ALTER TABLE iam.identity_account ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.identity_account FORCE ROW LEVEL SECURITY;
ALTER TABLE iam.role_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE iam.role_assignment FORCE ROW LEVEL SECURITY;

ALTER TABLE doc.document ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.document FORCE ROW LEVEL SECURITY;
ALTER TABLE doc.document_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.document_version FORCE ROW LEVEL SECURITY;
ALTER TABLE doc.document_relation ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.document_relation FORCE ROW LEVEL SECURITY;

-- Owner bypass policies (migrations and security-definer helpers only).
CREATE POLICY p_person_owner_all ON iam.person
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);
CREATE POLICY p_person_contact_owner_all ON iam.person_contact
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);
CREATE POLICY p_identity_account_owner_all ON iam.identity_account
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);
CREATE POLICY p_role_assignment_owner_all ON iam.role_assignment
    FOR ALL TO owner_iam USING (true) WITH CHECK (true);

CREATE POLICY p_document_owner_all ON doc.document
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);
CREATE POLICY p_document_version_owner_all ON doc.document_version
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);
CREATE POLICY p_document_relation_owner_all ON doc.document_relation
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);

-- Documented self-access predicates.
CREATE POLICY p_person_self_select ON iam.person
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (person_id = (SELECT iam.current_person_id()));

CREATE POLICY p_person_contact_self_select ON iam.person_contact
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (person_id = (SELECT iam.current_person_id()));

CREATE POLICY p_identity_account_self_select ON iam.identity_account
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        account_id = (SELECT iam.current_account_id())
        OR person_id = (SELECT iam.current_person_id())
    );

CREATE POLICY p_role_assignment_self_select ON iam.role_assignment
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (person_id = (SELECT iam.current_person_id()));

-- Document classification ladder: P is public-to-authenticated, I requires an
-- authenticated person. C/R/G policies are intentionally not invented; they
-- remain deny-by-default until the named-role predicates are approved.
CREATE POLICY p_document_classification_select ON doc.document
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        classification = 'P'
        OR (classification = 'I' AND (SELECT iam.current_person_id()) IS NOT NULL)
    );

CREATE POLICY p_document_version_classification_select ON doc.document_version
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        EXISTS (
            SELECT 1
            FROM doc.document d
            WHERE d.document_id = doc.document_version.document_id
              AND (
                  d.classification = 'P'
                  OR (d.classification = 'I' AND (SELECT iam.current_person_id()) IS NOT NULL)
              )
        )
    );

CREATE POLICY p_document_relation_classification_select ON doc.document_relation
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        EXISTS (
            SELECT 1 FROM doc.document_version v
            WHERE v.document_version_id = doc.document_relation.from_version_id
        )
        AND EXISTS (
            SELECT 1 FROM doc.document_version v
            WHERE v.document_version_id = doc.document_relation.to_version_id
        )
    );

-- Writes on RLS tables remain denied unless a documented predicate exists.
-- This is the A-01 posture: no invented write policy.

-- ===========================================================================
-- 3. Grants
-- ===========================================================================
-- Table privileges are deliberately narrower than schema ownership. No role
-- receives DELETE. app_erp receives INSERT/UPDATE but only a safe SELECT
-- column list on tables carrying R/G columns.

REVOKE ALL ON ALL TABLES IN SCHEMA iam, core, doc, policy, integration, ops FROM PUBLIC;

-- ERP: identity, core, documents, policy.
GRANT SELECT, INSERT, UPDATE ON
    iam.person_contact, iam.role, iam.permission, iam.role_permission,
    iam.role_assignment, iam.delegation
TO app_erp;

-- iam.person: gender (G), blood_group (R per the special-category matrix),
-- and notes (R) are not in the broad projection.
GRANT SELECT (
    person_id, legal_name, preferred_name, date_of_birth, photo_uri,
    deceased_flag, created_at, created_by, updated_at, updated_by, row_version
) ON iam.person TO app_erp;
GRANT INSERT, UPDATE ON iam.person TO app_erp;

-- iam.identity_account.disabled_reason is R.
GRANT SELECT (
    account_id, person_id, idp_code, subject, username, email, account_type,
    mfa_enabled, status, last_login_at, disabled_at, created_at, created_by,
    updated_at, updated_by, row_version
) ON iam.identity_account TO app_erp;
GRANT INSERT, UPDATE ON iam.identity_account TO app_erp;

GRANT SELECT, INSERT, UPDATE ON
    core.institution, core.society, core.org_unit, core.governance_body,
    core.governance_membership, core.statutory_approval, core.affiliation_record,
    core.academic_year, core.term, core.academic_calendar, core.calendar_milestone
TO app_erp;

GRANT SELECT, INSERT, UPDATE ON
    doc.document, doc.document_version, doc.document_relation
TO app_erp;

GRANT SELECT, INSERT, UPDATE ON
    policy.rule, policy.rule_version, policy.rule_scope, policy.rule_conflict,
    policy.policy_bundle, policy.policy_bundle_version, policy.policy_bundle_member
TO app_erp;

-- CIP: documents and policy are read-only. academic catalogue grants arrive in
-- W1b.
GRANT SELECT ON doc.document, doc.document_version, doc.document_relation TO app_cip;
GRANT SELECT ON
    policy.rule, policy.rule_version, policy.rule_scope, policy.rule_conflict,
    policy.policy_bundle, policy.policy_bundle_version, policy.policy_bundle_member
TO app_cip;

-- Integration service.
GRANT SELECT, INSERT, UPDATE ON
    integration.entity_type, integration.external_system, integration.external_id_mapping,
    integration.source_of_truth_rule, integration.sync_run, integration.sync_record,
    integration.sync_conflict, integration.record_provenance, integration.outbox_event
TO app_integration;

-- Outbox worker: read the queue and update delivery fields only.
GRANT SELECT ON integration.outbox_event TO app_worker;
GRANT UPDATE (status, published_at, retry_count) ON integration.outbox_event TO app_worker;

-- Audit writer: INSERT only, no SELECT, no UPDATE, no DELETE.
GRANT INSERT ON ops.audit_event TO audit_writer;

-- No runtime role owns a table; ownership remains with owner_<schema>.
-- The owner roles are not granted to application roles.
