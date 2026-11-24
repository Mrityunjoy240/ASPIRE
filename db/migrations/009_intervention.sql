-- 009_intervention.sql
-- Intervention case tables
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

-- Enum: intervention_case_status
CREATE TYPE intervention_case_status AS ENUM (
    'OPEN', 'IN_REVIEW', 'PLAN_PROPOSED', 'PENDING_APPROVAL', 'ACTIVE',
    'MONITORING', 'REPLAN_REQUIRED', 'ESCALATION_REQUIRED', 'RESOLVED', 'CLOSED'
);

-- intervention_cases
CREATE TABLE intervention_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES student_profiles(id) ON DELETE RESTRICT,
    mentor_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    status intervention_case_status NOT NULL DEFAULT 'OPEN',
    urgency_band TEXT NOT NULL,  -- URGENT | ATTENTION | MONITOR
    trigger_events JSONB,  -- Array of event IDs that opened the case
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_intervention_cases_student ON intervention_cases(student_id);
CREATE INDEX idx_intervention_cases_mentor ON intervention_cases(mentor_id);
CREATE INDEX idx_intervention_cases_status ON intervention_cases(status);
CREATE INDEX idx_intervention_cases_urgency ON intervention_cases(urgency_band);

-- intervention_plans
CREATE TABLE intervention_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES intervention_cases(id) ON DELETE RESTRICT,
    created_by TEXT NOT NULL,  -- 'SYSTEM_AGENT' or user UUID
    status TEXT NOT NULL,  -- PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED
    plan_actions JSONB NOT NULL,  -- Structured action array
    reason_codes TEXT[] NOT NULL,
    evidence JSONB NOT NULL,
    student_decision TEXT,  -- ACCEPTED | DECLINED | CUSTOMIZED
    student_reason TEXT,  -- Optional decline reason
    decided_at TIMESTAMPTZ,
    mentor_decision TEXT,  -- APPROVED | EDITED | REJECTED
    mentor_notes TEXT,
    mentor_acted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_intervention_plans_case ON intervention_plans(case_id);
CREATE INDEX idx_intervention_plans_status ON intervention_plans(status);