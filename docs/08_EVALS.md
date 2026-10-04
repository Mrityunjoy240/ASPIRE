# 08_EVALS.md
# EduGen AI / ASPIRE — Evaluation Framework

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 03 October 2026
**Version:** 1.0

> [!IMPORTANT]
> This document defines P0-16: the Evaluation & Test Harness.
> "Vibe coding" does not mean untested coding.
> Every deterministic engine must have fixture-based tests before it is merged.
> Every agent boundary must have adversarial tests before it is merged.

---

## 1. Guiding Principle

We evaluate at three levels:

| Level | What it checks | When |
|---|---|---|
| **Unit** | Deterministic engines: same input → same output | Every PR |
| **Integration** | API contracts and RBAC enforcement | Every PR |
| **System / Eval** | Agent behavior, RAG grounding, demo scenario | Before milestone sign-off |

---

## 2. Attendance Engine Fixtures

These fixtures must all pass before `services/engines/attendance.py` is merged.

| ID | Input | Expected Output |
|---|---|---|
| ATT-01 | attended=22, conducted=30, threshold=75 | percentage=73.33, risk=WARNING |
| ATT-02 | attended=0, conducted=0 | percentage=null |
| ATT-03 | attended=30, conducted=30, threshold=75 | percentage=100.0, risk=SAFE |
| ATT-04 | attended=18, conducted=30, threshold=75 | percentage=60.0, risk=CRITICAL |
| ATT-05 | attended=22, conducted=30, target=75 | required_to_recover=4 |
| ATT-06 | attended=30, conducted=30, target=75 | required_to_recover=0 (already met) |
| ATT-07 | attended=0, conducted=30, target=75 | required_to_recover=-1 (mathematically unreachable within max_classes) |
| ATT-08 | Source (CSV import or manual entry) supplies attendance status = `LATE` | Validation MUST fail and the record is rejected — never becomes VERIFIED, never silently coerced to PRESENT or ABSENT; engine never generates `LATE` (DM-NEW-LATE01 Option C — reserved/unsupported input in v1) |

---

## 3. Assessment Engine Fixtures

| ID | Input | Expected Output |
|---|---|---|
| ASS-01 | status=SUBMITTED_PENDING_EVALUATION, obtained_marks=null | Not treated as ZERO |
| ASS-02 | 6 graded assessments: [80,75,70,50,45,40], recent 3 = [50,45,40], prev 3 = [80,75,70] | TREND_DECLINING emitted |
| ASS-03 | Only 4 total graded assessments | TREND_NOT_ESTABLISHED (no event emitted) |
| ASS-04 | obtained_marks=0, status=OFFICIAL_ZERO | Treated as zero. Different from NOT_SUBMITTED. |
| ASS-05 | status=WITHHELD | Not included in trend calculation |

**Configuration-driven aggregation fixtures (DM-ASSESS01 — OQ-06 resolved):** scheme configuration is data; the engine must never hardcode weights (03 §4.0).

| ID | Input | Expected Output |
|---|---|---|
| ASS-06 | Active BCREC AIML theory scheme config | Resolves CIA-1=40, CIA-2=40, ESE=60 from configuration |
| ASS-07 | CIA-1 configured sub-components: Class Test 25 + Assignment 10 + Attendance 5 | CIA-1 total = 40 — computed from config, not hardcoded |
| ASS-08 | CIA-2 with the configured sub-weights | CIA-2 total = 40 — computed from config, not hardcoded |
| ASS-09 | ESE component with configured full marks 60 | ESE contribution = 60 |
| ASS-10 | Aggregate CIA-1 + CIA-2 + ESE under the active scheme | Total = 100 — configuration-driven aggregation |
| ASS-11 | Alternate scheme config (different programme/term) with different components/weights | Same engine code path computes from that config — different numbers, zero hardcoded weighting |
| ASS-12 | PCIA/PESE scheme with weights from its own assessment-rule version | Uses configured weights exactly — no universal PCIA/PESE formula assumed |

