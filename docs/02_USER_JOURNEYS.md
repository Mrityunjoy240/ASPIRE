# 02_USER_JOURNEYS.md
# EduGen AI / ASPIRE — User Journeys

**STATUS: 🟡 UNDER REVIEW — Reviewed by Mrityunjoy Kapat (02 Oct 2026). Pending real-user validation (OQ-05).**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 02 October 2026
**Version:** 1.1

> [!IMPORTANT]
> These journeys are intentionally minimal. We define only the flows required to drive
> `03_SYSTEM_SPEC.md` and `05_DATA_API_CONTRACTS.md` without guessing.
> Do NOT expand to 50+ journeys before specs are FROZEN.

> [!CAUTION]
> **[NEEDS VALIDATION]** — All journeys require confirmation from at least one real BCREC
> student and one BCREC mentor before this document moves to FROZEN. (Open Item OQ-05)

---

## Architectural Layer Convention
Every journey follows this strict layer separation. AI coding agents must not collapse these layers.

```
FACT (verified data in DB)
    ↓
DERIVED STATE (deterministic rule engine output)
    ↓
RISK SIGNAL (deterministic priority engine)
    ↓
AI INTERPRETATION (LLM agent — explains, proposes)
    ↓
PROPOSED ACTION (structured plan output)
    ↓
HUMAN APPROVAL (student / mentor — accept / edit / decline)
    ↓
EXECUTION (permitted tool calls only)
    ↓
VERIFICATION (state recomputed, outcome checked)
    ↓
CLOSE / REPLAN / ESCALATE
```

---

## 1. Student Journeys

### 1.1 — P0 North Star: Academic Risk Detection & Recovery

**Trigger:** Attendance rule engine derives that student is below the configured ESE threshold
and a deadline or exam is within the configured urgency window.

**Pre-condition:** Attendance data is verified (not in Conflict status). If data is conflicting,
see the data conflict branch at the end of this journey.

