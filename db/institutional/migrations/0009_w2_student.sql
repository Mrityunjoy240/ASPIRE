-- ===========================================================================
-- 0009_w2_student.sql
-- W2 student records
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- STU-01 student.admission_application
CREATE TABLE student.admission_application (
    application_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    programme_id uuid NOT NULL,
    batch_id uuid,
    application_no text NOT NULL,
    admission_year smallint NOT NULL,
    counselling_authority text,
    allotment_reference text,
    category text,
    eligibility_status text NOT NULL DEFAULT 'pending',
    application_status text NOT NULL DEFAULT 'draft',
    submitted_at timestamptz,
    verified_by uuid,
    verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_admission_application PRIMARY KEY (application_id)
);
ALTER TABLE student.admission_application OWNER TO owner_student;

-- STU-02 student.admission_offer
CREATE TABLE student.admission_offer (
    offer_id uuid NOT NULL DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL,
    offer_no text NOT NULL,
    offered_at timestamptz NOT NULL DEFAULT now(),
    accepted_at timestamptz,
    admission_confirmed_at timestamptz,
    fee_receipt_reference text,
    confirmed_by uuid,
    status text NOT NULL DEFAULT 'offered',
    remarks text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_admission_offer PRIMARY KEY (offer_id)
);
ALTER TABLE student.admission_offer OWNER TO owner_student;

-- STU-03 student.student
CREATE TABLE student.student (
    student_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    section_id uuid,
    admission_application_id uuid,
    college_roll_no text NOT NULL,
    admission_year smallint NOT NULL,
    entry_mode text NOT NULL DEFAULT 'regular',
    category text,
    date_of_admission date NOT NULL,
    expected_completion_year smallint,
    current_status text NOT NULL DEFAULT 'active',
    photo_uri text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_student PRIMARY KEY (student_id)
);
ALTER TABLE student.student OWNER TO owner_student;

-- STU-04 student.guardian
CREATE TABLE student.guardian (
    guardian_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    occupation text,
    education text,
    annual_income_band text,
    is_alumni boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_guardian PRIMARY KEY (guardian_id)
);
ALTER TABLE student.guardian OWNER TO owner_student;

-- STU-05 student.student_guardian
CREATE TABLE student.student_guardian (
    student_guardian_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    guardian_id uuid NOT NULL,
    relation text NOT NULL DEFAULT 'guardian',
    is_primary boolean NOT NULL DEFAULT FALSE,
    consent_status text NOT NULL DEFAULT 'pending',
    consent_recorded_at timestamptz,
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_student_guardian PRIMARY KEY (student_guardian_id)
);
ALTER TABLE student.student_guardian OWNER TO owner_student;

-- STU-06 student.student_document
CREATE TABLE student.student_document (
    student_document_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    document_type text NOT NULL,
    verification_status text NOT NULL DEFAULT 'pending',
    verified_by uuid,
    verified_at timestamptz,
    expires_on date,
    remarks text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_student_document PRIMARY KEY (student_document_id)
);
ALTER TABLE student.student_document OWNER TO owner_student;

-- STU-07 student.university_registration
CREATE TABLE student.university_registration (
    university_registration_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    registration_number text,
    registration_year smallint NOT NULL,
    status text NOT NULL DEFAULT 'pending',
    uploaded_at timestamptz,
    confirmed_at timestamptz,
    proof_document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_university_registration PRIMARY KEY (university_registration_id)
);
ALTER TABLE student.university_registration OWNER TO owner_student;

-- STU-08 student.exam_roll_number
CREATE TABLE student.exam_roll_number (
    exam_roll_number_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    programme_id uuid NOT NULL,
    roll_number text NOT NULL,
    college_code text NOT NULL,
    programme_code text NOT NULL,
    registration_year smallint NOT NULL,
    course_duration_years smallint NOT NULL,
    serial_no smallint NOT NULL,
    issued_on date NOT NULL DEFAULT CURRENT_DATE,
    is_current boolean NOT NULL DEFAULT TRUE,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_exam_roll_number PRIMARY KEY (exam_roll_number_id)
);
ALTER TABLE student.exam_roll_number OWNER TO owner_student;

-- STU-09 student.semester_registration
CREATE TABLE student.semester_registration (
    semester_registration_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    registration_no text,
    submitted_at timestamptz,
    approved_by uuid,
    approved_at timestamptz,
    status text NOT NULL DEFAULT 'draft',
    remarks text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_semester_registration PRIMARY KEY (semester_registration_id)
);
ALTER TABLE student.semester_registration OWNER TO owner_student;

-- STU-10 student.course_registration
CREATE TABLE student.course_registration (
    course_registration_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    semester_registration_id uuid NOT NULL,
    course_offering_id uuid NOT NULL,
    registration_type text NOT NULL DEFAULT 'regular',
    credits numeric(4,1) NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'registered',
    registered_at timestamptz NOT NULL DEFAULT now(),
    dropped_at timestamptz,
    drop_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_course_registration PRIMARY KEY (course_registration_id)
);
ALTER TABLE student.course_registration OWNER TO owner_student;

-- STU-11 student.status_history
CREATE TABLE student.status_history (
    status_history_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    status text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    reason text,
    order_document_version_id uuid,
    recorded_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_status_history PRIMARY KEY (status_history_id)
);
ALTER TABLE student.status_history OWNER TO owner_student;

