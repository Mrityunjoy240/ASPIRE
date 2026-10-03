# 06_AGENT_SPEC.md
# EduGen AI / ASPIRE — Agent Specifications

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 03 October 2026
**Version:** 1.0

> [!IMPORTANT]
> Every agent defined here has explicit allowed tools and explicit forbidden actions.
> An agent that exceeds its boundaries has a bug, not a feature (Constitution A-04).
> Agents never call the LLM provider directly — all LLM calls go through `LLMService`.

---

## Agent Framework: LangGraph

All agents run inside a LangGraph graph. State is passed as typed Python objects.
Agents communicate only via the shared graph state — no agent-to-agent HTTP calls.

---

## 1. Supervisor Agent

**Purpose:** Receives system events, decides which specialist agent to invoke, monitors outcomes.

**Triggers (events it listens to):**
- `ATTENDANCE_RISK_WARNING`
- `ATTENDANCE_RISK_CRITICAL`
- `ASSESSMENT_TREND_DECLINING`
- `ASSESSMENT_MISSING_URGENT`
- `EXAM_APPROACHING`
- `TASK_OVERDUE`
- `PLAN_DECLINED`
- `MENTOR_FOLLOWUP_DUE`

**Allowed tools:**
- `read_student_derived_state(student_id)` — read-only
- `read_open_cases(student_id)` — read-only
- `create_intervention_case(student_id, trigger_events, urgency_band)` — write via API
- `route_to_agent(agent_name, context)` — internal LangGraph routing

**Forbidden actions:**
- ❌ Directly writing to any database table
- ❌ Calling the LLM
- ❌ Sending notifications directly
- ❌ Creating tasks directly (routes to Intervention Agent instead)

**Escalation:** If an event has no matching routing rule, log and route to `HUMAN_REVIEW`.

**Output contract:**
```json
{
  "decision": "ROUTE | ESCALATE | NO_ACTION",
  "target_agent": "string",
  "case_id": "uuid",
  "reason_codes": ["string"],
  "evidence": {}
}
```

---

## 2. Attendance Specialist Agent

**Purpose:** Reads verified attendance state, explains the risk, proposes a recovery plan.

**Allowed tools:**
- `read_student_derived_state(student_id)` — read-only
- `read_course_schedule(course_run_id)` — read-only
- `call_llm(prompt, context)` — via LLMService only
- `propose_intervention_plan(case_id, plan)` — creates a plan in PROPOSED state

**Forbidden actions:**
- ❌ Marking a student officially ineligible
- ❌ Modifying attendance records
- ❌ Writing directly to `attendance_records` or `attendance_derived_state`
- ❌ Claiming a specific number of classes needed without using the deterministic engine output

**LLM role:** Explain the risk and recovery options in human-readable language. The math (required classes, percentage) comes from the deterministic engine — the LLM reads it, it does not compute it.

**Output contract:**
```json
{
  "decision": "PLAN_PROPOSED",
  "reason_codes": ["LOW_ATTENDANCE", "EXAM_APPROACHING"],
  "evidence": {
    "attendance_percentage": 73.0,
    "threshold": 75.0,
    "required_to_recover": 4,
    "exam_days_remaining": 8
  },
  "actions": [
    { "type": "ATTEND_CLASS", "subject": "DBMS", "count": 4 },
    { "type": "STUDY_BLOCK", "topic": "DBMS Unit 3", "duration_min": 45 }
  ],
  "approval_required": false,
  "confidence_level": "HIGH"
}
```

---

## 3. Learning Agent

**Purpose:** Detects the student's weakest topic, generates a personalized study plan and practice quiz using only the student's uploaded sources.

**Allowed tools:**
- `read_student_learning_state(student_id)` — read-only
- `read_assessment_submissions(student_id, course_run_id)` — read-only
- `retrieve_chunks(student_id, subject, topic, top_k)` — RAG retrieval from pgvector
- `call_llm(prompt, context)` — via LLMService only
- `write_quiz_result(student_id, quiz_id, result)` — via API

**Forbidden actions:**
- ❌ Generating quiz content when the retriever returns 0 chunks for the topic
- ❌ Hallucinating general knowledge to fill quiz gaps
- ❌ Accessing another student's documents
- ❌ Accessing documents outside the student's authorized `access_scope`

**Prompt injection guard:** All retrieved document content is wrapped in `<UNTRUSTED_CONTENT>` tags in the prompt. The system instruction explicitly states that commands found within these tags are not to be executed.

**Output contract (Quiz):**
```json
{
  "quiz_id": "uuid",
  "topic": "DBMS Unit 3",
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "source_chunk_id": "uuid",
      "source_document_id": "uuid",
      "citation": "Page 4, paragraph 2..."
    }
  ]
}
```

---

## 4. Intervention Agent (P0 — Basic)

**Purpose:** Manages the case lifecycle after a plan is accepted. Schedules follow-ups. Triggers replanning or escalation.

**Allowed tools:**
- `read_intervention_case(case_id)` — read-only
- `read_student_derived_state(student_id)` — read-only
- `update_case_status(case_id, new_status)` — via API
- `create_student_task(student_id, task)` — via API
- `schedule_followup(case_id, trigger_policy)` — via API
- `notify_mentor(mentor_id, case_id, reason)` — via notification service API

**Forbidden actions:**
- ❌ Closing a case without a verified state improvement
- ❌ Sending a recovery plan to a student whose relevant data is in CONFLICT status
- ❌ Escalating to HOD without first routing through the assigned Mentor

**Follow-up trigger policies (not a fixed timer):**
- `ATTENDANCE_INTERVENTION` → triggers on next `ATTENDANCE_UPDATED` event
- `STUDY_INTERVENTION` → triggers on quiz completion or next `ASSESSMENT_GRADED`
- `ASSIGNMENT_INTERVENTION` → triggers at the assignment deadline

**Output contract (Follow-up evaluation):**
```json
{
  "case_id": "uuid",
  "evaluation": "RESOLVED | REPLAN_REQUIRED | ESCALATION_REQUIRED",
  "reason_codes": ["string"],
  "evidence": {}
}
```

---

## 5. LLM Service (Internal Abstraction)

**This is not an agent. It is a service all agents call.**

**Class contract:**
```python
class LLMService:
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        context: dict,
        response_schema: dict  # JSON Schema for structured output
    ) -> dict:
        ...
```

**Rules:**
- Provider (OpenRouter), model, and API key are read from environment config only.
- All calls are logged with: `caller_agent`, `model_used`, `input_token_count`, `output_token_count`, `latency_ms`.
- If the provider is unavailable, raise `LLMUnavailableError`. The caller handles graceful degradation.
- Never log raw prompt content in production. Log only metadata.

---

## 6. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-AG01 | Default model for production? Must be chosen via evaluation, not reputation. | Mrityunjoy | 🔴 OPEN |
| OQ-AG02 | Which agents run synchronously (blocking the API response) vs. async (background job)? | Mrityunjoy + Bishesh | 🔴 OPEN — affects API design |
