-- ===========================================================================
-- 0013_w5_exam.sql
-- W5 exam results
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- EXM-01 exam.result_import
CREATE TABLE exam.result_import (
    result_import_id uuid NOT NULL DEFAULT gen_random_uuid(),
    term_id uuid NOT NULL,
    programme_id uuid NOT NULL,
    external_system_id uuid,
    source_label text NOT NULL,
    file_name text NOT NULL,
    sha256 text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    imported_by uuid NOT NULL,
    row_count integer NOT NULL DEFAULT 0,
    error_count integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'received',
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_result_import PRIMARY KEY (result_import_id)
);
ALTER TABLE exam.result_import OWNER TO owner_exam;

-- EXM-02 exam.result_set
CREATE TABLE exam.result_set (
    result_set_id uuid NOT NULL DEFAULT gen_random_uuid(),
    term_id uuid NOT NULL,
    programme_id uuid NOT NULL,
    batch_id uuid,
    import_id uuid,
    exam_label text NOT NULL,
    result_type text NOT NULL DEFAULT 'regular',
    status text NOT NULL DEFAULT 'imported',
    approved_by uuid,
    approved_at timestamptz,
    published_at timestamptz,
    external_publication_ref text,
    policy_bundle_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_result_set PRIMARY KEY (result_set_id)
);
ALTER TABLE exam.result_set OWNER TO owner_exam;

-- EXM-03 exam.result_record
CREATE TABLE exam.result_record (
    result_record_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    course_version_id uuid NOT NULL,
    course_offering_id uuid,
    result_set_id uuid NOT NULL,
    attempt_no smallint NOT NULL DEFAULT 1,
    is_backlog boolean NOT NULL DEFAULT FALSE,
    year_of_study smallint NOT NULL,
    current_revision_no integer NOT NULL DEFAULT 1,
    status text NOT NULL DEFAULT 'fail',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_result_record PRIMARY KEY (result_record_id)
);
ALTER TABLE exam.result_record OWNER TO owner_exam;

-- EXM-04 exam.result_revision
CREATE TABLE exam.result_revision (
    result_revision_id uuid NOT NULL DEFAULT gen_random_uuid(),
    result_record_id uuid NOT NULL,
    revision_no integer NOT NULL DEFAULT 1,
    cia_total numeric(6,2),
    pcia_total numeric(6,2),
    ese_total numeric(6,2),
    pese_total numeric(6,2),
    total_marks numeric(6,2),
    grade text,
    grade_point numeric(4,2),
    result_status text,
    computed_at timestamptz NOT NULL DEFAULT now(),
    computed_by uuid,
    published_at timestamptz,
    policy_bundle_version_id uuid,
    change_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_result_revision PRIMARY KEY (result_revision_id)
);
ALTER TABLE exam.result_revision OWNER TO owner_exam;

-- EXM-05 exam.result_input
CREATE TABLE exam.result_input (
    result_input_id uuid NOT NULL DEFAULT gen_random_uuid(),
    result_revision_id uuid NOT NULL,
    mark_entry_version_id uuid,
    component_code text NOT NULL,
    marks_used numeric(6,2) NOT NULL,
    max_marks_snapshot numeric(6,2) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_result_input PRIMARY KEY (result_input_id)
);
ALTER TABLE exam.result_input OWNER TO owner_exam;

-- EXM-06 exam.grade_card
CREATE TABLE exam.grade_card (
    grade_card_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    result_set_id uuid,
    version_no integer NOT NULL DEFAULT 1,
    sgpa numeric(4,2),
    ygpa numeric(4,2),
    cgpa numeric(4,2),
    credits_registered numeric(5,1),
    credits_earned numeric(5,1),
    status text NOT NULL DEFAULT 'draft',
    published_at timestamptz,
    is_current boolean NOT NULL DEFAULT TRUE,
    document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_grade_card PRIMARY KEY (grade_card_id)
);
ALTER TABLE exam.grade_card OWNER TO owner_exam;

-- EXM-07 exam.grade_card_result
CREATE TABLE exam.grade_card_result (
    grade_card_result_id uuid NOT NULL DEFAULT gen_random_uuid(),
    grade_card_id uuid NOT NULL,
    result_record_id uuid NOT NULL,
    result_revision_id uuid NOT NULL,
    included boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_grade_card_result PRIMARY KEY (grade_card_result_id)
);
ALTER TABLE exam.grade_card_result OWNER TO owner_exam;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- EXM-01
ALTER TABLE exam.result_import ADD CONSTRAINT uq_result_import UNIQUE (term_id, programme_id, sha256);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_source_label CHECK (char_length(source_label) <= 100);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_file_name CHECK (char_length(file_name) <= 300);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_sha256 CHECK (char_length(sha256) = 64);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_row_count CHECK (row_count >= 0);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_error_count CHECK (error_count >= 0);
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_status CHECK (status IN ('received', 'parsed', 'validated', 'imported', 'failed', 'quarantined'));
ALTER TABLE exam.result_import ADD CONSTRAINT ck_result_import_notes CHECK ((notes IS NULL OR (char_length(notes) <= 2000)));

