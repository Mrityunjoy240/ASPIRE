-- 017_followup_contract_alignment.sql
-- Contract alignment for intervention_follow_ups after the R5 review
-- fixes (ADR-004 Amendment 1, 16 Oct 2026).
--
--   1. id DEFAULT gen_random_uuid() — DEC-03 pattern (migrations 011/012):
--      real-PostgreSQL inserts that omit id must work. 016 declared
--      "id UUID PRIMARY KEY" without the server-side default every other
--      UUID table carries, so the 05 §9 contract block and the ORM/tests
--      disagreed with the live schema. Purely additive: a column DEFAULT
--      never rewrites existing rows; no backfill, no data lock beyond the
--      brief ACCESS EXCLUSIVE column alter.
--
--   2. status comment now names CANCELLED — ADR-004 Amendment 1 (Option B)
--      supersedes stale SCHEDULED siblings: SCHEDULED -> CANCELLED on a
--      terminal-case due dispatch (consumer branch a) and on fulfilment
--      of another same-case follow-up (branch b), each with the mandatory
--      FOLLOW_UP_SUPERSEDED audit row. The 016 status comment
--      (SCHEDULED | FULFILLED | EVALUATED) predates that decision.
--
-- No constraint, index, or lifecycle rewrite: FULFILLED/EVALUATED/RESOLVED
-- semantics stay exactly as 016 froze them; CANCELLED is a new terminal
-- status for never-evaluated siblings only (ADR-004 §2.9).
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

ALTER TABLE intervention_follow_ups
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

COMMENT ON COLUMN intervention_follow_ups.status IS
    'SCHEDULED | FULFILLED | EVALUATED | CANCELLED — CANCELLED = superseded sibling never evaluated (ADR-004 Amendment 1); RESOLVED/REPLAN_REQUIRED live in outcome, not status';
