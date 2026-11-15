-- ===========================================================================
-- 0010_w3_faculty.sql
-- W3 faculty and mentoring
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- FAC-01 faculty.faculty_profile
CREATE TABLE faculty.faculty_profile (
    faculty_profile_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    employee_id text NOT NULL,
    designation text NOT NULL,
    department_id uuid NOT NULL,
    joining_date date NOT NULL,
    employment_type text NOT NULL DEFAULT 'permanent',
    highest_qualification text,
    specialization text,
    workload_category text,
    status text NOT NULL DEFAULT 'active',
    relieving_date date,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_faculty_profile PRIMARY KEY (faculty_profile_id)
);
ALTER TABLE faculty.faculty_profile OWNER TO owner_faculty;

-- FAC-02 faculty.staff_profile
CREATE TABLE faculty.staff_profile (
    staff_profile_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL,
    employee_id text NOT NULL,
    designation text NOT NULL,
    org_unit_id uuid NOT NULL,
    reporting_to_person_id uuid,
    joining_date date NOT NULL,
    employment_type text NOT NULL DEFAULT 'permanent',
    status text NOT NULL DEFAULT 'active',
    relieving_date date,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_staff_profile PRIMARY KEY (staff_profile_id)
);
ALTER TABLE faculty.staff_profile OWNER TO owner_faculty;

-- FAC-03 faculty.mentor_assignment
CREATE TABLE faculty.mentor_assignment (
    mentor_assignment_id uuid NOT NULL DEFAULT gen_random_uuid(),
    mentor_person_id uuid NOT NULL,
    student_id uuid NOT NULL,
    term_id uuid NOT NULL,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    status text NOT NULL DEFAULT 'active',
    assigned_by uuid,
    notes_visibility text NOT NULL DEFAULT 'mentor_only',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_mentor_assignment PRIMARY KEY (mentor_assignment_id)
);
ALTER TABLE faculty.mentor_assignment OWNER TO owner_faculty;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- FAC-01
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT uq_faculty_profile_person UNIQUE (person_id);
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_employee_id CHECK (char_length(employee_id) <= 30);
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_designation CHECK (char_length(designation) <= 100);
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_employment_type CHECK (employment_type IN ('permanent', 'contractual', 'visiting', 'guest', 'part_time'));
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_highest_qualification CHECK ((highest_qualification IS NULL OR (char_length(highest_qualification) <= 200)));
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_specialization CHECK ((specialization IS NULL OR (char_length(specialization) <= 300)));
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_workload_category CHECK ((workload_category IS NULL OR (workload_category IN ('principal', 'professor', 'associate_professor', 'assistant_professor', 'other'))));
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_status CHECK (status IN ('active', 'on_leave', 'relieved', 'retired'));
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT ck_faculty_profile_relieving_date CHECK ((relieving_date IS NULL OR relieving_date >= joining_date));

-- FAC-02
ALTER TABLE faculty.staff_profile ADD CONSTRAINT uq_staff_profile_person UNIQUE (person_id);
ALTER TABLE faculty.staff_profile ADD CONSTRAINT ck_staff_profile_designation CHECK (char_length(designation) <= 100);
ALTER TABLE faculty.staff_profile ADD CONSTRAINT ck_staff_profile_reporting_to_person_id CHECK ((reporting_to_person_id IS NULL OR (reporting_to_person_id <> person_id)));
ALTER TABLE faculty.staff_profile ADD CONSTRAINT ck_staff_profile_employment_type CHECK (employment_type IN ('permanent', 'contractual', 'outsourced'));
ALTER TABLE faculty.staff_profile ADD CONSTRAINT ck_staff_profile_status CHECK (status IN ('active', 'on_leave', 'relieved', 'retired'));
ALTER TABLE faculty.staff_profile ADD CONSTRAINT ck_staff_profile_relieving_date CHECK ((relieving_date IS NULL OR relieving_date >= joining_date));

-- FAC-03
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT ck_mentor_assignment_valid_to CHECK ((valid_to IS NULL OR valid_to > valid_from));
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT ck_mentor_assignment_status CHECK (status IN ('active', 'ended', 'revoked'));
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT ck_mentor_assignment_notes_visibility CHECK (notes_visibility IN ('mentor_only', 'hod_and_mentor'));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- FAC-01
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT fk_faculty_profile_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE faculty.faculty_profile ADD CONSTRAINT fk_faculty_profile_department_id FOREIGN KEY (department_id) REFERENCES academic.department (department_id) ON DELETE RESTRICT;

