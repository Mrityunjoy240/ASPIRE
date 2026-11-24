-- ===========================================================================
-- 0008_w1b_academic.sql
-- W1b academic structure
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- ACD-01 academic.department
CREATE TABLE academic.department (
    department_id uuid NOT NULL DEFAULT gen_random_uuid(),
    org_unit_id uuid NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    short_name text,
    hod_person_id uuid,
    established_on date,
    is_active boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_department PRIMARY KEY (department_id)
);
ALTER TABLE academic.department OWNER TO owner_academic;

-- ACD-02 academic.programme
CREATE TABLE academic.programme (
    programme_id uuid NOT NULL DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL,
    department_id uuid NOT NULL,
    programme_code text NOT NULL,
    bcrec_code text NOT NULL,
    name text NOT NULL,
    level text NOT NULL,
    degree_awarded_by text NOT NULL DEFAULT 'MAKAUT',
    duration_years smallint NOT NULL DEFAULT 4,
    aicte_programme_code text,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_programme PRIMARY KEY (programme_id)
);
ALTER TABLE academic.programme OWNER TO owner_academic;

-- ACD-03 academic.programme_version
CREATE TABLE academic.programme_version (
    programme_version_id uuid NOT NULL DEFAULT gen_random_uuid(),
    programme_id uuid NOT NULL,
    version_no smallint NOT NULL DEFAULT 1,
    regulation_name text NOT NULL,
    regulation_reference text,
    effective_from_admission_year smallint NOT NULL,
    effective_to_admission_year smallint,
    total_credits integer NOT NULL,
    status text NOT NULL DEFAULT 'draft',
    approved_by uuid,
    approved_at timestamptz,
    source_document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_programme_version PRIMARY KEY (programme_version_id)
);
ALTER TABLE academic.programme_version OWNER TO owner_academic;

-- ACD-04 academic.batch
CREATE TABLE academic.batch (
    batch_id uuid NOT NULL DEFAULT gen_random_uuid(),
    programme_id uuid NOT NULL,
    programme_version_id uuid NOT NULL,
    admission_year smallint NOT NULL,
    entry_mode text NOT NULL DEFAULT 'regular',
    autonomy_status text NOT NULL DEFAULT 'transitional',
    current_term_id uuid,
    expected_graduation_year smallint,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_batch PRIMARY KEY (batch_id)
);
ALTER TABLE academic.batch OWNER TO owner_academic;

-- ACD-05 academic.section
CREATE TABLE academic.section (
    section_id uuid NOT NULL DEFAULT gen_random_uuid(),
    batch_id uuid NOT NULL,
    section_code text NOT NULL,
    name text,
    strength integer,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_section PRIMARY KEY (section_id)
);
ALTER TABLE academic.section OWNER TO owner_academic;

-- ACD-06 academic.curriculum
CREATE TABLE academic.curriculum (
    curriculum_id uuid NOT NULL DEFAULT gen_random_uuid(),
    programme_version_id uuid NOT NULL,
    term_no smallint NOT NULL,
    version_no smallint NOT NULL DEFAULT 1,
    total_credits integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'draft',
    approved_by uuid,
    approved_at timestamptz,
    effective_from_term_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_curriculum PRIMARY KEY (curriculum_id)
);
ALTER TABLE academic.curriculum OWNER TO owner_academic;

-- ACD-07 academic.curriculum_course
CREATE TABLE academic.curriculum_course (
    curriculum_course_id uuid NOT NULL DEFAULT gen_random_uuid(),
    curriculum_id uuid NOT NULL,
    course_version_id uuid NOT NULL,
    term_no smallint NOT NULL,
    sequence_no smallint NOT NULL DEFAULT 1,
    category text NOT NULL DEFAULT 'core',
    credits numeric(4,1) NOT NULL DEFAULT 0,
    is_mandatory boolean NOT NULL DEFAULT TRUE,
    contact_hours integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_curriculum_course PRIMARY KEY (curriculum_course_id)
);
ALTER TABLE academic.curriculum_course OWNER TO owner_academic;

-- ACD-08 academic.course
CREATE TABLE academic.course (
    course_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_code text NOT NULL,
    title text NOT NULL,
    course_type text NOT NULL DEFAULT 'theory',
    department_id uuid NOT NULL,
    is_active boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_course PRIMARY KEY (course_id)
);
ALTER TABLE academic.course OWNER TO owner_academic;