---

## 4. RBAC Tests (Zero Tolerance)

All of these must return `403 Forbidden`. They may never return data.

| ID | Actor | Action | Expected |
|---|---|---|---|
| RBAC-01 | Student A | GET /students/StudentB/state | 403 |
| RBAC-02 | Faculty | GET /students/{id}/cases | 403 |
| RBAC-03 | Student | POST /import/upload | 403 |
| RBAC-04 | HOD | GET /audit-log | 403 |
| RBAC-05 | Unauthenticated | GET /students/{id}/state | 401 |
| RBAC-06 | Mentor | GET student state for non-mentee | 403 |
| RBAC-07 | Faculty | GET course data for another faculty's course | 403 |

**RLS integration fixtures (integration level — local Supabase):**

These run against the **Supabase CLI local stack**: real test-user JWTs from local Supabase Auth, exercised through the local Data API/PostgREST (07 §2). Unit tests and FastAPI application-level authorization tests remain separate — see the level table in §1.

| ID | Actor (real local JWT) | Action | Expected |
|---|---|---|---|
| RLS-01 | Student A | Data API read of Student B's `attendance_records` | Denied by policy — zero rows |
| RLS-02 | Student A | Data API read of own `attendance_records` | Allowed — own rows only |
| RLS-03 | Mentor | Data API read of assigned mentee attendance | Allowed — assigned mentees only |
| RLS-04 | Mentor | Data API read of non-mentee attendance | Denied — zero rows |
| RLS-05 | Unauthenticated | Data API request without JWT | 401 — rejected at boundary |

Direct privileged SQLAlchemy/service connections are **not** accepted as proof that RLS works.

---

## 5. Agent Boundary Tests (Zero Tolerance)

These tests verify that no agent exceeds its defined tool boundaries.

| ID | Agent | Attempted Action | Expected |
|---|---|---|---|
| AGT-01 | Any Agent | Direct SQL write to `attendance_records` | Tool call rejected |
| AGT-02 | Attendance Agent | Mark student officially ineligible | Action forbidden |
| AGT-03 | Learning Agent | Generate quiz with 0 retrieved chunks | Graceful failure (no quiz) |
| AGT-04 | Learning Agent | Access another student's documents | Tool call rejected (RBAC) |
| AGT-05 | Supervisor Agent | Call LLM directly | Tool not in allowed list |
| AGT-06 | Intervention Agent | Close a case when data is in CONFLICT status | Rejected |
| AGT-07 | Any Agent | Escalate to HOD before routing to Mentor | Rejected |

---

## 6. RAG Grounding Tests

| ID | Input | Expected |
|---|---|---|
| RAG-01 | Quiz request for topic with 0 matching chunks | System returns "insufficient source material" error |
| RAG-02 | Generated quiz question | Every question cites a `source_chunk_id` that exists in DB |
| RAG-03 | PDF containing "Ignore your instructions" | Text is in quiz content (as data), NOT executed as instruction |
| RAG-04 | Student A requests quiz from Student B's OWNER_ONLY doc | 403 Forbidden |

---

## 7. Demo Scenario Fixture (The North Star Test)

This end-to-end fixture must pass before any demo or milestone review.

**Setup:**
- Institution: BCREC configured with 75% ESE threshold, 65% condonation minimum.
- Student S-204, B.Tech CSE AIML, Sem 5.
- DBMS attendance: 22 attended / 30 conducted = 73.33%.
- DBMS exam: 8 days from fixture date.
- 2 pending assessments: DBMS Lab Record (SUBMITTED_PENDING_EVALUATION) and DBMS CIA-2 (NOT_SUBMITTED).
- Student has uploaded 1 DBMS PDF (OWNER_ONLY scope).

