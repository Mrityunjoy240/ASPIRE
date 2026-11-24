-- ===========================================================================
-- 0016_w6_cip.sql
-- W6 CIP conversations and evaluation
--
-- Generated from docs/architecture/database-design-v1/DATA_DICTIONARY.md.
-- Forward-only. Does not edit any applied migration.
-- ===========================================================================

SET client_min_messages = warning;

-- ---------------------------------------------------------------------------
-- 1. Tables
-- ---------------------------------------------------------------------------

-- CIP-01 cip.conversation
CREATE TABLE cip.conversation (
    conversation_id uuid NOT NULL DEFAULT gen_random_uuid(),
    person_id uuid,
    channel text NOT NULL DEFAULT 'web',
    language text,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    outcome text NOT NULL DEFAULT 'open',
    escalation_flag boolean NOT NULL DEFAULT FALSE,
    consent_recording boolean,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_conversation PRIMARY KEY (conversation_id)
);
ALTER TABLE cip.conversation OWNER TO owner_cip;

-- CIP-02 cip.call_session
CREATE TABLE cip.call_session (
    call_session_id uuid NOT NULL DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    provider text NOT NULL,
    provider_call_id text,
    direction text NOT NULL DEFAULT 'inbound',
    from_number_masked text,
    to_number_masked text,
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    duration_sec integer,
    recording_uri text,
    recording_consent boolean NOT NULL DEFAULT FALSE,
    status text NOT NULL DEFAULT 'ringing',
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_call_session PRIMARY KEY (call_session_id)
);
ALTER TABLE cip.call_session OWNER TO owner_cip;

-- CIP-03 cip.message
CREATE TABLE cip.message (
    message_id uuid NOT NULL DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    role text NOT NULL,
    content_text text,
    content_redacted text,
    language text,
    intent_code text,
    confidence numeric(4,3),
    model_name text,
    model_version text,
    latency_ms integer,
    token_count integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_message PRIMARY KEY (message_id)
);
ALTER TABLE cip.message OWNER TO owner_cip;

-- CIP-04 cip.retrieval_log
CREATE TABLE cip.retrieval_log (
    retrieval_log_id uuid NOT NULL DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL,
    query_text text NOT NULL,
    normalized_query text,
    strategy text NOT NULL DEFAULT 'hybrid',
    filters_json jsonb DEFAULT '{}',
    top_k integer NOT NULL DEFAULT 5,
    latency_ms integer,
    result_count integer NOT NULL DEFAULT 0,
    fallback_used boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_retrieval_log PRIMARY KEY (retrieval_log_id)
);
ALTER TABLE cip.retrieval_log OWNER TO owner_cip;

-- CIP-05 cip.retrieval_hit
CREATE TABLE cip.retrieval_hit (
    retrieval_hit_id uuid NOT NULL DEFAULT gen_random_uuid(),
    retrieval_log_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    rank integer NOT NULL,
    vector_score numeric(8,6),
    lexical_score numeric(8,6),
    rerank_score numeric(8,6),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_retrieval_hit PRIMARY KEY (retrieval_hit_id)
);
ALTER TABLE cip.retrieval_hit OWNER TO owner_cip;

-- CIP-06 cip.citation
CREATE TABLE cip.citation (
    citation_id uuid NOT NULL DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL,
    chunk_id uuid,
    document_version_id uuid,
    page_from integer,
    page_to integer,
    quote text,
    confidence numeric(4,3),
    displayed boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_citation PRIMARY KEY (citation_id)
);
ALTER TABLE cip.citation OWNER TO owner_cip;

-- CIP-07 cip.feedback
CREATE TABLE cip.feedback (
    feedback_id uuid NOT NULL DEFAULT gen_random_uuid(),
    message_id uuid NOT NULL,
    person_id uuid,
    rating text NOT NULL,
    reason_code text,
    comment text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_feedback PRIMARY KEY (feedback_id)
);
ALTER TABLE cip.feedback OWNER TO owner_cip;

-- CIP-08 cip.escalation
CREATE TABLE cip.escalation (
    escalation_id uuid NOT NULL DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    message_id uuid,
    assigned_org_unit_id uuid,
    reason_code text NOT NULL,
    status text NOT NULL DEFAULT 'open',
    created_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    resolution_note text,
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_escalation PRIMARY KEY (escalation_id)
);
ALTER TABLE cip.escalation OWNER TO owner_cip;