-- ACD-09 academic.course_version
CREATE TABLE academic.course_version (
    course_version_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_id uuid NOT NULL,
    version_no smallint NOT NULL DEFAULT 1,
    title text NOT NULL,
    syllabus_text text,
    credits numeric(4,1) NOT NULL,
    contact_hours integer,
    course_outcomes_json jsonb DEFAULT '[]',
    effective_from_admission_year smallint NOT NULL,
    effective_to_admission_year smallint,
    status text NOT NULL DEFAULT 'draft',
    approved_by uuid,
    source_document_version_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_course_version PRIMARY KEY (course_version_id)
);
ALTER TABLE academic.course_version OWNER TO owner_academic;

-- ACD-10 academic.course_offering
CREATE TABLE academic.course_offering (
    course_offering_id uuid NOT NULL DEFAULT gen_random_uuid(),
    offering_code text NOT NULL,
    course_version_id uuid NOT NULL,
    term_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    section_id uuid,
    capacity integer,
    delivery_mode text NOT NULL DEFAULT 'offline',
    status text NOT NULL DEFAULT 'planned',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_course_offering PRIMARY KEY (course_offering_id)
);
ALTER TABLE academic.course_offering OWNER TO owner_academic;

-- ACD-11 academic.offering_faculty
CREATE TABLE academic.offering_faculty (
    offering_faculty_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL,
    person_id uuid NOT NULL,
    role_in_offering text NOT NULL DEFAULT 'instructor',
    is_assessor boolean NOT NULL DEFAULT FALSE,
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    allocated_hours integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_offering_faculty PRIMARY KEY (offering_faculty_id)
);
ALTER TABLE academic.offering_faculty OWNER TO owner_academic;

-- ACD-12 academic.timetable_slot
CREATE TABLE academic.timetable_slot (
    timetable_slot_id uuid NOT NULL DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL,
    day_of_week smallint NOT NULL,
    start_time time NOT NULL,
    end_time time NOT NULL,
    slot_type text NOT NULL DEFAULT 'theory',
    venue_text text,
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    status text NOT NULL DEFAULT 'planned',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_timetable_slot PRIMARY KEY (timetable_slot_id)
);
ALTER TABLE academic.timetable_slot OWNER TO owner_academic;

-- ACD-14 academic.section_teacher_assignment
CREATE TABLE academic.section_teacher_assignment (
    section_teacher_assignment_id uuid NOT NULL DEFAULT gen_random_uuid(),
    section_id uuid NOT NULL,
    person_id uuid NOT NULL,
    role_in_section text NOT NULL DEFAULT 'class_teacher',
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    status text NOT NULL DEFAULT 'active',
    assigned_at timestamptz NOT NULL DEFAULT now(),
    assigned_by uuid,
    authority_role_assignment_id uuid NOT NULL,
    source_document_version_id uuid,
    change_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_section_teacher_assignment PRIMARY KEY (section_teacher_assignment_id)
);
ALTER TABLE academic.section_teacher_assignment OWNER TO owner_academic;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- ACD-01
ALTER TABLE academic.department ADD CONSTRAINT uq_department_org_unit UNIQUE (org_unit_id);
ALTER TABLE academic.department ADD CONSTRAINT ck_department_code CHECK (char_length(code) <= 20);
ALTER TABLE academic.department ADD CONSTRAINT ck_department_name CHECK (char_length(name) <= 200);
ALTER TABLE academic.department ADD CONSTRAINT ck_department_short_name CHECK ((short_name IS NULL OR (char_length(short_name) <= 50)));
ALTER TABLE academic.department ADD CONSTRAINT ck_department_established_on CHECK ((established_on IS NULL OR established_on <= current_date));

-- ACD-02
ALTER TABLE academic.programme ADD CONSTRAINT uq_programme_bcrec_code UNIQUE (institution_id, bcrec_code);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_programme_code CHECK (char_length(programme_code) <= 20);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_bcrec_code CHECK (char_length(bcrec_code) <= 20);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_name CHECK (char_length(name) <= 200);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_level CHECK (level IN ('UG', 'PG', 'diploma', 'certificate'));
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_degree_awarded_by CHECK (char_length(degree_awarded_by) <= 200);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_duration_years CHECK (duration_years BETWEEN 1 AND 6);
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_aicte_programme_code CHECK ((aicte_programme_code IS NULL OR (char_length(aicte_programme_code) <= 50)));
ALTER TABLE academic.programme ADD CONSTRAINT ck_programme_status CHECK (status IN ('active', 'suspended', 'discontinued'));

