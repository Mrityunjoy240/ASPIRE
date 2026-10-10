# 05_DATA_API_CONTRACTS.md
# EduGen AI / ASPIRE — Data & API Contracts

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Primary Reviewer:** Bishesh Ghosh (Backend / Database)
**Date:** 03 October 2026
**Version:** 1.0

> [!IMPORTANT]
> This document is the source of truth for the PostgreSQL schema and internal API boundaries.
> **The System Spec (`03_SYSTEM_SPEC.md`) and this document must agree exactly.**
> If there is a conflict between them, stop and escalate before writing any code.

> **API contract authority (DM-API01 — FROZEN):** The HTTP API source of truth is **FastAPI route definitions + Pydantic request/response models**. FastAPI generates the OpenAPI document from them; the committed generated artifact **`contracts/openapi.json`** is the reviewable contract consumed by the TypeScript frontend (generated TS types are derived artifacts — never hand-edited, no duplicate contract files, CI fails on drift). This document remains the source of truth for the PostgreSQL schema and the *specification* of API boundaries; the machine-readable contract artifact is `contracts/openapi.json`.

> [!NOTE]
> **OQ-06 = RESOLVED (DM-ASSESS01): configuration-driven assessment structure.** Assessment
> components are configuration — no fixed/universal CIA/PCIA weighting exists. Scheme
> configuration uses the versioned `institution_rules` pattern (§12); `assessment_components`
> (§6) materializes components per course run. The BCREC AIML theory template (40/40/60) is a
> versioned configuration example (03 §4.0), never a schema constant.

---

## 1. General Rules

- **All tables have:** `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`.
- **Soft deletes only:** No production table uses `DELETE`. Use `status` or `deleted_at`.
- **All monetary/percentage values:** Use `NUMERIC(5,2)`, never `FLOAT`.
- **All timestamps:** `TIMESTAMPTZ` (with timezone). Never `TIMESTAMP`.
- **Enums:** Defined as PostgreSQL `TYPE` enums, not raw strings.
- **Foreign Keys:** Always explicitly defined with `ON DELETE RESTRICT` unless specified otherwise.

---

## 2. Core Identity & Auth Tables

### `institutions`
```sql
id               UUID PRIMARY KEY
name             TEXT NOT NULL
slug             TEXT UNIQUE NOT NULL        -- e.g., 'bcrec'
status           TEXT DEFAULT 'ACTIVE'
created_at       TIMESTAMPTZ
```

