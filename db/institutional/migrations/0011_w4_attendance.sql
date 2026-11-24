-- ===========================================================================
-- 0011_w4_attendance.sql
-- W4 attendance
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- ATT-01 attendance.session
CREATE TABLE attendance.session (
    session_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL,
    timetable_slot_id uuid,
    session_date date NOT NULL,
    start_time time NOT NULL,
    end_time time NOT NULL,
    session_type text NOT NULL DEFAULT 'theory',
    topic text,
    delivery_mode text NOT NULL DEFAULT 'offline',
    status text NOT NULL DEFAULT 'scheduled',
    held_by_person_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_session PRIMARY KEY (session_id)
);
ALTER TABLE attendance.session OWNER TO owner_attendance;

-- ATT-02 attendance.record
CREATE TABLE attendance.record (
    attendance_record_id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    student_id uuid NOT NULL,
    course_registration_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    status text NOT NULL DEFAULT 'absent',
    source text NOT NULL DEFAULT 'faculty_manual',
    marked_at timestamptz NOT NULL DEFAULT now(),
    marked_by uuid,
    remarks text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_record PRIMARY KEY (attendance_record_id)
);
ALTER TABLE attendance.record OWNER TO owner_attendance;

-- ATT-03 attendance.correction
CREATE TABLE attendance.correction (
    correction_id uuid NOT NULL DEFAULT gen_random_uuid(),
    attendance_record_id uuid NOT NULL,
    old_status text NOT NULL,
    new_status text NOT NULL,
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
    CONSTRAINT pk_correction PRIMARY KEY (correction_id)
);
ALTER TABLE attendance.correction OWNER TO owner_attendance;

-- ATT-04 attendance.summary
CREATE TABLE attendance.summary (
    summary_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    sessions_conducted integer NOT NULL DEFAULT 0,
    sessions_attended integer NOT NULL DEFAULT 0,
    attendance_pct numeric(5,2) NOT NULL DEFAULT 0,
    as_of timestamptz NOT NULL DEFAULT now(),
    calculation_version text NOT NULL DEFAULT 'v1',
    policy_rule_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_summary PRIMARY KEY (summary_id)
);
ALTER TABLE attendance.summary OWNER TO owner_attendance;

-- ATT-05 attendance.eligibility_assessment
CREATE TABLE attendance.eligibility_assessment (
    eligibility_assessment_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    rule_variant text NOT NULL,
    aggregate_pct numeric(5,2),
    theory_pct numeric(5,2),
    practical_pct numeric(5,2),
    outcome text NOT NULL DEFAULT 'pending',
    computed_at timestamptz NOT NULL DEFAULT now(),
    inputs_json jsonb DEFAULT '{}',
    policy_bundle_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_eligibility_assessment PRIMARY KEY (eligibility_assessment_id)
);
ALTER TABLE attendance.eligibility_assessment OWNER TO owner_attendance;

-- ATT-06 attendance.condonation_case
CREATE TABLE attendance.condonation_case (
    condonation_case_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    eligibility_assessment_id uuid NOT NULL,
    shortfall_pct numeric(5,2) NOT NULL,
    grounds text,
    evidence_summary text,
    hod_recommendation text,
    ac_decision text,
    decision_date date,
    order_document_version_id uuid,
    status text NOT NULL DEFAULT 'opened',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_condonation_case PRIMARY KEY (condonation_case_id)
);
ALTER TABLE attendance.condonation_case OWNER TO owner_attendance;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- ATT-01
ALTER TABLE attendance.session ADD CONSTRAINT uq_session_offering_date_start UNIQUE (course_offering_id, session_date, start_time);
ALTER TABLE attendance.session ADD CONSTRAINT uq_session_offering_target UNIQUE (session_id, course_offering_id);
ALTER TABLE attendance.session ADD CONSTRAINT ck_session_end_time CHECK (end_time > start_time);
ALTER TABLE attendance.session ADD CONSTRAINT ck_session_session_type CHECK (session_type IN ('theory', 'practical', 'tutorial'));
ALTER TABLE attendance.session ADD CONSTRAINT ck_session_topic CHECK ((topic IS NULL OR (char_length(topic) <= 500)));
ALTER TABLE attendance.session ADD CONSTRAINT ck_session_delivery_mode CHECK (delivery_mode IN ('offline', 'online', 'hybrid'));
ALTER TABLE attendance.session ADD CONSTRAINT ck_session_status CHECK (status IN ('scheduled', 'held', 'cancelled'));

