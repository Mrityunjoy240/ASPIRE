-- 0005_w1a_org_path_trigger.sql
-- Phase 2 / Wave W1a: correct the org-unit descendant path trigger.
--
-- 0002 created the trigger as AFTER UPDATE OF path. PostgreSQL fires an
-- UPDATE OF trigger only when the named column appears in the UPDATE target
-- list, not when a BEFORE trigger changes the column. Renaming an org unit
-- updates code, and the BEFORE trigger recomputes path, so the descendant
-- refresh never ran.
--
-- The corrected trigger fires on every UPDATE and the function already guards
-- on "NEW.path IS DISTINCT FROM OLD.path", so unrelated updates are cheap.
-- No column, constraint, or data is changed.

DROP TRIGGER trg_org_unit_descendant_paths ON core.org_unit;

CREATE TRIGGER trg_org_unit_descendant_paths
    AFTER UPDATE ON core.org_unit
    FOR EACH ROW EXECUTE FUNCTION core.refresh_org_unit_descendant_paths();
