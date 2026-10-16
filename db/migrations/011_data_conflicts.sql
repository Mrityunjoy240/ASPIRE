-- 011_data_conflicts.sql
-- Data Conflict Registry
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE data_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_table TEXT NOT NULL,
    entity_id UUID NOT NULL,
    existing_value JSONB NOT NULL,
    incoming_value JSONB NOT NULL,
    source_a TEXT NOT NULL,  -- e.g., 'MANUAL_ENTRY'
    source_b TEXT NOT NULL,  -- e.g., 'CSV_IMPORT'
    status TEXT DEFAULT 'OPEN',  -- OPEN | RESOLVED | IGNORED
    resolver_id UUID REFERENCES users(id) ON DELETE SET NULL,
    resolution JSONB,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_data_conflicts_entity ON data_conflicts(entity_table, entity_id);
CREATE INDEX idx_data_conflicts_status ON data_conflicts(status);