-- STU-12 student.eligibility_determination
CREATE TABLE student.eligibility_determination (
    eligibility_determination_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    gate_code text NOT NULL,
    scope_type text NOT NULL DEFAULT 'term',
    scope_id uuid,
    status text NOT NULL DEFAULT 'unknown',
    policy_rule_version_id uuid,
    source text NOT NULL DEFAULT 'computed',
    evidence_json jsonb DEFAULT '{}',
    determined_at timestamptz NOT NULL DEFAULT now(),
    determined_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_eligibility_determination PRIMARY KEY (eligibility_determination_id)
);
ALTER TABLE student.eligibility_determination OWNER TO owner_student;

-- STU-15 student.section_assignment
CREATE TABLE student.section_assignment (
    section_assignment_id uuid NOT NULL DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL,
    section_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    effective_from date NOT NULL DEFAULT CURRENT_DATE,
    effective_to date,
    assignment_reason text NOT NULL DEFAULT 'initial_allotment',
    status text NOT NULL DEFAULT 'active',
    approved_by uuid,
    authority_role_assignment_id uuid,
    source_document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_section_assignment PRIMARY KEY (section_assignment_id)
);
ALTER TABLE student.section_assignment OWNER TO owner_student;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- STU-01
ALTER TABLE student.admission_application ADD CONSTRAINT uq_admission_application_year_no UNIQUE (admission_year, application_no);
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_admission_year CHECK (admission_year BETWEEN 2000 AND 2100);
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_counselling_authority CHECK ((counselling_authority IS NULL OR (counselling_authority IN ('WBJEE', 'JEE', 'JELET', 'JECA', 'JEMAT', 'PGET', 'institute'))));
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_allotment_reference CHECK ((allotment_reference IS NULL OR (char_length(allotment_reference) <= 100)));
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_category CHECK ((category IS NULL OR (category IN ('general', 'obc_a', 'obc_b', 'sc', 'st', 'ews', 'tfw', 'pwd', 'other'))));
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_eligibility_status CHECK (eligibility_status IN ('pending', 'eligible', 'ineligible', 'conditional'));
ALTER TABLE student.admission_application ADD CONSTRAINT ck_admission_application_application_status CHECK (application_status IN ('draft', 'submitted', 'under_verification', 'eligible', 'ineligible', 'waitlisted', 'offered', 'admitted', 'withdrawn'));

-- STU-02
ALTER TABLE student.admission_offer ADD CONSTRAINT uq_admission_offer_application UNIQUE (application_id);
ALTER TABLE student.admission_offer ADD CONSTRAINT uq_admission_offer_no UNIQUE (offer_no);
ALTER TABLE student.admission_offer ADD CONSTRAINT ck_admission_offer_offer_no CHECK (char_length(offer_no) <= 50);
ALTER TABLE student.admission_offer ADD CONSTRAINT ck_admission_offer_accepted_at CHECK ((accepted_at IS NULL OR accepted_at >= offered_at));
ALTER TABLE student.admission_offer ADD CONSTRAINT ck_admission_offer_fee_receipt_reference CHECK ((fee_receipt_reference IS NULL OR (char_length(fee_receipt_reference) <= 100)));
ALTER TABLE student.admission_offer ADD CONSTRAINT ck_admission_offer_status CHECK (status IN ('offered', 'accepted', 'confirmed', 'declined', 'expired', 'cancelled'));
ALTER TABLE student.admission_offer ADD CONSTRAINT ck_admission_offer_remarks CHECK ((remarks IS NULL OR (char_length(remarks) <= 2000)));

-- STU-03
ALTER TABLE student.student ADD CONSTRAINT uq_student_college_roll UNIQUE (college_roll_no);
ALTER TABLE student.student ADD CONSTRAINT uq_student_person_batch UNIQUE (person_id, batch_id);
ALTER TABLE student.student ADD CONSTRAINT uq_student_batch_target UNIQUE (student_id, batch_id);
ALTER TABLE student.student ADD CONSTRAINT ck_student_college_roll_no CHECK (char_length(college_roll_no) <= 30);
ALTER TABLE student.student ADD CONSTRAINT ck_student_admission_year CHECK (admission_year BETWEEN 2000 AND 2100);
ALTER TABLE student.student ADD CONSTRAINT ck_student_entry_mode CHECK (entry_mode IN ('regular', 'lateral', 'transfer'));
ALTER TABLE student.student ADD CONSTRAINT ck_student_category CHECK ((category IS NULL OR (category IN ('general', 'obc_a', 'obc_b', 'sc', 'st', 'ews', 'tfw', 'pwd', 'other'))));
ALTER TABLE student.student ADD CONSTRAINT ck_student_expected_completion_year CHECK ((expected_completion_year IS NULL OR expected_completion_year >= admission_year));
ALTER TABLE student.student ADD CONSTRAINT ck_student_current_status CHECK (current_status IN ('active', 'detained', 'suspended', 'year_lag', 'graduated', 'withdrawn', 'migrated'));
ALTER TABLE student.student ADD CONSTRAINT ck_student_photo_uri CHECK ((photo_uri IS NULL OR (photo_uri ~ '^[A-Za-z][A-Za-z0-9+.-]*://')));