-- ACD-03
ALTER TABLE academic.programme_version ADD CONSTRAINT uq_programme_version UNIQUE (programme_id, version_no);
ALTER TABLE academic.programme_version ADD CONSTRAINT ex_programme_version_years EXCLUDE USING gist (programme_id WITH =, int4range(effective_from_admission_year, effective_to_admission_year, '[]') WITH &&);
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_version_no CHECK (version_no >= 1);
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_regulation_name CHECK (char_length(regulation_name) <= 200);
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_regulation_reference CHECK ((regulation_reference IS NULL OR (char_length(regulation_reference) <= 200)));
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_effective_from_admission_year CHECK (effective_from_admission_year BETWEEN 2000 AND 2100);
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_effective_to_admission_year CHECK ((effective_to_admission_year IS NULL OR effective_to_admission_year BETWEEN 2000 AND 2100) AND (effective_to_admission_year IS NULL OR effective_to_admission_year >= effective_from_admission_year));
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_total_credits CHECK (total_credits > 0);
ALTER TABLE academic.programme_version ADD CONSTRAINT ck_programme_version_status CHECK (status IN ('draft', 'approved', 'superseded', 'withdrawn'));

-- ACD-04
ALTER TABLE academic.batch ADD CONSTRAINT uq_batch_admission UNIQUE (programme_id, admission_year, entry_mode);
ALTER TABLE academic.batch ADD CONSTRAINT ck_batch_admission_year CHECK (admission_year BETWEEN 2000 AND 2100);
ALTER TABLE academic.batch ADD CONSTRAINT ck_batch_entry_mode CHECK (entry_mode IN ('regular', 'lateral', 'transfer'));
ALTER TABLE academic.batch ADD CONSTRAINT ck_batch_autonomy_status CHECK (autonomy_status IN ('autonomous', 'makaut', 'transitional'));
ALTER TABLE academic.batch ADD CONSTRAINT ck_batch_expected_graduation_year CHECK ((expected_graduation_year IS NULL OR expected_graduation_year >= admission_year));
ALTER TABLE academic.batch ADD CONSTRAINT ck_batch_status CHECK (status IN ('active', 'graduated', 'closed'));

-- ACD-05
ALTER TABLE academic.section ADD CONSTRAINT uq_section_code UNIQUE (batch_id, section_code);
ALTER TABLE academic.section ADD CONSTRAINT uq_section_batch_target UNIQUE (section_id, batch_id);
ALTER TABLE academic.section ADD CONSTRAINT ck_section_section_code CHECK (char_length(section_code) <= 10);
ALTER TABLE academic.section ADD CONSTRAINT ck_section_name CHECK ((name IS NULL OR (char_length(name) <= 100)));
ALTER TABLE academic.section ADD CONSTRAINT ck_section_strength CHECK ((strength IS NULL OR (strength >= 0)));
ALTER TABLE academic.section ADD CONSTRAINT ck_section_status CHECK (status IN ('active', 'merged', 'closed'));

-- ACD-06
ALTER TABLE academic.curriculum ADD CONSTRAINT uq_curriculum_version UNIQUE (programme_version_id, term_no, version_no);
ALTER TABLE academic.curriculum ADD CONSTRAINT ck_curriculum_term_no CHECK (term_no BETWEEN 1 AND 12);
ALTER TABLE academic.curriculum ADD CONSTRAINT ck_curriculum_version_no CHECK (version_no >= 1);
ALTER TABLE academic.curriculum ADD CONSTRAINT ck_curriculum_total_credits CHECK (total_credits >= 0);
ALTER TABLE academic.curriculum ADD CONSTRAINT ck_curriculum_status CHECK (status IN ('draft', 'approved', 'superseded'));