```
Step 1 — Notification
  System emits push/in-app notification.
  Notification carries: subject, risk type, urgency band.
  Does NOT include authoritative attendance % in the notification body
  if underlying data is stale or provisional.

Step 2 — Open Academic Health
  Student opens the mobile app → Home screen shows Academic Health card.
  Card shows: URGENT badge, subject name, risk type.
  Student taps to open the detail view.

Step 3 — Review Risk + Evidence
  Student sees a structured evidence panel:
  ┌─────────────────────────────────────┐
  │ Subject: DBMS                       │
  │ Attendance: 73%     Threshold: 75%  │
  │ Classes conducted: [N]              │
  │ Classes attended:  [M]              │
  │ Upcoming classes before exam: [K]   │
  │ Exam in: 8 days                     │
  │ Assessment trend: Declining         │
  │ Data freshness: Updated 2h ago      │
  └─────────────────────────────────────┘
  This panel is derived from deterministic engine output, NOT LLM-generated.

Step 4 — What-If Projection
  Student taps "What-If Calculator".
  System runs the attendance rule engine interactively:
    "If you attend the next [X] classes, your attendance reaches [Y]%."
  Student can drag a slider to explore scenarios.
  Output is deterministic — same input always produces same output.

Step 5 — Review AI Recovery Plan
  AI agent (having read the engine-derived facts) proposes a recovery plan.
  The plan is structured, not prose:
  {
    "reason_codes": ["LOW_ATTENDANCE", "EXAM_APPROACHING"],
    "evidence": ["attendance 73%", "threshold 75%", "exam 8d"],
    "actions": [
      { "type": "ATTEND_CLASS", "subject": "DBMS", "target_classes": [next N] },
      { "type": "STUDY_BLOCK",  "topic": "DBMS Unit 3", "duration_min": 45 },
      { "type": "PRACTICE_QUIZ", "topic": "DBMS", "source": "uploaded notes" }
    ],
    "approval_required": false,
    "confidence_level": "HIGH"
  }
  Student sees a human-readable rendering of this plan WITH the evidence.
  (DEC-01: the `evidence: [...]` above is the agent/LLM parse format —
  string[], per CONSTITUTION A-05. Before persistence it is converted to the
  canonical structured entries `{id, label, value, source, timestamp}`
  documented in 05_DATA_API_CONTRACTS.md, which is what the student UI
  renders — the label/value/source/timestamp panel of Step 3.)

Step 6 — Student Decision
  Student must see three options. There is no silent default.
  [Accept Plan]     → go to Step 7
  [Edit / Customize] → student adjusts plan → go to Step 7 with modified plan
  [Decline]          → student optionally provides reason →
                       system records PLAN_DECLINED state →
                       supervisor / intervention logic replans →
                       different plan is proposed or case is routed to mentor

  Decline reason examples surfaced in the UI:
    "I have another exam." / "I can't attend this class." /
    "This takes too much time." / "Other reason."

Step 7 — Accepted Plan → Unified Tasks
  System creates discrete tasks in the student's Unified Obligation stream.
  Student sees: "[View Tasks]" link immediately after accepting.
  Each task has: description, source (AI plan), deadline, status (Pending).
  Student can [Start Task] or [Mark Complete] for each task.
  Tasks are NOT created silently in the background without the student seeing them.

Step 8 — Learning Agent: Targeted Practice
  Learning Agent (already knowing the weak topic from Student State) surfaces:
    "You have DBMS notes uploaded. Do you want a targeted quiz on Unit 3?"
  Student taps [Generate Practice].
  Learning Agent retrieves relevant chunks from uploaded DBMS sources.
  Quiz is generated from verified source content, not hallucinated.
  Student completes quiz.
  Result (score, weak sub-topics) is recorded in Learning State.

Step 9 — System Verifies Updated State
  After each attendance update or task completion, system recomputes derived state.
  State machine transitions:
    Attendance rises above 75% → risk signal resolved → case closed.
    Student completes study tasks → learning state updated.
    Deadline passes without action → case escalation triggered.

Step 10 — Case Resolution
  Improved → case CLOSED, mentor notified.
  Unchanged after follow-up window → case moves to REPLAN_REQUIRED →
    different plan proposed or routed to mentor.
  Student declined repeatedly → ESCALATION_REQUIRED → mentor intervention.
```

**Stale / Conflicting Data Branch (must be handled, not ignored):**
```
If attendance data is in CONFLICT status when notification would fire:
  → Do NOT send "You are at risk" notification.
  → Do NOT show a recovery recommendation.
  → Show: "Your attendance data needs verification. Recovery recommendation is paused."
  → Link to data conflict notice for Admin/Faculty resolution.
  → Resume recommendation after conflict is resolved and state is recomputed.
```

---

### 1.2 — Routine Academic Check-In

**Trigger:** Student proactively opens the app to check their standing.

```
Step 1 — Open App → Home screen.
Step 2 — Student views Student State snapshot:
  - Attendance status per subject (colour-coded, not raw %)
  - Pending assignments with days remaining
  - Upcoming exams within 7 days
  - Any urgent tasks or unread AI guidance
Step 3 — Student opens Task List to see Unified Obligations.
Step 4 — Student decides: nothing urgent → close app.
         Or: deadline today → opens task to complete or request snooze.
```

---

## 2. Mentor Journeys

### 2.1 — P0 North Star: Case Queue Review & Intervention Approval

**Trigger:** Intervention case created for student S-204 (from Journey 1.1, Step 6 or escalation).

**Case state machine (relevant to all mentor journeys):**
```
OPEN
→ IN_REVIEW
→ PLAN_PROPOSED
→ PENDING_APPROVAL
→ ACTIVE
→ MONITORING
→ REPLAN_REQUIRED
→ ESCALATION_REQUIRED
→ RESOLVED
→ CLOSED
```
(Exact frozen lifecycle — `03_SYSTEM_SPEC.md` §10.2. `REPLAN_REQUIRED` returns to `IN_REVIEW`; `ESCALATION_REQUIRED` awaits HOD/CT action.)