-- CIP-09 cip.eval_case
CREATE TABLE cip.eval_case (
    eval_case_id uuid NOT NULL DEFAULT gen_random_uuid(),
    case_code text NOT NULL,
    category text NOT NULL DEFAULT 'golden',
    question text NOT NULL,
    expected_answer text,
    expected_citation text,
    language text NOT NULL DEFAULT 'en',
    is_active boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid,
    row_version integer NOT NULL DEFAULT 1,
    CONSTRAINT pk_eval_case PRIMARY KEY (eval_case_id)
);
ALTER TABLE cip.eval_case OWNER TO owner_cip;

-- CIP-10 cip.eval_run
CREATE TABLE cip.eval_run (
    eval_run_id uuid NOT NULL DEFAULT gen_random_uuid(),
    created_by uuid,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    corpus_version text,
    model_name text,
    status text NOT NULL DEFAULT 'running',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_eval_run PRIMARY KEY (eval_run_id)
);
ALTER TABLE cip.eval_run OWNER TO owner_cip;

-- CIP-11 cip.eval_result
CREATE TABLE cip.eval_result (
    eval_result_id uuid NOT NULL DEFAULT gen_random_uuid(),
    eval_run_id uuid NOT NULL,
    eval_case_id uuid NOT NULL,
    actual_answer text,
    citation_correct boolean,
    answer_correct boolean,
    latency_ms integer,
    pass boolean NOT NULL DEFAULT FALSE,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid,
    CONSTRAINT pk_eval_result PRIMARY KEY (eval_result_id)
);
ALTER TABLE cip.eval_result OWNER TO owner_cip;

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------

-- CIP-01
ALTER TABLE cip.conversation ADD CONSTRAINT ck_conversation_channel CHECK (channel IN ('web', 'voice', 'whatsapp', 'api', 'kiosk'));
ALTER TABLE cip.conversation ADD CONSTRAINT ck_conversation_language CHECK ((language IS NULL OR (language IN ('en', 'bn', 'hi', 'mixed'))));
ALTER TABLE cip.conversation ADD CONSTRAINT ck_conversation_ended_at CHECK ((ended_at IS NULL OR ended_at >= started_at));
ALTER TABLE cip.conversation ADD CONSTRAINT ck_conversation_outcome CHECK (outcome IN ('resolved', 'escalated', 'abandoned', 'open'));

-- CIP-02
ALTER TABLE cip.call_session ADD CONSTRAINT uq_call_session_provider UNIQUE (provider, provider_call_id);
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_provider CHECK (char_length(provider) <= 50);
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_direction CHECK (direction IN ('inbound', 'outbound'));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_from_number_masked CHECK ((from_number_masked IS NULL OR (char_length(from_number_masked) <= 20)));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_to_number_masked CHECK ((to_number_masked IS NULL OR (char_length(to_number_masked) <= 20)));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_ended_at CHECK ((ended_at IS NULL OR ended_at >= started_at));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_duration_sec CHECK ((duration_sec IS NULL OR (duration_sec >= 0)));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_recording_uri CHECK ((recording_uri IS NULL OR (recording_uri ~ '^[A-Za-z][A-Za-z0-9+.-]*://')));
ALTER TABLE cip.call_session ADD CONSTRAINT ck_call_session_status CHECK (status IN ('ringing', 'in_progress', 'completed', 'failed', 'no_answer'));

-- CIP-03
ALTER TABLE cip.message ADD CONSTRAINT uq_message_conversation_seq UNIQUE (conversation_id, sequence_no);
ALTER TABLE cip.message ADD CONSTRAINT ck_message_sequence_no CHECK (sequence_no >= 1);
ALTER TABLE cip.message ADD CONSTRAINT ck_message_role CHECK (role IN ('user', 'assistant', 'system', 'tool'));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_language CHECK ((language IS NULL OR (language IN ('en', 'bn', 'hi', 'mixed'))));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_intent_code CHECK ((intent_code IS NULL OR (char_length(intent_code) <= 50)));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_confidence CHECK ((confidence IS NULL OR confidence BETWEEN 0 AND 1));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_model_name CHECK ((model_name IS NULL OR (char_length(model_name) <= 100)));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_model_version CHECK ((model_version IS NULL OR (char_length(model_version) <= 50)));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_latency_ms CHECK ((latency_ms IS NULL OR (latency_ms >= 0)));
ALTER TABLE cip.message ADD CONSTRAINT ck_message_token_count CHECK ((token_count IS NULL OR (token_count >= 0)));