-- ACD-07
ALTER TABLE academic.curriculum_course ADD CONSTRAINT uq_curriculum_course UNIQUE (curriculum_id, course_version_id);
ALTER TABLE academic.curriculum_course ADD CONSTRAINT uq_curriculum_course_seq UNIQUE (curriculum_id, term_no, sequence_no);
ALTER TABLE academic.curriculum_course ADD CONSTRAINT ck_curriculum_course_term_no CHECK (term_no BETWEEN 1 AND 12);
ALTER TABLE academic.curriculum_course ADD CONSTRAINT ck_curriculum_course_sequence_no CHECK (sequence_no >= 1);
ALTER TABLE academic.curriculum_course ADD CONSTRAINT ck_curriculum_course_category CHECK (category IN ('core', 'elective', 'lab', 'sessional', 'project', 'mooc', 'mandatory_non_credit'));
ALTER TABLE academic.curriculum_course ADD CONSTRAINT ck_curriculum_course_credits CHECK (credits >= 0);
ALTER TABLE academic.curriculum_course ADD CONSTRAINT ck_curriculum_course_contact_hours CHECK ((contact_hours IS NULL OR (contact_hours >= 0)));

-- ACD-08
ALTER TABLE academic.course ADD CONSTRAINT ck_course_course_code CHECK (char_length(course_code) <= 30);
ALTER TABLE academic.course ADD CONSTRAINT ck_course_title CHECK (char_length(title) <= 300);
ALTER TABLE academic.course ADD CONSTRAINT ck_course_course_type CHECK (course_type IN ('theory', 'practical', 'sessional', 'project', 'mooc', 'non_credit'));

-- ACD-09
ALTER TABLE academic.course_version ADD CONSTRAINT uq_course_version UNIQUE (course_id, version_no);
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_version_no CHECK (version_no >= 1);
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_title CHECK (char_length(title) <= 300);
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_credits CHECK (credits > 0);
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_contact_hours CHECK ((contact_hours IS NULL OR (contact_hours >= 0)));
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_course_outcomes_json CHECK ((course_outcomes_json IS NULL OR (jsonb_typeof(course_outcomes_json) = 'array')));
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_effective_from_admission_year CHECK (effective_from_admission_year BETWEEN 2000 AND 2100);
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_effective_to_admission_year CHECK ((effective_to_admission_year IS NULL OR effective_to_admission_year >= effective_from_admission_year));
ALTER TABLE academic.course_version ADD CONSTRAINT ck_course_version_status CHECK (status IN ('draft', 'approved', 'superseded', 'retired'));

-- ACD-10
ALTER TABLE academic.course_offering ADD CONSTRAINT uq_course_offering UNIQUE NULLS NOT DISTINCT (course_version_id, term_id, section_id);
ALTER TABLE academic.course_offering ADD CONSTRAINT ck_course_offering_offering_code CHECK (char_length(offering_code) <= 50);
ALTER TABLE academic.course_offering ADD CONSTRAINT ck_course_offering_capacity CHECK ((capacity IS NULL OR (capacity >= 0)));
ALTER TABLE academic.course_offering ADD CONSTRAINT ck_course_offering_delivery_mode CHECK (delivery_mode IN ('offline', 'online', 'hybrid'));
ALTER TABLE academic.course_offering ADD CONSTRAINT ck_course_offering_status CHECK (status IN ('planned', 'active', 'completed', 'cancelled'));

-- ACD-11
ALTER TABLE academic.offering_faculty ADD CONSTRAINT uq_offering_faculty UNIQUE (course_offering_id, person_id, role_in_offering, valid_from);
ALTER TABLE academic.offering_faculty ADD CONSTRAINT ck_offering_faculty_role_in_offering CHECK (role_in_offering IN ('coordinator', 'instructor', 'lab_instructor', 'guest', 'moderator'));
ALTER TABLE academic.offering_faculty ADD CONSTRAINT ck_offering_faculty_valid_to CHECK ((valid_to IS NULL OR valid_to > valid_from));
ALTER TABLE academic.offering_faculty ADD CONSTRAINT ck_offering_faculty_allocated_hours CHECK ((allocated_hours IS NULL OR (allocated_hours >= 0)));

-- ACD-12
ALTER TABLE academic.timetable_slot ADD CONSTRAINT uq_timetable_slot UNIQUE (course_offering_id, day_of_week, start_time, valid_from);
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_day_of_week CHECK (day_of_week BETWEEN 1 AND 7);
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_end_time CHECK (end_time > start_time);
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_slot_type CHECK (slot_type IN ('theory', 'practical', 'tutorial'));
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_venue_text CHECK ((venue_text IS NULL OR (char_length(venue_text) <= 100)));
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_valid_to CHECK ((valid_to IS NULL OR valid_to > valid_from));
ALTER TABLE academic.timetable_slot ADD CONSTRAINT ck_timetable_slot_status CHECK (status IN ('planned', 'active', 'cancelled'));

