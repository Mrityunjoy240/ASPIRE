-- ===========================================================================
-- 0012_w4_assessment.sql
-- W4 assessment
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- ASM-01 assessment.scheme
CREATE TABLE assessment.scheme (
    scheme_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_version_id uuid NOT NULL,
    name text NOT NULL,
    effective_from_term_id uuid NOT NULL,
    effective_to_term_id uuid,
    status text NOT NULL DEFAULT 'draft',
    approved_by uuid,
    approved_at timestamptz,
    policy_bundle_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_scheme PRIMARY KEY (scheme_id)
);
ALTER TABLE assessment.scheme OWNER TO owner_assessment;

-- ASM-02 assessment.component
CREATE TABLE assessment.component (
    component_id uuid NOT NULL DEFAULT gen_random_uuid(),
    scheme_id uuid NOT NULL,
    component_code text NOT NULL,
    name text NOT NULL,
    component_type text NOT NULL DEFAULT 'internal',
    max_marks numeric(6,2) NOT NULL,
    weight_pct numeric(5,2) NOT NULL,
    parent_component_id uuid,
    sequence_no smallint NOT NULL DEFAULT 1,
    attendance_linked boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_component PRIMARY KEY (component_id)
);
ALTER TABLE assessment.component OWNER TO owner_assessment;

-- ASM-03 assessment.schedule
CREATE TABLE assessment.schedule (
    schedule_id uuid NOT NULL DEFAULT gen_random_uuid(),
    component_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    schedule_type text NOT NULL DEFAULT 'regular',
    scheduled_start timestamptz NOT NULL,
    scheduled_end timestamptz NOT NULL,
    duration_min integer NOT NULL,
    venue_text text,
    instructions text,
    status text NOT NULL DEFAULT 'planned',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_schedule PRIMARY KEY (schedule_id)
);
ALTER TABLE assessment.schedule OWNER TO owner_assessment;

-- ASM-04 assessment.mark_entry
CREATE TABLE assessment.mark_entry (
    mark_entry_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    component_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    current_version_no integer NOT NULL DEFAULT 1,
    status text NOT NULL DEFAULT 'draft',
    is_absent boolean NOT NULL DEFAULT FALSE,
    is_exempt boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_mark_entry PRIMARY KEY (mark_entry_id)
);
ALTER TABLE assessment.mark_entry OWNER TO owner_assessment;

-- ASM-05 assessment.mark_entry_version
CREATE TABLE assessment.mark_entry_version (
    mark_entry_version_id uuid NOT NULL DEFAULT gen_random_uuid(),
    mark_entry_id uuid NOT NULL,
    version_no integer NOT NULL,
    marks_obtained numeric(6,2),
    max_marks_snapshot numeric(6,2) NOT NULL,
    is_absent boolean NOT NULL DEFAULT FALSE,
    is_exempt boolean NOT NULL DEFAULT FALSE,
    status text NOT NULL DEFAULT 'draft',
    entered_by uuid NOT NULL,
    entered_at timestamptz NOT NULL DEFAULT now(),
    submitted_at timestamptz,
    verified_by uuid,
    verified_at timestamptz,
    change_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_mark_entry_version PRIMARY KEY (mark_entry_version_id)
);
ALTER TABLE assessment.mark_entry_version OWNER TO owner_assessment;

-- ASM-06 assessment.mark_correction
CREATE TABLE assessment.mark_correction (
    mark_correction_id uuid NOT NULL DEFAULT gen_random_uuid(),
    mark_entry_id uuid NOT NULL,
    from_version_id uuid NOT NULL,
    to_version_id uuid NOT NULL,
    reason text NOT NULL,
    requested_by uuid NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT now(),
    approved_by uuid,
    approved_at timestamptz,
    status text NOT NULL DEFAULT 'requested',
    evidence_document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_mark_correction PRIMARY KEY (mark_correction_id)
);
ALTER TABLE assessment.mark_correction OWNER TO owner_assessment;

