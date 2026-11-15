-- 004_student_profiles.sql
-- Student profile table
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE student_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE RESTRICT UNIQUE,
    batch_id UUID REFERENCES batches(id) ON DELETE RESTRICT,
    roll_number TEXT NOT NULL,
    mentor_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Assigned Mentor
    class_teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Assigned CT
    enrollment_year INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (batch_id, roll_number)
);

CREATE INDEX idx_student_profiles_batch_id ON student_profiles(batch_id);
CREATE INDEX idx_student_profiles_mentor_id ON student_profiles(mentor_id);
CREATE INDEX idx_student_profiles_class_teacher_id ON student_profiles(class_teacher_id);