### `users`
```sql
id               UUID PRIMARY KEY            -- mirrors Supabase Auth user id
institution_id   UUID REFERENCES institutions(id)
email            TEXT UNIQUE NOT NULL
full_name        TEXT NOT NULL
status           TEXT DEFAULT 'ACTIVE'       -- ACTIVE | SUSPENDED
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

**Enum: `user_role`**
`STUDENT | FACULTY | CLASS_TEACHER | MENTOR | HOD | ADMIN`

**Role resolution (FINAL):** `user_role_assignments` (below) is the **sole source of truth** for ASPIRE application roles. A user may hold multiple active role assignments. JWT role claims are never used, and there is no second authorization source on `users`.

### `user_role_assignments`
```sql
id                UUID PRIMARY KEY            -- surrogate PK (DM-AUTH03)
user_id           UUID REFERENCES users(id)
institution_id    UUID REFERENCES institutions(id)
role              user_role NOT NULL
scope_entity_type TEXT                       -- optional scope type; NULL = institution-wide
scope_entity_id   UUID                       -- optional scope id
valid_from        TIMESTAMPTZ
valid_to          TIMESTAMPTZ                -- NULL = open-ended
assigned_by       UUID REFERENCES users(id)
created_at        TIMESTAMPTZ
```

---

## 3. Academic Structure Tables

### `programmes`
```sql
id               UUID PRIMARY KEY
institution_id   UUID REFERENCES institutions(id)
name             TEXT NOT NULL               -- e.g., 'B.Tech CSE (AIML)'
code             TEXT NOT NULL               -- e.g., 'BTECH_CSE_AIML'
total_semesters  INT NOT NULL
```

### `batches`
```sql
id               UUID PRIMARY KEY
institution_id   UUID REFERENCES institutions(id)
programme_id     UUID REFERENCES programmes(id)
name             TEXT NOT NULL               -- e.g., '2024-2028'
start_year       INT NOT NULL
end_year         INT NOT NULL
status           TEXT DEFAULT 'ACTIVE'       -- ACTIVE | GRADUATED | SUSPENDED
```

### `semesters`
```sql
id               UUID PRIMARY KEY
batch_id         UUID REFERENCES batches(id)
semester_number  INT NOT NULL
start_date       DATE NOT NULL
end_date         DATE NOT NULL
status           TEXT DEFAULT 'UPCOMING'     -- UPCOMING | ACTIVE | COMPLETED
```

### `courses`
```sql
id               UUID PRIMARY KEY
institution_id   UUID REFERENCES institutions(id)
name             TEXT NOT NULL               -- e.g., 'Database Management Systems'
code             TEXT NOT NULL               -- e.g., 'CS501'
credit_hours     INT
```

### `course_runs`
-- A specific course offered in a specific semester to a specific batch.
```sql
id               UUID PRIMARY KEY
course_id        UUID REFERENCES courses(id)
semester_id      UUID REFERENCES semesters(id)
batch_id         UUID REFERENCES batches(id)
faculty_id       UUID REFERENCES users(id)   -- Subject Faculty
total_classes    INT NOT NULL DEFAULT 0
```

---

## 4. Student Profile Table

### `student_profiles`
```sql
id               UUID PRIMARY KEY
user_id          UUID REFERENCES users(id) UNIQUE
batch_id         UUID REFERENCES batches(id)
roll_number      TEXT NOT NULL
mentor_id        UUID REFERENCES users(id)   -- Assigned Mentor
class_teacher_id UUID REFERENCES users(id)   -- Assigned CT
enrollment_year  INT NOT NULL
```

---

## 5. Attendance Tables

### `attendance_records`
```sql
id               UUID PRIMARY KEY
student_id       UUID REFERENCES student_profiles(id)
course_run_id    UUID REFERENCES course_runs(id)
class_date       DATE NOT NULL
status           attendance_status NOT NULL  -- PRESENT | ABSENT | LATE (reserved) | CANCELLED
source_type      TEXT NOT NULL               -- CSV_IMPORT | MANUAL_ENTRY | API
source_id        TEXT                        -- import batch ID or entry ID
record_status    TEXT DEFAULT 'VERIFIED'     -- VERIFIED | PROVISIONAL | CONFLICT | SUPERSEDED
recorded_by      UUID REFERENCES users(id)
version          INT NOT NULL DEFAULT 1
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

**Enum: `attendance_status`**
`PRESENT | ABSENT | LATE | CANCELLED`

> **DM-NEW-LATE01 = DECIDED (Option C):** `LATE` is **reserved / unsupported as an input status in v1** — kept in the enum for schema compatibility only. The v1 attendance engine never generates `LATE`; a VERIFIED attendance calculation input must not contain `LATE`. If an imported or manually entered record contains `LATE`, the input MUST fail validation and be rejected — it must not become a VERIFIED attendance record and must not be silently coerced to PRESENT or ABSENT. No grace-period/configuration semantics in v1. Real institutional semantics may be decided later after BCREC validation.

### `attendance_derived_state`
-- Written by the Attendance Engine after every update. Never written by agents.
```sql
id                       UUID PRIMARY KEY
student_id               UUID REFERENCES student_profiles(id)
course_run_id            UUID REFERENCES course_runs(id)
classes_conducted        INT NOT NULL
classes_attended         INT NOT NULL
attendance_percentage    NUMERIC(5,2)        -- NULL if conducted = 0
risk_band                TEXT                -- SAFE | WARNING | CRITICAL | DATA_CONFLICT
required_to_recover      INT                 -- from calculate_required_classes()
computed_at              TIMESTAMPTZ NOT NULL
```

---

## 6. Assessment Tables

**FROZEN — DM-ASSESS01 (OQ-06 resolved): configuration-driven assessment structure.**