-- ASM-07 assessment.conflict_declaration
CREATE TABLE assessment.conflict_declaration (
    conflict_declaration_id uuid NOT NULL DEFAULT gen_random_uuid(),
    faculty_person_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    student_id uuid NOT NULL,
    relationship_type text NOT NULL,
    declared_at timestamptz NOT NULL DEFAULT now(),
    action_taken text NOT NULL DEFAULT 'none',
    reassigned_to_person_id uuid,
    status text NOT NULL DEFAULT 'declared',
    document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_conflict_declaration PRIMARY KEY (conflict_declaration_id)
);
ALTER TABLE assessment.conflict_declaration OWNER TO owner_assessment;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- ASM-01
ALTER TABLE assessment.scheme ADD CONSTRAINT uq_assessment_scheme UNIQUE (course_version_id, name, effective_from_term_id);
ALTER TABLE assessment.scheme ADD CONSTRAINT ck_scheme_name CHECK (char_length(name) <= 100);
ALTER TABLE assessment.scheme ADD CONSTRAINT ck_scheme_status CHECK (status IN ('draft', 'approved', 'active', 'superseded'));
ALTER TABLE assessment.scheme ADD CONSTRAINT ck_scheme_effective_window CHECK ((effective_to_term_id IS NULL OR effective_to_term_id <> effective_from_term_id));

-- ASM-02
ALTER TABLE assessment.component ADD CONSTRAINT uq_assessment_component_code UNIQUE (scheme_id, component_code);
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_component_code CHECK (component_code IN ('CIA1', 'CIA2', 'PCIA', 'PESE', 'ESE', 'ATTENDANCE', 'ASSIGNMENT', 'CLASS_TEST', 'VIVA', 'PROJECT'));
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_name CHECK (char_length(name) <= 150);
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_component_type CHECK (component_type IN ('internal', 'external', 'practical', 'sessional'));
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_max_marks CHECK (max_marks > 0);
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_weight_pct CHECK (weight_pct BETWEEN 0 AND 100);
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_parent_component_id CHECK ((parent_component_id IS NULL OR (parent_component_id <> component_id)));
ALTER TABLE assessment.component ADD CONSTRAINT ck_component_sequence_no CHECK (sequence_no >= 1);

-- ASM-03
ALTER TABLE assessment.schedule ADD CONSTRAINT uq_assessment_schedule UNIQUE (component_id, course_offering_id, schedule_type);
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_schedule_type CHECK (schedule_type IN ('regular', 'makeup', 'reassessment'));
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_scheduled_end CHECK (scheduled_end > scheduled_start);
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_duration_min CHECK (duration_min > 0);
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_venue_text CHECK ((venue_text IS NULL OR (char_length(venue_text) <= 100)));
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_instructions CHECK ((instructions IS NULL OR (char_length(instructions) <= 2000)));
ALTER TABLE assessment.schedule ADD CONSTRAINT ck_schedule_status CHECK (status IN ('planned', 'held', 'cancelled', 'rescheduled'));

-- ASM-04
ALTER TABLE assessment.mark_entry ADD CONSTRAINT uq_assessment_mark_entry UNIQUE (student_id, component_id, course_offering_id);
ALTER TABLE assessment.mark_entry ADD CONSTRAINT ck_mark_entry_current_version_no CHECK (current_version_no >= 1);
ALTER TABLE assessment.mark_entry ADD CONSTRAINT ck_mark_entry_status CHECK (status IN ('draft', 'submitted', 'verified', 'locked'));

-- ASM-05
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT uq_assessment_mark_version UNIQUE (mark_entry_id, version_no);
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_version_no CHECK (version_no >= 1);
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_max_marks_snapshot CHECK (max_marks_snapshot > 0);
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_status CHECK (status IN ('draft', 'submitted', 'verified', 'locked'));
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_submitted_at CHECK ((submitted_at IS NULL OR submitted_at >= entered_at));
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_verified_at CHECK ((verified_at IS NULL OR verified_at >= submitted_at));
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_change_reason CHECK ((change_reason IS NULL OR (char_length(change_reason) <= 1000)));
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT ck_mark_entry_version_marks_obtained CHECK ((marks_obtained IS NULL OR (marks_obtained >= 0 AND marks_obtained <= max_marks_snapshot)));

-- ASM-06
ALTER TABLE assessment.mark_correction ADD CONSTRAINT ck_mark_correction_to_version_id CHECK (to_version_id <> from_version_id);
ALTER TABLE assessment.mark_correction ADD CONSTRAINT ck_mark_correction_reason CHECK (char_length(reason) BETWEEN 5 AND 2000);
ALTER TABLE assessment.mark_correction ADD CONSTRAINT ck_mark_correction_approved_at CHECK ((approved_at IS NULL OR approved_at >= requested_at));
ALTER TABLE assessment.mark_correction ADD CONSTRAINT ck_mark_correction_status CHECK (status IN ('requested', 'approved', 'rejected', 'withdrawn'));

