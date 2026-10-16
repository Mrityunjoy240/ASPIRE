-- 008_tasks.sql
-- Unified task table
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.
-- DM-SS02: OVERUED is derived at query time, not persisted.

-- Enum: task_source_type
CREATE TYPE task_source_type AS ENUM (
    'CALENDAR', 'ASSESSMENT', 'AI_PLAN', 'MENTOR'
);

-- Enum: task_status
CREATE TYPE task_status AS ENUM (
    'PENDING', 'COMPLETED', 'SNOOZED'
);

-- student_tasks
CREATE TABLE student_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES student_profiles(id) ON DELETE RESTRICT,
    source_type task_source_type NOT NULL,
    source_id UUID NOT NULL,  -- FK to originating event/plan/case
    created_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    deadline TIMESTAMPTZ,
    status task_status NOT NULL DEFAULT 'PENDING',
    explicit_priority INT,  -- Optional override for sort
    urgency_score INT,  -- Computed by priority engine (0-100)
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_student_tasks_student ON student_tasks(student_id);
CREATE INDEX idx_student_tasks_deadline ON student_tasks(deadline);
CREATE INDEX idx_student_tasks_status ON student_tasks(status);
CREATE INDEX idx_student_tasks_source ON student_tasks(source_type, source_id);

-- OVERDUE is a derived display state (deadline < now AND status = PENDING).
-- Not persisted. No scheduler job rewrites PENDING → OVERDUE.