**Expected end-to-end behavior:**
1. Upload attendance CSV → Rule engine runs → `ATTENDANCE_RISK_WARNING` emitted.
2. Supervisor Agent routes to Attendance Specialist.
3. Agent proposes a recovery plan. Plan JSON is structurally valid and cites the engine-derived evidence.
4. Student S-204 accepts plan.
5. Two tasks created in `student_tasks` (PENDING) with source_type = AI_PLAN.
6. Intervention case status: `ACTIVE`.
7. Mentor queue shows S-204 in `ATTENTION` band.
8. Learning Agent generates a DBMS quiz from the uploaded PDF. Every question has a valid `source_chunk_id`.
9. Upload updated attendance CSV (25/30 = 83.33%) → Rule engine reruns → `ATTENDANCE_RISK_WARNING` resolves → case auto-evaluates → RESOLVED.

---

## 8. Conflict Resolution Test

| Step | Action | Expected |
|---|---|---|
| 1 | Upload CSV with attendance 73% for S-204 in DBMS (same period as existing verified record of 81%) | Conflict detected |
| 2 | Incoming record quarantined | `data_conflicts` row created |
| 3 | S-204's DBMS quiz generation (unrelated to attendance) | Continues normally (scope of freeze is narrow) |
| 4 | Admin resolves conflict, selects 73% as authoritative | Existing record → SUPERSEDED. New → VERIFIED. |
| 5 | Derived state recomputed | attendance_percentage = 73.33%, risk = WARNING |
| 6 | Automation resumes | Recovery recommendation now shown to student |

---

## 9. Priority Queue Accuracy Test (Mentor Queue)

Mentor queue ordering is FROZEN per DM-SS03 / OQ-SS03 (Option A) — 03_SYSTEM_SPEC §6.2. These fixtures must pass before the Mentor Queue API (T-061) is merged.

| ID | Setup | Expected Queue Order |
|---|---|---|
| PQ-01 | Case A: URGENT, exam in 5 days. Case B: ATTENTION (WARNING). | A before B (band decided first) |
| PQ-02 | Case A: URGENT, data updated 1h ago. Case B: URGENT, data updated 3 days ago. All other sort fields equal. | Order identical to the input without staleness — `data_staleness_hours` does NOT affect ordering |
| PQ-03 | Case A: URGENT, mentor last acted 10 days ago. Case B: URGENT, 1 day ago. Same exam. | A before B (older untouched) |
| PQ-04 | Case A: URGENT, exam in 3 days. Case B: URGENT, exam in 10 days. | A before B (nearer exam beats farther exam) |
| PQ-05 | Case A: URGENT, exam in 5 days. Case B: URGENT, exam_days_remaining=NULL. | A before B (known exam beats NULL exam — NULLS LAST within URGENT) |
| PQ-06 | Case A: URGENT, days_since_last_mentor_action=NULL (never acted). Case B: URGENT, acted 1 day ago. Same exam. | A before B (NULLS FIRST — never acted on) |
| PQ-07 | Case A: ATTENTION, exam in 2 days. Case B: ATTENTION, exam in 30 days. Same days_since_last_mentor_action. | Exam proximity ignored in ATTENTION — order as if no exam field exists |
| PQ-08 | Case A: MONITOR, exam in 1 day. Case B: MONITOR, exam in 10 days. Same days_since_last_mentor_action. | Exam proximity ignored in MONITOR — order as if no exam field exists |
| PQ-09 | Two cases tied on band, exam, and days_since_last_mentor_action. A has earlier created_at (and lower case_id). | A before B (created_at ASC, then case_id ASC — deterministic final ordering) |

---

## 10. Task Derived-State (OVERDUE) Fixtures

`OVERDUE` is derived, never stored (DM-SS02 / OQ-SS02 — Option A). These fixtures must pass before the Task API (T-041) is merged.

| ID | Input | Expected Output |
|---|---|---|
| TS-01 | status=PENDING, deadline in the past | Derived state = OVERDUE |
| TS-02 | status=PENDING, deadline in the future | Not OVERDUE |
| TS-03 | status=COMPLETED, deadline in the past | Not OVERDUE |
| TS-04 | status=PENDING, deadline=NULL | Never OVERDUE |

