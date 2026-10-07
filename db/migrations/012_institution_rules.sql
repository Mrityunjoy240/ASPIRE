-- 012_institution_rules.sql
-- Institution Configuration Table
-- Configuration-driven rules (thresholds, weights, schemes) live here — never hardcoded.
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE institution_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    rule_id TEXT NOT NULL,  -- e.g., 'attendance_threshold', 'assessment_scheme'
    scope_level TEXT NOT NULL,  -- INSTITUTION | BATCH | PROGRAMME | SEMESTER
    scope_id UUID,  -- ID of the scoped entity
    value JSONB NOT NULL,  -- supports numeric, boolean, complex objects
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,  -- NULL means currently active
    version INT NOT NULL DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE',
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (institution_id, rule_id, scope_level, scope_id, version)
);

CREATE INDEX idx_institution_rules_institution ON institution_rules(institution_id);
CREATE INDEX idx_institution_rules_scope ON institution_rules(scope_level, scope_id);
CREATE INDEX idx_institution_rules_effective ON institution_rules(effective_from, effective_to);