# 03_SYSTEM_SPEC.md
# EduGen AI / ASPIRE — System Specifications

**STATUS: 🟡 UNDER REVIEW**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 03 October 2026
**Version:** 1.1

> [!IMPORTANT]
> This document defines the **deterministic core** of ASPIRE. 
> These are the mathematical calculations, rules, state machines, and logic engines that operate 
> *before* the AI agents are invoked. 
> **AI agents are explicitly forbidden from performing these calculations.**

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
  "effective_from": "2024-07-01T00:00:00Z",
  "effective_to": null,
  "version": 1,
  "status": "ACTIVE",
  "updated_by": "admin_uuid"
}
```

---

## 2. Student State

The system maintains a continuously updated, deterministic view of the student.

**1. Verified Facts (DB Layer):**
Raw data points: attendance records, assignment submissions, test scores.
**2. Derived State (Engine Layer):**
Computed values: aggregate attendance %, assessment averages, risk indicators.
**3. Operational State (App Layer):**
Active intervention cases, pending unified tasks, unread notifications.

---

## 3. The Attendance Engine

Calculates current attendance and projects required recovery. Operates only on VERIFIED records.

### 3.1 Current Attendance Calculation
`Attendance % = (Classes Attended / Classes Conducted) * 100`
- Rounded to 2 decimal places.
- If `Classes Conducted == 0`, return `null`.

### 3.2 What-If Projection (Recovery Calculation)
Calculates consecutive future classes required to reach a target threshold.

```python
def calculate_required_classes(attended, conducted, target_threshold, max_classes=100):
    if conducted == 0:
        return 0 # Or NOT_APPLICABLE depending on caller context
        
    current_percentage = (attended / conducted) * 100
    if current_percentage >= target_threshold:
        return 0
        
    required_classes = 0
    while (attended / conducted) * 100 < target_threshold:
        if required_classes >= max_classes:
            return -1 # Mathematically unreachable within normal constraints
        required_classes += 1
        attended += 1
        conducted += 1
        
    return required_classes
```

### 3.3 Risk Detection (Not Official Decisions)
- IF Attendance % < `ese_eligibility_threshold` AND Attendance % >= `condonation_minimum`:
  Emit: `ATTENDANCE_RISK_WARNING`
- IF Attendance % < `condonation_minimum`:
  Emit: `ATTENDANCE_RISK_CRITICAL`

> **Rule:** The system *detects a risk relative to thresholds*. It does NOT officially mark a student as "ineligible". Official decisions belong to humans.

---

## 4. The Assessment Engine (CIA/PCIA)

### 4.1 Assessment Lifecycle States
Every assessment must be in one of these explicit states:
- `NOT_SUBMITTED`
- `SUBMITTED_PENDING_EVALUATION`
- `GRADED` (has numeric score)
- `OFFICIAL_ZERO` (explicitly awarded 0)
- `WITHHELD`
- `CANCELLED`

### 4.2 Trend Calculation
Runs when new `GRADED` or `OFFICIAL_ZERO` assessments are entered.
Normalized percentage: `assessment_percentage = (obtained_marks / maximum_marks) * 100`

```python
# Requires at least 6 graded assessments to establish a trend
if total_graded_assessments < 6:
    return TREND_NOT_ESTABLISHED

recent_avg = average(latest 3 graded assessments)
previous_avg = average(previous 3 graded assessments)

if previous_avg > 0:
    decline_ratio = (previous_avg - recent_avg) / previous_avg
    if decline_ratio > 0.15: # 15% relative drop
        emit(ASSESSMENT_TREND_DECLINING)
```

---

## 5. Unified Obligation Stream (Task Engine)

### 5.1 Task Schema & Provenance
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "source_type": "ENUM(CALENDAR, ASSESSMENT, AI_PLAN, MENTOR)",
  "source_id": "uuid (reference to originating event/plan)",
  "created_by": "uuid (user or system_actor)",
  "created_at": "timestamp",
  "title": "String",
  "deadline": "timestamp",
  "status": "ENUM(PENDING, COMPLETED, OVERDUE, SNOOZED)",
  "explicit_priority": "Integer (Optional override)"
}
```

### 5.2 Priority Sorting Precedence
To prevent ambiguity, tasks are sorted strictly by this cascade:
1. `status == OVERDUE` (always top)
2. `deadline` (ascending urgency)
3. `explicit_priority` (descending)
4. `source_type` rank (`MENTOR` > `ASSESSMENT` > `AI_PLAN` > `CALENDAR`)
5. `created_at` (ascending - oldest first)

---

## 6. Mentor Priority Queue Engine

Sorts open **intervention cases** (not students).

