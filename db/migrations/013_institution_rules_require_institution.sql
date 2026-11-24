-- 013_institution_rules_require_institution.sql
-- DEC-02 (approved): every institution_rules row belongs to an institution.
-- Global / institution-independent rules are NOT supported by this decision.
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.
--
-- Preflight: refuse to enforce NOT NULL while any existing row has a NULL
-- institution_id. Never silently delete, reassign, or invent ownership —
-- fix ownership through an approved backfill, then re-run this migration.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM institution_rules WHERE institution_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'DEC-02 preflight failed: institution_rules contains rows with institution_id IS NULL; refusing to enforce NOT NULL. Backfill institution ownership via an approved process, then re-run 013_institution_rules_require_institution.sql';
    END IF;
    ALTER TABLE institution_rules ALTER COLUMN institution_id SET NOT NULL;
END $$;