-- STU-04
ALTER TABLE student.guardian ADD CONSTRAINT uq_guardian_person UNIQUE (person_id);
ALTER TABLE student.guardian ADD CONSTRAINT ck_guardian_occupation CHECK ((occupation IS NULL OR (char_length(occupation) <= 100)));
ALTER TABLE student.guardian ADD CONSTRAINT ck_guardian_education CHECK ((education IS NULL OR (char_length(education) <= 100)));
ALTER TABLE student.guardian ADD CONSTRAINT ck_guardian_annual_income_band CHECK ((annual_income_band IS NULL OR (annual_income_band IN ('below_1l', '1l_3l', '3l_5l', '5l_10l', 'above_10l', 'not_disclosed'))));

-- STU-05
ALTER TABLE student.student_guardian ADD CONSTRAINT uq_student_guardian UNIQUE (student_id, guardian_id);
ALTER TABLE student.student_guardian ADD CONSTRAINT ck_student_guardian_relation CHECK (relation IN ('father', 'mother', 'guardian', 'sibling', 'other'));
ALTER TABLE student.student_guardian ADD CONSTRAINT ck_student_guardian_consent_status CHECK (consent_status IN ('pending', 'granted', 'denied', 'withdrawn'));
ALTER TABLE student.student_guardian ADD CONSTRAINT ck_student_guardian_valid_to CHECK ((valid_to IS NULL OR valid_to > valid_from));

-- STU-06
ALTER TABLE student.student_document ADD CONSTRAINT uq_student_document UNIQUE (student_id, document_type, document_version_id);
ALTER TABLE student.student_document ADD CONSTRAINT ck_student_document_document_type CHECK (document_type IN ('photo', 'signature', 'marksheet_10', 'marksheet_12', 'diploma', 'category_certificate', 'income_certificate', 'migration', 'transfer', 'medical', 'id_proof', 'other'));
ALTER TABLE student.student_document ADD CONSTRAINT ck_student_document_verification_status CHECK (verification_status IN ('pending', 'verified', 'rejected', 'expired'));
ALTER TABLE student.student_document ADD CONSTRAINT ck_student_document_remarks CHECK ((remarks IS NULL OR (char_length(remarks) <= 1000)));

-- STU-07
ALTER TABLE student.university_registration ADD CONSTRAINT uq_university_registration_student UNIQUE (student_id);
ALTER TABLE student.university_registration ADD CONSTRAINT ck_university_registration_registration_number CHECK ((registration_number IS NULL OR (char_length(registration_number) <= 50)));
ALTER TABLE student.university_registration ADD CONSTRAINT ck_university_registration_registration_year CHECK (registration_year BETWEEN 2000 AND 2100);
ALTER TABLE student.university_registration ADD CONSTRAINT ck_university_registration_status CHECK (status IN ('pending', 'uploaded', 'confirmed', 'rejected'));

-- STU-08
ALTER TABLE student.exam_roll_number ADD CONSTRAINT uq_exam_roll_number UNIQUE (roll_number);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_roll_number CHECK (char_length(roll_number) = 12);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_college_code CHECK (char_length(college_code) = 3);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_programme_code CHECK (char_length(programme_code) = 3);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_registration_year CHECK (registration_year BETWEEN 0 AND 99);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_course_duration_years CHECK (course_duration_years BETWEEN 1 AND 9);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_serial_no CHECK (serial_no BETWEEN 1 AND 999);
ALTER TABLE student.exam_roll_number ADD CONSTRAINT ck_exam_roll_number_status CHECK (status IN ('active', 'superseded', 'cancelled'));

-- STU-09
ALTER TABLE student.semester_registration ADD CONSTRAINT uq_semester_registration UNIQUE (student_id, term_id);
ALTER TABLE student.semester_registration ADD CONSTRAINT uq_semester_registration_student_target UNIQUE (semester_registration_id, student_id);
ALTER TABLE student.semester_registration ADD CONSTRAINT ck_semester_registration_registration_no CHECK ((registration_no IS NULL OR (char_length(registration_no) <= 50)));
ALTER TABLE student.semester_registration ADD CONSTRAINT ck_semester_registration_approved_at CHECK ((approved_at IS NULL OR approved_at >= submitted_at));
ALTER TABLE student.semester_registration ADD CONSTRAINT ck_semester_registration_status CHECK (status IN ('draft', 'submitted', 'approved', 'rejected', 'cancelled'));
ALTER TABLE student.semester_registration ADD CONSTRAINT ck_semester_registration_remarks CHECK ((remarks IS NULL OR (char_length(remarks) <= 1000)));

-- STU-10
ALTER TABLE student.course_registration ADD CONSTRAINT uq_course_registration UNIQUE (semester_registration_id, course_offering_id);
ALTER TABLE student.course_registration ADD CONSTRAINT uq_course_registration_target UNIQUE (course_registration_id, student_id, course_offering_id);
ALTER TABLE student.course_registration ADD CONSTRAINT ck_course_registration_registration_type CHECK (registration_type IN ('regular', 'backlog', 'audit', 'improvement'));
ALTER TABLE student.course_registration ADD CONSTRAINT ck_course_registration_credits CHECK (credits >= 0);
ALTER TABLE student.course_registration ADD CONSTRAINT ck_course_registration_status CHECK (status IN ('registered', 'dropped', 'completed', 'failed', 'withdrawn'));
ALTER TABLE student.course_registration ADD CONSTRAINT ck_course_registration_dropped_at CHECK ((dropped_at IS NULL OR dropped_at >= registered_at));
ALTER TABLE student.course_registration ADD CONSTRAINT ck_course_registration_drop_reason CHECK ((drop_reason IS NULL OR (char_length(drop_reason) <= 500)));

