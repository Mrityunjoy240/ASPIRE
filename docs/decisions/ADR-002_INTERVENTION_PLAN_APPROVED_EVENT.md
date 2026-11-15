# ADR-002: `INTERVENTION_PLAN_APPROVED` Domain Event

**STATUS: ✅ ACCEPTED — Team Lead directive (Mrityunjoy Kapat), 08 October 2026**
**Date:** 08 October 2026
**Author:** OpenCode (implementation agent)
**Amends:** `docs/03_SYSTEM_SPEC.md §8.2` (Canonical Event Catalog) — via this documented decision only (DM process per team lead directive)

---

## 1. Context & Problem Statement

Mentor plan approval (human-in-the-loop) is a distinct domain fact: a mentor
decides an intervention plan's fate, moving the case `PENDING_APPROVAL → ACTIVE`
(or `→ REPLAN_REQUIRED` on rejection) per `03_SYSTEM_SPEC.md §10.2`.

The Canonical Event Catalog (`03_SYSTEM_SPEC.md §8.2`) has no event for this
fact:

- `PLAN_ACCEPTED` / `PLAN_DECLINED` are **student** actions produced by the
  Student Action Service. Reusing `PLAN_ACCEPTED` for mentor approval would
  merge two semantically different facts and corrupt future consumer routing.
- The catalog is frozen: every event name must match it exactly
  (`03_SYSTEM_SPEC.md §8.1`, `06_AGENT_SPEC.md §1` note).

Until amended, mentor approval could not emit a domain event — treated as a
blocking contract gap rather than inventing or aliasing an event.

---

## 2. Decision

Add **one** new event to the Canonical Event Catalog:

| Event | Producer | Notes |
|---|---|---|
| `INTERVENTION_PLAN_APPROVED` | Case Approval Service | After a mentor **approval** (decision `APPROVED`/`EDITED`) moves the case to `ACTIVE` and the change is **committed** (ADR-002) |

`PLAN_ACCEPTED` and `PLAN_DECLINED` remain unchanged (student actions only).

**Emission rule:** the event fires only for decisions that produce an
approval (`APPROVED`, `EDITED` → case `ACTIVE`). A `REJECTED` decision
(case → `REPLAN_REQUIRED`) produces its mandatory `audit_log` row but **no**
domain event — emitting an "APPROVED"-named event for a rejection would be a
contract lie, and no catalog event exists for mentor rejection yet (possible
subject of a future ADR).

---

## 3. Event Contract

Uses the Minimal Event Contract from `03_SYSTEM_SPEC.md §8.1`:

```json
{
  "event_id": "uuid",
  "event_type": "INTERVENTION_PLAN_APPROVED",
  "student_id": "uuid",
  "source_id": "uuid (intervention_plans.id acted upon)",
  "occurred_at": "timestamp (UTC)",
  "data_version": 1,
  "payload": {
    "case_id": "uuid",
    "plan_id": "uuid",
    "mentor_id": "uuid",
    "decision": "APPROVED | EDITED",
    "previous_status": "PENDING_APPROVAL",
    "new_status": "ACTIVE"
  }
}
```

### Ordering guarantee

The event is published strictly **after** the database transaction containing
the case/plan state change (and its `audit_log` row) has been committed.
No event is ever published for a transition that rolled back.

### Audit separation

The `audit_log` record is written independently of the domain event
(append-only row, `action_type = PLAN_APPROVED_BY_MENTOR` for APPROVED/EDITED
per `07_SECURITY_TRUST.md §4`; `PLAN_REJECTED_BY_MENTOR` for REJECTED —
`audit_log.action_type` is free-form TEXT per `007_audit_log.sql`). The audit
row and the domain event are separate artifacts: the audit row proves the
write happened; the event notifies subscribers. Neither substitutes for the
other.

---

## 4. Producer / Consumer Contract

- **Producer:** Case Approval Service (`app/services/case_service.py`), via the
  in-process asyncio event bus (ADR-001, ARCH-02 — no Redis/Kafka in v1).
- **Consumers in v1:** none. No Supervisor routing rule and no agent trigger
  consumes this event yet; `06_AGENT_SPEC.md` routing table is intentionally
  unchanged. Future consumers (e.g., follow-up scheduling, notification
  adapters) subscribe to the exact name `INTERVENTION_PLAN_APPROVED`.
- **Supervisor behavior if received:** with no matching routing rule it falls
  to `human_review_required: true` — safe by construction.

---

## 5. State Transition Enforced by the Same Service

Per `03_SYSTEM_SPEC.md §10.2` (mentor rows only; the case must be in
`PENDING_APPROVAL`, otherwise the transition is refused with HTTP 409):

| Decision | Next case status | Plan status | Domain event |
|---|---|---|---|
| `APPROVED` | `ACTIVE` | unchanged (already `ACCEPTED`/`CUSTOMIZED` by the student step) | `INTERVENTION_PLAN_APPROVED` |
| `EDITED` (edits + approves) | `ACTIVE` | `CUSTOMIZED` | `INTERVENTION_PLAN_APPROVED` |
| `REJECTED` | `REPLAN_REQUIRED` | `DECLINED` | audit only (no catalog event — see §2) |

Plan statuses are constrained to
`PROPOSED | ACCEPTED | CUSTOMIZED | DECLINED | SUPERSEDED`
(`05_DATA_API_CONTRACTS.md §9`, migration `009_intervention.sql`) — there is no
`APPROVED` plan status; the mentor verdict lives in
`mentor_decision (APPROVED | EDITED | REJECTED)`. The pre-ADR endpoint's
`plan.status = "APPROVED"` on approval violated that documented schema
comment and is removed by this slice.

Note: the pre-existing endpoint applied transitions from any state and mapped
`EDITED → PLAN_PROPOSED`, contradicting §10.2. This slice makes the service the
single owner of the legal transition table.

---

## 6. Consequences

- Catalog amended through a documented decision instead of an ad-hoc code
  literal; `03_SYSTEM_SPEC.md §8.2` gains one row referencing this ADR.
- No change to student-action events, Supervisor routing, or agent tools.
- `contracts/openapi.json` does not change from the event itself (events are
  not part of the HTTP contract); the endpoint does gain a documented 409
  response for illegal transitions.