-- ACD-14
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT uq_section_teacher UNIQUE (section_id, person_id, role_in_section, valid_from);
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT ex_section_teacher_overlap EXCLUDE USING gist (section_id WITH =, daterange(valid_from, valid_to, '[]') WITH &&) WHERE (role_in_section = 'class_teacher');
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT ck_section_teacher_assignment_role_in_section CHECK (role_in_section IN ('class_teacher', 'co_class_teacher', 'substitute'));
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT ck_section_teacher_assignment_valid_to CHECK ((valid_to IS NULL OR valid_to > valid_from));
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT ck_section_teacher_assignment_status CHECK (status IN ('active', 'ended', 'superseded', 'cancelled'));
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT ck_section_teacher_assignment_change_reason CHECK ((change_reason IS NULL OR (char_length(change_reason) <= 1000)));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- ACD-01
ALTER TABLE academic.department ADD CONSTRAINT fk_department_org_unit_id FOREIGN KEY (org_unit_id) REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT;
ALTER TABLE academic.department ADD CONSTRAINT fk_department_hod_person_id FOREIGN KEY (hod_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ACD-02
ALTER TABLE academic.programme ADD CONSTRAINT fk_programme_institution_id FOREIGN KEY (institution_id) REFERENCES core.institution (institution_id) ON DELETE RESTRICT;
ALTER TABLE academic.programme ADD CONSTRAINT fk_programme_department_id FOREIGN KEY (department_id) REFERENCES academic.department (department_id) ON DELETE RESTRICT;

-- ACD-03
ALTER TABLE academic.programme_version ADD CONSTRAINT fk_programme_version_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE academic.programme_version ADD CONSTRAINT fk_programme_version_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE academic.programme_version ADD CONSTRAINT fk_programme_version_source_document_version_id FOREIGN KEY (source_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ACD-04
ALTER TABLE academic.batch ADD CONSTRAINT fk_batch_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE academic.batch ADD CONSTRAINT fk_batch_programme_version_id FOREIGN KEY (programme_version_id) REFERENCES academic.programme_version (programme_version_id) ON DELETE RESTRICT;
ALTER TABLE academic.batch ADD CONSTRAINT fk_batch_current_term_id FOREIGN KEY (current_term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;

-- ACD-05
ALTER TABLE academic.section ADD CONSTRAINT fk_section_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;

-- ACD-06
ALTER TABLE academic.curriculum ADD CONSTRAINT fk_curriculum_programme_version_id FOREIGN KEY (programme_version_id) REFERENCES academic.programme_version (programme_version_id) ON DELETE RESTRICT;
ALTER TABLE academic.curriculum ADD CONSTRAINT fk_curriculum_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE academic.curriculum ADD CONSTRAINT fk_curriculum_effective_from_term_id FOREIGN KEY (effective_from_term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;

-- ACD-07
ALTER TABLE academic.curriculum_course ADD CONSTRAINT fk_curriculum_course_curriculum_id FOREIGN KEY (curriculum_id) REFERENCES academic.curriculum (curriculum_id) ON DELETE RESTRICT;
ALTER TABLE academic.curriculum_course ADD CONSTRAINT fk_curriculum_course_course_version_id FOREIGN KEY (course_version_id) REFERENCES academic.course_version (course_version_id) ON DELETE RESTRICT;

-- ACD-08
ALTER TABLE academic.course ADD CONSTRAINT fk_course_department_id FOREIGN KEY (department_id) REFERENCES academic.department (department_id) ON DELETE RESTRICT;

-- ACD-09
ALTER TABLE academic.course_version ADD CONSTRAINT fk_course_version_course_id FOREIGN KEY (course_id) REFERENCES academic.course (course_id) ON DELETE RESTRICT;
ALTER TABLE academic.course_version ADD CONSTRAINT fk_course_version_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE academic.course_version ADD CONSTRAINT fk_course_version_source_document_version_id FOREIGN KEY (source_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ACD-10
ALTER TABLE academic.course_offering ADD CONSTRAINT fk_course_offering_course_version_id FOREIGN KEY (course_version_id) REFERENCES academic.course_version (course_version_id) ON DELETE RESTRICT;
ALTER TABLE academic.course_offering ADD CONSTRAINT fk_course_offering_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE academic.course_offering ADD CONSTRAINT fk_course_offering_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE academic.course_offering ADD CONSTRAINT fk_course_offering_section_id FOREIGN KEY (section_id) REFERENCES academic.section (section_id) ON DELETE RESTRICT;

-- ACD-11
ALTER TABLE academic.offering_faculty ADD CONSTRAINT fk_offering_faculty_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;
ALTER TABLE academic.offering_faculty ADD CONSTRAINT fk_offering_faculty_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ACD-12
ALTER TABLE academic.timetable_slot ADD CONSTRAINT fk_timetable_slot_course_offering_id FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id) ON DELETE RESTRICT;

-- ACD-14
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT fk_section_teacher_assignment_section_id FOREIGN KEY (section_id) REFERENCES academic.section (section_id) ON DELETE RESTRICT;
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT fk_section_teacher_assignment_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT fk_section_teacher_assignment_assigned_by FOREIGN KEY (assigned_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT fk_section_teacher_assignment_authority_role_assignment_id FOREIGN KEY (authority_role_assignment_id) REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT;
ALTER TABLE academic.section_teacher_assignment ADD CONSTRAINT fk_section_teacher_assignment_source_document_version_id FOREIGN KEY (source_document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- ACD-01
CREATE INDEX ix_department_hod ON academic.department (hod_person_id);
CREATE UNIQUE INDEX uq_department_code_lower ON academic.department (lower(code));

-- ACD-02
CREATE INDEX ix_programme_department_status ON academic.programme (department_id, status);
CREATE UNIQUE INDEX uq_programme_code ON academic.programme (institution_id, lower(programme_code));

-- ACD-03
CREATE INDEX ix_programme_version_from ON academic.programme_version (programme_id, effective_from_admission_year);
CREATE INDEX ix_programme_version_status ON academic.programme_version (status);
CREATE INDEX ix_programme_version_approved_by ON academic.programme_version (approved_by);
CREATE INDEX ix_programme_version_source_document_version_id ON academic.programme_version (source_document_version_id);

-- ACD-04
CREATE INDEX ix_batch_programme_year ON academic.batch (programme_id, admission_year);
CREATE INDEX ix_batch_autonomy ON academic.batch (autonomy_status);
CREATE INDEX ix_batch_programme_version_id ON academic.batch (programme_version_id);
CREATE INDEX ix_batch_current_term_id ON academic.batch (current_term_id);

-- ACD-05
CREATE INDEX ix_section_batch ON academic.section (batch_id);

-- ACD-06
CREATE INDEX ix_curriculum_programme_term ON academic.curriculum (programme_version_id, term_no);
CREATE INDEX ix_curriculum_approved_by ON academic.curriculum (approved_by);
CREATE INDEX ix_curriculum_effective_from_term_id ON academic.curriculum (effective_from_term_id);

-- ACD-07
CREATE INDEX ix_curriculum_course_version ON academic.curriculum_course (course_version_id);
CREATE INDEX ix_curriculum_course_seq ON academic.curriculum_course (curriculum_id, term_no, sequence_no);

-- ACD-08
CREATE INDEX ix_course_title_fts ON academic.course USING gin (to_tsvector('english', title));
CREATE UNIQUE INDEX uq_course_code_lower ON academic.course (lower(course_code));
CREATE INDEX ix_course_department_id ON academic.course (department_id);

-- ACD-09
CREATE INDEX ix_course_version_course ON academic.course_version (course_id, version_no);
CREATE INDEX ix_course_version_status ON academic.course_version (status);
CREATE INDEX ix_course_version_approved_by ON academic.course_version (approved_by);
CREATE INDEX ix_course_version_source_document_version_id ON academic.course_version (source_document_version_id);

-- ACD-10
CREATE INDEX ix_course_offering_term_batch ON academic.course_offering (term_id, batch_id);
CREATE INDEX ix_course_offering_version ON academic.course_offering (course_version_id);
CREATE UNIQUE INDEX uq_course_offering_code ON academic.course_offering (lower(offering_code));
CREATE INDEX ix_course_offering_batch_id ON academic.course_offering (batch_id);
CREATE INDEX ix_course_offering_section_id ON academic.course_offering (section_id);

-- ACD-11
CREATE INDEX ix_offering_faculty_person ON academic.offering_faculty (person_id, valid_to);
CREATE INDEX ix_offering_faculty_offering_role ON academic.offering_faculty (course_offering_id, role_in_offering);
CREATE UNIQUE INDEX uq_offering_faculty_coordinator ON academic.offering_faculty (course_offering_id) WHERE role_in_offering = 'coordinator' AND valid_to IS NULL;

-- ACD-12
CREATE INDEX ix_timetable_slot_offering_day ON academic.timetable_slot (course_offering_id, day_of_week, start_time);

-- ACD-14
CREATE INDEX ix_section_teacher_section_role ON academic.section_teacher_assignment (section_id, role_in_section, valid_from DESC);
CREATE INDEX ix_section_teacher_person ON academic.section_teacher_assignment (person_id, valid_to);
CREATE INDEX ix_section_teacher_authority ON academic.section_teacher_assignment (authority_role_assignment_id);
CREATE UNIQUE INDEX uq_section_teacher_open_class ON academic.section_teacher_assignment (section_id) WHERE role_in_section = 'class_teacher' AND status = 'active' AND valid_to IS NULL;
CREATE INDEX ix_section_teacher_assignment_assigned_by ON academic.section_teacher_assignment (assigned_by);
CREATE INDEX ix_section_teacher_assignment_source_document_version_id ON academic.section_teacher_assignment (source_document_version_id);

-- ---------------------------------------------------------------------------
-- 5. Staged foreign keys from W1a (OD-12, POSTGRES_ARCHITECTURE 17.3)
-- ---------------------------------------------------------------------------
-- Each source column was created in W1a. The target table is created here, so
-- the constraint is added and validated in this migration. NOT VALID keeps the
-- addition metadata-only; VALIDATE then checks the data.

ALTER TABLE iam.role_assignment
    ADD CONSTRAINT fk_role_assignment_programme
    FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id)
    NOT VALID;
ALTER TABLE iam.role_assignment VALIDATE CONSTRAINT fk_role_assignment_programme;

ALTER TABLE iam.role_assignment
    ADD CONSTRAINT fk_role_assignment_batch
    FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id)
    NOT VALID;
ALTER TABLE iam.role_assignment VALIDATE CONSTRAINT fk_role_assignment_batch;

ALTER TABLE iam.role_assignment
    ADD CONSTRAINT fk_role_assignment_course_offering
    FOREIGN KEY (course_offering_id) REFERENCES academic.course_offering (course_offering_id)
    NOT VALID;
ALTER TABLE iam.role_assignment VALIDATE CONSTRAINT fk_role_assignment_course_offering;

ALTER TABLE core.statutory_approval
    ADD CONSTRAINT fk_statutory_approval_programme
    FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id)
    NOT VALID;
ALTER TABLE core.statutory_approval VALIDATE CONSTRAINT fk_statutory_approval_programme;

ALTER TABLE core.affiliation_record
    ADD CONSTRAINT fk_affiliation_record_programme
    FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id)
    NOT VALID;
ALTER TABLE core.affiliation_record VALIDATE CONSTRAINT fk_affiliation_record_programme;

ALTER TABLE policy.rule_scope
    ADD CONSTRAINT fk_rule_scope_programme
    FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id)
    NOT VALID;
ALTER TABLE policy.rule_scope VALIDATE CONSTRAINT fk_rule_scope_programme;

ALTER TABLE policy.rule_scope
    ADD CONSTRAINT fk_rule_scope_batch
    FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id)
    NOT VALID;