-- EXM-02
ALTER TABLE exam.result_set ADD CONSTRAINT uq_result_set UNIQUE NULLS NOT DISTINCT (term_id, programme_id, batch_id, exam_label, result_type);
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_exam_label CHECK (char_length(exam_label) <= 100);
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_result_type CHECK (result_type IN ('regular', 'supplementary', 'super_supplementary'));
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_status CHECK (status IN ('imported', 'draft', 'approved', 'published', 'withheld'));
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_published_at CHECK ((published_at IS NULL OR published_at >= approved_at));
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_external_publication_ref CHECK ((external_publication_ref IS NULL OR (char_length(external_publication_ref) <= 200)));
ALTER TABLE exam.result_set ADD CONSTRAINT ck_result_set_published_gate CHECK ((status <> 'published' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL) OR external_publication_ref IS NOT NULL));

-- EXM-03
ALTER TABLE exam.result_record ADD CONSTRAINT uq_result_record UNIQUE (student_id, course_version_id, result_set_id);
ALTER TABLE exam.result_record ADD CONSTRAINT ck_result_record_attempt_no CHECK (attempt_no >= 1);
ALTER TABLE exam.result_record ADD CONSTRAINT ck_result_record_year_of_study CHECK (year_of_study BETWEEN 1 AND 5);
ALTER TABLE exam.result_record ADD CONSTRAINT ck_result_record_current_revision_no CHECK (current_revision_no >= 1);
ALTER TABLE exam.result_record ADD CONSTRAINT ck_result_record_status CHECK (status IN ('pass', 'fail', 'absent', 'withheld'));

-- EXM-04
ALTER TABLE exam.result_revision ADD CONSTRAINT uq_result_revision UNIQUE (result_record_id, revision_no);
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_revision_no CHECK (revision_no >= 1);
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_cia_total CHECK ((cia_total IS NULL OR (cia_total >= 0)));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_pcia_total CHECK ((pcia_total IS NULL OR (pcia_total >= 0)));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_ese_total CHECK ((ese_total IS NULL OR (ese_total >= 0)));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_pese_total CHECK ((pese_total IS NULL OR (pese_total >= 0)));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_total_marks CHECK ((total_marks IS NULL OR (total_marks >= 0)));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_grade CHECK ((grade IS NULL OR (grade IN ('O', 'E', 'A', 'B', 'C', 'D', 'F', 'I'))));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_grade_point CHECK ((grade_point IS NULL OR grade_point BETWEEN 0 AND 10));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_result_status CHECK ((result_status IS NULL OR (result_status IN ('X', 'XP', 'P'))));
ALTER TABLE exam.result_revision ADD CONSTRAINT ck_result_revision_change_reason CHECK ((change_reason IS NULL OR (char_length(change_reason) <= 1000)));

-- EXM-05
ALTER TABLE exam.result_input ADD CONSTRAINT uq_result_input UNIQUE (result_revision_id, component_code);
ALTER TABLE exam.result_input ADD CONSTRAINT ck_result_input_component_code CHECK (char_length(component_code) <= 30);
ALTER TABLE exam.result_input ADD CONSTRAINT ck_result_input_marks_used CHECK (marks_used >= 0);
ALTER TABLE exam.result_input ADD CONSTRAINT ck_result_input_max_marks_snapshot CHECK (max_marks_snapshot > 0);

-- EXM-06
ALTER TABLE exam.grade_card ADD CONSTRAINT uq_grade_card UNIQUE (student_id, term_id, version_no);
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_version_no CHECK (version_no >= 1);
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_sgpa CHECK ((sgpa IS NULL OR sgpa BETWEEN 0 AND 10));
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_ygpa CHECK ((ygpa IS NULL OR ygpa BETWEEN 0 AND 10));
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_cgpa CHECK ((cgpa IS NULL OR cgpa BETWEEN 0 AND 10));
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_credits_registered CHECK ((credits_registered IS NULL OR (credits_registered >= 0)));
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_status CHECK (status IN ('draft', 'published', 'superseded', 'withheld'));
ALTER TABLE exam.grade_card ADD CONSTRAINT ck_grade_card_credits_earned CHECK ((credits_earned IS NULL OR (credits_earned >= 0 AND credits_earned <= credits_registered)));

