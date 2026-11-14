-- ===========================================================================
-- 0015_w6_knowledge.sql
-- W6 knowledge corpus
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;
-- KNW-02 knowledge.embedding is deliberately absent. OD-06 records the
-- default posture "do not create the column until this is decided"; the
-- embedding model and dimension are still open. The current
-- postgres:16-alpine image also provides no vector extension. The
-- supported path is the official pgvector/pgvector:pg16 image (or a
-- version-pinned compiled pgvector build) once OD-06 closes. See the W6
-- evidence in docs/implementation/database/IMPLEMENTATION_PLAN.md.

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- KNW-01 knowledge.document_chunk
CREATE TABLE knowledge.document_chunk (
    chunk_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_version_id uuid NOT NULL,
    ingestion_run_id uuid,
    sequence_no integer NOT NULL,
    chunk_text text NOT NULL,
    section_path text,
    page_from integer,
    page_to integer,
    token_count integer NOT NULL,
    language text,
    chunking_profile text NOT NULL DEFAULT 'default',
    text_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_document_chunk PRIMARY KEY (chunk_id)
);
ALTER TABLE knowledge.document_chunk OWNER TO owner_knowledge;

-- KNW-03 knowledge.ingestion_run
CREATE TABLE knowledge.ingestion_run (
    ingestion_run_id uuid NOT NULL DEFAULT gen_random_uuid(),
    triggered_by uuid,
    source_type text NOT NULL,
    source_uri text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running',
    documents_seen integer NOT NULL DEFAULT 0,
    versions_created integer NOT NULL DEFAULT 0,
    chunks_created integer NOT NULL DEFAULT 0,
    embeddings_created integer NOT NULL DEFAULT 0,
    error_count integer NOT NULL DEFAULT 0,
    error_summary text,
    parser_version text,
    ocr_engine text,
    chunker_version text,
    embedding_model text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_ingestion_run PRIMARY KEY (ingestion_run_id)
);
ALTER TABLE knowledge.ingestion_run OWNER TO owner_knowledge;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- KNW-01
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT uq_document_chunk_version_profile_seq UNIQUE (document_version_id, chunking_profile, sequence_no);
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_sequence_no CHECK (sequence_no >= 0);
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_chunk_text CHECK (char_length(chunk_text) BETWEEN 1 AND 20000);
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_section_path CHECK ((section_path IS NULL OR (char_length(section_path) <= 1000)));
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_page_from CHECK ((page_from IS NULL OR (page_from >= 1)));
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_page_to CHECK ((page_to IS NULL OR page_to >= page_from));
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_token_count CHECK (token_count > 0);
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_language CHECK ((language IS NULL OR (language IN ('en', 'bn', 'hi', 'multilingual', 'other'))));
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_chunking_profile CHECK (char_length(chunking_profile) <= 50);
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT ck_document_chunk_text_hash CHECK (char_length(text_hash) = 64);

-- KNW-03
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_source_type CHECK (source_type IN ('file_upload', 'url', 'folder_scan', 'api'));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_source_uri CHECK ((source_uri IS NULL OR (char_length(source_uri) <= 2000)));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_finished_at CHECK ((finished_at IS NULL OR finished_at >= started_at));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_status CHECK (status IN ('running', 'completed', 'completed_with_errors', 'failed'));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_documents_seen CHECK (documents_seen >= 0);
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_versions_created CHECK (versions_created >= 0);
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_chunks_created CHECK (chunks_created >= 0);
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_embeddings_created CHECK (embeddings_created >= 0);
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_error_count CHECK (error_count >= 0);
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_error_summary CHECK ((error_summary IS NULL OR (char_length(error_summary) <= 5000)));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_parser_version CHECK ((parser_version IS NULL OR (char_length(parser_version) <= 50)));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_ocr_engine CHECK ((ocr_engine IS NULL OR (char_length(ocr_engine) <= 50)));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_chunker_version CHECK ((chunker_version IS NULL OR (char_length(chunker_version) <= 50)));
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT ck_ingestion_run_embedding_model CHECK ((embedding_model IS NULL OR (char_length(embedding_model) <= 100)));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- KNW-01
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT fk_document_chunk_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;
ALTER TABLE knowledge.document_chunk ADD CONSTRAINT fk_document_chunk_ingestion_run_id FOREIGN KEY (ingestion_run_id) REFERENCES knowledge.ingestion_run (ingestion_run_id) ON DELETE RESTRICT;