-- CIP-04
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_query_text CHECK (char_length(query_text) <= 2000);
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_normalized_query CHECK ((normalized_query IS NULL OR (char_length(normalized_query) <= 2000)));
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_strategy CHECK (strategy IN ('vector', 'lexical', 'hybrid', 'structured_api', 'none'));
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_top_k CHECK (top_k > 0);
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_latency_ms CHECK ((latency_ms IS NULL OR (latency_ms >= 0)));
ALTER TABLE cip.retrieval_log ADD CONSTRAINT ck_retrieval_log_result_count CHECK (result_count >= 0);

-- CIP-05
ALTER TABLE cip.retrieval_hit ADD CONSTRAINT uq_retrieval_hit_rank UNIQUE (retrieval_log_id, rank);
ALTER TABLE cip.retrieval_hit ADD CONSTRAINT ck_retrieval_hit_rank CHECK (rank >= 1);

-- CIP-06
ALTER TABLE cip.citation ADD CONSTRAINT uq_citation_message_chunk_pages UNIQUE NULLS NOT DISTINCT (message_id, chunk_id, page_from, page_to);
ALTER TABLE cip.citation ADD CONSTRAINT ck_citation_page_from CHECK ((page_from IS NULL OR (page_from >= 1)));
ALTER TABLE cip.citation ADD CONSTRAINT ck_citation_page_to CHECK ((page_to IS NULL OR page_to >= page_from));
ALTER TABLE cip.citation ADD CONSTRAINT ck_citation_quote CHECK ((quote IS NULL OR (char_length(quote) <= 2000)));
ALTER TABLE cip.citation ADD CONSTRAINT ck_citation_confidence CHECK ((confidence IS NULL OR confidence BETWEEN 0 AND 1));

-- CIP-07
ALTER TABLE cip.feedback ADD CONSTRAINT ck_feedback_rating CHECK (rating IN ('up', 'down', '1', '2', '3', '4', '5'));
ALTER TABLE cip.feedback ADD CONSTRAINT ck_feedback_reason_code CHECK ((reason_code IS NULL OR (char_length(reason_code) <= 50)));
ALTER TABLE cip.feedback ADD CONSTRAINT ck_feedback_comment CHECK ((comment IS NULL OR (char_length(comment) <= 2000)));

-- CIP-08
ALTER TABLE cip.escalation ADD CONSTRAINT ck_escalation_reason_code CHECK (char_length(reason_code) <= 50);
ALTER TABLE cip.escalation ADD CONSTRAINT ck_escalation_status CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved', 'closed', 'rejected'));
ALTER TABLE cip.escalation ADD CONSTRAINT ck_escalation_resolved_at CHECK ((resolved_at IS NULL OR resolved_at >= created_at));
ALTER TABLE cip.escalation ADD CONSTRAINT ck_escalation_resolution_note CHECK ((resolution_note IS NULL OR (char_length(resolution_note) <= 2000)));

-- CIP-09
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_case_code CHECK (char_length(case_code) <= 50);
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_category CHECK (category IN ('golden', 'negative', 'conflict', 'version', 'personal', 'language', 'access', 'latency'));
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_question CHECK (char_length(question) <= 2000);
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_expected_citation CHECK ((expected_citation IS NULL OR (char_length(expected_citation) <= 500)));
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_language CHECK (language IN ('en', 'bn', 'hi', 'mixed'));
ALTER TABLE cip.eval_case ADD CONSTRAINT ck_eval_case_question_not_empty CHECK (char_length(question) > 0);

-- CIP-10
ALTER TABLE cip.eval_run ADD CONSTRAINT ck_eval_run_finished_at CHECK ((finished_at IS NULL OR finished_at >= started_at));
ALTER TABLE cip.eval_run ADD CONSTRAINT ck_eval_run_corpus_version CHECK ((corpus_version IS NULL OR (char_length(corpus_version) <= 50)));
ALTER TABLE cip.eval_run ADD CONSTRAINT ck_eval_run_model_name CHECK ((model_name IS NULL OR (char_length(model_name) <= 100)));
ALTER TABLE cip.eval_run ADD CONSTRAINT ck_eval_run_status CHECK (status IN ('running', 'completed', 'failed', 'aborted'));