ALTER TABLE policy.rule_scope VALIDATE CONSTRAINT fk_rule_scope_batch;

-- ---------------------------------------------------------------------------
-- 6. Business-rule triggers
-- ---------------------------------------------------------------------------

-- ACD-09: an update is rejected once a course_offering exists. DELETE is
-- already restricted by the course_offering foreign key.
CREATE OR REPLACE FUNCTION academic.reject_course_version_update()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, academic
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM academic.course_offering o
        WHERE o.course_version_id = OLD.course_version_id
    ) THEN
        RAISE EXCEPTION
            'academic.course_version %: content is frozen because a course offering exists',
            OLD.course_version_id;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION academic.reject_course_version_update() OWNER TO owner_academic;
REVOKE EXECUTE ON FUNCTION academic.reject_course_version_update() FROM PUBLIC;

CREATE TRIGGER trg_course_version_freeze
    BEFORE UPDATE ON academic.course_version
    FOR EACH ROW
    EXECUTE FUNCTION academic.reject_course_version_update();

-- ACD-10: section_id must belong to batch_id.
CREATE OR REPLACE FUNCTION academic.enforce_course_offering_section_batch()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, academic
AS $function$
BEGIN
    IF NEW.section_id IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM academic.section s
           WHERE s.section_id = NEW.section_id
             AND s.batch_id = NEW.batch_id
       )
    THEN
        RAISE EXCEPTION
            'academic.course_offering: section % does not belong to batch %',
            NEW.section_id, NEW.batch_id;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION academic.enforce_course_offering_section_batch() OWNER TO owner_academic;