-- ASM-07
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT uq_assessment_conflict UNIQUE (faculty_person_id, course_offering_id, student_id);
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT ck_conflict_declaration_relationship_type CHECK (relationship_type IN ('child', 'sibling', 'spouse', 'relative', 'other'));
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT ck_conflict_declaration_action_taken CHECK (action_taken IN ('none', 'reassigned', 'recused'));
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT ck_conflict_declaration_reassigned_to_person_id CHECK ((reassigned_to_person_id IS NULL OR (reassigned_to_person_id <> faculty_person_id)));
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT ck_conflict_declaration_status CHECK (status IN ('declared', 'under_review', 'resolved', 'rejected'));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- ASM-01
ALTER TABLE assessment.scheme ADD CONSTRAINT fk_scheme_course_version_id FOREIGN KEY (course_version_id) REFERENCES academic.course_version (course_version_id) ON DELETE RESTRICT;
ALTER TABLE assessment.scheme ADD CONSTRAINT fk_scheme_effective_from_term_id FOREIGN KEY (effective_from_term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE assessment.scheme ADD CONSTRAINT fk_scheme_effective_to_term_id FOREIGN KEY (effective_to_term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE assessment.scheme ADD CONSTRAINT fk_scheme_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.scheme ADD CONSTRAINT fk_scheme_policy_bundle_version_id FOREIGN KEY (policy_bundle_version_id) REFERENCES policy.policy_bundle_version (policy_bundle_version_id) ON DELETE RESTRICT;

-- ASM-02
ALTER TABLE assessment.component ADD CONSTRAINT fk_component_scheme_id FOREIGN KEY (scheme_id) REFERENCES assessment.scheme (scheme_id) ON DELETE RESTRICT;
ALTER TABLE assessment.component ADD CONSTRAINT fk_component_parent_component_id FOREIGN KEY (parent_component_id) REFERENCES assessment.component (component_id) ON DELETE RESTRICT;

-- ASM-03
ALTER TABLE assessment.schedule ADD CONSTRAINT fk_schedule_component_id FOREIGN KEY (component_id) REFERENCES assessment.component (component_id) ON DELETE RESTRICT;
ALTER TABLE assessment.schedule ADD CONSTRAINT fk_schedule_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;

-- ASM-04
ALTER TABLE assessment.mark_entry ADD CONSTRAINT fk_mark_entry_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_entry ADD CONSTRAINT fk_mark_entry_component_id FOREIGN KEY (component_id) REFERENCES assessment.component (component_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_entry ADD CONSTRAINT fk_mark_entry_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;

-- ASM-05
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT fk_mark_entry_version_mark_entry_id FOREIGN KEY (mark_entry_id) REFERENCES assessment.mark_entry (mark_entry_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT fk_mark_entry_version_entered_by FOREIGN KEY (entered_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_entry_version ADD CONSTRAINT fk_mark_entry_version_verified_by FOREIGN KEY (verified_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ASM-06
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_mark_entry_id FOREIGN KEY (mark_entry_id) REFERENCES assessment.mark_entry (mark_entry_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_from_version_id FOREIGN KEY (from_version_id) REFERENCES assessment.mark_entry_version (mark_entry_version_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_to_version_id FOREIGN KEY (to_version_id) REFERENCES assessment.mark_entry_version (mark_entry_version_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_requested_by FOREIGN KEY (requested_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.mark_correction ADD CONSTRAINT fk_mark_correction_evidence_document_version_id FOREIGN KEY (evidence_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ASM-07
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT fk_conflict_declaration_faculty_person_id FOREIGN KEY (faculty_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT fk_conflict_declaration_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT fk_conflict_declaration_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT fk_conflict_declaration_reassigned_to_person_id FOREIGN KEY (reassigned_to_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE assessment.conflict_declaration ADD CONSTRAINT fk_conflict_declaration_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- ASM-01
CREATE INDEX ix_assessment_scheme_course_status ON assessment.scheme (course_version_id, status);
CREATE INDEX ix_assessment_scheme_from_term ON assessment.scheme (effective_from_term_id);
CREATE INDEX ix_scheme_effective_to_term_id ON assessment.scheme (effective_to_term_id);
CREATE INDEX ix_scheme_approved_by ON assessment.scheme (approved_by);
CREATE INDEX ix_scheme_policy_bundle_version_id ON assessment.scheme (policy_bundle_version_id);

-- ASM-02
CREATE INDEX ix_assessment_component_scheme_sequence ON assessment.component (scheme_id, sequence_no);
CREATE INDEX ix_assessment_component_parent ON assessment.component (parent_component_id);

-- ASM-03
CREATE INDEX ix_assessment_schedule_offering_start ON assessment.schedule (course_offering_id, scheduled_start);

-- ASM-04
CREATE INDEX ix_assessment_mark_entry_offering_component ON assessment.mark_entry (course_offering_id, component_id);
CREATE INDEX ix_assessment_mark_entry_student ON assessment.mark_entry (student_id);
CREATE INDEX ix_mark_entry_component_id ON assessment.mark_entry (component_id);

-- ASM-05
CREATE INDEX ix_assessment_mark_version_entry ON assessment.mark_entry_version (mark_entry_id, version_no DESC);
CREATE INDEX ix_assessment_mark_version_entered_by ON assessment.mark_entry_version (entered_by);
CREATE INDEX ix_mark_entry_version_verified_by ON assessment.mark_entry_version (verified_by);

-- ASM-06
CREATE INDEX ix_assessment_mark_correction_entry ON assessment.mark_correction (mark_entry_id, requested_at DESC);
CREATE INDEX ix_assessment_mark_correction_status ON assessment.mark_correction (status);
CREATE INDEX ix_mark_correction_from_version_id ON assessment.mark_correction (from_version_id);
CREATE INDEX ix_mark_correction_to_version_id ON assessment.mark_correction (to_version_id);
CREATE INDEX ix_mark_correction_requested_by ON assessment.mark_correction (requested_by);
CREATE INDEX ix_mark_correction_approved_by ON assessment.mark_correction (approved_by);
CREATE INDEX ix_mark_correction_evidence_document_version_id ON assessment.mark_correction (evidence_document_version_id);

-- ASM-07
CREATE INDEX ix_assessment_conflict_offering_status ON assessment.conflict_declaration (course_offering_id, status);
CREATE INDEX ix_assessment_conflict_faculty ON assessment.conflict_declaration (faculty_person_id);
CREATE INDEX ix_conflict_declaration_student_id ON assessment.conflict_declaration (student_id);
CREATE INDEX ix_conflict_declaration_reassigned_to_person_id ON assessment.conflict_declaration (reassigned_to_person_id);
CREATE INDEX ix_conflict_declaration_document_version_id ON assessment.conflict_declaration (document_version_id);

-- ---------------------------------------------------------------------------
-- 5. Business-rule triggers
-- ---------------------------------------------------------------------------

-- ASM-02: once any mark_entry exists for a scheme, max_marks, weight_pct, and
-- component_code are frozen. A structural change requires a new scheme.
CREATE OR REPLACE FUNCTION assessment.enforce_component_immutable()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, assessment
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM assessment.mark_entry me
        JOIN assessment.component c ON c.component_id = me.component_id
        WHERE c.scheme_id = OLD.scheme_id
    ) THEN
        RAISE EXCEPTION
            'assessment.component %: max_marks, weight_pct, and component_code are frozen after the first mark entry',
            OLD.component_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION assessment.enforce_component_immutable() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_component_immutable() FROM PUBLIC;

CREATE TRIGGER trg_component_immutable
    BEFORE UPDATE OF max_marks, weight_pct, component_code ON assessment.component
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_component_immutable();

-- ASM-02: sibling weight_pct values must sum to 100 within each parent group.
-- The check is deferred so a complete scheme can be inserted in one
-- transaction. The dictionary's prose does not define nested normalisation
-- further; each group of siblings (including the root group) is required to
-- total 100.
CREATE OR REPLACE FUNCTION assessment.enforce_component_weight_sum()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, assessment
AS $function$
DECLARE
    v_scheme uuid;
    r record;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_scheme := OLD.scheme_id;
    ELSE
        v_scheme := NEW.scheme_id;
    END IF;

    FOR r IN
        SELECT c.parent_component_id AS parent_id,
               sum(c.weight_pct) AS total
        FROM assessment.component c
        WHERE c.scheme_id = v_scheme
        GROUP BY c.parent_component_id
    LOOP
        IF r.total <> 100 THEN
            RAISE EXCEPTION
                'assessment.component: sibling weight_pct in scheme % (parent %) sums to %, expected 100',
                v_scheme,
                coalesce(r.parent_id::text, '<root>'),
                r.total
                USING ERRCODE = 'check_violation';
        END IF;
    END LOOP;
    RETURN NULL;
END;
$function$;
ALTER FUNCTION assessment.enforce_component_weight_sum() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_component_weight_sum() FROM PUBLIC;

CREATE CONSTRAINT TRIGGER trg_component_weight_sum
    AFTER INSERT OR UPDATE OR DELETE ON assessment.component
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_component_weight_sum();

-- ASM-05: a verified or locked version is immutable.
CREATE OR REPLACE FUNCTION assessment.enforce_mark_version_immutable()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, assessment
AS $function$
BEGIN
    IF OLD.status IN ('verified', 'locked') THEN
        RAISE EXCEPTION
            'assessment.mark_entry_version %: a % version is immutable',
            OLD.mark_entry_version_id, OLD.status
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION assessment.enforce_mark_version_immutable() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_mark_version_immutable() FROM PUBLIC;

CREATE TRIGGER trg_mark_version_immutable
    BEFORE UPDATE OR DELETE ON assessment.mark_entry_version
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_mark_version_immutable();

-- ASM-06: both referenced versions must belong to the correction's mark entry.
CREATE OR REPLACE FUNCTION assessment.enforce_mark_correction_versions()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, assessment
AS $function$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM assessment.mark_entry_version v
        WHERE v.mark_entry_version_id = NEW.from_version_id
          AND v.mark_entry_id = NEW.mark_entry_id
    ) OR NOT EXISTS (
        SELECT 1
        FROM assessment.mark_entry_version v
        WHERE v.mark_entry_version_id = NEW.to_version_id
          AND v.mark_entry_id = NEW.mark_entry_id
    ) THEN
        RAISE EXCEPTION
            'assessment.mark_correction: from_version_id and to_version_id must belong to mark entry %',
            NEW.mark_entry_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION assessment.enforce_mark_correction_versions() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_mark_correction_versions() FROM PUBLIC;

CREATE TRIGGER trg_mark_correction_versions
    BEFORE INSERT OR UPDATE ON assessment.mark_correction
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_mark_correction_versions();

-- ASM-07: an unresolved conflict declaration blocks a mark entered by that
-- faculty member for that student in that offering. The dictionary assigns the
-- check to the authorization service; because this database is the shared
-- enforcement point for several applications, it is also enforced here.
CREATE OR REPLACE FUNCTION assessment.enforce_mark_conflict()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, assessment
AS $function$
DECLARE
    v_offering uuid;
    v_student uuid;
BEGIN
    SELECT me.course_offering_id, me.student_id
      INTO v_offering, v_student
      FROM assessment.mark_entry me
     WHERE me.mark_entry_id = NEW.mark_entry_id;

    IF EXISTS (
        SELECT 1
        FROM assessment.conflict_declaration cd
        WHERE cd.faculty_person_id = NEW.entered_by
          AND cd.course_offering_id = v_offering
          AND cd.student_id = v_student
          AND cd.status IN ('declared', 'under_review')
    ) THEN
        RAISE EXCEPTION
            'assessment.mark_entry_version: unresolved conflict declaration blocks faculty % for student %',
            NEW.entered_by, v_student
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION assessment.enforce_mark_conflict() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_mark_conflict() FROM PUBLIC;

CREATE TRIGGER trg_mark_conflict
    BEFORE INSERT OR UPDATE OF entered_by, mark_entry_id ON assessment.mark_entry_version
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_mark_conflict();

-- ASM-07 also names attendance.record writes. The table belongs to W4a, so the
-- guard is installed here, after the declaration table exists.
CREATE OR REPLACE FUNCTION assessment.enforce_attendance_conflict()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, assessment
AS $function$
BEGIN
    IF NEW.marked_by IS NULL THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM assessment.conflict_declaration cd
        WHERE cd.faculty_person_id = NEW.marked_by
          AND cd.course_offering_id = NEW.course_offering_id
          AND cd.student_id = NEW.student_id
          AND cd.status IN ('declared', 'under_review')
    ) THEN
        RAISE EXCEPTION
            'attendance.record: unresolved conflict declaration blocks faculty % for student %',
            NEW.marked_by, NEW.student_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION assessment.enforce_attendance_conflict() OWNER TO owner_assessment;
REVOKE EXECUTE ON FUNCTION assessment.enforce_attendance_conflict() FROM PUBLIC;

CREATE TRIGGER trg_attendance_conflict
    BEFORE INSERT OR UPDATE OF marked_by, course_offering_id, student_id
    ON attendance.record
    FOR EACH ROW
    EXECUTE FUNCTION assessment.enforce_attendance_conflict();

-- ---------------------------------------------------------------------------
-- 6. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA assessment FROM PUBLIC;

-- ASM-01 to ASM-05 are class I or C in every column.
GRANT SELECT, INSERT, UPDATE ON
    assessment.scheme, assessment.component, assessment.schedule,
    assessment.mark_entry, assessment.mark_entry_version
TO app_erp;

-- ASM-06 is class C/R: reason and evidence_document_version_id are class R.
-- reason is mandatory, so a direct INSERT without it is impossible. The
-- application gets a read projection only until a named-role correction
-- service is approved (OD-16 / A-01).
GRANT SELECT (
    mark_correction_id, mark_entry_id, from_version_id, to_version_id,
    requested_by, requested_at, approved_by, approved_at, status,
    created_at, created_by, updated_at, updated_by, row_version
) ON assessment.mark_correction TO app_erp;

-- ASM-07 is class R in every column. No application grant exists until the
-- named-role declaration view is approved (OD-16 / A-01).

-- ---------------------------------------------------------------------------
-- 7. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every assessment table. The only
-- documented 9.3 application intent is mark_entry_version: faculty see marks
-- for their own offerings. The student arm additionally requires the W5
-- result-set publication link and is deferred; the COE arm requires A-01.
-- mark_entry carries a support SELECT policy so the version policy can resolve
-- the offering without bypassing RLS.

ALTER TABLE assessment.scheme ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.scheme FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.component ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.component FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.schedule FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_entry ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_entry FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_entry_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_entry_version FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_correction ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.mark_correction FORCE ROW LEVEL SECURITY;
ALTER TABLE assessment.conflict_declaration ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.conflict_declaration FORCE ROW LEVEL SECURITY;

CREATE POLICY p_assessment_scheme_owner_all ON assessment.scheme
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_component_owner_all ON assessment.component
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_schedule_owner_all ON assessment.schedule
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_mark_entry_owner_all ON assessment.mark_entry
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_mark_version_owner_all ON assessment.mark_entry_version
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_mark_correction_owner_all ON assessment.mark_correction
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);
CREATE POLICY p_assessment_conflict_owner_all ON assessment.conflict_declaration
    FOR ALL TO owner_assessment USING (true) WITH CHECK (true);

-- Support policy for the mark_entry_version policy below.
CREATE POLICY p_assessment_mark_entry_access_select ON assessment.mark_entry
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING ((SELECT iam.is_allocated_to_offering(course_offering_id)));

-- Documented 9.3 intent: faculty see marks for their own offerings. The
-- student arm (own row when verified/locked and the result set is published)
-- waits for exam.result_set in W5; the COE arm waits for A-01.
CREATE POLICY p_assessment_mark_version_access_select
    ON assessment.mark_entry_version
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        EXISTS (
            SELECT 1
            FROM assessment.mark_entry me
            WHERE me.mark_entry_id = mark_entry_version.mark_entry_id
              AND (SELECT iam.is_allocated_to_offering(me.course_offering_id))
        )
    );

-- ---------------------------------------------------------------------------
-- 8. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE assessment.component IS
    'ASM-02: trg_component_immutable freezes max_marks, weight_pct, and component_code once any mark_entry exists for the scheme. trg_component_weight_sum is a deferred constraint trigger requiring each sibling group (including the root group) to total 100 weight_pct; a complete scheme must be written in one transaction.';

COMMENT ON TABLE assessment.mark_entry IS
    'ASM-04: current_version_no is maintained by the version-insert service and is not trigger-maintained here; the service must update the pointer and insert the version in one transaction.';

COMMENT ON TABLE assessment.mark_entry_version IS
    'ASM-05: trg_mark_version_immutable rejects UPDATE and DELETE after status becomes verified or locked. The student RLS arm waits for the W5 result-set publication link.';

COMMENT ON TABLE assessment.mark_correction IS
    'ASM-06: trg_mark_correction_versions enforces that both versions belong to the same mark entry. reason and evidence_document_version_id are class R and are outside the app_erp projection.';

COMMENT ON TABLE assessment.conflict_declaration IS
    'ASM-07: class R in every column; no app_erp grant. trg_mark_conflict and trg_attendance_conflict enforce the documented system rule that an unresolved declaration blocks assessment and attendance writes by that faculty member for that student.';

COMMENT ON POLICY p_assessment_mark_version_access_select
    ON assessment.mark_entry_version IS
    'POSTGRES_ARCHITECTURE 9.3: allocated-faculty arm implemented. The student arm waits for exam.result_set publication (W5) and the COE arm waits for A-01.';