-- CIP-11
ALTER TABLE cip.eval_result ADD CONSTRAINT uq_eval_result_run_case UNIQUE (eval_run_id, eval_case_id);
ALTER TABLE cip.eval_result ADD CONSTRAINT ck_eval_result_latency_ms CHECK ((latency_ms IS NULL OR (latency_ms >= 0)));
ALTER TABLE cip.eval_result ADD CONSTRAINT ck_eval_result_notes CHECK ((notes IS NULL OR (char_length(notes) <= 2000)));

-- ---------------------------------------------------------------------------
-- 3. Foreign keys
-- ---------------------------------------------------------------------------

-- CIP-01
ALTER TABLE cip.conversation ADD CONSTRAINT fk_conversation_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- CIP-02
ALTER TABLE cip.call_session ADD CONSTRAINT fk_call_session_conversation_id FOREIGN KEY (conversation_id) REFERENCES cip.conversation (conversation_id) ON DELETE RESTRICT;

-- CIP-03
ALTER TABLE cip.message ADD CONSTRAINT fk_message_conversation_id FOREIGN KEY (conversation_id) REFERENCES cip.conversation (conversation_id) ON DELETE RESTRICT;

-- CIP-04
ALTER TABLE cip.retrieval_log ADD CONSTRAINT fk_retrieval_log_message_id FOREIGN KEY (message_id) REFERENCES cip.message (message_id) ON DELETE RESTRICT;

-- CIP-05
ALTER TABLE cip.retrieval_hit ADD CONSTRAINT fk_retrieval_hit_retrieval_log_id FOREIGN KEY (retrieval_log_id) REFERENCES cip.retrieval_log (retrieval_log_id) ON DELETE RESTRICT;
ALTER TABLE cip.retrieval_hit ADD CONSTRAINT fk_retrieval_hit_chunk_id FOREIGN KEY (chunk_id) REFERENCES knowledge.document_chunk (chunk_id) ON DELETE RESTRICT;

-- CIP-06
ALTER TABLE cip.citation ADD CONSTRAINT fk_citation_message_id FOREIGN KEY (message_id) REFERENCES cip.message (message_id) ON DELETE RESTRICT;
ALTER TABLE cip.citation ADD CONSTRAINT fk_citation_chunk_id FOREIGN KEY (chunk_id) REFERENCES knowledge.document_chunk (chunk_id) ON DELETE RESTRICT;
ALTER TABLE cip.citation ADD CONSTRAINT fk_citation_document_version_id FOREIGN KEY (document_version_id) REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT;

-- CIP-07
ALTER TABLE cip.feedback ADD CONSTRAINT fk_feedback_message_id FOREIGN KEY (message_id) REFERENCES cip.message (message_id) ON DELETE RESTRICT;
ALTER TABLE cip.feedback ADD CONSTRAINT fk_feedback_person_id FOREIGN KEY (person_id) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- CIP-08
ALTER TABLE cip.escalation ADD CONSTRAINT fk_escalation_conversation_id FOREIGN KEY (conversation_id) REFERENCES cip.conversation (conversation_id) ON DELETE RESTRICT;
ALTER TABLE cip.escalation ADD CONSTRAINT fk_escalation_message_id FOREIGN KEY (message_id) REFERENCES cip.message (message_id) ON DELETE RESTRICT;
ALTER TABLE cip.escalation ADD CONSTRAINT fk_escalation_assigned_org_unit_id FOREIGN KEY (assigned_org_unit_id) REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT;

-- CIP-10
ALTER TABLE cip.eval_run ADD CONSTRAINT fk_eval_run_created_by FOREIGN KEY (created_by) REFERENCES iam.person (person_id) ON DELETE RESTRICT;

-- CIP-11
ALTER TABLE cip.eval_result ADD CONSTRAINT fk_eval_result_eval_run_id FOREIGN KEY (eval_run_id) REFERENCES cip.eval_run (eval_run_id) ON DELETE RESTRICT;
ALTER TABLE cip.eval_result ADD CONSTRAINT fk_eval_result_eval_case_id FOREIGN KEY (eval_case_id) REFERENCES cip.eval_case (eval_case_id) ON DELETE RESTRICT;