```
Step 1 — Mentor logs into Web Workspace → opens Priority Queue.

Step 2 — Queue is ordered by urgency band (URGENT / ATTENTION / MONITOR),
  not alphabetically by student name.
  Each queue card shows WHY the student is there:
  ┌─────────────────────────────────────────────────────┐
  │ [URGENT]  S-204  Rahul Das                          │
  │ • DBMS attendance: 73%  (threshold: 75%)            │
  │ • ESE exam: 8 days away                             │
  │ • Assessment trend: Declining                       │
  │ • 2 tasks pending                                   │
  │ Attendance last updated: 6h ago                     │
  │ Marks last updated: 2 days ago                      │
  │ Last contact: 3 days ago  |  Response: None         │
  └─────────────────────────────────────────────────────┘
  Mentor does NOT need to open each student to understand why they are urgent.

Step 3 — Mentor taps card → opens Student 360 view.
  Full evidence panel visible:
  - All subjects attendance (with freshness indicator per subject)
  - Assessment breakdown
  - Active tasks (accepted/pending/overdue)
  - AI-proposed recovery plan
  - Intervention history

Step 4 — Mentor reviews the AI-proposed plan.
  Plan is shown as structured actions with evidence — same structure as Step 5 in Journey 1.1.

Step 5 — Mentor decision (three paths):
  [Approve Plan]
    → case moves to ACTIVE (mentor approval — `PENDING_APPROVAL → ACTIVE`, 03 §10.2)
    → student receives confirmation notification
    → follow-up scheduled per intervention policy (see below)

  [Edit & Approve]
    → mentor modifies the plan (e.g., adds required 1:1 meeting)
    → edited plan saved with actor + timestamp
    → case moves to ACTIVE (mentor edits + approves — `PENDING_APPROVAL → ACTIVE`, 03 §10.2)
    → student sees the revised plan with mentor's additions

  [Reject → Replan Required]
    → case moves to REPLAN_REQUIRED
    → mentor optionally adds reason/note
    → supervisor agent replans or routes to human contact
    → rejection is recorded (not silently discarded)

  [Request Student Meeting]
    → case moves to IN_REVIEW
    → system creates a meeting request task for both student and mentor
    → case remains open until meeting is logged

  [Snooze / Monitor: X days]
    → case moves to MONITORING
    → system suppresses queue alert for configured period
    → case returns to queue if state worsens during monitoring window

Step 6 — Follow-up (intervention-type specific, not a fixed 3 days):
  Attendance intervention → follow-up triggered after next attendance data update
  Study intervention       → follow-up triggered after quiz completion or next assessment
  Assignment intervention  → follow-up triggered at the assignment deadline
  Mentor can also manually set a custom follow-up date.

Step 7 — Follow-up evaluation:
  State improved (attendance above threshold, tasks completed) → case RESOLVED → CLOSED.
  State unchanged → case returns to REPLAN_REQUIRED.
  Student non-responsive → case moves to ESCALATION_REQUIRED.
```

---

### 2.2 — Case Escalation

**Trigger:** ESCALATION_REQUIRED state reached (student non-responsive, or plan repeatedly failed).

```
Step 1 — Mentor sees ESCALATION_REQUIRED flag in queue.
Step 2 — Mentor opens full case history:
  - Original risk event
  - All plans proposed
  - Student responses (accepted/declined/ignored)
  - Intervention outcomes
  - All mentor actions
Step 3 — Mentor adds an escalation note.
Step 4 — Mentor selects escalation target: HOD / CT / Support Services.
Step 5 — Escalated case appears in the target's view with full history.
Step 6 — Original mentor retains visibility; case ownership is transferred.
```

