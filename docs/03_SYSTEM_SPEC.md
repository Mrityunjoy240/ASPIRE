# 03_SYSTEM_SPEC.md
# EduGen AI / ASPIRE — System Specifications

**STATUS: 🟡 UNDER REVIEW**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 03 October 2026
**Version:** 1.2

> [!IMPORTANT]
> This document defines the **deterministic core** of ASPIRE.
> These are the mathematical calculations, rules, state machines, and logic engines
> that operate *before* the AI agents are invoked.
> **AI agents are explicitly forbidden from performing these calculations.**
>
> **No deterministic engine, agent, or AI-generated plan may mutate an official
> academic fact or institutional decision.**
>
> ```
> Attendance %       → engine
> Risk signal        → engine
> Recovery plan      → agent proposal
> Student decision   → student
> Mentor approval    → mentor
> Official eligibility → authorized human / institutional workflow
> ```

---

## 1. Institution Configuration Hierarchy

Configuration is not a flat object. It follows a strict hierarchy with versioning and effective dates.

**Hierarchy:**
`Institution → Academic Scheme → Batch → Programme → Semester → Rule`

**Schema for a Rule:**
```json
{
  "rule_id": "attendance_threshold",
  "scope_level": "BATCH",
  "scope_id": "batch_2024_2028",
  "value": 75.0,
  "rule_scope": "AGGREGATE_ATTENDANCE",
  "effective_from": "2024-07-01T00:00:00Z",
  "effective_to": null,
  "version": 1,
  "status": "ACTIVE",
  "updated_by": "admin_uuid"
}
```

> **`rule_scope`** is mandatory. The attendance risk engine does not assume course-specific eligibility.
> Eligibility scope must come from the active institutional rule configuration.
> A student at 73% in DBMS is not officially ineligible for DBMS ESE unless the rule's
> `rule_scope` applies at subject level. Default for BCREC is `AGGREGATE_ATTENDANCE`.

---

## 2. Student State

The system maintains a continuously updated, deterministic view of the student.

**1. Verified Facts (DB Layer):** Raw data points: attendance records, submissions, grades.
**2. Derived State (Engine Layer):** Computed values: aggregate attendance %, assessment averages, risk indicators.
**3. Operational State (App Layer):** Active cases, pending tasks, unread notifications.

---

## 3. The Attendance Engine

Calculates current attendance and projects recovery. Operates only on VERIFIED records.

> **`LATE` is reserved — DM-NEW-LATE01 (DECIDED):** `LATE` is unsupported as an input status in v1. The engine never generates `LATE` records, and a VERIFIED attendance calculation input must not contain `LATE`. If an imported or manually entered record contains `LATE`, the input MUST fail validation and be rejected — it must not become a VERIFIED record and must not be silently coerced to PRESENT or ABSENT. No grace-period rule exists in v1; institutional semantics deferred to post-BCREC validation.

### 3.1 Current Attendance Calculation
`Attendance % = (Classes Attended / Classes Conducted) * 100`
- Rounded to 2 decimal places.
- **If `Classes Conducted == 0`, return `null`** (not 0, not 100).

### 3.2 What-If Projection (Recovery Calculation)
Returns the number of consecutive future classes a student must attend to reach the target threshold.

**Return value contract:**
- `None` = NOT_APPLICABLE (no data / conducted is 0)
- `0` = already at or above target
- Positive integer = consecutive classes required
- `-1` = target unreachable within the configured `max_classes` horizon

```python
def calculate_required_classes(
    attended: int,
    conducted: int,
    target_threshold: float,
    max_classes: int = 100
) -> int | None:
    if conducted == 0:
        return None  # NOT_APPLICABLE — no data

    if (attended / conducted) * 100 >= target_threshold:
        return 0  # Already at or above target

    required = 0
    a, c = attended, conducted
    while (a / c) * 100 < target_threshold:
        if required >= max_classes:
            return -1  # Unreachable within max_classes horizon
        required += 1
        a += 1
        c += 1
    return required
```

> **Note on `-1`:** Returns `-1` when the target cannot be reached within the configured `max_classes` horizon. This does NOT mean mathematically impossible in the abstract — it means unreachable within the defined operating boundary. The system displays a condonation guidance message, not an ineligibility declaration.

### 3.3 Risk Detection (System Signals — Not Official Decisions)

These are **system risk signals**. They are not official eligibility states.
A student receiving `ATTENDANCE_RISK_CRITICAL` is not officially ineligible — that decision belongs to the institution.

