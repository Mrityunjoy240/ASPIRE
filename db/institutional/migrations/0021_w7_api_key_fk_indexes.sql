-- ===========================================================================
-- 0021_w7_api_key_fk_indexes.sql
-- W7 / Phase 9B: leading indexes for the two remaining api_key foreign keys.
--
-- 0019 indexed api_key.client_id but not created_by/updated_by. The FK-index
-- invariant (every foreign-key column has a leading index) is enforced by
-- test_10, and the same invariant is applied to every other W1a+ table.
--
-- This migration adds only two indexes. It changes no data, grant, policy, or
-- function.
--
-- Forward-only. Does not edit the applied 0019 file.
-- ===========================================================================

SET client_min_messages = warning;

CREATE INDEX ix_api_key_created_by ON iam.api_key (created_by);
CREATE INDEX ix_api_key_updated_by ON iam.api_key (updated_by);

DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(name, ', ')
    INTO missing
    FROM (VALUES ('ix_api_key_created_by'), ('ix_api_key_updated_by')) AS t(name)
    WHERE to_regclass('iam.' || t.name) IS NULL;

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION '0021: expected index(es) missing: %', missing;
    END IF;
END
$$;
