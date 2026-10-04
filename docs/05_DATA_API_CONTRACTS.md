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

> [!CAUTION]
> **OQ-06 (CIA/PCIA exact structure) is still OPEN.** The Assessment tables are marked
> `[PENDING OQ-06]` and must not be built until that open item is resolved by Bishesh.

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

**[PENDING OQ-06] — Exact CIA/PCIA component structure needed from Bishesh before finalizing.**

### `assessment_components`
-- Defines the type and weight of each CIA/PCIA component for a course run.
```sql
id               UUID PRIMARY KEY
course_run_id    UUID REFERENCES course_runs(id)
name             TEXT NOT NULL               -- e.g., 'CIA-1', 'Lab Record'
type             TEXT NOT NULL               -- CIA | PCIA | LAB | ASSIGNMENT
max_marks        NUMERIC(5,2) NOT NULL
weight_percent   NUMERIC(5,2)                -- [PENDING OQ-06]
is_mandatory     BOOLEAN DEFAULT TRUE
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
source_system    TEXT NOT NULL               -- CSV_IMPORT | MENTOR_WEB | RULE_ENGINE | AGENT
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
trigger_events   JSONB                       -- Array of event IDs that opened the case
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
evidence         JSONB NOT NULL
student_decision TEXT                        -- ACCEPTED | DECLINED | CUSTOMIZED
student_reason   TEXT                        -- Optional decline reason
decided_at       TIMESTAMPTZ
mentor_decision  TEXT                        -- APPROVED | EDITED | REJECTED
mentor_notes     TEXT
mentor_acted_at  TIMESTAMPTZ
```

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
institution_id   UUID REFERENCES institutions(id)
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

---

## 13. Internal API Boundary Rules

These rules govern how every service and agent may interact with the database.
**No agent writes to these tables directly via SQL.**
All writes go through the typed API layer.

| Resource | GET | POST | PATCH | DELETE |
|---|---|---|---|---|
| `/students/{id}/state` | Student (own), Mentor, Faculty, Admin | — | — | — |
| `/students/{id}/attendance` | As above | Admin, Faculty | Admin, Faculty | — |
| `/students/{id}/tasks` | Student (own), Mentor | System Agent, Mentor | Student (own) | — |
| `/students/{id}/cases` | Student (own), Mentor | Rule Engine | Mentor | — |
| `/cases/{id}/plans` | Student, Mentor | System Agent | Student, Mentor | — |
| `/institution-rules` | Admin | Admin | Admin | — |
| `/import/upload` | Admin | Admin | — | — |
| `/documents` | Scoped by access_scope | Student, Faculty | — | — |

---

## 14. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-05 | Who is the BCREC contact for real data samples? | All | 🔴 OPEN |
| OQ-06 | Exact CIA/PCIA component structure and weightings for autonomous batches | Bishesh | 🔴 OPEN — blocks finalizing `assessment_components` |
| OQ-07 | MAR points calculation rules | Abhijit | 🔴 OPEN |
| OQ-08 | Confirm correct roll number format at BCREC | Bishesh | 🔴 OPEN |