-- KNW-03
ALTER TABLE knowledge.ingestion_run ADD CONSTRAINT fk_ingestion_run_triggered_by FOREIGN KEY (triggered_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- KNW-01
CREATE INDEX ix_document_chunk_fts ON knowledge.document_chunk USING gin (to_tsvector('simple', chunk_text));
CREATE INDEX ix_document_chunk_version_seq ON knowledge.document_chunk (document_version_id, sequence_no);
CREATE INDEX ix_document_chunk_language ON knowledge.document_chunk (language);
CREATE INDEX ix_document_chunk_ingestion_run_id ON knowledge.document_chunk (ingestion_run_id);

-- KNW-03
CREATE INDEX ix_ingestion_run_started ON knowledge.ingestion_run (started_at DESC);
CREATE INDEX ix_ingestion_run_status ON knowledge.ingestion_run (status);
CREATE INDEX ix_ingestion_run_triggered_by ON knowledge.ingestion_run (triggered_by);

-- ---------------------------------------------------------------------------
-- 5. Business-rule triggers and helpers
-- ---------------------------------------------------------------------------

-- KNW-01: the classification lookup is owned by the document schema so the
-- check sees the true classification regardless of the caller's document RLS
-- visibility. It is the database half of the ingestion-service filter.
CREATE OR REPLACE FUNCTION doc.classification_of(p_document_version_id uuid)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
    SELECT d.classification
    FROM doc.document_version v
    JOIN doc.document d ON d.document_id = v.document_id
    WHERE v.document_version_id = $1
$function$;
ALTER FUNCTION doc.classification_of(uuid) OWNER TO owner_doc;
REVOKE EXECUTE ON FUNCTION doc.classification_of(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION doc.classification_of(uuid) TO app_cip, owner_knowledge;

CREATE OR REPLACE FUNCTION knowledge.enforce_chunk_source_classification()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, knowledge
AS $function$
DECLARE
    v_classification text;
BEGIN
    v_classification := doc.classification_of(NEW.document_version_id);
    IF v_classification IS NULL THEN
        RAISE EXCEPTION
            'knowledge.document_chunk: source document version % not found',
            NEW.document_version_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF v_classification IN ('R', 'G') THEN
        RAISE EXCEPTION
            'knowledge.document_chunk: source document is classified % and cannot be chunked',
            v_classification
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$function$;
ALTER FUNCTION knowledge.enforce_chunk_source_classification() OWNER TO owner_knowledge;
REVOKE EXECUTE ON FUNCTION knowledge.enforce_chunk_source_classification() FROM PUBLIC;

CREATE TRIGGER trg_document_chunk_source_classification
    BEFORE INSERT OR UPDATE ON knowledge.document_chunk
    FOR EACH ROW
    EXECUTE FUNCTION knowledge.enforce_chunk_source_classification();

-- KNW-01: chunks are append-only (POSTGRES_ARCHITECTURE 10.2).
CREATE TRIGGER trg_document_chunk_append_only
    BEFORE UPDATE OR DELETE ON knowledge.document_chunk
    FOR EACH ROW
    EXECUTE FUNCTION ops.reject_mutation();

-- ---------------------------------------------------------------------------
-- 6. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON knowledge.document_chunk, knowledge.ingestion_run FROM PUBLIC;

-- POSTGRES_ARCHITECTURE 3.1: app_cip writes knowledge. No role receives DELETE.
GRANT SELECT, INSERT, UPDATE ON
    knowledge.document_chunk, knowledge.ingestion_run
TO app_cip;

-- ---------------------------------------------------------------------------
-- 7. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every knowledge table. The only
-- documented 9.3 intent is classification inheritance for chunks.

ALTER TABLE knowledge.document_chunk ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.document_chunk FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge.ingestion_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.ingestion_run FORCE ROW LEVEL SECURITY;

CREATE POLICY p_document_chunk_owner_all ON knowledge.document_chunk
    FOR ALL TO owner_knowledge USING (true) WITH CHECK (true);
CREATE POLICY p_ingestion_run_owner_all ON knowledge.ingestion_run
    FOR ALL TO owner_knowledge USING (true) WITH CHECK (true);

-- POSTGRES_ARCHITECTURE 9.3: a chunk inherits its source version's
-- classification. The subquery is itself subject to doc RLS, so a chunk is
-- visible only when the caller can see the source version. The doc C/R/G arms
-- wait for A-01, so app_cip currently sees P/I chunks.
CREATE POLICY p_document_chunk_classification_select ON knowledge.document_chunk
    FOR SELECT TO app_cip
    USING (
        EXISTS (
            SELECT 1
            FROM doc.document_version v
            WHERE v.document_version_id = knowledge.document_chunk.document_version_id
        )
    );

-- ---------------------------------------------------------------------------
-- 8. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON SCHEMA knowledge IS
    'KNW-02 knowledge.embedding is deliberately absent: OD-06 forbids creating the vector column before the embedding model and dimension are decided. The current postgres:16-alpine image has no vector extension; the supported path is the official pgvector/pgvector:pg16 image or a version-pinned compiled build once OD-06 closes.';

COMMENT ON TABLE knowledge.document_chunk IS
    'KNW-01: retrieval unit. trg_document_chunk_source_classification rejects an R/G source; trg_document_chunk_append_only seals the row. RLS inherits doc classification through doc.document_version; the C arm waits for A-01.';

COMMENT ON TABLE knowledge.ingestion_run IS
    'KNW-03: provenance counters and status. The run is mutable while it progresses (POSTGRES_ARCHITECTURE 10.2 does not seal it). RLS is deny-by-default for application roles until a service-role arm is approved under A-01.';

COMMENT ON FUNCTION doc.classification_of(uuid) IS
    'KNW-01: returns the classification of a document version. SECURITY DEFINER owned by owner_doc so the chunk trigger is not limited by the caller''s document RLS.';

COMMENT ON FUNCTION knowledge.enforce_chunk_source_classification() IS
    'KNW-01: rejects a chunk whose source document is classified R or G.';

COMMENT ON POLICY p_document_chunk_classification_select ON knowledge.document_chunk IS
    'POSTGRES_ARCHITECTURE 9.3: classification inheritance. P is visible to an authenticated session; I requires a person; C/R/G wait for the named-role mapping (A-01).';