---

## 3. Faculty / CT Journeys (P1)

### 3.1 — Course Operational Snapshot (Subject Faculty)

```
Step 1 — Faculty logs in → Web Workspace → assigned subject view.
Step 2 — Sees course analytics: attendance distribution, assessment breakdown, missing data alerts.
Step 3 — Identifies that a significant portion of the class is below threshold on one topic.
Step 4 — Faculty uploads supplementary material for that topic to the Learning Workspace.
Step 5 — Faculty optionally proposes a notice or announces a remedial class through the system.
```

---

### 3.2 — Class-Wide Attendance Review (CT)

```
Step 1 — CT logs in → Web Workspace → class view.
Step 2 — Views attendance aggregated across all subjects for the assigned batch.
Step 3 — Identifies students consistently missing multiple subjects.
Step 4 — CT can trigger a mentor review request for those students.
```

---

## 4. HOD Journeys (P1)

### 4.1 — Department Health Check

```
Step 1 — HOD logs in → Web Workspace → Department Dashboard.
Step 2 — Views aggregates: department attendance trends, missing assessment data.
Step 3 — Reviews mentor caseload distribution.
Step 4 — Reviews escalated cases from mentors.
Step 5 — HOD decides institutional response; records decision in the system.
```

---

## 5. System Journeys

### 5.1 — Data Ingestion & Conflict Resolution

**Trigger:** Admin uploads a CSV file containing updated attendance records.

**Definition of a conflict (important):**
A conflict is NOT a large attendance drop. A large drop can be a legitimate fact.
A conflict is when **two sources or two versions assert different values for the same
underlying fact for the same student / course / time period.**

Example of a conflict:
```
Source A (faculty entry, verified):  DBMS attendance for S-204 = 81%  [as of Batch Day 45]
Source B (new CSV import):           DBMS attendance for S-204 = 73%  [as of Batch Day 45]
```

```
Step 1  — Admin uploads CSV via the import interface.
Step 2  — System parses file format and validates schema.
Step 3  — Record-level validation: required fields, data types, date formats, range checks.
Step 4  — System matches each record to student / course / attendance period via
           configured identifiers.
Step 5  — System compares incoming record to existing verified or provisional records
           for the same fact and period.
Step 6  — Conflict detected (two sources assert different values for the same fact/period):
           → Conflicting record is quarantined (not committed as authoritative).
           → Status of the affected record set: CONFLICT.
Step 7  — Automated actions that DEPEND ON the conflicting fact are paused.
           Scope is narrow: only automation that uses the attendance % for DBMS is frozen.
           Other automation (quiz generation, career tasks, other subjects) continues normally.
Step 8  — Authorized Faculty or Admin receives a conflict alert.
           Conflict review panel shows:
           • Existing value: 81%  (source: faculty entry, verified, date/time, actor)
           • Incoming value: 73%  (source: CSV import, batch ID, row reference)
           • Previous correction history if any
           • Both records side-by-side with full provenance metadata
Step 9  — Human selects the authoritative value, or submits a corrected value.
Step 10 — System writes resolution:
           • Authoritative record saved with new status: VERIFIED
           • Superseded record preserved in history with status: SUPERSEDED
           • Resolution metadata saved: resolver actor, timestamp, decision reason
Step 11 — Student State recomputed for affected student(s).
Step 12 — Downstream derived state re-evaluated:
           • Risk signals recomputed
           • Urgent tasks re-evaluated
           • Open intervention cases re-evaluated
Step 13 — Paused automation for the affected fact is resumed with the resolved value.
Step 14 — Audit event emitted: records the conflict, both values, resolution, resolver.
```

---

*Document version 1.1 — Corrections applied after Mrityunjoy review (02 Oct 2026)*
*Source: Master Product Engineering Book v1.0 + Constitution + PRD v1.1 review decisions*
