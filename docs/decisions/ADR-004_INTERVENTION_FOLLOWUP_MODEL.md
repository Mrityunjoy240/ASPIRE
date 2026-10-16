# ADR-004: Intervention Follow-up Persistence Model

**STATUS: ✅ ACCEPTED — Team Lead directive (Mrityunjoy Kapat), 13 October 2026 (option C)**
**Date:** 13 October 2026
**Author:** OpenCode (implementation agent)
**Amends:** `docs/05_DATA_API_CONTRACTS.md §9` (new `intervention_follow_ups` table + API shape) — via this documented decision only (DM process, ADR-002 precedent). No change to the frozen transition table `03_SYSTEM_SPEC.md §10.2`, the event catalog `03 §8.2`, or `02_USER_JOURNEYS.md` — this ADR supplies the missing persistence/policy contracts those documents already assume.

> **Amendment 1 (16 October 2026) — senior-review remediation F2/F3/F6.** The
> sections below are amended in place; original wording changed only where the
> review found the contract under-specified or wrong:
> 1. **§2.1** — consumption rule for multiple follow-ups (review F3): stacking
>    stays legal at *scheduling* time, but exactly one follow-up drives a case
>    cycle; competing `SCHEDULED` rows are `CANCELLED` (superseded). `status`
>    comment gains `CANCELLED`; `id` gains `DEFAULT gen_random_uuid()` (F6,
>    migration 017 — applied via ALTER, migration 016 is not rewritten).
> 2. **§2.3/§2.4** — lifecycle gains `SCHEDULED → CANCELLED`; a DUE dispatch
>    against a non-ACTIVE case cancels the stale row (fixes EMITTED-then-stale);
>    one fulfilment cancels its same-case siblings (`SKIP LOCKED`).
> 3. **§2.5** — predicate corrected (review F2): single attendance-rows query
>    (no conflict/aggregate split), `risk_cleared` (WARNING/CRITICAL rows must
>    be gone — the ORIGINAL risk must resolve), materialized-task requirement
>    (vacuous zero-materialized pass removed; approved plan now required), and
>    approved-plan `reason_codes` evaluation (unknown code fails closed).
> 4. **§2.8** — adds audit `FOLLOW_UP_SUPERSEDED`. **§2.9** — `CANCELLED`
>    status decided (cancel *endpoint* still deferred).
> 5. Plan→task materialization is still unimplemented in production (no
>    `PLAN_ACCEPTED` consumer) — until it lands, the materialization
>    requirement is exercised by tests/seeded tasks only; cases resolve only
>    when tasks exist and are completed (fail-closed, never vacuous).

---

## 1. Context & Problem Statement

`03_SYSTEM_SPEC.md §10.2` freezes three follow-up rows that R5 left **blocked** at the contract gate:

| Current State | Action | Actor | Next State |
|---|---|---|---|
| `ACTIVE` | Follow-up due | `RULE_ENGINE` (on scheduler-emitted event) | `MONITORING` |
| `MONITORING` | Improvement verified by engine | `RULE_ENGINE` | `RESOLVED` |
| `MONITORING` | No improvement, follow-up expires | `RULE_ENGINE` (on scheduler-emitted event) | `REPLAN_REQUIRED` |

The producer contract exists (`MENTOR_FOLLOWUP_DUE`, Follow-up Scheduler, 03 §8.2; time-based, 03 §8.3) but **nothing persisted a follow-up**: no due date, no trigger policy, no evaluation window. `schedule_followup(case_id, trigger_policy)` (06 §4) is an unimplemented agent tool; `02 §2.1` Steps 5-7 define the user-facing policy (event-driven triggers per intervention type + optional mentor custom date; evaluation outcomes RESOLVED / REPLAN_REQUIRED / ESCALATION_REQUIRED). The R4 contract gate deferred `MENTOR_FOLLOWUP_DUE` for exactly this reason; R5 could not implement the three rows without inventing a table — which the constitution forbids (`05` is the schema contract; migrations are the schema authority).

