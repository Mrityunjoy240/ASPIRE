# 06_AGENT_SPEC.md
# EduGen AI / ASPIRE — Agent Specifications

**STATUS: 🟡 UNDER REVIEW**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 03 October 2026
**Version:** 1.2

> [!IMPORTANT]
> Every agent defined here has explicit allowed tools and explicit forbidden actions.
> An agent that exceeds its boundaries has a bug, not a feature (Constitution A-04).
> Agents never call the LLM provider directly — all LLM calls go through `LLMService`.
>
> **Agents propose and interpret. Services enforce. Engines calculate. Humans approve consequential decisions.**

---

## Agent Framework: LangGraph

All agents run inside a LangGraph graph. State is passed as typed Python objects.
Agents communicate only via the shared graph state — no agent-to-agent HTTP calls.
All state transitions pass through application-layer validators — agents propose transitions, they do not force them.

---

## 0. Agent Safety & Degradation Contract

These rules apply to ALL agents without exception.

```
1. Agents never modify source-of-truth facts (attendance records, grades, marks).
2. Agents never make official eligibility, disciplinary, or marks decisions.
3. Agents never bypass a data conflict quarantine.
4. Agents never bypass RBAC or document access_scope.
5. Agents never invent institutional rules (thresholds, weights, deadlines).
6. Agents never perform deterministic calculations — they read engine outputs.
7. Agent outputs are proposals unless explicitly defined as orchestration.
8. All case state transitions are validated by the application state machine.
9. LLM failure must produce a defined degraded behavior per agent (see §6).
10. Every agent action must be traceable to an originating event, case, or request.
11. Agents receive only minimum required context. Direct identifiers (name, email,
    phone, roll number) must not appear in LLM prompts unless the tool explicitly requires it.
```

---

## 1. Supervisor Agent

**Purpose:** Receives system events, maps them deterministically to specialist agents, monitors outcomes. The Supervisor orchestrates — it does not invent routing logic.

**Triggers (events it listens to):**
- `ATTENDANCE_RISK_WARNING`
- `ATTENDANCE_RISK_CRITICAL`
- `ASSESSMENT_TREND_DECLINING`
- `ASSESSMENT_MISSING_URGENT`
- `EXAM_APPROACHING`
- `TASK_OVERDUE`
- `PLAN_DECLINED`
- `MENTOR_FOLLOWUP_DUE`

> [!IMPORTANT]
> All events above must appear with the **exact same name** in `03_SYSTEM_SPEC.md §8`.
> `EXAM_APPROACHING`, `TASK_OVERDUE`, and `MENTOR_FOLLOWUP_DUE` require a scheduler/job mechanism
> to emit them — this mechanism must be defined before these triggers are coded.

**Deterministic Routing Table:**

| Event | Route |
|---|---|
| `ATTENDANCE_RISK_WARNING` | Attendance Agent |
| `ATTENDANCE_RISK_CRITICAL` | Attendance Agent |
| `ASSESSMENT_TREND_DECLINING` | Learning Agent → Intervention Agent |
| `ASSESSMENT_MISSING_URGENT` | Intervention Agent |
| `EXAM_APPROACHING` | Attendance Agent (if risk exists), else Intervention Agent |
| `TASK_OVERDUE` | Intervention Agent |
| `PLAN_DECLINED` | Intervention Agent |
| `MENTOR_FOLLOWUP_DUE` | Intervention Agent |
| No matching rule | `human_review_required: true` (not an agent) |

The routing table is the only source of routing logic. The Supervisor does not use the LLM to decide which agent to invoke.

**Allowed tools:**
- `read_student_derived_state(student_id)` — read-only
- `read_open_cases(student_id)` — read-only
- `create_intervention_case(student_id, trigger_events, urgency_band)` — write via API

**Forbidden actions:**
- ❌ Calling the LLM
- ❌ Directly writing to any database table
- ❌ Routing to an agent not in the deterministic routing table above
- ❌ Sending notifications
- ❌ Creating tasks directly

