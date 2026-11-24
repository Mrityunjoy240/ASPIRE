-- ===========================================================================
-- 0014_w5_doc_notice.sql
-- W5 notices
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- DOC-04 doc.notice
CREATE TABLE doc.notice (
    notice_id uuid NOT NULL DEFAULT gen_random_uuid(),
    notice_no text NOT NULL,
    category text NOT NULL DEFAULT 'general',
    issuing_org_unit_id uuid,
    owner_person_id uuid,
    status text NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_notice PRIMARY KEY (notice_id)
);
ALTER TABLE doc.notice OWNER TO owner_doc;

-- DOC-05 doc.notice_version
CREATE TABLE doc.notice_version (
    notice_version_id uuid NOT NULL DEFAULT gen_random_uuid(),
    notice_id uuid NOT NULL,
    version_no integer NOT NULL DEFAULT 1,
    title text NOT NULL,
    body_markdown text NOT NULL,
    publish_at timestamptz,
    effective_from timestamptz,
    effective_to timestamptz,
    status text NOT NULL DEFAULT 'draft',
    supersedes_version_id uuid,
    document_version_id uuid,
    approved_by uuid,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_notice_version PRIMARY KEY (notice_version_id)
);
ALTER TABLE doc.notice_version OWNER TO owner_doc;

-- DOC-06 doc.notice_audience
CREATE TABLE doc.notice_audience (
    notice_audience_id uuid NOT NULL DEFAULT gen_random_uuid(),
    notice_version_id uuid NOT NULL,
    audience_type text NOT NULL DEFAULT 'all',
    programme_id uuid,
    batch_id uuid,
    term_id uuid,
    role_id uuid,
    org_unit_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_notice_audience PRIMARY KEY (notice_audience_id)
);
ALTER TABLE doc.notice_audience OWNER TO owner_doc;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- DOC-04
ALTER TABLE doc.notice ADD CONSTRAINT ck_notice_notice_no CHECK (char_length(notice_no) <= 50);
ALTER TABLE doc.notice ADD CONSTRAINT ck_notice_category CHECK (category IN ('academic', 'examination', 'admission', 'fee', 'event', 'placement', 'general', 'urgent'));
ALTER TABLE doc.notice ADD CONSTRAINT ck_notice_status CHECK (status IN ('draft', 'active', 'withdrawn', 'archived'));

-- DOC-05
ALTER TABLE doc.notice_version ADD CONSTRAINT uq_notice_version UNIQUE (notice_id, version_no);
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_version_no CHECK (version_no >= 1);
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_title CHECK (char_length(title) <= 300);
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_body_markdown CHECK (char_length(body_markdown) <= 20000);
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_effective_to CHECK ((effective_to IS NULL OR effective_to > effective_from));
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_status CHECK (status IN ('draft', 'scheduled', 'published', 'superseded', 'withdrawn'));
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_supersedes_version_id CHECK ((supersedes_version_id IS NULL OR (supersedes_version_id <> notice_version_id)));
ALTER TABLE doc.notice_version ADD CONSTRAINT ck_notice_version_publish_at_scheduled CHECK ((status <> 'scheduled' OR publish_at IS NOT NULL));

