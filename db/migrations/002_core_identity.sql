-- 002_core_identity.sql
-- Core identity & auth tables
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

-- Enum: user_role
CREATE TYPE user_role AS ENUM (
    'STUDENT', 'FACULTY', 'CLASS_TEACHER', 'MENTOR', 'HOD', 'ADMIN'
);

-- institutions
CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- mirrors Supabase Auth user id
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE | SUSPENDED
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- user_role_assignments (sole source of truth for ASPIRE application roles)
CREATE TABLE user_role_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT,
    role user_role NOT NULL,
    scope_entity_type TEXT,  -- optional scope type; NULL = institution-wide
    scope_entity_id UUID,    -- optional scope id
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,    -- NULL = open-ended
    assigned_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Ensure no overlapping role assignments for same user/role/scope
    CONSTRAINT unique_role_assignment UNIQUE (user_id, role, scope_entity_type, scope_entity_id, valid_from)
);

CREATE INDEX idx_user_role_assignments_user_id ON user_role_assignments(user_id);
CREATE INDEX idx_user_role_assignments_institution_id ON user_role_assignments(institution_id);
CREATE INDEX idx_user_role_assignments_valid_range ON user_role_assignments(valid_from, valid_to);