-- STU-11
ALTER TABLE student.status_history ADD CONSTRAINT ex_status_history_overlap EXCLUDE USING gist (student_id WITH =, daterange(effective_from, effective_to, '[]') WITH &&);
ALTER TABLE student.status_history ADD CONSTRAINT ck_status_history_status CHECK (status IN ('active', 'detained', 'suspended', 'year_lag', 'graduated', 'withdrawn', 'migrated'));
ALTER TABLE student.status_history ADD CONSTRAINT ck_status_history_effective_to CHECK ((effective_to IS NULL OR effective_to > effective_from));
ALTER TABLE student.status_history ADD CONSTRAINT ck_status_history_reason CHECK ((reason IS NULL OR (char_length(reason) <= 2000)));

-- STU-12
ALTER TABLE student.eligibility_determination ADD CONSTRAINT ck_eligibility_determination_gate_code CHECK (char_length(gate_code) <= 50);
ALTER TABLE student.eligibility_determination ADD CONSTRAINT ck_eligibility_determination_scope_type CHECK (scope_type IN ('institution', 'programme', 'batch', 'term', 'course_offering'));
ALTER TABLE student.eligibility_determination ADD CONSTRAINT ck_eligibility_determination_status CHECK (status IN ('pass', 'fail', 'waived', 'unknown', 'not_applicable'));
ALTER TABLE student.eligibility_determination ADD CONSTRAINT ck_eligibility_determination_source CHECK (source IN ('computed', 'imported', 'manual', 'external_api'));
ALTER TABLE student.eligibility_determination ADD CONSTRAINT ck_eligibility_determination_scope_population CHECK ((scope_type = 'institution' AND scope_id IS NULL) OR (scope_type <> 'institution' AND scope_id IS NOT NULL));

