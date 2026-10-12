-- 014_llm_attempt_audit.sql
-- Per-attempt LLM gateway audit metadata (06 §5, 07 §4, DM-LLM01).
-- Metadata only: never raw prompt content, never student PII.
-- Lifecycle: one durable row per actual dispatch attempt. The row is
-- committed with outcome IN_PROGRESS BEFORE the provider is called (no
-- dispatch without it), then updated to the terminal outcome AFTER the
-- attempt (no result consumed without it). If the terminal update never
-- commits, the IN_PROGRESS row remains discoverable — it means the attempt
-- was initiated and its terminal outcome is not durably known; it is never
-- treated as success. No automatic retries are made to recover audit writes.
-- LIVE: every HTTP attempt incl. the bounded retry gets its own row.
-- MOCK: one row per complete() call.
-- DM-NEW-ORM01: Migration files are the ONLY schema authority.

CREATE TABLE llm_attempt_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- client-generated uuid4 per attempt row
    request_id UUID NOT NULL,          -- one id per LLMService.complete() call; attempt rows share it
    caller_agent TEXT NOT NULL,        -- e.g., 'attendance_specialist'
    prompt_version TEXT,               -- caller-supplied; NULL when the caller has no version
    response_schema_version TEXT,      -- response model class name; NULL for unstructured replies
    provider TEXT NOT NULL,            -- openrouter | mock
    model TEXT NOT NULL,               -- configured model; 'mock-fixture' in MOCK (no model invoked)
    attempt INT NOT NULL,              -- 1-based attempt within the request (1..2 with one bounded retry)
    outcome TEXT NOT NULL,             -- IN_PROGRESS (pre-dispatch row; terminal outcome unknown) |
                                       --   SUCCESS | SCHEMA_REJECTED | PROVIDER_FAILURE | RETRY_EXHAUSTED
    failure_reason TEXT,               -- timeout | rate_limit | http_error | network_error |
                                       --   invalid_structured_output; NULL on success and while IN_PROGRESS
    latency_ms INT NOT NULL,           -- per-attempt wall time; 0 while IN_PROGRESS (unknown until finished)
    input_token_count INT,             -- provider usage.prompt_tokens; NULL when unreported (MOCK: always NULL)
    output_token_count INT,            -- provider usage.completion_tokens; NULL likewise
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- attempt initiation time (set at begin, never rewritten)
);

CREATE INDEX idx_llm_attempt_audit_request ON llm_attempt_audit(request_id);
CREATE INDEX idx_llm_attempt_audit_outcome ON llm_attempt_audit(outcome);
CREATE INDEX idx_llm_attempt_audit_created_at ON llm_attempt_audit(created_at);