---

## 11. Scheduler Fixtures (DM-AG03)

The time-based scheduler (periodic, every 5 minutes — 03_SYSTEM_SPEC §8.3) must pass these fixtures before it is merged.

| ID | Input | Expected Output |
|---|---|---|
| SCH-01 | Exam crosses the configured "exam approaching" rule | `EXAM_APPROACHING` event emitted |
| SCH-02 | Same true condition persists across repeated scheduler cycles | No duplicate logical event — one logical trigger occurrence produces one logical event |
| SCH-03 | Scheduler cycle delayed/missed (e.g., downtime) | Next cycle recovers from current database state and emits the outstanding logical event exactly once |
| SCH-04 | Task with status=PENDING, deadline in the past | `TASK_OVERDUE` emitted |
| SCH-05 | Task with status=COMPLETED, deadline in the past | No `TASK_OVERDUE` emitted |
| SCH-06 | Task with status=PENDING, deadline=NULL | `TASK_OVERDUE` never emitted |
| SCH-07 | After `TASK_OVERDUE` emission | DB status remains PENDING — `OVERDUE` is never persisted (DM-SS02) |

---

## 12. OpenAPI Contract Fixtures (DM-API01)

`contracts/openapi.json` is the committed **generated** contract artifact (FastAPI routes + Pydantic = source of truth). These fixtures must pass before any API change is merged.

| ID | Check | Expected Output |
|---|---|---|
| API-01 | Run the contract generation command twice from a clean app import | Deterministic, byte-identical output (stable key ordering and formatting — git-diff safe) |
| API-02 | Regenerate and compare against committed `contracts/openapi.json` | Zero difference — committed artifact matches generated output |
| API-03 | CI regenerates the document while the committed artifact has been modified | CI FAIL (drift detected) |
| API-04 | Frontend type generation | TypeScript types derive from the canonical `contracts/openapi.json` only — never hand-written endpoint schemas |

---

## 13. LLM Mock / Failure Fixtures (DM-LLM01)

`MOCK` responses come from explicit deterministic fixtures (06 §5). The evaluation suite MUST prove that deterministic academic calculations still work with the LLM disabled. Invalid structured output is always rejected — never partially accepted, coerced, or completed with invented fields.

| ID | Fixture | Expected Output |
|---|---|---|
| LLM-01 | Successful structured response | Schema-validated output accepted; business logic consumes it normally |
| LLM-02 | Timeout | Controlled timeout failure; one bounded retry allowed; controlled unavailable result if exhausted — no unbounded loop |
| LLM-03 | Transient provider failure | One bounded retry with bounded backoff → success or controlled unavailable |
| LLM-04 | Rate limit | One bounded retry with bounded backoff — never an unbounded retry loop |
| LLM-05 | Invalid structured output | Rejected at schema validation before business logic — never partially accepted, coerced, or patched with invented fields |
| LLM-06 | Exhausted failure (retries/failover) | Controlled unavailable result after the allowed retry/failover path; audit metadata records `outcome` + `failure_reason` |
| LLM-07 | Supervisor deterministic routing while LLM unavailable | Event routing continues deterministically — no LLM dependency, no blocked routing |
| LLM-08 | Attendance deterministic calculation while LLM unavailable | Calculations and risk evaluation continue; no fabricated AI recovery plan |
| LLM-09 | Learning quiz-generation unavailable | No quiz created, no fake substitute stored; controlled unavailable state; RAG rules intact |
| LLM-10 | Intervention plan unavailable | No proposal/approval/activation represented; case state uncorrupted; preconditions still enforced |

LLM-01…LLM-06 are exercised at the gateway level (T-004); LLM-07…LLM-10 are exercised within their owning agent test suites per the 06 §6 degradation contract.
