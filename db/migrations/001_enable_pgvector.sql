-- 001_enable_pgvector.sql
-- Enable pgvector extension for embeddings support (Learning Workspace RAG)
-- DM-NEW-ORM01: This migration file is the ONLY schema authority.

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is available
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE EXCEPTION 'pgvector extension not installed';
    END IF;
END $$;