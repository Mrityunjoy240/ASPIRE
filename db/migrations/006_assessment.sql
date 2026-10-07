-- 006_assessment.sql
-- Assessment tables (configuration-driven per DM-ASSESS01)
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

-- Enum: assessment_component_type
CREATE TYPE assessment_component_type AS ENUM (
    'CIA', 'CIA-1', 'CIA-2', 'PCIA', 'ESE', 'PESE', 'LAB',
    'ASSIGNMENT', 'CLASS_TEST', 'ATTENDANCE', 'QUIZ', 'PROJECT', 'VIVA'
);

-- Enum: assessment_submission_status
CREATE TYPE assessment_submission_status AS ENUM (
    'NOT_SUBMITTED', 'SUBMITTED_PENDING_EVALUATION', 'GRADED',
    'OFFICIAL_ZERO', 'WITHHELD', 'CANCELLED'
);

-- assessment_components
-- Configuration rows for a course run's assessment components (DM-ASSESS01).
-- Configuration lives here/in institution_rules; calculation logic lives in the engine.
CREATE TABLE assessment_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_run_id UUID REFERENCES course_runs(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,  -- e.g., 'CIA-1', 'Class Test', 'Assignment', 'ESE'
    type assessment_component_type NOT NULL,
    max_marks NUMERIC(5,2) NOT NULL,
    weight_percent NUMERIC(5,2),  -- contribution/weighting from active scheme configuration
    is_mandatory BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_assessment_components_course_run ON assessment_components(course_run_id);

-- assessment_submissions
CREATE TABLE assessment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES student_profiles(id) ON DELETE RESTRICT,
    assessment_component_id UUID REFERENCES assessment_components(id) ON DELETE RESTRICT,
    status assessment_submission_status NOT NULL,
    obtained_marks NUMERIC(5,2),  -- NULL if not graded
    maximum_marks NUMERIC(5,2) NOT NULL,
    submitted_at TIMESTAMPTZ,
    graded_at TIMESTAMPTZ,
    graded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    record_status TEXT DEFAULT 'VERIFIED',  -- VERIFIED | PROVISIONAL | CONFLICT | SUPERSEDED
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, assessment_component_id, version)
);

CREATE INDEX idx_assessment_submissions_student ON assessment_submissions(student_id);
CREATE INDEX idx_assessment_submissions_component ON assessment_submissions(assessment_component_id);
CREATE INDEX idx_assessment_submissions_status ON assessment_submissions(status);