-- ATT-02
ALTER TABLE attendance.record ADD CONSTRAINT uq_attendance_record_session_student UNIQUE (session_id, student_id);
ALTER TABLE attendance.record ADD CONSTRAINT ck_record_status CHECK (status IN ('present', 'absent', 'late', 'excused'));
ALTER TABLE attendance.record ADD CONSTRAINT ck_record_source CHECK (source IN ('faculty_manual', 'import', 'biometric', 'device'));
ALTER TABLE attendance.record ADD CONSTRAINT ck_record_remarks CHECK ((remarks IS NULL OR (char_length(remarks) <= 500)));

-- ATT-03
ALTER TABLE attendance.correction ADD CONSTRAINT ck_correction_old_status CHECK (old_status IN ('present', 'absent', 'late', 'excused'));
ALTER TABLE attendance.correction ADD CONSTRAINT ck_correction_new_status CHECK (new_status IN ('present', 'absent', 'late', 'excused') AND new_status <> old_status);
ALTER TABLE attendance.correction ADD CONSTRAINT ck_correction_reason CHECK (char_length(reason) BETWEEN 5 AND 2000);
ALTER TABLE attendance.correction ADD CONSTRAINT ck_correction_approved_at CHECK ((approved_at IS NULL OR approved_at >= requested_at));
ALTER TABLE attendance.correction ADD CONSTRAINT ck_correction_status CHECK (status IN ('requested', 'approved', 'rejected', 'withdrawn'));

-- ATT-04
ALTER TABLE attendance.summary ADD CONSTRAINT uq_attendance_summary_asof UNIQUE (student_id, course_offering_id, as_of);
ALTER TABLE attendance.summary ADD CONSTRAINT ck_summary_sessions_conducted CHECK (sessions_conducted >= 0);
ALTER TABLE attendance.summary ADD CONSTRAINT ck_summary_attendance_pct CHECK (attendance_pct BETWEEN 0 AND 100);
ALTER TABLE attendance.summary ADD CONSTRAINT ck_summary_calculation_version CHECK (char_length(calculation_version) <= 20);
ALTER TABLE attendance.summary ADD CONSTRAINT ck_summary_sessions_attended CHECK ((sessions_attended >= 0 AND sessions_attended <= sessions_conducted));

-- ATT-05
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT uq_attendance_eligibility_variant UNIQUE (student_id, term_id, rule_variant, computed_at);
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT ck_eligibility_assessment_rule_variant CHECK (rule_variant IN ('aggregate', 'split'));
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT ck_eligibility_assessment_aggregate_pct CHECK ((aggregate_pct IS NULL OR aggregate_pct BETWEEN 0 AND 100));
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT ck_eligibility_assessment_theory_pct CHECK ((theory_pct IS NULL OR theory_pct BETWEEN 0 AND 100));
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT ck_eligibility_assessment_practical_pct CHECK ((practical_pct IS NULL OR practical_pct BETWEEN 0 AND 100));
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT ck_eligibility_assessment_outcome CHECK (outcome IN ('eligible', 'shortage', 'not_condonable', 'pending'));

