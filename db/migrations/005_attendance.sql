-- 005_attendance.sql
-- Attendance tables
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.
-- DM-NEW-LATE01: LATE is reserved/unsupported in v1, kept in enum for schema compatibility only.

-- Enum: attendance_status
CREATE TYPE attendance_status AS ENUM (
    'PRESENT', 'ABSENT', 'LATE', 'CANCELLED'
);

-- attendance_records
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES student_profiles(id) ON DELETE RESTRICT,
    course_run_id UUID REFERENCES course_runs(id) ON DELETE RESTRICT,
    class_date DATE NOT NULL,
    status attendance_status NOT NULL,
    source_type TEXT NOT NULL,  -- CSV_IMPORT | MANUAL_ENTRY | API
    source_id TEXT,             -- import batch ID or entry ID
    record_status TEXT DEFAULT 'VERIFIED',  -- VERIFIED | PROVISIONAL | CONFLICT | SUPERSEDED
    recorded_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, course_run_id, class_date, version)
);

CREATE INDEX idx_attendance_records_student_course ON attendance_records(student_id, course_run_id);
CREATE INDEX idx_attendance_records_course_run_date ON attendance_records(course_run_id, class_date);
CREATE INDEX idx_attendance_records_record_status ON attendance_records(record_status);

-- attendance_derived_state
-- Written by the Attendance Engine after every update. Never written by agents.
CREATE TABLE attendance_derived_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES student_profiles(id) ON DELETE RESTRICT,
    course_run_id UUID REFERENCES course_runs(id) ON DELETE RESTRICT,
    classes_conducted INT NOT NULL,
    classes_attended INT NOT NULL,
    attendance_percentage NUMERIC(5,2),  -- NULL if conducted = 0
    risk_band TEXT,  -- SAFE | WARNING | CRITICAL | DATA_CONFLICT
    required_to_recover INT,  -- from calculate_required_classes()
    computed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (student_id, course_run_id)
);

CREATE INDEX idx_attendance_derived_state_student ON attendance_derived_state(student_id);
CREATE INDEX idx_attendance_derived_state_risk_band ON attendance_derived_state(risk_band);