-- EXM-07
ALTER TABLE exam.grade_card_result ADD CONSTRAINT uq_grade_card_result UNIQUE (grade_card_id, result_record_id);

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- EXM-01
ALTER TABLE exam.result_import ADD CONSTRAINT fk_result_import_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_import ADD CONSTRAINT fk_result_import_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_import ADD CONSTRAINT fk_result_import_external_system_id FOREIGN KEY (external_system_id) REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_import ADD CONSTRAINT fk_result_import_imported_by FOREIGN KEY (imported_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- EXM-02
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_import_id FOREIGN KEY (import_id) REFERENCES exam.result_import (result_import_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_set ADD CONSTRAINT fk_result_set_policy_bundle_version_id FOREIGN KEY (policy_bundle_version_id) REFERENCES policy.policy_bundle_version (policy_bundle_version_id) ON DELETE RESTRICT;

-- EXM-03
ALTER TABLE exam.result_record ADD CONSTRAINT fk_result_record_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_record ADD CONSTRAINT fk_result_record_course_version_id FOREIGN KEY (course_version_id) REFERENCES academic.course_version (course_version_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_record ADD CONSTRAINT fk_result_record_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_record ADD CONSTRAINT fk_result_record_result_set_id FOREIGN KEY (result_set_id) REFERENCES exam.result_set (result_set_id) ON DELETE RESTRICT;

-- EXM-04
ALTER TABLE exam.result_revision ADD CONSTRAINT fk_result_revision_result_record_id FOREIGN KEY (result_record_id) REFERENCES exam.result_record (result_record_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_revision ADD CONSTRAINT fk_result_revision_computed_by FOREIGN KEY (computed_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_revision ADD CONSTRAINT fk_result_revision_policy_bundle_version_id FOREIGN KEY (policy_bundle_version_id) REFERENCES policy.policy_bundle_version (policy_bundle_version_id) ON DELETE RESTRICT;

-- EXM-05
ALTER TABLE exam.result_input ADD CONSTRAINT fk_result_input_result_revision_id FOREIGN KEY (result_revision_id) REFERENCES exam.result_revision (result_revision_id) ON DELETE RESTRICT;
ALTER TABLE exam.result_input ADD CONSTRAINT fk_result_input_mark_entry_version_id FOREIGN KEY (mark_entry_version_id) REFERENCES assessment.mark_entry_version (mark_entry_version_id) ON DELETE RESTRICT;

-- EXM-06
ALTER TABLE exam.grade_card ADD CONSTRAINT fk_grade_card_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE exam.grade_card ADD CONSTRAINT fk_grade_card_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE exam.grade_card ADD CONSTRAINT fk_grade_card_result_set_id FOREIGN KEY (result_set_id) REFERENCES exam.result_set (result_set_id) ON DELETE RESTRICT;
ALTER TABLE exam.grade_card ADD CONSTRAINT fk_grade_card_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- EXM-07
ALTER TABLE exam.grade_card_result ADD CONSTRAINT fk_grade_card_result_grade_card_id FOREIGN KEY (grade_card_id) REFERENCES exam.grade_card (grade_card_id) ON DELETE RESTRICT;
ALTER TABLE exam.grade_card_result ADD CONSTRAINT fk_grade_card_result_result_record_id FOREIGN KEY (result_record_id) REFERENCES exam.result_record (result_record_id) ON DELETE RESTRICT;
ALTER TABLE exam.grade_card_result ADD CONSTRAINT fk_grade_card_result_result_revision_id FOREIGN KEY (result_revision_id) REFERENCES exam.result_revision (result_revision_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- EXM-01
CREATE INDEX ix_result_import_term_programme ON exam.result_import (term_id, programme_id);
CREATE INDEX ix_result_import_status_imported ON exam.result_import (status, imported_at);
CREATE INDEX ix_result_import_programme_id ON exam.result_import (programme_id);
CREATE INDEX ix_result_import_external_system_id ON exam.result_import (external_system_id);
CREATE INDEX ix_result_import_imported_by ON exam.result_import (imported_by);

-- EXM-02
CREATE INDEX ix_result_set_term_programme_status ON exam.result_set (term_id, programme_id, status);
CREATE INDEX ix_result_set_published ON exam.result_set (published_at);
CREATE INDEX ix_result_set_programme_id ON exam.result_set (programme_id);
CREATE INDEX ix_result_set_batch_id ON exam.result_set (batch_id);
CREATE INDEX ix_result_set_import_id ON exam.result_set (import_id);
CREATE INDEX ix_result_set_approved_by ON exam.result_set (approved_by);
CREATE INDEX ix_result_set_policy_bundle_version_id ON exam.result_set (policy_bundle_version_id);

-- EXM-03
CREATE INDEX ix_result_record_student_course ON exam.result_record (student_id, course_version_id);
CREATE INDEX ix_result_record_result_set ON exam.result_record (result_set_id);
CREATE INDEX ix_result_record_status ON exam.result_record (status);
CREATE INDEX ix_result_record_course_version_id ON exam.result_record (course_version_id);
CREATE INDEX ix_result_record_course_offering_id ON exam.result_record (course_offering_id);

-- EXM-04
CREATE INDEX ix_result_revision_record_no ON exam.result_revision (result_record_id, revision_no DESC);
CREATE INDEX ix_result_revision_status ON exam.result_revision (result_status);
CREATE INDEX ix_result_revision_computed_by ON exam.result_revision (computed_by);
CREATE INDEX ix_result_revision_policy_bundle_version_id ON exam.result_revision (policy_bundle_version_id);

-- EXM-05
CREATE INDEX ix_result_input_mark_version ON exam.result_input (mark_entry_version_id);

-- EXM-06
CREATE INDEX ix_grade_card_student_term_version ON exam.grade_card (student_id, term_id, version_no DESC);
CREATE INDEX ix_grade_card_result_set ON exam.grade_card (result_set_id);
CREATE UNIQUE INDEX uq_grade_card_current ON exam.grade_card (student_id, term_id) WHERE is_current;
CREATE INDEX ix_grade_card_term_id ON exam.grade_card (term_id);
CREATE INDEX ix_grade_card_document_version_id ON exam.grade_card (document_version_id);

-- EXM-07
CREATE INDEX ix_grade_card_result_record ON exam.grade_card_result (result_record_id);
CREATE INDEX ix_grade_card_result_result_revision_id ON exam.grade_card_result (result_revision_id);

-- ---------------------------------------------------------------------------
-- 5. Business-rule triggers
-- ---------------------------------------------------------------------------

-- EXM-04: a published result revision is immutable. Draft revisions remain
-- editable by the COE service until publication.
CREATE OR REPLACE FUNCTION exam.enforce_result_revision_seal()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, exam
AS $function$
BEGIN
    IF OLD.published_at IS NOT NULL THEN
        RAISE EXCEPTION
            'exam.result_revision %: a published revision is immutable',
            OLD.result_revision_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION exam.enforce_result_revision_seal() OWNER TO owner_exam;
REVOKE EXECUTE ON FUNCTION exam.enforce_result_revision_seal() FROM PUBLIC;

CREATE TRIGGER trg_result_revision_seal
    BEFORE UPDATE OR DELETE ON exam.result_revision
    FOR EACH ROW
    EXECUTE FUNCTION exam.enforce_result_revision_seal();

-- EXM-05: result_input is append-only (POSTGRES_ARCHITECTURE 10.2).
CREATE OR REPLACE FUNCTION exam.enforce_result_input_append_only()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, exam
AS $function$
BEGIN
    RAISE EXCEPTION
        'exam.result_input %: append-only table',
        OLD.result_input_id
        USING ERRCODE = 'check_violation';
END;
$function$;
ALTER FUNCTION exam.enforce_result_input_append_only() OWNER TO owner_exam;
REVOKE EXECUTE ON FUNCTION exam.enforce_result_input_append_only() FROM PUBLIC;

CREATE TRIGGER trg_result_input_append_only
    BEFORE UPDATE OR DELETE ON exam.result_input
    FOR EACH ROW
    EXECUTE FUNCTION exam.enforce_result_input_append_only();

-- EXM-07: grade_card_result is append-only and must reference a revision that
-- belongs to the same result record.
CREATE OR REPLACE FUNCTION exam.enforce_grade_card_result_append_only()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, exam
AS $function$
BEGIN
    RAISE EXCEPTION
        'exam.grade_card_result %: append-only table',
        OLD.grade_card_result_id
        USING ERRCODE = 'check_violation';
END;
$function$;
ALTER FUNCTION exam.enforce_grade_card_result_append_only() OWNER TO owner_exam;
REVOKE EXECUTE ON FUNCTION exam.enforce_grade_card_result_append_only() FROM PUBLIC;

CREATE TRIGGER trg_grade_card_result_append_only
    BEFORE UPDATE OR DELETE ON exam.grade_card_result
    FOR EACH ROW
    EXECUTE FUNCTION exam.enforce_grade_card_result_append_only();

CREATE OR REPLACE FUNCTION exam.enforce_grade_card_result_revision()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, exam
AS $function$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM exam.result_revision r
        WHERE r.result_revision_id = NEW.result_revision_id
          AND r.result_record_id = NEW.result_record_id
    ) THEN
        RAISE EXCEPTION
            'exam.grade_card_result: revision % does not belong to result record %',
            NEW.result_revision_id, NEW.result_record_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION exam.enforce_grade_card_result_revision() OWNER TO owner_exam;
REVOKE EXECUTE ON FUNCTION exam.enforce_grade_card_result_revision() FROM PUBLIC;

CREATE TRIGGER trg_grade_card_result_revision
    BEFORE INSERT OR UPDATE ON exam.grade_card_result
    FOR EACH ROW
    EXECUTE FUNCTION exam.enforce_grade_card_result_revision();

-- ---------------------------------------------------------------------------
-- 6. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA exam FROM PUBLIC;

-- Every column of every EXM table is class C.
GRANT SELECT, INSERT, UPDATE ON
    exam.result_import, exam.result_set, exam.result_record,
    exam.result_revision, exam.result_input, exam.grade_card,
    exam.grade_card_result
TO app_erp;

-- ---------------------------------------------------------------------------
-- 7. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every exam table. The only documented
-- 9.3 intent is result_revision: a student sees the published revision only.
-- The COE arm waits for the named-role mapping (A-01); draft revisions and
-- every other exam table remain deny-by-default for application roles.

ALTER TABLE exam.result_import ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.result_import FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.result_set ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.result_set FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.result_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.result_record FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.result_revision ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.result_revision FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.result_input ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.result_input FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.grade_card ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.grade_card FORCE ROW LEVEL SECURITY;
ALTER TABLE exam.grade_card_result ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam.grade_card_result FORCE ROW LEVEL SECURITY;

CREATE POLICY p_result_import_owner_all ON exam.result_import
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_result_set_owner_all ON exam.result_set
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_result_record_owner_all ON exam.result_record
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_result_revision_owner_all ON exam.result_revision
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_result_input_owner_all ON exam.result_input
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_grade_card_owner_all ON exam.grade_card
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);
CREATE POLICY p_grade_card_result_owner_all ON exam.grade_card_result
    FOR ALL TO owner_exam USING (true) WITH CHECK (true);

-- Support policy for the revision policy below: a student can resolve only
-- their own result record. This exposes no other student's row and no revision.
CREATE POLICY p_result_record_access_select ON exam.result_record
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        student_id IN (
            SELECT s.student_id
            FROM student.student s
            WHERE s.person_id = (SELECT iam.current_person_id())
        )
    );

-- Documented 9.3 intent: student sees the published revision only. The COE
-- arm is deferred under A-01.
CREATE POLICY p_result_revision_access_select ON exam.result_revision
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        published_at IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM exam.result_record rr
            WHERE rr.result_record_id = result_revision.result_record_id
              AND rr.student_id IN (
                  SELECT s.student_id
                  FROM student.student s
                  WHERE s.person_id = (SELECT iam.current_person_id())
              )
        )
    );

-- ---------------------------------------------------------------------------
-- 8. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE exam.result_import IS
    'EXM-01: provenance row; the unique key binds a file to a term/programme by SHA-256.';

COMMENT ON TABLE exam.result_set IS
    'EXM-02: publication cannot precede approval (ck_result_set_published_at). Approval and publication authority remain with the COE and are not role-mapped until A-01.';

COMMENT ON TABLE exam.result_revision IS
    'EXM-04: draft revisions are COE-only; the student policy exposes a revision only after published_at is set. trg_result_revision_seal makes a published revision immutable.';

COMMENT ON TABLE exam.result_input IS
    'EXM-05: append-only trace from a result revision to the exact mark versions used; trg_result_input_append_only rejects update and delete.';

COMMENT ON TABLE exam.grade_card IS
    'EXM-06: at most one current grade card per student/term (uq_grade_card_current).';

COMMENT ON TABLE exam.grade_card_result IS
    'EXM-07: append-only composition; trg_grade_card_result_revision requires the revision to belong to the record.';

COMMENT ON POLICY p_result_revision_access_select ON exam.result_revision IS
    'POSTGRES_ARCHITECTURE 9.3: student sees own published revision only. Draft revisions and the COE arm wait for A-01.';