The entities below represent configurable assessment components: component/type, full marks (`max_marks`), contribution/weighting (`weight_percent`), applicability (`is_mandatory`), and scope (`course_run_id` → course/term → programme → institution). Effective dates and versioning are provided by the existing **`institution_rules`** pattern (§12: `scope_level`, `scope_id`, `value JSONB`, `effective_from`, `effective_to`, `version`, `status`) — the assessment scheme (full component hierarchy incl. sub-weights such as Class Test/Assignment/Attendance inside CIA-1) lives there as a versioned configuration entry. **No new columns are invented here — the existing architecture already has the extensibility pattern.**

> **Bounded contract follow-up (not silently invented):** if per-course-run materialization of *nested* sub-components is required (a parent/child link inside `assessment_components`), that single missing piece (`parent_component_id`) must be added as an explicit, reviewed migration — flagged here rather than guessed. The scheme JSONB can already express the hierarchy in the meantime.

### `assessment_components`
-- Configuration rows for a course run's assessment components (DM-ASSESS01).
-- Configuration lives here/in institution_rules; calculation logic lives in the engine — never the reverse.
```sql
id               UUID PRIMARY KEY
course_run_id    UUID REFERENCES course_runs(id)
name             TEXT NOT NULL               -- e.g., 'CIA-1', 'Class Test', 'Assignment', 'ESE'
type             TEXT NOT NULL               -- CIA | CIA-1 | CIA-2 | PCIA | ESE | PESE | LAB | ASSIGNMENT | CLASS_TEST | ATTENDANCE | QUIZ | PROJECT | VIVA
max_marks        NUMERIC(5,2) NOT NULL       -- full marks
weight_percent   NUMERIC(5,2)                -- contribution/weighting from the active scheme configuration (DM-ASSESS01)
is_mandatory     BOOLEAN DEFAULT TRUE        -- applicability
```

### `assessment_submissions`
```sql
id                     UUID PRIMARY KEY
student_id             UUID REFERENCES student_profiles(id)
assessment_component_id UUID REFERENCES assessment_components(id)
status                 assessment_submission_status NOT NULL
obtained_marks         NUMERIC(5,2)                -- NULL if not graded
maximum_marks          NUMERIC(5,2) NOT NULL
submitted_at           TIMESTAMPTZ
graded_at              TIMESTAMPTZ
graded_by              UUID REFERENCES users(id)
record_status          TEXT DEFAULT 'VERIFIED'     -- VERIFIED | PROVISIONAL | CONFLICT | SUPERSEDED
version                INT NOT NULL DEFAULT 1
```

**Enum: `assessment_submission_status`**
`NOT_SUBMITTED | SUBMITTED_PENDING_EVALUATION | GRADED | OFFICIAL_ZERO | WITHHELD | CANCELLED`

---

## 7. Audit & Provenance Table

Every privileged write in the entire system produces one of these rows.

### `audit_log`
```sql
id               UUID PRIMARY KEY
actor_id         UUID REFERENCES users(id)   -- Can be a system agent UUID
actor_type       TEXT NOT NULL               -- USER | SYSTEM_AGENT
action_type      TEXT NOT NULL               -- e.g., 'ATTENDANCE_UPDATED', 'PLAN_APPROVED'
entity_table     TEXT NOT NULL               -- e.g., 'attendance_records'
entity_id        UUID NOT NULL
previous_state   JSONB
new_state        JSONB
source_system    TEXT NOT NULL               -- CSV_IMPORT | MENTOR_WEB | RULE_ENGINE | AGENT | STUDENT_APP
created_at       TIMESTAMPTZ NOT NULL
```

---

## 8. Unified Task Table