**Team lead decision (13 Oct 2026): option (C)** — implement the **full follow-up persistence model per 02 §2.1 event-driven triggers**, unblocking all three rows. (Option (a) keep blocked; option (b) deterministic improvement check without persistence were rejected.)

---

## 2. Decision

### 2.1 New table `intervention_follow_ups` (migration 016, 05 §9)

```sql
id                       UUID PRIMARY KEY DEFAULT gen_random_uuid()  -- default added by migration 017 (F6)
case_id                  UUID NOT NULL REFERENCES intervention_cases(id) ON DELETE RESTRICT
trigger_type             TEXT NOT NULL   -- ATTENDANCE_INTERVENTION | STUDY_INTERVENTION | ASSIGNMENT_INTERVENTION | CUSTOM_DATE
status                   TEXT NOT NULL DEFAULT 'SCHEDULED'  -- SCHEDULED | FULFILLED | EVALUATED | CANCELLED
due_at                   TIMESTAMPTZ     -- CUSTOM_DATE only (mentor-set); NULL for event-driven types
triggered_at             TIMESTAMPTZ     -- fulfilment time (event fired / due date reached)
evaluation_window_ends_at TIMESTAMPTZ    -- set on fulfilment; expiry drives the REPLAN/RESOLVED re-check
evaluated_at             TIMESTAMPTZ     -- improvement check performed (expiry or immediate)
outcome                  TEXT            -- RESOLVED | REPLAN_REQUIRED | NULL while pending
created_by               TEXT NOT NULL   -- 'SYSTEM' or user UUID (mentor)
created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
```

Indexes: `(case_id)`, `(status)`, `(status, due_at)` for the scheduler scan, unique partial guard is **not** added (multiple follow-ups per case are legal — a mentor may stack a custom date on top of an event-driven one); the SCHEDULED→FULFILLED flip under `FOR UPDATE` is the concurrency guard.

**Consumption rule (amendment 1, review F3):** stacking is legal at
*scheduling* time, but **exactly one follow-up drives a case cycle**:
when one follow-up fulfils, every other `SCHEDULED` sibling of that case
is `CANCELLED` in the same transaction; and a DUE dispatch that finds the
case no longer `ACTIVE` cancels that stale row instead of leaving it
`SCHEDULED` behind an already-EMITTED occurrence. Cancellation never
invents a case transition (the `03 §10.2` rows stay authoritative).

### 2.2 Two fulfilment paths, one frozen transition row

The frozen `ACTIVE→MONITORING` row is performed by a **deterministic `RULE_ENGINE` consumer** (`FollowUpConsumer`) in all cases. Two trigger paths feed it, reconciling 03 §10.2's scheduler parenthetical with 02 §2.1 / 06 §4's event-driven policy:

1. **Time path (CUSTOM_DATE)** — the scheduler (`MentorFollowupDueCondition`, 03 §8.3) emits `MENTOR_FOLLOWUP_DUE` when `due_at <= now` (DUE phase). This is the literal "scheduler-emitted event" of the frozen table and **unblocks `MENTOR_FOLLOWUP_DUE` from the R4 deferred list** (`EXAM_APPROACHING` stays deferred — unchanged blocker).
2. **Event path (per 02 §2.1 Step 6 / 06 §4 trigger policies)** — the consumer also subscribes to the policy trigger events and fulfils matching SCHEDULED follow-ups:

   | Follow-up trigger_type | Fulfilling catalog events (03 §8.2) |
   |---|---|
   | `ATTENDANCE_INTERVENTION` | `ATTENDANCE_UPDATED` |
   | `STUDY_INTERVENTION` | `ASSESSMENT_GRADED`, `QUIZ_COMPLETED` |
   | `ASSIGNMENT_INTERVENTION` | `TASK_OVERDUE` (deadline crossed — DM-SS02) |

   The lead's option-C directive explicitly selects 02 §2.1's event-driven triggers; the frozen table's "(on scheduler-emitted event)" parenthetical covers the time path. Both paths are `RULE_ENGINE`-actor transitions. No new catalog event is invented.

### 2.3 Lifecycle & idempotency (lead option A — consumer-side dedup)

Follow-up status drives everything; the payload `phase` (`DUE` | `EXPIRY`) is advisory only:

