-- 007_audit_log.sql
-- Audit & provenance table
-- Every privileged write in the entire system produces one of these rows.
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Can be a system agent UUID
    actor_type TEXT NOT NULL,  -- USER | SYSTEM_AGENT
    action_type TEXT NOT NULL,  -- e.g., 'ATTENDANCE_UPDATED', 'PLAN_APPROVED'
    entity_table TEXT NOT NULL,  -- e.g., 'attendance_records'
    entity_id UUID NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    source_system TEXT NOT NULL,  -- CSV_IMPORT | MENTOR_WEB | RULE_ENGINE | AGENT | STUDENT_APP
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_table, entity_id);
CREATE INDEX idx_audit_log_action ON audit_log(action_type);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);