### 6.1 Urgency Bands
- **URGENT:** `ATTENDANCE_RISK_CRITICAL` OR (any risk + Exam < `exam_approaching_days`).
- **ATTENTION:** `ATTENDANCE_RISK_WARNING` OR missed assessment.
- **MONITOR:** Manual "Snooze/Monitor" state, or routine check.

### 6.2 Queue Sorting Precedence
1. Urgency Band (URGENT > ATTENTION > MONITOR)
2. `data_staleness_hours` ASC (Freshest data first. Example: 2 hours stale appears above 3 days stale).
3. `days_since_last_mentor_action` DESC (Oldest untouched cases first).

---

## 7. Learning Workspace (RAG Module)

### 7.1 Resource Access Scope (RBAC)
Documents are not just bound to a `student_id`. Access is governed by scope:
- `OWNER_ONLY` (Student's private notes)
- `COURSE_SHARED` (Accessible to all students enrolled in a specific course run)
- `TEACHER_PUBLISHED` (Material pushed by faculty)
- `INSTITUTION_PUBLISHED` (Global guides)

### 7.2 Quiz Generation Contract
- LLM must be provided retrieved chunks based on the scope above.
- **Graceful Failure:** If no chunks are retrieved, generation MUST abort. No hallucinated quizzes.
- **Citation:** The LLM output MUST provide exact references, returning:
  `{"source_document_id": "uuid", "source_chunk_id": "uuid", "citation_text": "..."}`
- **Prompt Injection Guard:** All retrieved content is explicitly marked and bounded as untrusted context in the prompt (`<UNTRUSTED_CONTENT>...</UNTRUSTED_CONTENT>`). Agents are instructed to ignore system commands found within these boundaries.

---

## 8. Event & Trigger Engine

The central nervous system. Deterministic engines emit events; the supervisor agent consumes them.
**Core Events:**
`ATTENDANCE_UPDATED`, `ASSESSMENT_GRADED`, `EXAM_APPROACHING`, `TASK_OVERDUE`, `PLAN_ACCEPTED`, `PLAN_DECLINED`, `DATA_CONFLICT`, `MENTOR_FOLLOWUP_DUE`

---

## 9. Calendar / Event Engine

Maintains the timeline of the batch.
**Event Types:** `ACADEMIC_EVENT`, `HOLIDAY`, `CLASS`, `EXAM`, `DEADLINE`.
Supports `RESCHEDULED_EVENT` and `CANCELLED_EVENT` statuses to properly supersede old dates without deleting history.

---

## 10. Intervention Case State Machine

Defines the exact lifecycle of an intervention.
`OPEN` → `IN_REVIEW` → `PLAN_PROPOSED` → `PENDING_APPROVAL` → `ACTIVE` → `MONITORING` → `REPLAN_REQUIRED` → `ESCALATION_REQUIRED` → `RESOLVED` → `CLOSED`

---

## 11. Data Ingestion & Conflict Resolution

Handles bulk data entry (e.g., CSV).
1. **UPLOAD** → **PARSE** → **SCHEMA VALIDATE**
2. **RECORD VALIDATE** (types, ranges)
3. **MATCH** (to student/course/period)
4. **CONFLICT DETECT:** Occurs if incoming data disagrees with existing verified data for the exact same underlying fact (not just a large numeric drop).
5. **QUARANTINE:** Conflicting incoming record is placed in `CONFLICT` state.
6. **FREEZE:** Automation depending *specifically on that conflicting fact* is paused.
7. **HUMAN RESOLUTION:** Admin/Faculty selects the authoritative value.
8. **VERSION:** Losing record is marked `SUPERSEDED`. Winning is `VERIFIED`.
9. **RECOMPUTE** derived state → **RESUME** automation.

---

## 12. RBAC / Permission Engine

Strict permission matrix enforced at the API/tool layer:
- **Student:** Own data only.
- **Faculty:** Data for assigned course runs only.
- **CT:** Aggregates and class data for assigned batch.
- **Mentor:** Full 360 view for assigned mentees only.
- **HOD:** Department aggregates and escalations.
- **Admin:** Configuration, imports, role mapping.

---

## 13. Audit & Provenance

Every state mutation (attendance entry, grade update, plan approval, conflict resolution) must record:
- `actor_id` (UUID of user or system agent)
- `timestamp`
- `action_type`
- `previous_state` (JSON)
- `new_state` (JSON)
- `source_system` (e.g., CSV_IMPORT, MENTOR_WEB, RULE_ENGINE)

---

## 14. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-05 | Who is the BCREC contact who can provide real data samples for ingestion validation? | All | 🔴 OPEN |
| OQ-06 | What is the exact CIA/PCIA component structure and weightings for autonomous batches at BCREC? | Bishesh | 🔴 OPEN |
| OQ-07 | How are MAR (Mandatory Additional Requirements) points calculated? | Abhijit | 🔴 OPEN |