```
SCHEDULED  --(DUE: event path or scheduler)-->  FULFILLED  --(EXPIRY: scheduler)-->  EVALUATED
SCHEDULED  --(superseded: sibling fulfilled, or case no longer ACTIVE at dispatch)-->  CANCELLED
```

- **Dedup (R4 lead decision, option A):** the follow-up row **is** the persisted logical identity. The consumer locks the row `FOR UPDATE` and flips `SCHEDULED→FULFILLED` (or `FULFILLED→EVALUATED` at expiry) in the same transaction as the case transition + audit row. A duplicate bus dispatch (window B recovery, at-least-once) re-reads the row, sees the committed status, and no-ops. No dedup table; no reliance on the regenerated wire `event_id`.
- **Supersession (amendment 1):** `CANCELLED` is terminal; a `CANCELLED` row receiving a DUE dispatch no-ops. `CANCELLED` rows leave every scheduler/event scan (status filters), so a stale row can never re-fire or block later cycles.
- **Expiry emission:** the scheduler reuses `MENTOR_FOLLOWUP_DUE` with `phase=EXPIRY` when `status=FULFILLED AND evaluation_window_ends_at <= now`. `scheduler_occurrences` idempotency still holds: the logical key differs (`trigger_value = evaluation_window_ends_at` ≠ `due_at`).
- **Window D (handler failure terminal — documented exposure):** the event bus swallows handler exceptions, so a failed consumer run leaves the follow-up SCHEDULED/FULFILLED while the occurrence is already EMITTED — no automatic redelivery. Recovery is operational (mentor schedules a new follow-up). This matches the frozen R4 delivery semantics; it is recorded here rather than papered over.

### 2.4 Transition + evaluation rules

On DUE fulfilment (case must be `ACTIVE`, follow-up `SCHEDULED`):

0. **Supersession first (amendment 1):** with the case lock held, every other
   `SCHEDULED` sibling of the case is `CANCELLED` (audit
   `FOLLOW_UP_SUPERSEDED`, `SKIP LOCKED` — deadlock-safe against a concurrent
   txn holding a sibling while waiting on this case).
1. `follow-up → FULFILLED`, `triggered_at = now`, `evaluation_window_ends_at = now + window`.
2. Case `ACTIVE → MONITORING` (audit `CASE_FOLLOWUP_DUE`).
3. **Immediate improvement check** (below). If verified: case `MONITORING → RESOLVED` (`resolved_at` set, audit `CASE_IMPROVEMENT_VERIFIED`), follow-up `→ EVALUATED outcome=RESOLVED`. Else the case waits in MONITORING until the window expires.

On EXPIRY (case must be `MONITORING`, follow-up `FULFILLED`):

4. Improvement re-check. Verified → `MONITORING → RESOLVED` (`CASE_IMPROVEMENT_VERIFIED`). Not verified → `MONITORING → REPLAN_REQUIRED` (audit `CASE_FOLLOWUP_EXPIRED`). Either way follow-up `→ EVALUATED` with the outcome.

State mismatch (amendment 1): a `SCHEDULED` row dispatched while the case is
**not** `ACTIVE` → the row is `CANCELLED` (audit `FOLLOW_UP_SUPERSEDED`; no
case transition, no rollback-noop — this closes the EMITTED-then-stale
exposure because the DUE condition does not filter on case status). Any other
mismatch (follow-up already processed, expiry case not `MONITORING`) →
**no-op** (idempotent consumer; logged).

`REPLAN_REQUIRED → ESCALATION_REQUIRED` (02 §2.1 Step 7 "student non-responsive") remains **out of scope**: no contracted escalation criteria exist (R5 gate finding stands; routes through the Intervention Agent proposal path once 06 §4 defines criteria + human confirmation).

### 2.5 Improvement predicate (deterministic — engines calculate)

02 §2.1 Step 7: *"State improved (attendance above threshold, tasks completed)"*. Frozen as (**amendment 1** — review F2 corrected the earlier under-specified version):

`verified = attendance_ok AND risk_cleared AND tasks_ok AND reasons_ok`

