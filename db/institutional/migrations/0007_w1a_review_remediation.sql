-- ===========================================================================
-- 0007_w1a_review_remediation.sql
-- W1a review decisions, 7 November 2026.
--
-- 1. app_erp must not write the sensitive fields even though the design grants
--    broad INSERT/UPDATE on the schema:
--      iam.person:           gender (G), blood_group (R), notes (R)
--      iam.identity_account: disabled_reason (R)
--    Table-level INSERT/UPDATE is replaced by an explicit column list. Every
--    other column keeps the write access it had, so no new rule is invented.
--
-- 2. DOC-02: the classification-downgrade guard belongs on doc.document, the
--    table that owns classification. A document_version inherits it. The
--    "audited declassification record" exception is a future feature and is
--    deliberately not implemented; downgrades are rejected unconditionally
--    until that contract exists.
--
-- 3. Review interpretations recorded as database comments:
--      - an approved academic calendar is treated as the active calendar;
--      - course_type and student_category may narrow an entity scope.
--
-- Forward-only. Supersedes the grant block in 0003_w1a_security.sql without
-- editing that already-applied file.
-- ===========================================================================

-- ===========================================================================
-- 1. app_erp column-level write grants
-- ===========================================================================

REVOKE INSERT, UPDATE ON iam.person FROM app_erp;

GRANT INSERT (
    person_id, legal_name, preferred_name, date_of_birth, photo_uri,
    deceased_flag, created_at, created_by, updated_at, updated_by, row_version
) ON iam.person TO app_erp;

GRANT UPDATE (
    person_id, legal_name, preferred_name, date_of_birth, photo_uri,
    deceased_flag, created_at, created_by, updated_at, updated_by, row_version
) ON iam.person TO app_erp;

REVOKE INSERT, UPDATE ON iam.identity_account FROM app_erp;

GRANT INSERT (
    account_id, person_id, idp_code, subject, username, email, account_type,
    mfa_enabled, status, last_login_at, disabled_at, created_at, created_by,
    updated_at, updated_by, row_version
) ON iam.identity_account TO app_erp;

GRANT UPDATE (
    account_id, person_id, idp_code, subject, username, email, account_type,
    mfa_enabled, status, last_login_at, disabled_at, created_at, created_by,
    updated_at, updated_by, row_version
) ON iam.identity_account TO app_erp;

-- ===========================================================================
-- 2. DOC-02: no classification downgrade on doc.document
-- ===========================================================================

CREATE OR REPLACE FUNCTION doc.reject_classification_downgrade()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, doc
AS $function$
DECLARE
    old_rank integer;
    new_rank integer;
BEGIN
    old_rank := CASE OLD.classification
        WHEN 'P' THEN 1
        WHEN 'I' THEN 2
        WHEN 'C' THEN 3
        WHEN 'R' THEN 4
        WHEN 'G' THEN 5
    END;

    new_rank := CASE NEW.classification
        WHEN 'P' THEN 1
        WHEN 'I' THEN 2
        WHEN 'C' THEN 3
        WHEN 'R' THEN 4
        WHEN 'G' THEN 5
    END;

    IF new_rank < old_rank THEN
        RAISE EXCEPTION
            'doc.document: classification cannot be downgraded from % to % without an audited declassification record',
            OLD.classification, NEW.classification;
    END IF;

    RETURN NEW;
END;
$function$;

ALTER FUNCTION doc.reject_classification_downgrade() OWNER TO owner_doc;
REVOKE EXECUTE ON FUNCTION doc.reject_classification_downgrade() FROM PUBLIC;

CREATE TRIGGER trg_document_classification_no_downgrade
    BEFORE UPDATE OF classification ON doc.document
    FOR EACH ROW
    WHEN (NEW.classification IS DISTINCT FROM OLD.classification)
    EXECUTE FUNCTION doc.reject_classification_downgrade();

-- ===========================================================================
-- 3. Record the review interpretations
-- ===========================================================================

COMMENT ON INDEX core.uq_academic_calendar_approved_per_term IS
    'Review ruling 2026-11-07: an approved calendar is treated as the active calendar for its term until a distinct active state is defined.';

COMMENT ON CONSTRAINT ck_rule_scope_scope_match ON policy.rule_scope IS
    'Review ruling 2026-11-07: course_type and student_category may narrow an institution/programme/batch/term scope; they are the sole scope only when scope_type names them.';