-- ATT-06
ALTER TABLE attendance.condonation_case ADD CONSTRAINT uq_condonation_student_term UNIQUE (student_id, term_id);
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_shortfall_pct CHECK (shortfall_pct BETWEEN 0 AND 100);
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_grounds CHECK ((grounds IS NULL OR (char_length(grounds) <= 2000)));
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_evidence_summary CHECK ((evidence_summary IS NULL OR (char_length(evidence_summary) <= 2000)));
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_hod_recommendation CHECK ((hod_recommendation IS NULL OR (char_length(hod_recommendation) <= 2000)));
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_ac_decision CHECK ((ac_decision IS NULL OR (ac_decision IN ('condoned', 'not_condoned', 'deferred'))));
ALTER TABLE attendance.condonation_case ADD CONSTRAINT ck_condonation_case_status CHECK (status IN ('opened', 'hod_recommended', 'ac_review', 'approved', 'rejected', 'closed'));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- ATT-01
ALTER TABLE attendance.session ADD CONSTRAINT fk_session_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE attendance.session ADD CONSTRAINT fk_session_timetable_slot_id FOREIGN KEY (timetable_slot_id) REFERENCES academic.timetable_slot (timetable_slot_id) ON DELETE RESTRICT;
ALTER TABLE attendance.session ADD CONSTRAINT fk_session_held_by_person_id FOREIGN KEY (held_by_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ATT-02
ALTER TABLE attendance.record ADD CONSTRAINT fk_record_session_id FOREIGN KEY (session_id) REFERENCES attendance.session (session_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_record_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_record_course_registration_id FOREIGN KEY (course_registration_id) REFERENCES student.course_registration (course_registration_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_record_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_record_marked_by FOREIGN KEY (marked_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_attendance_record_registration FOREIGN KEY (course_registration_id, student_id, course_offering_id) REFERENCES student.course_registration (course_registration_id, student_id, course_offering_id) ON DELETE RESTRICT;
ALTER TABLE attendance.record ADD CONSTRAINT fk_attendance_record_session_offering FOREIGN KEY (session_id, course_offering_id) REFERENCES attendance.session (session_id, course_offering_id) ON DELETE RESTRICT;

-- ATT-03
ALTER TABLE attendance.correction ADD CONSTRAINT fk_correction_attendance_record_id FOREIGN KEY (attendance_record_id) REFERENCES attendance.record (attendance_record_id) ON DELETE RESTRICT;
ALTER TABLE attendance.correction ADD CONSTRAINT fk_correction_requested_by FOREIGN KEY (requested_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE attendance.correction ADD CONSTRAINT fk_correction_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE attendance.correction ADD CONSTRAINT fk_correction_evidence_document_version_id FOREIGN KEY (evidence_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ATT-04
ALTER TABLE attendance.summary ADD CONSTRAINT fk_summary_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE attendance.summary ADD CONSTRAINT fk_summary_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE attendance.summary ADD CONSTRAINT fk_summary_policy_rule_version_id FOREIGN KEY (policy_rule_version_id) REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT;

-- ATT-05
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT fk_eligibility_assessment_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT fk_eligibility_assessment_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE attendance.eligibility_assessment ADD CONSTRAINT fk_eligibility_assessment_policy_bundle_version_id FOREIGN KEY (policy_bundle_version_id) REFERENCES policy.policy_bundle_version (policy_bundle_version_id) ON DELETE RESTRICT;

-- ATT-06
ALTER TABLE attendance.condonation_case ADD CONSTRAINT fk_condonation_case_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE attendance.condonation_case ADD CONSTRAINT fk_condonation_case_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE attendance.condonation_case ADD CONSTRAINT fk_condonation_case_eligibility_assessment_id FOREIGN KEY (eligibility_assessment_id) REFERENCES attendance.eligibility_assessment (eligibility_assessment_id) ON DELETE RESTRICT;
ALTER TABLE attendance.condonation_case ADD CONSTRAINT fk_condonation_case_order_document_version_id FOREIGN KEY (order_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- ATT-01
CREATE INDEX ix_session_offering_date ON attendance.session (course_offering_id, session_date);
CREATE INDEX ix_session_date_status ON attendance.session (session_date, status);
CREATE INDEX ix_session_timetable_slot_id ON attendance.session (timetable_slot_id);
CREATE INDEX ix_session_held_by_person_id ON attendance.session (held_by_person_id);

-- ATT-02
CREATE INDEX ix_attendance_record_student_session ON attendance.record (student_id, session_id);
CREATE INDEX ix_attendance_record_session_status ON attendance.record (session_id, status);
CREATE INDEX ix_attendance_record_registration ON attendance.record (course_registration_id);
CREATE INDEX ix_attendance_record_offering ON attendance.record (course_offering_id);
CREATE INDEX ix_record_marked_by ON attendance.record (marked_by);

-- ATT-03
CREATE INDEX ix_attendance_correction_record ON attendance.correction (attendance_record_id);
CREATE INDEX ix_attendance_correction_status_requested ON attendance.correction (status, requested_at);
CREATE INDEX ix_correction_requested_by ON attendance.correction (requested_by);
CREATE INDEX ix_correction_approved_by ON attendance.correction (approved_by);
CREATE INDEX ix_correction_evidence_document_version_id ON attendance.correction (evidence_document_version_id);

-- ATT-04
CREATE INDEX ix_attendance_summary_student_offering_asof ON attendance.summary (student_id, course_offering_id, as_of DESC);
CREATE INDEX ix_attendance_summary_offering ON attendance.summary (course_offering_id);
CREATE INDEX ix_summary_policy_rule_version_id ON attendance.summary (policy_rule_version_id);

-- ATT-05
CREATE INDEX ix_attendance_eligibility_student_term ON attendance.eligibility_assessment (student_id, term_id, computed_at DESC);
CREATE INDEX ix_attendance_eligibility_outcome ON attendance.eligibility_assessment (outcome);
CREATE INDEX ix_eligibility_assessment_term_id ON attendance.eligibility_assessment (term_id);
CREATE INDEX ix_eligibility_assessment_policy_bundle_version_id ON attendance.eligibility_assessment (policy_bundle_version_id);

-- ATT-06
CREATE INDEX ix_condonation_term_status ON attendance.condonation_case (term_id, status);
CREATE INDEX ix_condonation_student ON attendance.condonation_case (student_id);
CREATE INDEX ix_condonation_case_eligibility_assessment_id ON attendance.condonation_case (eligibility_assessment_id);
CREATE INDEX ix_condonation_case_order_document_version_id ON attendance.condonation_case (order_document_version_id);

-- ---------------------------------------------------------------------------
-- 5. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA attendance FROM PUBLIC;

-- All columns of ATT-01, ATT-02, ATT-04, and ATT-05 are class C or I.
GRANT SELECT, INSERT, UPDATE ON
    attendance.session, attendance.record, attendance.summary,
    attendance.eligibility_assessment
TO app_erp;

-- ATT-03 is class C/R: reason and evidence_document_version_id are class R.
-- reason is mandatory, so a direct INSERT without it is impossible. The
-- application gets a read projection only until a named-role correction
-- service is approved (OD-16 / A-01).
GRANT SELECT (
    correction_id, attendance_record_id, old_status, new_status,
    requested_by, requested_at, approved_by, approved_at, status,
    created_at, created_by, updated_at, updated_by, row_version
) ON attendance.correction TO app_erp;

-- ATT-06 is class R in every column. No application grant exists until the
-- named-role case view is approved (OD-16 / A-01).

-- ---------------------------------------------------------------------------
-- 6. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every attendance table. Application
-- policies implement only the documented 9.3 intent for attendance.record;
-- every other application access is deny-by-default. owner_attendance owns
-- the tables and receives an explicit ALL policy because FORCE RLS applies to
-- owners too.

ALTER TABLE attendance.session ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.session FORCE ROW LEVEL SECURITY;
ALTER TABLE attendance.record ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.record FORCE ROW LEVEL SECURITY;
ALTER TABLE attendance.correction ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.correction FORCE ROW LEVEL SECURITY;
ALTER TABLE attendance.summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.summary FORCE ROW LEVEL SECURITY;
ALTER TABLE attendance.eligibility_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.eligibility_assessment FORCE ROW LEVEL SECURITY;
ALTER TABLE attendance.condonation_case ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.condonation_case FORCE ROW LEVEL SECURITY;

CREATE POLICY p_session_owner_all ON attendance.session
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);
CREATE POLICY p_attendance_record_owner_all ON attendance.record
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);
CREATE POLICY p_attendance_correction_owner_all ON attendance.correction
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);
CREATE POLICY p_attendance_summary_owner_all ON attendance.summary
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);
CREATE POLICY p_attendance_eligibility_owner_all ON attendance.eligibility_assessment
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);
CREATE POLICY p_condonation_owner_all ON attendance.condonation_case
    FOR ALL TO owner_attendance USING (true) WITH CHECK (true);

-- POSTGRES_ARCHITECTURE 9.3: access if the student is visible or the actor is
-- allocated to the offering named by the record. The two arms are evaluated
-- against the record's own columns, not student-wide.
CREATE POLICY p_attendance_record_access_select ON attendance.record
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        (SELECT iam.can_access_student(student_id))
        OR (SELECT iam.is_allocated_to_offering(course_offering_id))
    );

-- ---------------------------------------------------------------------------
-- 7. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE attendance.record IS
    'ATT-02: the two composite foreign keys enforce that the student is registered in the session offering. p_attendance_record_access_select implements the 9.3 student-visible-or-allocated-faculty intent. No application write policy is installed; writes remain deny-by-default under A-01.';

COMMENT ON TABLE attendance.correction IS
    'ATT-03: the old and new status are both stored; the service updates attendance.record and writes the correction in one transaction. reason and evidence_document_version_id are class R and are outside the app_erp projection.';

COMMENT ON TABLE attendance.summary IS
    'ATT-04: derived snapshot. as_of and calculation_version make it recomputable; no trigger maintains it.';

COMMENT ON TABLE attendance.eligibility_assessment IS
    'ATT-05: both aggregate and split variants are stored with the policy bundle version. No gate blocks a student by default (G-01).';

COMMENT ON TABLE attendance.condonation_case IS
    'ATT-06: class R in every column. No app_erp grant exists until the named-role case view is approved (OD-16 / A-01).';