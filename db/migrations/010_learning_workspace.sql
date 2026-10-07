-- 010_learning_workspace.sql
-- Learning Workspace tables (RAG for AI copilot)
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

-- learning_documents
CREATE TABLE learning_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by UUID REFERENCES users(id) ON DELETE RESTRICT,
    access_scope TEXT NOT NULL,  -- OWNER_ONLY | COURSE_SHARED | TEACHER_PUBLISHED | INSTITUTION_PUBLISHED
    scope_id UUID,  -- course_run_id if COURSE_SHARED, null if INSTITUTION_PUBLISHED
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,  -- Object storage reference
    processing_status TEXT DEFAULT 'PENDING',  -- PENDING | CHUNKED | FAILED
    subject_tag TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_learning_documents_uploaded_by ON learning_documents(uploaded_by);
CREATE INDEX idx_learning_documents_scope ON learning_documents(access_scope, scope_id);
CREATE INDEX idx_learning_documents_processing ON learning_documents(processing_status);

-- document_chunks
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES learning_documents(id) ON DELETE RESTRICT,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,  -- Raw text of the chunk
    embedding vector(1024),  -- pgvector (BGE-M3 produces 1024-dim)
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_document ON document_chunks(document_id);
-- HNSW index for vector similarity search (created after data population)
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);