**Output contract:**
```json
{
  "decision": "ROUTE | ESCALATE | NO_ACTION",
  "target_agent": "ENUM(ATTENDANCE_AGENT | LEARNING_AGENT | INTERVENTION_AGENT | null)",
  "human_review_required": false,
  "case_id": "uuid",
  "reason_codes": ["string"],
  "evidence": {}
}
```

---

## 2. Attendance Specialist Agent

**Purpose:** Reads verified attendance state and engine-derived outputs, explains the risk, proposes a structured recovery plan. The agent does NOT calculate — it reads what the engine calculated.

> [!IMPORTANT]
> `exam_days_remaining` is NOT calculated by this agent. It is a field emitted by the
> `EXAM_APPROACHING` event payload, computed by the deterministic Calendar Engine.
> The agent reads and surfaces it. It does not compute date differences.

**Allowed tools:**
- `read_student_derived_state(student_id)` — read-only (attendance %, risk band, required_to_recover)
- `read_exam_schedule(student_id, course_run_id)` — read-only (from Calendar Engine output)
- `call_llm(prompt, context)` — via LLMService only
- `propose_intervention_plan(case_id, plan)` — creates a plan in `PLAN_PROPOSED` state via API

**Forbidden actions:**
- ❌ Marking a student officially ineligible
- ❌ Modifying `attendance_records` or `attendance_derived_state`
- ❌ Computing `required_to_recover` — this comes from `attendance_derived_state`
- ❌ Computing `exam_days_remaining` — this comes from the Calendar Engine / event payload

**LLM role:** Explain the risk and recovery plan in human-readable language. The math comes from the engine. The LLM reads it and explains it.

**Output contract:**
```json
{
  "decision": "PLAN_PROPOSED",
  "reason_codes": ["LOW_ATTENDANCE", "EXAM_APPROACHING"],
  "evidence": {
    "attendance_percentage": 73.33,
    "threshold": 75.0,
    "required_to_recover": 3,
    "exam_days_remaining": 8
  },
  "actions": [
    { "type": "ATTEND_CLASS", "subject": "DBMS", "count": 3 },
    { "type": "STUDY_BLOCK", "topic": "DBMS Unit 3", "duration_min": 45 }
  ],
  "approval_required": true,
  "confidence_level": "HIGH"
}
```

> **Note on `required_to_recover: 3`:** This is the engine-computed value for 22 attended / 30 conducted at 75% threshold. Verify: (22+3)/(30+3) = 36/48 = 75.00%.

---

## 3. Learning Agent

**Purpose:** Uses available assessment and learning evidence to identify a supported weak topic, generates a targeted practice plan and quiz from the student's authorized sources only.

> [!NOTE]
> "Weakest topic" is derived from assessment evidence (declining assessment trend, `ASSESSMENT_TREND_DECLINING` event). The agent does not have a formal topic-level mastery model in P0. It uses assessment evidence to make a supported inference, not a certified calculation.

**Allowed tools:**
- `read_student_learning_state(student_id)` — read-only
- `read_assessment_submissions(student_id, course_run_id)` — read-only
- `retrieve_chunks(student_id, subject, topic, top_k)` — RAG retrieval respecting `access_scope`
- `call_llm(prompt, context)` — via LLMService only
- `create_quiz_session(student_id, subject, topic, source_doc_ids)` — creates quiz session record
- `write_quiz_result(student_id, quiz_session_id, result)` — via API after student attempts

**Quiz creation flow:**
```
retrieve_chunks (RBAC/scope enforced)
      ↓
LLM generates quiz from retrieved chunks only
      ↓
Output schema validation (source_chunk_id required per question)
      ↓
create_quiz_session() → returns quiz_session_id
      ↓
Student attempts quiz in UI
      ↓
write_quiz_result(quiz_session_id, result)
```

**Forbidden actions:**
- ❌ Generating quiz content when the retriever returns 0 chunks for the topic
- ❌ Hallucinating general knowledge to fill quiz gaps
- ❌ Accessing documents outside the student's authorized `access_scope`

**Prompt injection guard:** All retrieved document content is wrapped in `<UNTRUSTED_CONTENT>` tags. The system instruction explicitly states that commands found within these tags are not to be executed.