REVOKE EXECUTE ON FUNCTION academic.enforce_course_offering_section_batch() FROM PUBLIC;

CREATE TRIGGER trg_course_offering_section_batch
    BEFORE INSERT OR UPDATE OF section_id, batch_id ON academic.course_offering
    FOR EACH ROW
    EXECUTE FUNCTION academic.enforce_course_offering_section_batch();

-- ACD-14: the Faculty-role and HOD/Principal authority-scope validation
-- triggers are deferred under A-01. There is no permission catalogue or
-- role-to-office mapping to validate against, and inventing one here would
-- create policy rather than implement it.

-- ---------------------------------------------------------------------------
-- 7. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA academic FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON
    academic.department, academic.programme, academic.programme_version,
    academic.batch, academic.section, academic.curriculum,
    academic.curriculum_course, academic.course, academic.course_version,
    academic.course_offering, academic.offering_faculty,
    academic.timetable_slot, academic.section_teacher_assignment
TO app_erp;

-- CIP reads the academic catalogue only. Delivery and authority tables
-- (course_offering, offering_faculty, timetable_slot,
-- section_teacher_assignment) are not part of that projection.
GRANT SELECT ON
    academic.department, academic.programme, academic.programme_version,
    academic.batch, academic.section, academic.curriculum,
    academic.curriculum_course, academic.course, academic.course_version