- **IF** `attendance < ese_eligibility_threshold` AND `attendance >= condonation_minimum`:
  Emit: `ATTENDANCE_RISK_WARNING`
- **IF** `attendance < condonation_minimum`:
  Emit: `ATTENDANCE_RISK_CRITICAL`
- **IF** `attendance >= ese_eligibility_threshold` AND `attendance < ese_eligibility_threshold + watch_margin` AND exam is approaching *(config-driven, only if `ATTENDANCE_WATCH` feature flag is enabled)*:
  Emit: `ATTENDANCE_WATCH`

> `watch_margin` must be defined in `institution_rules`. Do not hardcode a value. If the team has not agreed on this margin, the `ATTENDANCE_WATCH` signal must not be emitted.

---

## 4. The Assessment Engine (CIA/PCIA)

**FROZEN — DM-ASSESS01 / OQ-06 = RESOLVED (configuration-driven assessment structure).**

### 4.0 Assessment Scheme Configuration (FROZEN — DM-ASSESS01)

ASPIRE uses a **versioned, configuration-driven assessment component model.** The assessment engine MUST NOT hardcode one universal CIA/PCIA/ESE weighting. Component applicability and weighting come from the **effective assessment-scheme configuration** for the institution/programme/course/term (versioned `institution_rules` pattern, 05 §12; materialized per course run in `assessment_components`, 05 §6).

Supported component types (configurable — not universally applicable): `CIA-1`, `CIA-2`, `PCIA`, `ESE`, `PESE`, `Assignment`, `Class Test`, `Attendance`, `Quiz`, `Project`, `Viva`.

**Configuration vs calculation logic:** scheme configuration (component/type, full marks, contribution/weighting, applicability, effective dates/version, institution/programme/course scope) is **data**. The deterministic calculation engine is **logic** that consumes the active configuration. Configuration numbers are never engine constants.

**Current BCREC CSE(AIML) 5th-semester theory template — a versioned BCREC assessment configuration (documented/seeded example, NOT a universal engine rule):**

```text
CIA-1 = 40
  Class Test = 25
  Assignment = 10
  Attendance = 5

CIA-2 = 40
  Class Test = 25
  Assignment = 10
  Attendance = 5

ESE = 60

Total = 100
```

This documents the currently published BCREC AIML theory structure **only**. Not every BCREC course uses this structure — other BCREC autonomous syllabi can use different practical assessment structures. ASPIRE models the rule as configuration, not a global constant: **do NOT hardcode these numbers into calculation logic.**

**Practical / PCIA:** `PCIA` and `PESE` are supported component types. Their exact weighting MUST come from the applicable curriculum/assessment-rule version. Do not infer a universal PCIA formula from an unrelated course or programme.

**Assessment data model must represent:** component/type · full marks · contribution/weighting · applicability · effective dates/version · institution/programme/course scope. The deterministic calculation engine consumes the active configuration.

### 4.1 Assessment Lifecycle States
```
NOT_SUBMITTED
SUBMITTED_PENDING_EVALUATION
GRADED
OFFICIAL_ZERO
WITHHELD
CANCELLED
```

**`trend_eligible` assessments = `GRADED` + `OFFICIAL_ZERO`**
Both are finalized numeric outcomes. `WITHHELD` and `CANCELLED` are excluded.

### 4.2 Trend Calculation

Runs when new `GRADED` or `OFFICIAL_ZERO` assessments are entered.
Normalized: `assessment_percentage = (obtained_marks / maximum_marks) * 100`

**Assessment scope:** Trend calculation scope and component mixing (CIA/PCIA) follow the active assessment-scheme configuration — DM-ASSESS01 (OQ-06 resolved). Cross-component aggregation uses the scheme's configured components/weights, never hardcoded constants. Trend algorithm and rules below are unchanged.

```python
def compute_trend(eligible_assessments: list) -> str:
    """
    eligible_assessments: chronologically ordered list of GRADED + OFFICIAL_ZERO
    Each item: { obtained_marks, maximum_marks }
    """
    if len(eligible_assessments) < 6:
        return "TREND_NOT_ESTABLISHED"

    recent = eligible_assessments[-3:]
    previous = eligible_assessments[-6:-3]

    recent_avg = avg([(a.obtained / a.maximum) * 100 for a in recent])
    previous_avg = avg([(a.obtained / a.maximum) * 100 for a in previous])

    if previous_avg == 0:
        return "TREND_NOT_ESTABLISHED"  # Cannot compute a meaningful ratio

    decline_ratio = (previous_avg - recent_avg) / previous_avg
    if decline_ratio > 0.15:
        emit("ASSESSMENT_TREND_DECLINING")

    return "COMPUTED"
```