- **Attendance (`attendance_ok`):** ONE query over **all** `attendance_derived_state` rows for the student (attended, conducted, risk_band); improvement requires: no `DATA_CONFLICT` row (a conflicted feed is never aggregated — conflict is not a band to paper over), `conducted > 0`, and aggregate percentage `>=` the institution `attendance_threshold` (same institution→batch→75.00 fallback resolver as the attendance what-if endpoint, shared in `app/services/rules_reader.py`). **No derived attendance data → not verified** (fail-closed: the engine never invents academic facts — CONSTITUTION A-01).
- **Risk (`risk_cleared`):** **no** row with `risk_band ∈ {WARNING, CRITICAL}`. The ORIGINAL risk must be resolved — an aggregate above threshold can mask a course run that is still at risk (per-run bands). `DATA_CONFLICT` is handled by `attendance_ok`; `SAFE`/`NULL` bands do not block.
- **Tasks (`tasks_ok`):** the case's **APPROVED** plan (`mentor_decision ∈ {APPROVED, EDITED}`, newest first; `PENDING_APPROVAL → ACTIVE` is the approval, so an ACTIVE case always has one) is **required**; every plan action must be materialized as a `student_tasks` row (`source_type = AI_PLAN`, `source_id =` plan id) and every materialized task must be `COMPLETED`. **Zero-materialized / partial-materialization plans do NOT pass** (the earlier vacuous-true-while-unimplemented rule is removed — fail-closed; the `PLAN_ACCEPTED` consumer that materializes tasks is still a documented dependency, see amendment note in the header).
- **Reasons (`reasons_ok`):** every approved-plan `reason_codes` entry must hold: `LOW_ATTENDANCE → attendance_ok AND risk_cleared`; any unknown/not-yet-evaluable code → `False` (fail-closed — `verified` never rests on an unevidenced assumption). No approved plan → not verified. (Codes outside today's evaluable vocabulary may still be carried on plans — 06 §4 trigger policies fulfil by event type — but they cannot by themselves verify; non-academic codes such as `EXAM_APPROACHING` are deferred to their owning contract.)

The check runs only inside the `RULE_ENGINE` consumer — never from an LLM, never from the agent layer (06 §4's `human_review_required: true` follow-up-evaluation envelope remains reserved for the future agent path; the frozen table assigns these three rows to `RULE_ENGINE`, and engines calculate).

### 2.6 Evaluation window (configuration-driven)

`FOLLOWUP_EVALUATION_WINDOW_DAYS` resolved per student institution: `institution_rules` row `rule_id='followup_evaluation_window_days'`, `value={"days": N}`, institution scope preferred, batch scope honored; **fallback constant 7 days** when no rule exists (same defaulting pattern as `attendance_threshold` → 75.00; the fallback is documented here, not silently invented). The window is stored denormalized on the follow-up row at fulfilment time (`evaluation_window_ends_at`) so later rule edits never rewrite in-flight windows.

### 2.7 API surface (mentor human actions)

- `POST /api/v1/cases/{case_id}/follow-ups` — mentor/admin/HOD (shared `_authorize_mentor_case_write`; **HOD only when the case is `ESCALATION_REQUIRED` — 07 §2 "HOD: Escalations", lead-directed F5 alignment, 16 Oct 2026**); case must be `ACTIVE` (409 otherwise); `trigger_type` required; `due_at` required IFF `CUSTOM_DATE` (future timestamp), forbidden otherwise. Creates a SCHEDULED row + audit `FOLLOW_UP_SCHEDULED`. Justified like close/escalate: a contracted human action with no other invocation path until the client slices (R11); agent `schedule_followup` (06 §4) will call the same service later.
- `GET /api/v1/cases/{case_id}/follow-ups` — read list for the case (same record-level authz; ordering `created_at DESC`).

### 2.8 Audit action names (added by this ADR — 07 §4 is a mandatory minimum, not an exhaustive whitelist)

| action_type | Trigger |
|---|---|
| `FOLLOW_UP_SCHEDULED` | Mentor schedules a follow-up (entity: `intervention_follow_ups`) |
| `FOLLOW_UP_SUPERSEDED` | A `SCHEDULED` follow-up is `CANCELLED` — sibling fulfilled (reason `superseded_by_fulfilment`) or case no longer ACTIVE at dispatch (reason `case_not_active`) (entity: `intervention_follow_ups`; amendment 1) |
| `CASE_FOLLOWUP_DUE` | `ACTIVE → MONITORING` |
| `CASE_IMPROVEMENT_VERIFIED` | `MONITORING → RESOLVED` |
| `CASE_FOLLOWUP_EXPIRED` | `MONITORING → REPLAN_REQUIRED` |

Actor: `RULE_ENGINE` with `actor_id = NULL` for consumer transitions (audit model allows NULL actor); mentor scheduling uses `USER` + the mentor id. `source_system = CORE_PLATFORM` for consumer rows, `MENTOR_WEB` for the endpoint. No PII in state JSON (07 §4).

### 2.9 Explicitly not decided here

- Auto-creation of a follow-up at mentor approval (02 §2.1 Step 5 "scheduled per intervention policy") — requires per-case intervention typing, which does not exist on `intervention_cases`/`intervention_plans` (05 §9). P0 is mentor-scheduled + agent-scheduled via the same service; auto-selection by type is a future ADR once typing is modeled.
- Event-driven re-verification of improvement while in `MONITORING` (checking on every `ATTENDANCE_UPDATED` mid-window) — deferred; the immediate check at DUE plus the EXPIRY re-check cover the frozen rows.
- A cancel **endpoint** (mentor-initiated cancellation) — still deferred until a cancel contract exists. The `CANCELLED` *status* itself is decided by amendment 1 (consumer-side supersession only — no human cancel path).
- ESCALATION proposal criteria (REPLAN → ESCALATION_REQUIRED) — still blocked (see §2.4).
- Known bounded exposure (amendment 1): an event-driven row (NULL `due_at`) left `SCHEDULED` on a case that left ACTIVE **without** a consumer fulfilment (e.g. mentor resolves the case directly) is inert — the event scan requires `ACTIVE` and the DUE condition requires `due_at` — and is never auto-cancelled; cleanup needs either a mentor cancel endpoint (above) or a future case-terminal sweep. Not a firing risk: inert rows can never fulfil.

---

## 3. Event & payload contracts

No new catalog events. `MENTOR_FOLLOWUP_DUE` payload gains two keys (additive, `data_version` stays 1 — additive keys are compatible with the Minimal Event Contract):

**DUE (time path):**
```json
{
  "case_id": "uuid",
  "follow_up_id": "uuid",
  "trigger_type": "CUSTOM_DATE",
  "phase": "DUE"
}
```

**EXPIRY (time path):**
```json
{
  "case_id": "uuid",
  "follow_up_id": "uuid",
  "phase": "EXPIRY"
}
```

Event-path fulfilment carries no new events — the consumer reacts to existing catalog events (`ATTENDANCE_UPDATED`, `ASSESSMENT_GRADED`, `QUIZ_COMPLETED`, `TASK_OVERDUE`) whose payloads are unchanged.

---

## 4. Consequences

- The three blocked `§10.2` rows become implementable and implemented; `MENTOR_FOLLOWUP_DUE` leaves the R4 deferred list (`EXAM_APPROACHING` remains deferred).
- First **writing** bus consumer lands (R4's option-A precondition): dedup = follow-up row status under `FOR UPDATE`; window-D exposure documented (§2.3).
- 05 §9 gains one table (migration 016); OpenAPI gains two paths. Follows every prior schema-addition rule: migration-first, ORM mirrors migration, sqlite variant only where PG types cannot compile.
- `REPLAN_REQUIRED → ESCALATION_REQUIRED` remains blocked with a documented reason (criteria + confirmation surface undefined in 06 §4).
- **Amendment 1 consequences:** migration `017_followup_contract_alignment.sql` (id server default + status comment — `016` applied to real databases is not rewritten); `FOLLOW_UP_SUPERSEDED` audit action; `CANCELLED` rows exit all scans; the improvement predicate fails closed on missing plans / zero task materialization / unknown reason codes / still-active risk bands.