### `student_tasks`
```sql
id               UUID PRIMARY KEY
student_id       UUID REFERENCES student_profiles(id)
source_type      task_source_type NOT NULL
source_id        UUID NOT NULL               -- FK to originating event/plan/case
created_by       UUID REFERENCES users(id)   -- user or system actor
title            TEXT NOT NULL
deadline         TIMESTAMPTZ
status           task_status NOT NULL DEFAULT 'PENDING'
explicit_priority INT                        -- Optional override for sort
urgency_score    INT                         -- Computed by priority engine (0-100)
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

**Enum: `task_source_type`**
`CALENDAR | ASSESSMENT | AI_PLAN | MENTOR`

**Enum: `task_status`**
`PENDING | COMPLETED | SNOOZED`

> **DM-SS02 / OQ-SS02 = DECIDED (Option A):** `OVERDUE` must NOT exist as an independent persisted value. It is derived at query time when `status = PENDING AND deadline < now`; tasks with `deadline = NULL` can never be `OVERDUE`; completing a task removes the derived state automatically. No scheduler job rewrites `PENDING → OVERDUE` in the database.

---

## 9. Intervention Case Tables

### `intervention_cases`
```sql
id               UUID PRIMARY KEY
student_id       UUID REFERENCES student_profiles(id)
mentor_id        UUID REFERENCES users(id)
status           intervention_case_status NOT NULL DEFAULT 'OPEN'
urgency_band     TEXT NOT NULL               -- URGENT | ATTENTION | MONITOR
trigger_events   JSONB                       -- Array of event IDs (strings) that opened the case
opened_at        TIMESTAMPTZ NOT NULL
resolved_at      TIMESTAMPTZ
closed_at        TIMESTAMPTZ
```

**Enum: `intervention_case_status`**
`OPEN | IN_REVIEW | PLAN_PROPOSED | PENDING_APPROVAL | ACTIVE | MONITORING | REPLAN_REQUIRED | ESCALATION_REQUIRED | RESOLVED | CLOSED`

### `intervention_plans`
```sql
id               UUID PRIMARY KEY
case_id          UUID REFERENCES intervention_cases(id)
created_by       TEXT NOT NULL               -- 'SYSTEM_AGENT' or user UUID
status           TEXT NOT NULL               -- PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED
plan_actions     JSONB NOT NULL              -- Structured action array
reason_codes     TEXT[] NOT NULL
evidence         JSONB NOT NULL              -- Array of structured evidence entries (contract below)
student_decision TEXT                        -- ACCEPTED | DECLINED | CUSTOMIZED
student_reason   TEXT                        -- Optional decline reason
decided_at       TIMESTAMPTZ
mentor_decision  TEXT                        -- APPROVED | EDITED | REJECTED
mentor_notes     TEXT
mentor_acted_at  TIMESTAMPTZ
```

**Evidence entry contract (DEC-01, approved).** `evidence` persists as a JSON
**array** of entry objects (empty array `[]` = no evidence yet). Each entry has
exactly these fields:

| Field | Type | Rules |
|---|---|---|
| `id` | string (UUID) | Stable entry identity for `evidenceRefs`; generated with the project's UUID convention (uuid4 at build time). Unique within one `evidence` array. |
| `label` | string | Non-empty human-readable caption. |
| `value` | string \| number \| boolean | Typed scalar. Backend-typed facts keep their original type (numbers are not stringified). Objects/arrays/`null`/NaN are rejected. |
| `source` | string | **Verified provenance only** — a backend source or approved source metadata. Never produced by the LLM, never defaulted. |
| `timestamp` | string (ISO-8601, UTC offset) | **Provenance time of the observed fact**, timezone-aware. Never clocked at write time, never from model output. |

Conversion rule: the LLM/agent layer parses `evidence` as `string[]`
(CONSTITUTION A-05, `10_TASKS` supervisor step 4). Before persistence that
array passes through the conversion boundary in `app/services/evidence.py`
(`convert_llm_evidence`), which requires backend-supplied
`EvidenceProvenance(source, timestamp)` and refuses (raises) when provenance
is missing or an item is unsupported — provenance-free input never produces an
entry, so no metadata can be fabricated. Producers holding typed backend facts
use `build_evidence_entry` so value types survive. Versioning of this contract
is deferred (DEC-01).

---

## 10. Learning Workspace Tables

### `learning_documents`
```sql
id               UUID PRIMARY KEY
uploaded_by      UUID REFERENCES users(id)
access_scope     TEXT NOT NULL               -- OWNER_ONLY | COURSE_SHARED | TEACHER_PUBLISHED | INSTITUTION_PUBLISHED
scope_id         UUID                        -- course_run_id if COURSE_SHARED, null if INSTITUTION_PUBLISHED
filename         TEXT NOT NULL
storage_path     TEXT NOT NULL               -- Object storage reference
processing_status TEXT DEFAULT 'PENDING'    -- PENDING | CHUNKED | FAILED
subject_tag      TEXT
created_at       TIMESTAMPTZ
```

### `document_chunks`
```sql
id               UUID PRIMARY KEY
document_id      UUID REFERENCES learning_documents(id)
chunk_index      INT NOT NULL
content          TEXT NOT NULL               -- Raw text of the chunk
embedding        vector(1024)                -- pgvector (BGE-M3 produces 1024-dim)
created_at       TIMESTAMPTZ
```

---

## 11. Data Conflict Registry

### `data_conflicts`
```sql
id               UUID PRIMARY KEY
entity_table     TEXT NOT NULL
entity_id        UUID NOT NULL
existing_value   JSONB NOT NULL
incoming_value   JSONB NOT NULL
source_a         TEXT NOT NULL               -- e.g., 'MANUAL_ENTRY'
source_b         TEXT NOT NULL               -- e.g., 'CSV_IMPORT'
status           TEXT DEFAULT 'OPEN'         -- OPEN | RESOLVED | IGNORED
resolver_id      UUID REFERENCES users(id)
resolution       JSONB
resolved_at      TIMESTAMPTZ
created_at       TIMESTAMPTZ
```

---

## 12. Institution Configuration Table

### `institution_rules`
```sql
id               UUID PRIMARY KEY
institution_id   UUID NOT NULL REFERENCES institutions(id)  -- DEC-02: institution-owned, enforced by migration 013
rule_id          TEXT NOT NULL               -- e.g., 'attendance_threshold'
scope_level      TEXT NOT NULL               -- INSTITUTION | BATCH | PROGRAMME | SEMESTER
scope_id         UUID                        -- ID of the scoped entity
value            JSONB NOT NULL              -- supports numeric, boolean, complex objects
effective_from   TIMESTAMPTZ NOT NULL
effective_to     TIMESTAMPTZ                 -- NULL means currently active
version          INT NOT NULL DEFAULT 1
status           TEXT DEFAULT 'ACTIVE'
updated_by       UUID REFERENCES users(id)
```

> **DEC-02 (approved):** every rule row belongs to an institution — there are
> no global / institution-independent rules. Migration 012 originally left
> `institution_id` nullable; migration 013 enforces `NOT NULL` with a
> preflight that aborts while any NULL-ownership row exists.

---

## 13. Internal API Boundary Rules

These rules govern how every service and agent may interact with the database.
**No agent writes to these tables directly via SQL.**
All writes go through the typed API layer.

> The machine-readable contract for these endpoints is the generated **`contracts/openapi.json`** (DM-API01) — FastAPI routes + Pydantic models are the source of truth; the committed artifact is generated, never hand-edited.

| Resource | GET | POST | PATCH | DELETE |
|---|---|---|---|---|
| `/students/{id}/state` | Student (own), Mentor, Faculty, Admin | — | — | — |
| `/students/{id}/attendance` | As above | Admin, Faculty | Admin, Faculty | — |
| `/students/{id}/tasks` | Student (own), Mentor | System Agent, Mentor | Student (own) | — |
| `/students/{id}/cases` | Student (own), Mentor | Rule Engine | Mentor | — |
| `/cases/{id}/plans` | Student, Mentor | System Agent | Student, Mentor | — |
| `/cases` | Mentor (assigned mentees), HOD | — | — | — |
| `/institution-rules` | Admin | Admin | Admin | — |
| `/import/upload` | Admin | Admin | — | — |
| `/documents` | Scoped by access_scope | Student, Faculty | — | — |

---

## 14. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-05 | Who is the BCREC contact for real data samples? | All | 🔴 OPEN |
| OQ-06 | Exact CIA/PCIA component structure and weightings for autonomous batches | Bishesh | ✅ RESOLVED — DM-ASSESS01 (OQ-06 = RESOLVED): configuration-driven scheme via `institution_rules` + `assessment_components`; no universal weighting |
| OQ-07 | MAR points calculation rules | Abhijit | 🔴 OPEN |
| OQ-08 | Confirm correct roll number format at BCREC | Bishesh | 🔴 OPEN |