---

## 5. Unified Obligation Stream (Task Engine)

### 5.1 Task Schema & Provenance
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "source_type": "ENUM(CALENDAR, ASSESSMENT, AI_PLAN, MENTOR)",
  "source_id": "uuid",
  "created_by": "uuid",
  "created_at": "timestamp",
  "title": "string",
  "deadline": "timestamp | null",
  "status": "ENUM(PENDING, COMPLETED, SNOOZED)",
  "explicit_priority": "int | null"
}
```

> **`OVERDUE` is a derived state, not a stored status — DM-SS02 / OQ-SS02 = DECIDED (Option A).** A task is `OVERDUE` when `status = PENDING` AND `deadline < now`. It must NOT exist as an independent persisted value in the task status enum; stored statuses remain `PENDING | COMPLETED | SNOOZED`. The task engine/UI may display `OVERDUE` as a derived state. No scheduler job may rewrite `PENDING → OVERDUE` in the database. Completing a task removes the derived `OVERDUE` state automatically. Tasks with `deadline = NULL` can never be `OVERDUE`. Existing explicit business states are never overwritten merely because a deadline has passed.

> Rule: Lower `deadline` timestamp always takes precedence over explicit source priority.

### 5.2 Priority Sorting Precedence
1. Derived OVERDUE first (`deadline < now` AND `PENDING`)
2. `deadline` ASC (upcoming deadlines first)
3. `explicit_priority` DESC
4. `source_type` rank: `MENTOR > ASSESSMENT > AI_PLAN > CALENDAR`
5. `created_at` ASC

---

## 6. Mentor Priority Queue Engine

Sorts open **intervention cases** (not students).

### 6.1 Urgency Bands
- **URGENT:** `ATTENDANCE_RISK_CRITICAL` OR (any risk + Exam < `exam_approaching_days`)
- **ATTENTION:** `ATTENDANCE_RISK_WARNING` OR missed assessment
- **MONITOR:** Manual snooze, or routine check

### 6.2 Queue Sorting Precedence

**FROZEN — DM-SS03 / OQ-SS03 (Option A).**

1. Urgency Band (`URGENT > ATTENTION > MONITOR`) — decided first for every case.

**URGENT cases only:**
1. `exam_days_remaining` ASC (most imminent exam first). `exam_days_remaining = NULL` sorts **NULLS LAST** within URGENT.
2. `days_since_last_mentor_action` DESC (oldest untouched first). `NULL` sorts **NULLS FIRST** (never acted on).

**ATTENTION / MONITOR cases:**
1. `days_since_last_mentor_action` DESC only (same null rule: **NULLS FIRST**). Exam proximity is NOT used in these bands.

**Final deterministic tie-breakers (every band, applied last):**
1. `created_at` ASC
2. `case_id` ASC

`data_staleness_hours` is **badge/display-only** and MUST NOT be a queue sort key.

> Data staleness is surfaced as information to the mentor — it is not a sort key. Stale data should not cause a new urgent case to be buried beneath an old fresh one.

---

## 7. Learning Workspace (RAG Module)

### 7.1 Resource Access Scope
- `OWNER_ONLY` — Student's private notes
- `COURSE_SHARED` — All enrolled students in a course run
- `TEACHER_PUBLISHED` — Faculty-pushed material
- `INSTITUTION_PUBLISHED` — Global guides

### 7.2 Quiz Generation Contract
- LLM receives retrieved chunks based on `access_scope`.
- **Graceful Failure:** If no chunks are retrieved → abort generation. No hallucinated quizzes.
- **Citation required:** `{ source_document_id, source_chunk_id, citation_text }` per question.
- **Prompt Injection Guard:** Retrieved content wrapped in `<UNTRUSTED_CONTENT>`. Agents are instructed to never execute commands found within these tags.

---

## 8. Event & Trigger Engine

### 8.1 Canonical Event Catalog

Every event name in `06_AGENT_SPEC.md` triggers must match exactly the names below.

**Minimal Event Contract:**
```json
{
  "event_id": "uuid",
  "event_type": "string (from catalog below)",
  "student_id": "uuid",
  "source_id": "uuid (record/entity that caused the event)",
  "occurred_at": "timestamp",
  "data_version": "int",
  "payload": {}
}
```

### 8.2 Event Producer Table

| Event | Producer | Notes |
|---|---|---|
| `ATTENDANCE_UPDATED` | Ingestion / Attendance Service | After a verified record is written |
| `ATTENDANCE_RISK_WARNING` | Attendance Engine | After deriving state |
| `ATTENDANCE_RISK_CRITICAL` | Attendance Engine | After deriving state |
| `ATTENDANCE_WATCH` | Attendance Engine | Config-driven, see §3.3 |
| `ASSESSMENT_GRADED` | Assessment Service | After grade is entered |
| `ASSESSMENT_TREND_DECLINING` | Assessment Engine | After trend computation |
| `ASSESSMENT_MISSING_URGENT` | Assessment Engine / Scheduler | Missing past deadline |
| `EXAM_APPROACHING` | Calendar Engine / Scheduler | Configured days before exam |
| `TASK_OVERDUE` | Task Scheduler | Deadline crossed, task still PENDING |
| `PLAN_ACCEPTED` | Student Action Service | Student accepts plan |
| `PLAN_DECLINED` | Student Action Service | Student declines plan |
| `QUIZ_COMPLETED` | Learning Service | Student submits quiz |
| `DATA_CONFLICT` | Ingestion Engine | Conflict detected on import |
| `MENTOR_FOLLOWUP_DUE` | Follow-up Scheduler | Per intervention policy |

### 8.3 Time-Based Scheduler (DM-AG03 / OQ-AG03 — FROZEN: hybrid trigger model)

- **State-change events remain event-driven.**
- **Time-based events use a periodic application scheduler running every 5 minutes.** Covered events: `EXAM_APPROACHING`, `TASK_OVERDUE`, `MENTOR_FOLLOWUP_DUE`.
- The scheduler evaluates time-based conditions and emits domain events. It does not directly invoke agents or mutate business state.

**Architecture boundary:**
```text
DB/current state
      ↓