-- STU-15
ALTER TABLE student.section_assignment ADD CONSTRAINT uq_section_assignment_start UNIQUE (student_id, effective_from);
ALTER TABLE student.section_assignment ADD CONSTRAINT ex_section_assignment_overlap EXCLUDE USING gist (student_id WITH =, daterange(effective_from, effective_to, '[]') WITH &&);
ALTER TABLE student.section_assignment ADD CONSTRAINT ck_section_assignment_effective_to CHECK ((effective_to IS NULL OR effective_to > effective_from));
ALTER TABLE student.section_assignment ADD CONSTRAINT ck_section_assignment_assignment_reason CHECK (assignment_reason IN ('initial_allotment', 'transfer', 'section_merge', 'readmission', 'correction'));
ALTER TABLE student.section_assignment ADD CONSTRAINT ck_section_assignment_status CHECK (status IN ('active', 'ended', 'cancelled'));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- STU-01
ALTER TABLE student.admission_application ADD CONSTRAINT fk_admission_application_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE student.admission_application ADD CONSTRAINT fk_admission_application_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE student.admission_application ADD CONSTRAINT fk_admission_application_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE student.admission_application ADD CONSTRAINT fk_admission_application_verified_by FOREIGN KEY (verified_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-02
ALTER TABLE student.admission_offer ADD CONSTRAINT fk_admission_offer_application_id FOREIGN KEY (application_id) REFERENCES student.admission_application (application_id) ON DELETE RESTRICT;
ALTER TABLE student.admission_offer ADD CONSTRAINT fk_admission_offer_confirmed_by FOREIGN KEY (confirmed_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-03
ALTER TABLE student.student ADD CONSTRAINT fk_student_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE student.student ADD CONSTRAINT fk_student_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE student.student ADD CONSTRAINT fk_student_section_id FOREIGN KEY (section_id) REFERENCES academic.section (section_id) ON DELETE RESTRICT;
ALTER TABLE student.student ADD CONSTRAINT fk_student_admission_application_id FOREIGN KEY (admission_application_id) REFERENCES student.admission_application (application_id) ON DELETE RESTRICT;

-- STU-04
ALTER TABLE student.guardian ADD CONSTRAINT fk_guardian_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-05
ALTER TABLE student.student_guardian ADD CONSTRAINT fk_student_guardian_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.student_guardian ADD CONSTRAINT fk_student_guardian_guardian_id FOREIGN KEY (guardian_id) REFERENCES student.guardian (guardian_id) ON DELETE RESTRICT;

-- STU-06
ALTER TABLE student.student_document ADD CONSTRAINT fk_student_document_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.student_document ADD CONSTRAINT fk_student_document_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;
ALTER TABLE student.student_document ADD CONSTRAINT fk_student_document_verified_by FOREIGN KEY (verified_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-07
ALTER TABLE student.university_registration ADD CONSTRAINT fk_university_registration_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.university_registration ADD CONSTRAINT fk_university_registration_proof_document_version_id FOREIGN KEY (proof_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- STU-08
ALTER TABLE student.exam_roll_number ADD CONSTRAINT fk_exam_roll_number_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.exam_roll_number ADD CONSTRAINT fk_exam_roll_number_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;

-- STU-09
ALTER TABLE student.semester_registration ADD CONSTRAINT fk_semester_registration_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.semester_registration ADD CONSTRAINT fk_semester_registration_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE student.semester_registration ADD CONSTRAINT fk_semester_registration_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-10
ALTER TABLE student.course_registration ADD CONSTRAINT fk_course_registration_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.course_registration ADD CONSTRAINT fk_course_registration_semester_registration_id FOREIGN KEY (semester_registration_id) REFERENCES student.semester_registration (semester_registration_id) ON DELETE RESTRICT;
ALTER TABLE student.course_registration ADD CONSTRAINT fk_course_registration_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE student.course_registration ADD CONSTRAINT fk_course_registration_semester_student FOREIGN KEY (semester_registration_id, student_id) REFERENCES student.semester_registration (semester_registration_id, student_id) ON DELETE RESTRICT;

-- STU-11
ALTER TABLE student.status_history ADD CONSTRAINT fk_status_history_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.status_history ADD CONSTRAINT fk_status_history_order_document_version_id FOREIGN KEY (order_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;
ALTER TABLE student.status_history ADD CONSTRAINT fk_status_history_recorded_by FOREIGN KEY (recorded_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-12
ALTER TABLE student.eligibility_determination ADD CONSTRAINT fk_eligibility_determination_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.eligibility_determination ADD CONSTRAINT fk_eligibility_determination_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE student.eligibility_determination ADD CONSTRAINT fk_eligibility_determination_policy_rule_version_id FOREIGN KEY (policy_rule_version_id) REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT;
ALTER TABLE student.eligibility_determination ADD CONSTRAINT fk_eligibility_determination_determined_by FOREIGN KEY (determined_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- STU-15
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_section_id FOREIGN KEY (section_id) REFERENCES academic.section (section_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_authority_role_assignment_id FOREIGN KEY (authority_role_assignment_id) REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_source_document_version_id FOREIGN KEY (source_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_student_batch FOREIGN KEY (student_id, batch_id) REFERENCES student.student (student_id, batch_id) ON DELETE RESTRICT;
ALTER TABLE student.section_assignment ADD CONSTRAINT fk_section_assignment_section_batch FOREIGN KEY (section_id, batch_id) REFERENCES academic.section (section_id, batch_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- STU-01
CREATE INDEX ix_admission_application_programme_year_status ON student.admission_application (programme_id, admission_year, application_status);
CREATE INDEX ix_admission_application_person_id ON student.admission_application (person_id);
CREATE INDEX ix_admission_application_batch_id ON student.admission_application (batch_id);
CREATE INDEX ix_admission_application_verified_by ON student.admission_application (verified_by);

-- STU-02
CREATE INDEX ix_admission_offer_status ON student.admission_offer (status);
CREATE INDEX ix_admission_offer_confirmed_by ON student.admission_offer (confirmed_by);

-- STU-03
CREATE INDEX ix_student_batch_section ON student.student (batch_id, section_id);
CREATE INDEX ix_student_status ON student.student (current_status);
CREATE INDEX ix_student_person ON student.student (person_id);
CREATE INDEX ix_student_section_id ON student.student (section_id);
CREATE INDEX ix_student_admission_application_id ON student.student (admission_application_id);

-- STU-05
CREATE INDEX ix_student_guardian_student_primary ON student.student_guardian (student_id, is_primary);
CREATE UNIQUE INDEX uq_student_guardian_primary ON student.student_guardian (student_id) WHERE is_primary AND valid_to IS NULL;
CREATE INDEX ix_student_guardian_guardian_id ON student.student_guardian (guardian_id);

-- STU-06
CREATE INDEX ix_student_document_student_type ON student.student_document (student_id, document_type);
CREATE INDEX ix_student_document_status ON student.student_document (verification_status);
CREATE INDEX ix_student_document_document_version_id ON student.student_document (document_version_id);
CREATE INDEX ix_student_document_verified_by ON student.student_document (verified_by);

-- STU-07
CREATE INDEX ix_university_registration_status ON student.university_registration (status);
CREATE UNIQUE INDEX uq_university_registration_number ON student.university_registration (lower(registration_number)) WHERE registration_number IS NOT NULL;
CREATE INDEX ix_university_registration_proof_document_version_id ON student.university_registration (proof_document_version_id);

-- STU-08
CREATE INDEX ix_exam_roll_number_student_current ON student.exam_roll_number (student_id, is_current);
CREATE INDEX ix_exam_roll_number_year_serial ON student.exam_roll_number (registration_year, serial_no);
CREATE UNIQUE INDEX uq_exam_roll_number_current ON student.exam_roll_number (student_id) WHERE is_current;
CREATE INDEX ix_exam_roll_number_programme_id ON student.exam_roll_number (programme_id);

-- STU-09
CREATE INDEX ix_semester_registration_term_status ON student.semester_registration (term_id, status);
CREATE INDEX ix_semester_registration_student ON student.semester_registration (student_id);
CREATE UNIQUE INDEX uq_semester_registration_no ON student.semester_registration (registration_no) WHERE registration_no IS NOT NULL;
CREATE INDEX ix_semester_registration_approved_by ON student.semester_registration (approved_by);

-- STU-10
CREATE INDEX ix_course_registration_offering_status ON student.course_registration (course_offering_id, status);
CREATE INDEX ix_course_registration_semester ON student.course_registration (semester_registration_id);
CREATE INDEX ix_course_registration_student_offering ON student.course_registration (student_id, course_offering_id);

-- STU-11
CREATE INDEX ix_status_history_student_from ON student.status_history (student_id, effective_from);
CREATE INDEX ix_status_history_order_document_version_id ON student.status_history (order_document_version_id);
CREATE INDEX ix_status_history_recorded_by ON student.status_history (recorded_by);

-- STU-12
CREATE INDEX ix_eligibility_student_gate_term ON student.eligibility_determination (student_id, gate_code, term_id);
CREATE INDEX ix_eligibility_status_determined ON student.eligibility_determination (status, determined_at);
CREATE INDEX ix_eligibility_determination_term_id ON student.eligibility_determination (term_id);
CREATE INDEX ix_eligibility_determination_policy_rule_version_id ON student.eligibility_determination (policy_rule_version_id);
CREATE INDEX ix_eligibility_determination_determined_by ON student.eligibility_determination (determined_by);

-- STU-15
CREATE INDEX ix_section_assignment_student_from ON student.section_assignment (student_id, effective_from DESC);
CREATE INDEX ix_section_assignment_section_from ON student.section_assignment (section_id, effective_from DESC);
CREATE UNIQUE INDEX uq_section_assignment_open ON student.section_assignment (student_id) WHERE effective_to IS NULL AND status = 'active';
CREATE INDEX ix_section_assignment_batch_id ON student.section_assignment (batch_id);
CREATE INDEX ix_section_assignment_approved_by ON student.section_assignment (approved_by);
CREATE INDEX ix_section_assignment_authority_role_assignment_id ON student.section_assignment (authority_role_assignment_id);
CREATE INDEX ix_section_assignment_source_document_version_id ON student.section_assignment (source_document_version_id);

-- ---------------------------------------------------------------------------
-- 5. Documented security-definer helpers (POSTGRES_ARCHITECTURE 9.2)
-- ---------------------------------------------------------------------------
-- The helpers are owned by owner_iam. They read the relationship tables under
-- an explicit owner_iam SELECT policy (section 8) rather than broadening an
-- application role. The mentor arm and the named HOD/Registrar/COE/Auditor
-- arms require W3 and the A-01 permission catalogue respectively; they are not
-- invented here. The mentor arm is added in W3 by replacing this function.

GRANT USAGE ON SCHEMA student, academic TO owner_iam;
GRANT SELECT ON
    student.student, student.student_guardian, student.guardian,
    student.course_registration
TO owner_iam;
GRANT SELECT ON
    academic.section_teacher_assignment, academic.offering_faculty
TO owner_iam;

CREATE OR REPLACE FUNCTION iam.is_section_teacher(p_section_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM academic.section_teacher_assignment sta
        WHERE sta.section_id = $1
          AND sta.person_id = (SELECT iam.current_person_id())
          AND sta.status = 'active'
          AND sta.valid_from <= current_date
          AND (sta.valid_to IS NULL OR sta.valid_to >= current_date)
    )
$$;
ALTER FUNCTION iam.is_section_teacher(uuid) OWNER TO owner_iam;

CREATE OR REPLACE FUNCTION iam.is_allocated_to_offering(p_offering_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM academic.offering_faculty f
        WHERE f.course_offering_id = $1
          AND f.person_id = (SELECT iam.current_person_id())
          AND f.valid_from <= current_date
          AND (f.valid_to IS NULL OR f.valid_to >= current_date)
    )
$$;
ALTER FUNCTION iam.is_allocated_to_offering(uuid) OWNER TO owner_iam;

CREATE OR REPLACE FUNCTION iam.can_access_student(p_student_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT
        EXISTS (
            SELECT 1
            FROM student.student s
            WHERE s.student_id = $1
              AND s.person_id = (SELECT iam.current_person_id())
        )
        OR EXISTS (
            SELECT 1
            FROM student.student_guardian sg
            JOIN student.guardian g ON g.guardian_id = sg.guardian_id
            WHERE sg.student_id = $1
              AND g.person_id = (SELECT iam.current_person_id())
              AND sg.consent_status = 'granted'
              AND sg.valid_from <= current_date
              AND (sg.valid_to IS NULL OR sg.valid_to >= current_date)
        )
        OR EXISTS (
            SELECT 1
            FROM student.student s
            JOIN academic.section_teacher_assignment sta
              ON sta.section_id = s.section_id
            WHERE s.student_id = $1
              AND sta.person_id = (SELECT iam.current_person_id())
              AND sta.status = 'active'
              AND sta.valid_from <= current_date
              AND (sta.valid_to IS NULL OR sta.valid_to >= current_date)
        )
        OR EXISTS (
            SELECT 1
            FROM student.course_registration cr
            JOIN academic.offering_faculty f
              ON f.course_offering_id = cr.course_offering_id
            WHERE cr.student_id = $1
              AND cr.status IN ('registered', 'completed')
              AND f.person_id = (SELECT iam.current_person_id())
              AND f.valid_from <= current_date
              AND (f.valid_to IS NULL OR f.valid_to >= current_date)
        )
$$;
ALTER FUNCTION iam.can_access_student(uuid) OWNER TO owner_iam;

CREATE OR REPLACE FUNCTION iam.can_access_offering(p_offering_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT iam.is_allocated_to_offering($1)
        OR EXISTS (
            SELECT 1
            FROM student.course_registration cr
            JOIN student.student s ON s.student_id = cr.student_id
            WHERE cr.course_offering_id = $1
              AND cr.status IN ('registered', 'completed')
              AND s.person_id = (SELECT iam.current_person_id())
        )
$$;
ALTER FUNCTION iam.can_access_offering(uuid) OWNER TO owner_iam;

REVOKE EXECUTE ON FUNCTION iam.is_section_teacher(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.is_allocated_to_offering(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.can_access_student(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION iam.can_access_offering(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION iam.is_section_teacher(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.is_allocated_to_offering(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.can_access_student(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;
GRANT EXECUTE ON FUNCTION iam.can_access_offering(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;

-- ---------------------------------------------------------------------------
-- 6. Business-rule triggers
-- ---------------------------------------------------------------------------

-- STU-08: the stored components must reconstruct the roll number exactly.
CREATE OR REPLACE FUNCTION student.enforce_exam_roll_number_format()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, student
AS $function$
BEGIN
    IF NEW.roll_number <> (
        NEW.college_code
        || NEW.programme_code
        || lpad(NEW.registration_year::text, 2, '0')
        || NEW.course_duration_years::text
        || lpad(NEW.serial_no::text, 3, '0')
    ) THEN
        RAISE EXCEPTION
            'student.exam_roll_number: % does not match its components',
            NEW.roll_number;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION student.enforce_exam_roll_number_format() OWNER TO owner_student;
REVOKE EXECUTE ON FUNCTION student.enforce_exam_roll_number_format() FROM PUBLIC;

CREATE TRIGGER trg_exam_roll_number_format
    BEFORE INSERT OR UPDATE ON student.exam_roll_number
    FOR EACH ROW
    EXECUTE FUNCTION student.enforce_exam_roll_number_format();

-- STU-12: the dictionary defines eligibility determinations as evidence that
-- is never overwritten ("a re-evaluation writes a new row").
CREATE OR REPLACE FUNCTION student.seal_eligibility_determination()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, student
AS $function$
BEGIN
    RAISE EXCEPTION
        'student.eligibility_determination is append-only; write a new determination';
END;
$function$;
ALTER FUNCTION student.seal_eligibility_determination() OWNER TO owner_student;
REVOKE EXECUTE ON FUNCTION student.seal_eligibility_determination() FROM PUBLIC;

CREATE TRIGGER trg_eligibility_determination_seal
    BEFORE UPDATE OR DELETE ON student.eligibility_determination
    FOR EACH ROW
    EXECUTE FUNCTION student.seal_eligibility_determination();

-- ---------------------------------------------------------------------------
-- 7. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA student FROM PUBLIC;

-- Tables with no R/G column. Table privileges are necessary but not
-- sufficient: RLS remains the row filter and no application write policy is
-- invented (A-01 posture).
GRANT SELECT, INSERT, UPDATE ON
    student.admission_offer, student.university_registration,
    student.exam_roll_number, student.semester_registration,
    student.course_registration, student.eligibility_determination,
    student.section_assignment
TO app_erp;

-- STU-01: category (R/G) is outside the application projection.
GRANT SELECT (
    application_id, person_id, programme_id, batch_id, application_no,
    admission_year, counselling_authority, allotment_reference,
    eligibility_status, application_status, submitted_at, verified_by,
    verified_at, created_at, created_by, updated_at, updated_by, row_version
) ON student.admission_application TO app_erp;
GRANT INSERT (
    application_id, person_id, programme_id, batch_id, application_no,
    admission_year, counselling_authority, allotment_reference,
    eligibility_status, application_status, submitted_at, verified_by,
    verified_at, created_at, created_by, updated_at, updated_by, row_version
) ON student.admission_application TO app_erp;
GRANT UPDATE (
    person_id, programme_id, batch_id, application_no, admission_year,
    counselling_authority, allotment_reference, eligibility_status,
    application_status, submitted_at, verified_by, verified_at,
    updated_at, updated_by, row_version
) ON student.admission_application TO app_erp;

-- STU-03: category (R/G) is outside the application projection.
GRANT SELECT (
    student_id, person_id, batch_id, section_id, admission_application_id,
    college_roll_no, admission_year, entry_mode, date_of_admission,
    expected_completion_year, current_status, photo_uri,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.student TO app_erp;
GRANT INSERT (
    student_id, person_id, batch_id, section_id, admission_application_id,
    college_roll_no, admission_year, entry_mode, date_of_admission,
    expected_completion_year, current_status, photo_uri,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.student TO app_erp;
GRANT UPDATE (
    person_id, batch_id, section_id, admission_application_id,
    college_roll_no, admission_year, entry_mode, date_of_admission,
    expected_completion_year, current_status, photo_uri,
    updated_at, updated_by, row_version
) ON student.student TO app_erp;

-- STU-04: annual_income_band (R) is outside the application projection.
GRANT SELECT (
    guardian_id, person_id, occupation, education, is_alumni,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.guardian TO app_erp;
GRANT INSERT (
    guardian_id, person_id, occupation, education, is_alumni,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.guardian TO app_erp;
GRANT UPDATE (
    person_id, occupation, education, is_alumni,
    updated_at, updated_by, row_version
) ON student.guardian TO app_erp;

-- STU-05: consent fields (R) are outside the application projection.
GRANT SELECT (
    student_guardian_id, student_id, guardian_id, relation, is_primary,
    valid_from, valid_to, created_at, created_by, updated_at, updated_by,
    row_version
) ON student.student_guardian TO app_erp;
GRANT INSERT (
    student_guardian_id, student_id, guardian_id, relation, is_primary,
    valid_from, valid_to, created_at, created_by, updated_at, updated_by,
    row_version
) ON student.student_guardian TO app_erp;
GRANT UPDATE (
    student_id, guardian_id, relation, is_primary, valid_from, valid_to,
    updated_at, updated_by, row_version
) ON student.student_guardian TO app_erp;

-- STU-06 is R/G in every column. No application grant exists until the
-- named-role verification view is approved (OD-16 / A-01).

-- STU-11: reason (R) is outside the application projection.
GRANT SELECT (
    status_history_id, student_id, status, effective_from, effective_to,
    order_document_version_id, recorded_by,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.status_history TO app_erp;
GRANT INSERT (
    status_history_id, student_id, status, effective_from, effective_to,
    order_document_version_id, recorded_by,
    created_at, created_by, updated_at, updated_by, row_version
) ON student.status_history TO app_erp;
GRANT UPDATE (
    student_id, status, effective_from, effective_to,
    order_document_version_id, recorded_by,
    updated_at, updated_by, row_version
) ON student.status_history TO app_erp;

-- ---------------------------------------------------------------------------
-- 8. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every student table. Application
-- policies are implemented only for the two documented intents (9.3); every
-- other table is deny-by-default for non-owner roles. owner_iam receives
-- explicit SELECT policies because the security-definer helpers run as that
-- role.

ALTER TABLE student.admission_application ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.admission_application FORCE ROW LEVEL SECURITY;
ALTER TABLE student.admission_offer ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.admission_offer FORCE ROW LEVEL SECURITY;
ALTER TABLE student.student ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.student FORCE ROW LEVEL SECURITY;
ALTER TABLE student.guardian ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.guardian FORCE ROW LEVEL SECURITY;
ALTER TABLE student.student_guardian ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.student_guardian FORCE ROW LEVEL SECURITY;
ALTER TABLE student.student_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.student_document FORCE ROW LEVEL SECURITY;
ALTER TABLE student.university_registration ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.university_registration FORCE ROW LEVEL SECURITY;
ALTER TABLE student.exam_roll_number ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.exam_roll_number FORCE ROW LEVEL SECURITY;
ALTER TABLE student.semester_registration ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.semester_registration FORCE ROW LEVEL SECURITY;
ALTER TABLE student.course_registration ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.course_registration FORCE ROW LEVEL SECURITY;
ALTER TABLE student.status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.status_history FORCE ROW LEVEL SECURITY;
ALTER TABLE student.eligibility_determination ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.eligibility_determination FORCE ROW LEVEL SECURITY;
ALTER TABLE student.section_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE student.section_assignment FORCE ROW LEVEL SECURITY;

CREATE POLICY p_admission_application_owner_all ON student.admission_application
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_admission_offer_owner_all ON student.admission_offer
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_student_owner_all ON student.student
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_guardian_owner_all ON student.guardian
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_student_guardian_owner_all ON student.student_guardian
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_student_document_owner_all ON student.student_document
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_university_registration_owner_all ON student.university_registration
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_exam_roll_number_owner_all ON student.exam_roll_number
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_semester_registration_owner_all ON student.semester_registration
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_course_registration_owner_all ON student.course_registration
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_status_history_owner_all ON student.status_history
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_eligibility_determination_owner_all ON student.eligibility_determination
    FOR ALL TO owner_student USING (true) WITH CHECK (true);
CREATE POLICY p_section_assignment_owner_all ON student.section_assignment
    FOR ALL TO owner_student USING (true) WITH CHECK (true);

-- Helper read policies for owner_iam (security-definer relationship checks).
CREATE POLICY p_student_helper_select ON student.student
    FOR SELECT TO owner_iam USING (true);
CREATE POLICY p_student_guardian_helper_select ON student.student_guardian
    FOR SELECT TO owner_iam USING (true);
CREATE POLICY p_guardian_helper_select ON student.guardian
    FOR SELECT TO owner_iam USING (true);
CREATE POLICY p_course_registration_helper_select ON student.course_registration
    FOR SELECT TO owner_iam USING (true);
CREATE POLICY p_section_teacher_assignment_helper_select
    ON academic.section_teacher_assignment
    FOR SELECT TO owner_iam USING (true);

-- Documented intent 1: student.student via iam.can_access_student.
CREATE POLICY p_student_access_select ON student.student
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING ((SELECT iam.can_access_student(student_id)));

-- Documented intent 2: section_assignment self and open class teacher.
-- HOD, Registrar, and Auditor arms require the A-01 permission catalogue.
CREATE POLICY p_section_assignment_access_select ON student.section_assignment
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (
        student_id IN (
            SELECT s.student_id
            FROM student.student s
            WHERE s.person_id = (SELECT iam.current_person_id())
        )
        OR iam.is_section_teacher(section_id)
    );

-- ---------------------------------------------------------------------------
-- 9. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE student.student IS
    'STU-03: current_status and section_id are derived caches. The application updates them in the same transaction as status_history or section_assignment; a nightly reconciliation reports drift. No cache-sync trigger is installed because the design assigns this to the service.';

COMMENT ON TABLE student.exam_roll_number IS
    'STU-08: trg_exam_roll_number_format enforces that college_code || programme_code || registration_year (2) || course_duration_years (1) || serial_no (3) equals roll_number.';

COMMENT ON TABLE student.eligibility_determination IS
    'STU-12: append-only evidence. scope_id is polymorphic within the documented controlled set and is validated by the application against integration.entity_type; there is no foreign key. trg_eligibility_determination_seal rejects UPDATE and DELETE.';

COMMENT ON TABLE student.section_assignment IS
    'STU-15: history is never deleted. Open/close and the student.section_id cache update are one application transaction; composite foreign keys prevent a cross-batch assignment.';

COMMENT ON POLICY p_student_access_select ON student.student IS
    'POSTGRES_ARCHITECTURE 9.3: self, consenting guardian, open section teacher, and allocated faculty are implemented. The mentor arm is added in W3; HOD/Registrar/COE/Auditor arms wait for A-01.';