-- FAC-02
ALTER TABLE faculty.staff_profile ADD CONSTRAINT fk_staff_profile_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE faculty.staff_profile ADD CONSTRAINT fk_staff_profile_org_unit_id FOREIGN KEY (org_unit_id) REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT;
ALTER TABLE faculty.staff_profile ADD CONSTRAINT fk_staff_profile_reporting_to_person_id FOREIGN KEY (reporting_to_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- FAC-03
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT fk_mentor_assignment_mentor_person_id FOREIGN KEY (mentor_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT fk_mentor_assignment_student_id FOREIGN KEY (student_id) REFERENCES student.student (student_id) ON DELETE RESTRICT;
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT fk_mentor_assignment_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE faculty.mentor_assignment ADD CONSTRAINT fk_mentor_assignment_assigned_by FOREIGN KEY (assigned_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- FAC-01
CREATE INDEX ix_faculty_profile_department_status ON faculty.faculty_profile (department_id, status);
CREATE INDEX ix_faculty_profile_designation ON faculty.faculty_profile (designation);
CREATE UNIQUE INDEX uq_faculty_profile_employee ON faculty.faculty_profile (lower(employee_id));

-- FAC-02
CREATE INDEX ix_staff_profile_org_status ON faculty.staff_profile (org_unit_id, status);
CREATE UNIQUE INDEX uq_staff_profile_employee ON faculty.staff_profile (lower(employee_id));
CREATE INDEX ix_staff_profile_reporting_to_person_id ON faculty.staff_profile (reporting_to_person_id);

-- FAC-03
CREATE INDEX ix_mentor_assignment_mentor_term ON faculty.mentor_assignment (mentor_person_id, term_id);
CREATE INDEX ix_mentor_assignment_student_term ON faculty.mentor_assignment (student_id, term_id);
CREATE UNIQUE INDEX uq_mentor_assignment_active ON faculty.mentor_assignment (student_id, term_id) WHERE status = 'active';
CREATE INDEX ix_mentor_assignment_term_id ON faculty.mentor_assignment (term_id);
CREATE INDEX ix_mentor_assignment_assigned_by ON faculty.mentor_assignment (assigned_by);

-- ---------------------------------------------------------------------------
-- 5. Documented security-definer helpers (POSTGRES_ARCHITECTURE 9.2)
-- ---------------------------------------------------------------------------
-- FAC-03 completes the mentor arm. The helper reads
-- faculty.mentor_assignment as owner_iam through an explicit SELECT grant.
-- DATA_DICTIONARY 1.6 does not list the faculty schema for RLS, so no policy
-- is invented here; the relationship filters access to student rows through
-- iam.can_access_student.

GRANT USAGE ON SCHEMA faculty TO owner_iam;
GRANT SELECT ON faculty.mentor_assignment TO owner_iam;

CREATE OR REPLACE FUNCTION iam.is_mentor_of(p_student_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM faculty.mentor_assignment ma
        WHERE ma.student_id = $1
          AND ma.mentor_person_id = (SELECT iam.current_person_id())
          AND ma.status = 'active'
          AND ma.valid_from <= current_date
          AND (ma.valid_to IS NULL OR ma.valid_to >= current_date)
    )
$$;
ALTER FUNCTION iam.is_mentor_of(uuid) OWNER TO owner_iam;
REVOKE EXECUTE ON FUNCTION iam.is_mentor_of(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION iam.is_mentor_of(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;

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
        OR iam.is_mentor_of($1)
$$;
ALTER FUNCTION iam.can_access_student(uuid) OWNER TO owner_iam;
REVOKE EXECUTE ON FUNCTION iam.can_access_student(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION iam.can_access_student(uuid) TO app_erp, app_cip, app_integration, app_worker, app_reporting, audit_writer;

-- ---------------------------------------------------------------------------
-- 6. Business-rule trigger
-- ---------------------------------------------------------------------------

-- FAC-03: a mentor must hold an active faculty profile. The dictionary does
-- not define "active" beyond the profile status; joining/relieving dates are
-- not re-interpreted here.
CREATE OR REPLACE FUNCTION faculty.enforce_mentor_active_profile()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, faculty
AS $function$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM faculty.faculty_profile fp
        WHERE fp.person_id = NEW.mentor_person_id
          AND fp.status = 'active'
    ) THEN
        RAISE EXCEPTION
            'faculty.mentor_assignment: mentor % has no active faculty profile',
            NEW.mentor_person_id;
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION faculty.enforce_mentor_active_profile() OWNER TO owner_faculty;
REVOKE EXECUTE ON FUNCTION faculty.enforce_mentor_active_profile() FROM PUBLIC;

CREATE TRIGGER trg_mentor_assignment_active_profile
    BEFORE INSERT OR UPDATE OF mentor_person_id ON faculty.mentor_assignment
    FOR EACH ROW
    EXECUTE FUNCTION faculty.enforce_mentor_active_profile();

-- ---------------------------------------------------------------------------
-- 7. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA faculty FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE ON
    faculty.faculty_profile, faculty.staff_profile
TO app_erp;

-- FAC-03 notes_visibility is class R and is outside the application
-- projection until a named-role view is approved (OD-16 / A-01).
GRANT SELECT (
    mentor_assignment_id, mentor_person_id, student_id, term_id, assigned_at,
    valid_from, valid_to, status, assigned_by,
    created_at, created_by, updated_at, updated_by, row_version
) ON faculty.mentor_assignment TO app_erp;
GRANT INSERT (
    mentor_assignment_id, mentor_person_id, student_id, term_id, assigned_at,
    valid_from, valid_to, status, assigned_by,
    created_at, created_by, updated_at, updated_by, row_version
) ON faculty.mentor_assignment TO app_erp;
GRANT UPDATE (
    mentor_person_id, student_id, term_id, valid_from, valid_to, status,
    assigned_by, updated_at, updated_by, row_version
) ON faculty.mentor_assignment TO app_erp;

-- ---------------------------------------------------------------------------
-- 8. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE faculty.mentor_assignment IS
    'FAC-03: trg_mentor_assignment_active_profile enforces that mentor_person_id holds a faculty_profile with status = active. The partial unique index uq_mentor_assignment_active keeps one active mentor per student and term. notes_visibility is class R and is not granted to app_erp.';

COMMENT ON POLICY p_student_access_select ON student.student IS
    'POSTGRES_ARCHITECTURE 9.3: self, consenting guardian, open section teacher, allocated faculty, and active mentor are implemented. HOD/Registrar/COE/Auditor arms wait for A-01.';