periodic scheduler
      ↓
evaluate time condition
      ↓
emit domain event
      ↓
existing event-driven routing / Supervisor
```

**Scheduler lifecycle:**
- Run one evaluation immediately at application startup.
- Then run every **5 minutes**.
- A delayed/missed cycle must be recoverable by the next evaluation from current database state.
- Scheduler execution MUST be idempotent: one logical trigger occurrence must not produce duplicate logical events. Do not create duplicate events merely because the same condition remains true across multiple scheduler cycles.

**`TASK_OVERDUE` rule (DM-SS02 preserved):**
- `OVERDUE` remains a derived display/query state: `status = PENDING AND deadline < now`.
- The scheduler MUST NOT persist `OVERDUE` and MUST NOT rewrite `PENDING → OVERDUE`.
- The scheduler MAY emit `TASK_OVERDUE` when the task crosses the deadline condition.

**Business-rule ownership:**
The scheduler MUST NOT invent or hardcode business thresholds. For example, the definition of "exam approaching" remains owned by the applicable system/configuration rule. The scheduler only evaluates that frozen rule against current time/state.

**The scheduler MUST NOT:**
- directly call an LLM
- directly execute an agent plan
- directly approve or mutate human-authority decisions
- persist `OVERDUE`
- replace the existing event-driven architecture for ordinary state changes

---

## 9. Calendar / Event Engine

**Event Types:** `ACADEMIC_EVENT`, `HOLIDAY`, `CLASS`, `EXAM`, `DEADLINE`

Supports `RESCHEDULED_EVENT` and `CANCELLED_EVENT` to supersede old dates without deleting history.
The Calendar Engine produces `exam_days_remaining` — agents read this value; they do not compute date differences.

---

## 10. Intervention Case State Machine

### 10.1 States
`OPEN → IN_REVIEW → PLAN_PROPOSED → PENDING_APPROVAL → ACTIVE → MONITORING → REPLAN_REQUIRED → ESCALATION_REQUIRED → RESOLVED → CLOSED`

### 10.2 Legal Transition Table

**No actor may perform a transition not listed in this table.**

| Current State | Action | Actor | Next State |
|---|---|---|---|
| `OPEN` | System creates case | Supervisor Agent | `IN_REVIEW` |
| `IN_REVIEW` | Agent proposes plan | Attendance/Intervention Agent | `PLAN_PROPOSED` |
| `PLAN_PROPOSED` | Student accepts | Student | `PENDING_APPROVAL` |
| `PLAN_PROPOSED` | Student edits + accepts | Student | `PENDING_APPROVAL` |
| `PLAN_PROPOSED` | Student declines | Student | `REPLAN_REQUIRED` |
| `PENDING_APPROVAL` | Mentor approves | Mentor | `ACTIVE` |
| `PENDING_APPROVAL` | Mentor edits + approves | Mentor | `ACTIVE` |
| `PENDING_APPROVAL` | Mentor rejects | Mentor | `REPLAN_REQUIRED` |
| `ACTIVE` | Follow-up due | `RULE_ENGINE` (on scheduler-emitted event) | `MONITORING` |
| `MONITORING` | Improvement verified by engine | `RULE_ENGINE` | `RESOLVED` |
| `MONITORING` | No improvement, follow-up expires | `RULE_ENGINE` (on scheduler-emitted event) | `REPLAN_REQUIRED` |
| `REPLAN_REQUIRED` | New plan proposed | Agent | `PLAN_PROPOSED` |
| `REPLAN_REQUIRED` | Escalation proposed | Intervention Agent | `ESCALATION_REQUIRED` |
| `ESCALATION_REQUIRED` | Mentor escalates to HOD/CT | Mentor | `ESCALATION_REQUIRED` (pending HOD) |
| `RESOLVED` | Mentor closes | Mentor | `CLOSED` |
| Any state | Data conflict on affecting fact | Ingestion Engine | Automation paused (see §11) |

> **Scheduler boundary (DM-AG03):** The Scheduler only evaluates time conditions and emits the time-based domain event (§8.3). It does not directly mutate case state. The deterministic event consumer / `RULE_ENGINE` validates and performs the transition shown above.

---

## 11. Data Ingestion & Conflict Resolution

**Definition of a conflict:** Two sources or two versions assert different values for the same fact (student / course / time period). A large value change is not automatically a conflict.

Steps: `UPLOAD → PARSE → SCHEMA VALIDATE → RECORD VALIDATE → MATCH → CONFLICT DETECT → QUARANTINE → FREEZE (narrow scope) → HUMAN RESOLUTION → VERSION → RECOMPUTE → RESUME`

- **Freeze scope is narrow:** Only automation depending on the specific conflicting fact is paused. Other automation for the same student continues.
- After resolution: losing record → `SUPERSEDED`, winning record → `VERIFIED`. Audit event recorded.

---

## 12. RBAC / Permission Engine

| Role | Access |
|---|---|
| Student | Own data only |
| Faculty | Data for assigned course runs only |
| CT | Aggregates and class data for assigned batch |
| Mentor | Student 360 for assigned mentees only. **Excludes counselling/restricted-support data unless separately authorized.** |
| HOD | Department aggregates and escalated cases only. Not individual student confidential records by default. |
| Admin | Configuration, imports, role mapping |

---

## 13. Audit & Provenance

Every privileged write produces one audit record.

```json
{
  "id": "uuid",
  "actor_id": "uuid",
  "actor_type": "ENUM(USER, SYSTEM, AGENT, RULE_ENGINE)",
  "action_type": "string",
  "entity_table": "string",
  "entity_id": "uuid",
  "previous_state": "jsonb",
  "new_state": "jsonb",
  "source_system": "string",
  "created_at": "timestamp"
}
```

For agent-triggered mutations, the provenance chain must be traceable:
`event → case → agent run → proposed action → human approval → mutation`

---

## 14. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-05 | BCREC data contact for real validation samples | All | 🔴 OPEN |
| OQ-06 | CIA/PCIA component structure and weights for autonomous batches | Bishesh | ✅ RESOLVED — DM-ASSESS01 (OQ-06 = RESOLVED): configuration-driven scheme; BCREC AIML theory template documented in §4.0 as versioned configuration |
| OQ-07 | MAR points calculation rules | Abhijit | 🔴 OPEN |
| OQ-08 | Exact roll number format at BCREC | Bishesh | 🔴 OPEN |
| OQ-AG03 | Scheduler mechanism for EXAM_APPROACHING, TASK_OVERDUE, MENTOR_FOLLOWUP_DUE | Bishesh | ✅ RESOLVED — DM-AG03 (hybrid: event-driven state changes + 5-minute periodic scheduler, §8.3) |
| OQ-SS01 | `ATTENDANCE_WATCH` margin — what value? Team must agree before this signal is implemented. | All | 🔴 OPEN |
| OQ-SS02 | `OVERDUE` — derived display state or persisted status? | All | ✅ RESOLVED — DM-SS02 (Option A): derived, never persisted |
| OQ-SS03 | Mentor queue exact sort order | All | ✅ RESOLVED — DM-SS03 (Option A): frozen in §6.2 |