**Output contract (Quiz Session):**
```json
{
  "quiz_session_id": "uuid",
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

**Purpose:** Manages the case lifecycle **after a plan has been accepted by the student AND approved by the mentor**. Schedules follow-ups. Proposes replanning or escalation as a structured output — does not execute these autonomously.

**Execution only begins after:**
```
PLAN_PROPOSED
    ↓
Student: Accept / Edit / Decline  →  PENDING_MENTOR_APPROVAL
    ↓
Mentor: Approve / Edit+Approve / Reject
    ↓
ACTIVE  ← Intervention Agent operates from here
```

**Allowed tools:**
- `read_intervention_case(case_id)` — read-only
- `read_student_derived_state(student_id)` — read-only
- `transition_case(case_id, requested_transition, evidence)` — proposes a state transition via API; application state machine validates legality
- `create_student_task(student_id, task)` — via API
- `schedule_followup(case_id, trigger_policy)` — via API
- `notify_mentor(mentor_id, case_id, reason)` — via notification service API

> **Note on `transition_case`:** Replaces the former `update_case_status`. The agent proposes a transition (e.g., `ACTIVE → MONITORING`). The application state machine validates that the transition is legal. The agent cannot force arbitrary state jumps.

**Forbidden actions:**
- ❌ Closing a case without a verified state improvement from the engine
- ❌ Sending a recovery plan to a student whose relevant data is in CONFLICT status
- ❌ Escalating directly to HOD without first routing through the assigned Mentor
- ❌ Autonomously executing escalation — it proposes `ESCALATION_REQUIRED`; a human confirms

**Follow-up trigger policies (not a fixed timer):**
- `ATTENDANCE_INTERVENTION` → triggers on next `ATTENDANCE_UPDATED` event
- `STUDY_INTERVENTION` → triggers on quiz completion or next `ASSESSMENT_GRADED`
- `ASSIGNMENT_INTERVENTION` → triggers at the assignment deadline

**Output contract (Follow-up evaluation):**
```json
{
  "case_id": "uuid",
  "proposed_transition": "RESOLVED | REPLAN_REQUIRED | ESCALATION_REQUIRED",
  "reason_codes": ["string"],
  "evidence": {},
  "human_review_required": true
}
```

---

## 5. LLM Service (Internal Abstraction)

**This is not an agent. It is a service all agents must use.**

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
- All calls are logged with:
  `caller_agent`, `model_used`, `input_token_count`, `output_token_count`, `latency_ms`,
  `request_id`, `prompt_version`, `response_schema_version`
- Never log raw prompt content in production. Log only metadata.
- If the provider is unavailable, raise `LLMUnavailableError`. The caller handles graceful degradation.

---

## 6. LLM Unavailability — Per-Agent Degradation

Constitution P-02: The deterministic core must remain operational when the LLM is down.

| Agent | LLM unavailable behavior |
|---|---|
| Supervisor | Deterministic routing continues. Events are still consumed and routed. No LLM needed. |
| Attendance Agent | Risk warning + exact calculation (from engine) shown to student. Natural-language explanation unavailable. Plan proposal blocked. Case put in `PENDING_LLM_AVAILABLE` state. |
| Learning Agent | Quiz generation unavailable. Source retrieval/search can continue. Student shown "Study guide unavailable — try again later". |
| Intervention Agent | Deterministic follow-up evaluation and state transitions continue. Replan proposals blocked. |
| LLM Service | Raises `LLMUnavailableError` immediately. Does not retry without explicit policy. |

---

## 7. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-AG01 | Default model for P0? Must be chosen via evaluation, not reputation. | Mrityunjoy | 🔴 OPEN |
| OQ-AG02 | Which agents run synchronously vs. async background jobs? | Mrityunjoy + Bishesh | 🔴 OPEN — affects API design |
| OQ-AG03 | Scheduler mechanism for `EXAM_APPROACHING`, `TASK_OVERDUE`, `MENTOR_FOLLOWUP_DUE` events — cron job or event-driven? | Bishesh | 🔴 OPEN |