TO app_cip;

-- ---------------------------------------------------------------------------
-- 8. Row-level security
-- ---------------------------------------------------------------------------
-- ACD-14 is the only W1b table with a documented RLS intent (9.3). The
-- assigned teacher sees own rows. The HOD/Principal/Auditor arms require the
-- permission catalogue and are deferred under A-01; writes remain denied to
-- application roles, matching the W1a deny-by-default posture.

ALTER TABLE academic.section_teacher_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE academic.section_teacher_assignment FORCE ROW LEVEL SECURITY;

CREATE POLICY p_section_teacher_assignment_owner_all
    ON academic.section_teacher_assignment
    FOR ALL TO owner_academic
    USING (true) WITH CHECK (true);

CREATE POLICY p_section_teacher_assignment_self_select
    ON academic.section_teacher_assignment
    FOR SELECT TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer
    USING (person_id = (SELECT iam.current_person_id()));

-- ---------------------------------------------------------------------------
-- 9. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON INDEX academic.uq_programme_code IS
    'ACD-02: the column contract says programme_code is unique per institution; the index line says lower(programme_code). Implemented as unique (institution_id, lower(programme_code)), which satisfies both intents.';

COMMENT ON CONSTRAINT uq_course_offering ON academic.course_offering IS
    'ACD-10: NULLS NOT DISTINCT is used so a course version has at most one section-less offering per term; the dictionary does not state this explicitly.';

COMMENT ON TABLE academic.course_version IS
    'ACD-09: content is frozen after the first course_offering references the version (trg_course_version_freeze).';

COMMENT ON TABLE academic.section_teacher_assignment IS
    'ACD-14: Faculty-role and HOD/Principal authority-scope validation triggers are deferred under A-01 because the permission catalogue and role-to-office mapping do not exist yet. The authority_role_assignment_id foreign key is enforced; its semantic validity is not.';

COMMENT ON TABLE academic.timetable_slot IS
    'ACD-12: room_id is deliberately absent; venue_text is the schedule label. Room allocation is outside V1.';