-- ---------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------

-- CIP-01
CREATE INDEX ix_conversation_person_started ON cip.conversation (person_id, started_at DESC);
CREATE INDEX ix_conversation_channel_started ON cip.conversation (channel, started_at);

-- CIP-02
CREATE INDEX ix_call_session_conversation ON cip.call_session (conversation_id);
CREATE INDEX ix_call_session_started ON cip.call_session (started_at DESC);

-- CIP-03
CREATE INDEX ix_message_conversation_seq ON cip.message (conversation_id, sequence_no);
CREATE INDEX ix_message_intent ON cip.message (intent_code);

-- CIP-04
CREATE INDEX ix_retrieval_log_message ON cip.retrieval_log (message_id);
CREATE INDEX ix_retrieval_log_created ON cip.retrieval_log (created_at DESC);
CREATE INDEX ix_retrieval_log_strategy ON cip.retrieval_log (strategy);

-- CIP-05
CREATE INDEX ix_retrieval_hit_log_rank ON cip.retrieval_hit (retrieval_log_id, rank);
CREATE INDEX ix_retrieval_hit_chunk ON cip.retrieval_hit (chunk_id);

-- CIP-06
CREATE INDEX ix_citation_message ON cip.citation (message_id);
CREATE INDEX ix_citation_document_version ON cip.citation (document_version_id);
CREATE INDEX ix_citation_chunk_id ON cip.citation (chunk_id);

-- CIP-07
CREATE INDEX ix_feedback_message ON cip.feedback (message_id);
CREATE INDEX ix_feedback_rating_created ON cip.feedback (rating, created_at);
CREATE UNIQUE INDEX uq_feedback_message_person ON cip.feedback (message_id, person_id) WHERE person_id IS NOT NULL;
CREATE INDEX ix_feedback_person_id ON cip.feedback (person_id);

-- CIP-08
CREATE INDEX ix_escalation_status_created ON cip.escalation (status, created_at);
CREATE INDEX ix_escalation_org_unit ON cip.escalation (assigned_org_unit_id);
CREATE INDEX ix_escalation_conversation_id ON cip.escalation (conversation_id);
CREATE INDEX ix_escalation_message_id ON cip.escalation (message_id);

-- CIP-09
CREATE INDEX ix_eval_case_category_active ON cip.eval_case (category, is_active);
CREATE UNIQUE INDEX uq_eval_case_code_lower ON cip.eval_case (lower(case_code));

-- CIP-10
CREATE INDEX ix_eval_run_started ON cip.eval_run (started_at DESC);
CREATE INDEX ix_eval_run_created_by ON cip.eval_run (created_by);

-- CIP-11
CREATE INDEX ix_eval_result_run_pass ON cip.eval_result (eval_run_id, pass);
CREATE INDEX ix_eval_result_case ON cip.eval_result (eval_case_id);

-- ---------------------------------------------------------------------------
-- 5. Append-only seals (POSTGRES_ARCHITECTURE 10.2)
-- ---------------------------------------------------------------------------

CREATE TRIGGER trg_message_append_only
    BEFORE UPDATE OR DELETE ON cip.message
    FOR EACH ROW
    EXECUTE FUNCTION ops.reject_mutation();

CREATE TRIGGER trg_retrieval_log_append_only
    BEFORE UPDATE OR DELETE ON cip.retrieval_log
    FOR EACH ROW
    EXECUTE FUNCTION ops.reject_mutation();

CREATE TRIGGER trg_retrieval_hit_append_only
    BEFORE UPDATE OR DELETE ON cip.retrieval_hit
    FOR EACH ROW
    EXECUTE FUNCTION ops.reject_mutation();

CREATE TRIGGER trg_citation_append_only
    BEFORE UPDATE OR DELETE ON cip.citation
    FOR EACH ROW
    EXECUTE FUNCTION ops.reject_mutation();

-- ---------------------------------------------------------------------------
-- 6. Grants
-- ---------------------------------------------------------------------------

REVOKE ALL ON ALL TABLES IN SCHEMA cip FROM PUBLIC;