-- DOC-06
ALTER TABLE doc.notice_audience ADD CONSTRAINT uq_notice_audience UNIQUE NULLS NOT DISTINCT (notice_version_id, audience_type, programme_id, batch_id, term_id, role_id, org_unit_id);
ALTER TABLE doc.notice_audience ADD CONSTRAINT ck_notice_audience_audience_type CHECK (audience_type IN ('all', 'programme', 'batch', 'term', 'role', 'org_unit', 'person'));
ALTER TABLE doc.notice_audience ADD CONSTRAINT ck_notice_audience_target_required CHECK ((audience_type = 'all' OR programme_id IS NOT NULL OR batch_id IS NOT NULL OR term_id IS NOT NULL OR role_id IS NOT NULL OR org_unit_id IS NOT NULL));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- DOC-04
ALTER TABLE doc.notice ADD CONSTRAINT fk_notice_issuing_org_unit_id FOREIGN KEY (issuing_org_unit_id) REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice ADD CONSTRAINT fk_notice_owner_person_id FOREIGN KEY (owner_person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- DOC-05
ALTER TABLE doc.notice_version ADD CONSTRAINT fk_notice_version_notice_id FOREIGN KEY (notice_id) REFERENCES doc.notice (notice_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_version ADD CONSTRAINT fk_notice_version_supersedes_version_id FOREIGN KEY (supersedes_version_id) REFERENCES doc.notice_version (notice_version_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_version ADD CONSTRAINT fk_notice_version_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_version ADD CONSTRAINT fk_notice_version_approved_by FOREIGN KEY (approved_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- DOC-06
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_notice_version_id FOREIGN KEY (notice_version_id) REFERENCES doc.notice_version (notice_version_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_programme_id FOREIGN KEY (programme_id) REFERENCES academic.programme (programme_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_batch_id FOREIGN KEY (batch_id) REFERENCES academic.batch (batch_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_term_id FOREIGN KEY (term_id) REFERENCES core.term (term_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_role_id FOREIGN KEY (role_id) REFERENCES iam.role (role_id) ON DELETE RESTRICT;
ALTER TABLE doc.notice_audience ADD CONSTRAINT fk_notice_audience_org_unit_id FOREIGN KEY (org_unit_id) REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- DOC-04
CREATE INDEX ix_notice_category_status ON doc.notice (category, status);
CREATE INDEX ix_notice_issuing_org_unit ON doc.notice (issuing_org_unit_id);
CREATE UNIQUE INDEX uq_notice_no_lower ON doc.notice (lower(notice_no));
CREATE INDEX ix_notice_owner_person_id ON doc.notice (owner_person_id);

-- DOC-05
CREATE INDEX ix_notice_version_notice_no ON doc.notice_version (notice_id, version_no DESC);
CREATE INDEX ix_notice_version_publish_status ON doc.notice_version (publish_at, status);
CREATE INDEX ix_notice_version_supersedes_version_id ON doc.notice_version (supersedes_version_id);
CREATE INDEX ix_notice_version_document_version_id ON doc.notice_version (document_version_id);
CREATE INDEX ix_notice_version_approved_by ON doc.notice_version (approved_by);

-- DOC-06
CREATE INDEX ix_notice_audience_version ON doc.notice_audience (notice_version_id);
CREATE INDEX ix_notice_audience_programme_batch ON doc.notice_audience (programme_id, batch_id);
CREATE INDEX ix_notice_audience_role ON doc.notice_audience (role_id);
CREATE INDEX ix_notice_audience_batch_id ON doc.notice_audience (batch_id);
CREATE INDEX ix_notice_audience_term_id ON doc.notice_audience (term_id);
CREATE INDEX ix_notice_audience_org_unit_id ON doc.notice_audience (org_unit_id);

-- ---------------------------------------------------------------------------
-- 5. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON doc.notice, doc.notice_version, doc.notice_audience FROM PUBLIC;

-- DOC-04 and DOC-05 are class P/I; DOC-06 is class I.
GRANT SELECT, INSERT, UPDATE ON
    doc.notice, doc.notice_version, doc.notice_audience
TO app_erp;

GRANT SELECT ON
    doc.notice, doc.notice_version, doc.notice_audience
TO app_cip;

-- ---------------------------------------------------------------------------
-- 6. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every doc table. No notice policy is
-- documented in POSTGRES_ARCHITECTURE 9.3; the audience-based intent in
-- ERD_KNOWLEDGE_CIP is not implementable until A-01 maps named roles and
-- G-19 confirms notice approval. Application access therefore remains
-- deny-by-default; only the owner role receives a policy.

ALTER TABLE doc.notice ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.notice FORCE ROW LEVEL SECURITY;
ALTER TABLE doc.notice_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.notice_version FORCE ROW LEVEL SECURITY;
ALTER TABLE doc.notice_audience ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc.notice_audience FORCE ROW LEVEL SECURITY;

CREATE POLICY p_notice_owner_all ON doc.notice
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);
CREATE POLICY p_notice_version_owner_all ON doc.notice_version
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);
CREATE POLICY p_notice_audience_owner_all ON doc.notice_audience
    FOR ALL TO owner_doc USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 7. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE doc.notice IS
    'DOC-04: logical notice identity. RLS is deny-by-default; the audience policy waits for A-01 and G-19.';

COMMENT ON TABLE doc.notice_version IS
    'DOC-05: a version can be scheduled only with publish_at. Automated approval/publishing is deferred under G-19.';

COMMENT ON TABLE doc.notice_audience IS
    'DOC-06: audience attaches to a version. The dictionary lists audience_type=person but has no person_id column; that target is unimplementable as written and is recorded in the final report.';