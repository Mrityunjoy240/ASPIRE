-- 016_intervention_follow_ups.sql
-- Follow-up persistence for the three RULE_ENGINE follow-up rows of the
-- frozen intervention state machine (docs/03_SYSTEM_SPEC.md 10.2) and the
-- follow-up policy of docs/02_USER_JOURNEYS.md 2.1 Steps 5-7 /
-- docs/06_AGENT_SPEC.md 4 (schedule_followup). Contract: ADR-004
-- (docs/decisions/ADR-004_INTERVENTION_FOLLOWUP_MODEL.md), added to
-- docs/05_DATA_API_CONTRACTS.md 9 by the same decision. Lead directive
-- (option C), 13 Oct 2026.
--
-- Lifecycle: SCHEDULED -> FULFILLED (due: event path or scheduler-emitted
-- MENTOR_FOLLOWUP_DUE) -> EVALUATED (expiry re-check; outcome RESOLVED or
-- REPLAN_REQUIRED). The status flip under SELECT ... FOR UPDATE is the
-- durable consumer-side dedup (ADR-004 2.3, lead option A): a duplicate
-- bus dispatch re-reads the committed status and no-ops. due_at is set for
-- CUSTOM_DATE only (02 2.1 Step 6 mentor custom date); event-driven types
-- carry NULL due_at and are fulfilled by their policy trigger events.
-- evaluation_window_ends_at is denormalized at fulfilment so later rule
-- edits never rewrite in-flight windows (ADR-004 2.6).
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE intervention_follow_ups (
    id                        UUID PRIMARY KEY,
    case_id                   UUID NOT NULL REFERENCES intervention_cases(id) ON DELETE RESTRICT,
    trigger_type              TEXT NOT NULL,             -- ATTENDANCE_INTERVENTION | STUDY_INTERVENTION | ASSIGNMENT_INTERVENTION | CUSTOM_DATE
    status                    TEXT NOT NULL DEFAULT 'SCHEDULED',  -- SCHEDULED | FULFILLED | EVALUATED
    due_at                    TIMESTAMPTZ,               -- CUSTOM_DATE only; NULL for event-driven types
    triggered_at              TIMESTAMPTZ,               -- fulfilment time (event fired / due date reached)
    evaluation_window_ends_at TIMESTAMPTZ,               -- set on fulfilment; drives the expiry re-check
    evaluated_at              TIMESTAMPTZ,               -- improvement check performed
    outcome                   TEXT,                      -- RESOLVED | REPLAN_REQUIRED | NULL while pending
    created_by                TEXT NOT NULL,             -- 'SYSTEM' or user UUID
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_intervention_follow_ups_case ON intervention_follow_ups (case_id);
CREATE INDEX idx_intervention_follow_ups_status ON intervention_follow_ups (status);
-- Scheduler scan: due candidates (SCHEDULED + due_at) and expiry candidates
-- (FULFILLED + evaluation_window_ends_at) both start from status.
CREATE INDEX idx_intervention_follow_ups_due ON intervention_follow_ups (status, due_at);
CREATE INDEX idx_intervention_follow_ups_window ON intervention_follow_ups (status, evaluation_window_ends_at);