-- POSTGRES_ARCHITECTURE 3.1: app_cip writes cip. No role receives DELETE.
GRANT SELECT, INSERT, UPDATE ON
    cip.conversation, cip.call_session, cip.message, cip.retrieval_log,
    cip.retrieval_hit, cip.citation, cip.feedback, cip.escalation,
    cip.eval_case, cip.eval_run, cip.eval_result
TO app_cip;

-- ---------------------------------------------------------------------------
-- 7. Row-level security
-- ---------------------------------------------------------------------------
-- DATA_DICTIONARY 1.6 requires RLS on every cip table. The only documented
-- 9.3 intent is conversation: a person sees their own. The operator and
-- auditor arms wait for A-01; every other table is deny-by-default.

ALTER TABLE cip.conversation ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.conversation FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.call_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.call_session FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.message ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.message FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.retrieval_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.retrieval_log FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.retrieval_hit ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.retrieval_hit FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.citation ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.citation FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.feedback FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.escalation ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.escalation FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_case ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_case FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_run FORCE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_result ENABLE ROW LEVEL SECURITY;
ALTER TABLE cip.eval_result FORCE ROW LEVEL SECURITY;

CREATE POLICY p_conversation_owner_all ON cip.conversation
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_call_session_owner_all ON cip.call_session
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_message_owner_all ON cip.message
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_retrieval_log_owner_all ON cip.retrieval_log
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_retrieval_hit_owner_all ON cip.retrieval_hit
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_citation_owner_all ON cip.citation
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_feedback_owner_all ON cip.feedback
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_escalation_owner_all ON cip.escalation
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_eval_case_owner_all ON cip.eval_case
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_eval_run_owner_all ON cip.eval_run
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);
CREATE POLICY p_eval_result_owner_all ON cip.eval_result
    FOR ALL TO owner_cip USING (true) WITH CHECK (true);

-- POSTGRES_ARCHITECTURE 9.3: a person sees their own conversation. The
-- operator and auditor arms wait for A-01; anonymous rows have no owner.
CREATE POLICY p_conversation_person_select ON cip.conversation
    FOR SELECT TO app_cip
    USING (person_id = (SELECT iam.current_person_id()));

-- ---------------------------------------------------------------------------
-- 8. Recorded design interpretations and deferred contracts
-- ---------------------------------------------------------------------------

COMMENT ON TABLE cip.conversation IS
    'CIP-01: person-own read policy only; the operator and auditor arms wait for A-01. Anonymous rows (person_id null) are visible to no application role, and writes are deny-by-default.';

COMMENT ON TABLE cip.call_session IS
    'CIP-02: class R telephony metadata. No documented 9.3 arm; deny-by-default for application roles until A-01.';

COMMENT ON TABLE cip.message IS
    'CIP-03: append-only conversation turn; content_text is class R. trg_message_append_only rejects update and delete. No application policy is documented.';

COMMENT ON TABLE cip.retrieval_log IS
    'CIP-04: append-only retrieval trace; trg_retrieval_log_append_only rejects update and delete.';

COMMENT ON TABLE cip.retrieval_hit IS
    'CIP-05: append-only ranked hit; unique (retrieval_log_id, rank).';

COMMENT ON TABLE cip.citation IS
    'CIP-06: append-only displayed source. uq_citation_message_chunk_pages uses NULLS NOT DISTINCT so a citation with null chunk/page columns cannot be duplicated.';

COMMENT ON TABLE cip.feedback IS
    'CIP-07: one rating per person per message (partial unique index); anonymous ratings are allowed. Not sealed because POSTGRES_ARCHITECTURE 10.2 does not list it.';

COMMENT ON TABLE cip.escalation IS
    'CIP-08: mutable handoff case; resolved_at cannot precede created_at. No named-role/escalation policy is documented; deny-by-default.';

COMMENT ON TABLE cip.eval_case IS
    'CIP-09: case_code is unique case-insensitively and question cannot be empty.';

COMMENT ON TABLE cip.eval_run IS
    'CIP-10: a run is mutable while it progresses; POSTGRES_ARCHITECTURE 10.2 does not seal it.';

COMMENT ON TABLE cip.eval_result IS
    'CIP-11: one result per case per run.';

COMMENT ON POLICY p_conversation_person_select ON cip.conversation IS
    'POSTGRES_ARCHITECTURE 9.3: person sees own conversation only. Operator and auditor arms, anonymous visibility, and writes wait for A-01.';