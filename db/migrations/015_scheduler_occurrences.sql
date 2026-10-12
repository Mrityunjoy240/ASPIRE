-- 015_scheduler_occurrences.sql
-- Technical emission bookkeeping for the time-based scheduler (DM-AG03,
-- docs/03_SYSTEM_SPEC.md 8.3; docs/05_DATA_API_CONTRACTS.md 7).
-- Approved at the R4 contract gate: EC-SCH-01/03 (no duplicate logical
-- events for triggers already emitted; outstanding occurrences recovered
-- across restarts) need durable fired-trigger state; this table is
-- technical metadata only, never business state. The scheduler writes this
-- table and nothing else (it never mutates task/case business state —
-- DM-SS02). Lifecycle: a fresh row is committed with state='CLAIMED' BEFORE
-- the domain event is published, then flipped to 'EMITTED' after publish.
-- A CLAIMED row found on a later cycle means a crash between claim and
-- mark: the occurrence is re-emitted once (EC-SCH-02: recovered, not
-- lost). If the crash happened after the handlers already ran, that
-- re-emission is a duplicate bus DISPATCH (delivery is at-least-once);
-- duplicate business effects stay impossible only because the current
-- TASK_OVERDUE consumer is route-only — a future writing consumer must
-- dedup on this primary key before it writes.
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE scheduler_occurrences (
    event_type    TEXT NOT NULL,             -- catalog name, e.g. 'TASK_OVERDUE' (03 8.1)
    source_id     UUID NOT NULL,             -- triggering entity (e.g. student_tasks.id)
    trigger_value TIMESTAMPTZ NOT NULL,      -- the time-condition value that fired (e.g. deadline)
    student_id    UUID NOT NULL REFERENCES student_profiles(id) ON DELETE RESTRICT,
    state         TEXT NOT NULL DEFAULT 'CLAIMED',  -- CLAIMED | EMITTED
    claimed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    emitted_at    TIMESTAMPTZ,               -- NULL while CLAIMED (emission not durably confirmed)
    PRIMARY KEY (event_type, source_id, trigger_value)
);
