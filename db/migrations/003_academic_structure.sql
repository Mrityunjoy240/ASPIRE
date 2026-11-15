-- 003_academic_structure.sql
-- Academic structure tables
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

-- programmes
CREATE TABLE programmes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    total_semesters INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (institution_id, code)
);

-- batches
CREATE TABLE batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    programme_id UUID REFERENCES programmes(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    start_year INT NOT NULL,
    end_year INT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE | GRADUATED | SUSPENDED
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_batches_programme_id ON batches(programme_id);

-- semesters
CREATE TABLE semesters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID REFERENCES batches(id) ON DELETE RESTRICT,
    semester_number INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'UPCOMING',  -- UPCOMING | ACTIVE | COMPLETED
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (batch_id, semester_number)
);

CREATE INDEX idx_semesters_batch_id ON semesters(batch_id);

-- courses
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    credit_hours INT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (institution_id, code)
);

-- course_runs
CREATE TABLE course_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE RESTRICT,
    semester_id UUID REFERENCES semesters(id) ON DELETE RESTRICT,
    batch_id UUID REFERENCES batches(id) ON DELETE RESTRICT,
    faculty_id UUID REFERENCES users(id) ON DELETE RESTRICT,  -- Subject Faculty
    total_classes INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (course_id, semester_id, batch_id)
);

CREATE INDEX idx_course_runs_semester_id ON course_runs(semester_id);
CREATE INDEX idx_course_runs_batch_id ON course_runs(batch_id);
CREATE INDEX idx_course_runs_faculty_id ON course_runs(faculty_id);