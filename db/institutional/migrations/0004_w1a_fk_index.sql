-- 0004_w1a_fk_index.sql
-- Phase 2 / Wave W1a: complete the documented FK-index rule.
--
-- DATA_DICTIONARY.md section 1.2 states:
--   "Every FK column gets a btree index unless the entry says otherwise."
--
-- Validation of the W1a schema found one foreign-key column without a
-- supporting index: core.statutory_approval.institution_id. Every other W1a
-- foreign-key column already has a btree index whose first key column is the
-- FK column.
--
-- This is a forward-only follow-up rather than an edit to 0002_w1a_schema.sql,
-- because 0002 is already applied and checksum-recorded. It changes no column,
-- constraint, or behaviour.

CREATE INDEX ix_statutory_approval_institution
    ON core.statutory_approval (institution_id);
ALTER INDEX core.ix_statutory_approval_institution OWNER TO owner_core;
