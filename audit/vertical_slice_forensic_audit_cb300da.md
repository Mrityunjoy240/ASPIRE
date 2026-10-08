# ASPIRE Vertical Slice Forensic Audit

**Subject:** Vertical slice — Mentor intervention-plan approval (`INTERVENTION_PLAN_APPROVED`)
**Audited commit:** `cb300da` on `feature/vertical-slice-case-approval`
**Parent commit:** `82a36d8`
**Audit mode:** Read-only forensic verification. No code was changed. No fixes were implemented.
**Report file:** `audit/vertical_slice_forensic_audit_cb300da.md` (only artifact produced)

---

## 1. Executive Summary

The slice implements the full approval loop the Team Lead specified: ADR-002 event contract → canonical catalog row (03 §8.2) → 06 note → typed in-process event bus (`app/core/events.py`) → thin transactional service (`app/services/case_service.py`) → slim FastAPI route → typed frontend API client + queue-page approve/decline controls → 46 tests → OpenAPI regeneration → working-state doc → commit + push.

**Regression gate: all runnable gates pass.** 46/46 tests, clean `tsc`, clean ESLint, successful Next build (7 routes), OpenAPI regeneration produces zero diff (no drift), and the SQLAlchemy `MultipleResultsFound` repro command was executed and confirmed.

However, the audit found **four P1 defects**, none of which is architecture-breaking, and all of which are cheaply fixable:

- **F-01:** The approve endpoint 500s on any case holding ≥2 intervention plans (proven against SQLAlchemy 2.0.50). Latent today only because no plan-creation path exists in production code yet; guaranteed to fire after the first reject→replan cycle.
- **F-02:** The slice's own primary documentation deliverable — the canonical event catalog row at `docs/03_SYSTEM_SPEC.md:327` — states the event is "published after commit" when a mentor "approves/edits/**rejects**", directly contradicting ADR-002 §2/§5 (rejection = audit only) and the implementation. The canonical contract doc is wrong about the very rule the slice was designed to establish.
- **F-03:** Zero concurrency control on the approval mutation. Two simultaneous approvals both pass stale-read validation → state-machine violation (03 §10.2), duplicate `audit_log` rows with an incorrect `previous_state`, and duplicate domain events.
- **F-04:** Frozen queue ordering DM-SS03 (03 §6.2) is violated by both the backend sort (pre-existing) and the frontend sort that was **rewritten inside this slice** while carrying a comment falsely claiming "Sort per DM-SS03". 5 of the 9 frozen PQ fixtures in `08_EVALS.md` §9 fail.

**Verdict: FAIL — FIX REQUIRED.** The failure is documentation-contract and ordering/race correctness, not architecture. Engines/agents/RBAC/transaction-order boundaries all held. No P0 exists: every P1 has a narrow, contained remedy.

---

## 2. Scope Audited

**Audited (verified against real code/tests/git/spec):**

- Git history, commit diff, parent blobs, numstat, and test-deletion check for `82a36d8..cb300da`.
- Backend: `app/api/routers/cases.py`, `app/services/case_service.py`, `app/core/events.py`, `app/api/deps.py`, `app/api/schemas.py`, `app/main.py`, `db/migrations/009_intervention.sql`, `app/models/intervention.py`.
- Frontend: `apps/web/app/queue/page.tsx`, `apps/web/app/lib/api.ts`, `apps/web/app/layout.tsx` / `WebLayout`, Sidebar, absence of `middleware.ts` / login page.
- Tests: `tests/test_api_routers.py`, `tests/test_case_service.py`, `tests/test_events.py`, `tests/test_engines.py` (46 total).
- Specs: `docs/03_SYSTEM_SPEC.md` (§6.2 DM-SS03, §8.1/8.2 catalog, §10.2 state machine), `docs/05_DATA_API_CONTRACTS.md`, `docs/06_AGENT_SPEC.md`, `docs/07_SECURITY_TRUST.md` (§2 RBAC, §4 audit events), `docs/02_USER_JOURNEYS.md`, `docs/08_EVALS.md` §9 (PQ fixtures), `docs/10_TASKS.md` (T-061), `docs/04_ARCHITECTURE.md`, `docs/AI_WORKING_STATE.md`, `docs/decisions/ADR-002_INTERVENTION_PLAN_APPROVED_EVENT.md`, `DESIGN.md`, `AGENTS.md`.
- CI: `.github/workflows/ci.yml`.
- Regression commands: pytest, typecheck, lint, build, OpenAPI regen/diff, ruff check/format, mypy, SQLAlchemy repro.

**Not audited (out of scope / impossible in this environment):** live Supabase E2E (OQ-A02), real JWKS token auth, browser/visual verification, Supervisor/agent routing (agent code does not exist), GH Actions execution (local-only), native Android clients (out of repo ownership).

---

## 3. Repository / Git Findings

| Check | Result |
|---|---|
| Parent of `cb300da` | `82a36d8` |
| Files changed | 16, +1350 / −201 |
| Tests weakened/deleted | **None.** Test deltas purely additive: 194/0, 204/0, 86/0 |
| Migrations / models changed | **None** (zero `db/` or `app/models/` files in diff) |
| package.json changes | **None** (no new dependencies) |
| Worktree after audit | Clean except intentionally untracked `.opencode/` and `.docx` |
| Scope creep | None found beyond the four disclosed pre-existing bug fixes |

Per-file numstat (frontend carries the bulk): `queue/page.tsx` 275/151, `case_service.py` 158/0, `events.py` 83/0, `api.ts` 104/0, `cases.py` 43/28, `AI_WORKING_STATE.md` 31/18, ADR-002 135/0 (new), openapi.json 12/1, `main.py` 6/0, `schemas.py` 2/2, `deps.py` 11/1, 03 1/0, 06 5/0.

**No test files were modified** — `test_api_routers.py` (204/0), `test_case_service.py` (194/0), `test_events.py` (86/0) are net-new/append-only relative to parent.

---

## 4. Specification Compliance

| Spec requirement | Status |
|---|---|
| 03 §8.2 catalog row added for `INTERVENTION_PLAN_APPROVED` | ✅ Present at `docs/03_SYSTEM_SPEC.md:327`, linked to ADR-002 |
| ADR-002 emission rule (APPROVED/EDITED only; reject = audit only) | ✅ Implemented in `case_service.py:34` `_APPROVAL_DECISIONS`; ✅ service test asserts `events == []` on REJECTED |
| 06 agent-spec note added | ✅ `docs/06_AGENT_SPEC.md:68` |
| 05 §9 plan-status set respected | ✅ `plan.status` unchanged on APPROVED (stays `ACCEPTED`); `mentor_decision` carries verdict; tested |
| 05 §9 `mentor_decision` enum APPROVED/EDITED/REJECTED | ✅ Matches implementation and schemas |
| 03 §10.2 state machine `PENDING_APPROVAL → ACTIVE` | ✅ `ILLEGAL_TRANSISION` guard + tested |
| 03 §6.2 DM-SS03 queue ordering | ❌ **Violated — F-04** (backend + frontend) |
| Catalog row emission text vs ADR-002 | ❌ **Contradicts ADR — F-02** |
| DM-API01 contract-first + CI drift enforcement | ⚠️ Regen performed, zero drift; **CI has no drift check — F-09** |
| 05:286 `trigger_events` "Array of event IDs" | ⚠️ Model/Pydantic are `list[dict]` — three-way conflict — **F-08** |
| `10_TASKS.md` T-061 design (PATCH route, `EDITED_APPROVED`, 422) | ⚠️ Historical/superseded; 05+03+ADR govern; impl matches 05 — noted in F-26 |

**Document conflicts found (surfaced, not silently resolved):**

1. `03:327` vs ADR-002 §2/§5 — rejection emission (F-02, in-slice, canonical doc wrong).
2. `02_USER_JOURNEYS.md` "REPLAN_REQUIRED returns to IN_REVIEW" vs 03 §10.2 `REPLAN_REQUIRED → PLAN_PROPOSED` (historical).
3. `10_TASKS.md` T-061 (client-side TS state machine, PATCH mentor-action route, `EDITED_APPROVED`) vs actual architecture (FastAPI POST approve, `EDITED`) (historical; 05 wins).
4. `05:286` "Array of event IDs" vs `schemas.py:151` / `models/intervention.py:21` `list[dict]` (historical, now typed wrong in frontend too — F-08).

---

## 5. State Machine Findings

- Transitions implemented exactly per 03 §10.2: `PENDING_APPROVAL → ACTIVE` on APPROVED, `→ PLAN_PROPOSED` on EDITED, `→ REJECTED` on REJECTED.
- `ILLEGAL_TRANSISION` error raised on any other case status; tested (`test_case_service.py`).
- On APPROVED, `plan.status` intentionally unchanged (`ACCEPTED` stays); `mentor_decision` field carries the verdict — compliant with 05 §9 enum set.
- **Race defect (F-03):** no `SELECT FOR UPDATE`, no version/CAS column (migration `009_intervention.sql` has none). Two concurrent approvals both read `PENDING_APPROVAL`, both pass the guard, both commit → the machine processes the same transition twice: duplicate audit rows, duplicate `previous_state`, duplicate events. §10.2 assumes single-flight transitions; nothing enforces that server-side.
- **Actor ambiguity (F-11):** 03 §10.2 names the actor "Mentor"; 07 §2 grants HOD only "Escalations"; the handler contains a pure-HOD branch (`cases.py:177`) that is unreachable because `require_mentor_or_admin` (`deps.py:207`) rejects pure-HOD earlier. Dead code + unresolved authority question.

---

## 6. Event Contract Findings

- `DomainEvent` (03 §8.1 minimal contract) faithfully implemented: `event_name`, `data_version=1`, `source_id=plan.id`, `occurred_at`, `actor_id`, payload — all documented in ADR-002.
- Event-name spelling consistent repo-wide (grep-verified): `INTERVENTION_PLAN_APPROVED`, `PLAN_APPROVED_BY_MENTOR` (audit action, correctly distinct from domain event).
- `PLAN_ACCEPTED` / `PLAN_DECLINED` remain student-only: **no code anywhere emits them** — no semantic misuse.
- Emission strictly after `session.commit()`; commit failure skips publish (exception-isolated, inline `await`).
- **No consumers exist** — ADR-documented deferral; `02_USER_JOURNEYS.md` §2.1 Step 5 (student notification, follow-up scheduling) will not happen (F-10, P3, must land before P0 demo).
- Catalog row emission rule contradicts ADR and code (F-02).
- Reliability: crash-after-commit-before-emit loses the event — **known limitation** of frozen ARCH-02 in-process bus (no outbox). Not a contract violation; classified under F-22.

---

## 7. Transaction / Atomicity Findings

Verified order in `case_service.py`:

1. Decision validation (`_APPROVAL_DECISIONS`, non-empty check) — lines 27–34 region
2. Case state validation (`ILLEGAL_TRANSISION`) — ~92–99
3. State mutation — ~100–107
4. `log_audit(...)` staged on the **same** session — ~119–129
5. `await session.commit()` — 131
6. `event_bus.publish(...)` **after** commit — 133–150

✅ Audit + state share one transaction — an audit row can never exist without the mutation, and vice versa.
✅ Authorize (route) → validate → mutate → audit → commit → emit; commit-failure test proves emit is skipped (`probe asserts session.commit.called` before publish — emit-before-commit would fail).
⚠️ Single known weakness: emit-after-commit is not durable (F-22, known ARCH-02 limitation).

---

## 8. Idempotency / Concurrency Findings

- **F-03 (P1):** No row lock, no optimistic version, no CAS. Stale-read double-approval is possible (double-click is client-mitigated by `pendingId` disable, but multi-tab/replay is not). Consequences: state-machine double-transition, duplicate audit with wrong `previous_state`, duplicate events.
- **F-20 (P3):** Retry after a lost response yields 409 error UX although the mutation persisted — non-idempotent UX, state-safe for single flight. No idempotency key support.
- Existing single-request behavior is correct: a second approve after success returns 409 (tested), and reject→approve sequences are rejected by `ILLEGAL_TRANSISION`.

---

## 9. RBAC / Security Findings

**Sound (verified):**

- JWT RS256 → `users` row must be `ACTIVE` → roles resolved from `user_role_assignments` with validity window (`deps.py get_auth_context`).
- Route protected by `require_mentor_or_admin` (`deps.py:207`) **and** per-case scope check (`cases.py:177`): admin OR HOD OR `case.mentor_id == auth.user_id`.
- No client-supplied authority: request body is only `decision` (Literal) + `mentor_notes` (`schemas.py:157-160`); `actor_id = auth.user_id`, `case_id` from path, status fields server-derived (`cases.py:193-199`).
- No role/status/priority fields accepted from the client; payload and previous status fully server-derived.
- Server is the sole enforcement point — correct posture.

**Findings:**

- **F-06 (P2):** Zero client-side authorization/route gating: no `middleware.ts`, no login page, static `WebLayout`, role-less Sidebar. The Approve control renders for any visitor; server correctly returns 401/403 but the UI violates the audit's least-privilege expectation ("unauthorized users cannot access the control").
- **F-13 (P3):** `NEXT_PUBLIC_ASPIRE_DEV_TOKEN` embeddable in the client bundle + manual localStorage paste → audit attribution is the token subject; a shared token = audit-spoofing surface. Lead-approved dev tradeoff (no sign-in UI exists anywhere yet).
- **F-21 (P3):** 404-vs-403 branch (`cases.py:177`) is an existence oracle for authenticated mentors (UUIDs → negligible).
- **F-23 (P3, pre-existing):** `SUPABASE_JWKS_URI` unset + token presented → `_fetch_jwks` raises `ValueError`; `_decode_token` catches only `JWTError` → unhandled 500 (`deps.py:57-58`).
- **F-24 (P3, pre-existing):** `allow_origins=["*"]` with `allow_credentials=True` (`main.py:39-44`).

---

## 10. Audit Trail Findings

- Every approve/reject produces one `audit_log` row in the same transaction as the mutation (test: `session.add.assert_called_once`).
- Fields verified: `action_type` = `PLAN_APPROVED_BY_MENTOR` / `PLAN_REJECTED_BY_MENTOR`, `entity_table` = `intervention_plans`, `actor_id` = authenticated user, `source_system` = `MENTOR_WEB`, `previous_state`/`new_state` contain full case+plan JSON snapshots.
- Actions are correct free-text per `007_audit_log.sql` (no enum constraint).
- **F-15 (P3):** `PLAN_REJECTED_BY_MENTOR` is not listed in 07 §4 mandatory-events table (no reject action appears there) — documentation gap only.
- **F-25 (P3):** The audit row's `entity_table` is the plan; the case-status change is only visible inside the JSON snapshots — a two-entity mutation recorded against one entity. Not forbidden by 05/07; noted.
- There is **no separate audit record** for the case-status change itself (same as F-25).

---

## 11. API / OpenAPI Findings

- `POST /api/cases/{case_id}/approve` is thin: `require_mentor_or_admin` → `get_event_bus` → `approve_plan(...)` → map errors to HTTP. All logic lives in the service.
- Error mapping: `CaseNotFound → 404`, scope failure → 403, `ILLEGAL_TRANSISION → 409`, bad decision → 400, auth missing → 401. Proper `HTTPException` objects (fixes parent's bare-int raises — §20).
- OpenAPI regenerated (`python scripts/generate_openapi.py`): 11 paths, **`git diff contracts/openapi.json` empty — no drift**.
- **F-14 (P3):** 409/400 responses declared description-only — no `{detail}` body schema for typed clients; 422 is the framework default.
- **F-09 (P2):** DM-API01's "CI fails on drift" claim is not implemented — `ci.yml` runs typecheck/lint/build only; neither pytest nor an openapi-diff job exists.
- **F-16 (P3):** `app/services/case_service.py:15` imports `log_audit` from `app.api.deps` — service layer depends on the HTTP layer (inverted direction, ARCH-04 nit).

---

## 12. Test Quality Findings

**Verified strengths** (mutation-style checks actually hold):

- Removing event emission → fails (happy path asserts `received`).
- Removing audit write → fails (`session.add.assert_called_once`).
- Emitting before commit → fails (probe asserts `session.commit.called` pre-publish).
- Emitting a rejection event → fails (`events == []`).
- Illegal transition → 409 tested; audit `previous_state`/`new_state` asserted; `mentor_decision` persisted; plan status unchanged on APPROVED asserted.
- Unit/integration split respected: engines pure; API tests mock `get_auth_context`; service tests mock session.

**F-07 (P2) — gaps / false confidence:**

1. **No student/faculty 403 test.** `test_approve_requires_auth` only covers *missing token → 401*. Deleting the `require_mentor_or_admin` dependency from the route would still pass (the route's own `get_auth_context` still raises 401). The role gate is effectively untested.
2. **No multi-plan test** — F-01 exists precisely because no test creates a second plan on a case.
3. **No commit-failure/rollback test** (only emit-after-commit ordering is probed).
4. **No true duplicate-request test** — concurrency (F-03) and retry-idempotency (F-20) are untested.
5. **No PQ fixture tests** — all 9 frozen `08_EVALS.md` §9 fixtures are unimplemented in code.
6. Queue tests use an **empty list** only — the parent's `StudentTask` NameError fix (§20) is therefore correct but its non-empty-queue path remains untested.
7. Counts: **46 tests** = 16 engines + 17 API + 8 service + 5 events (verified via `--collect-only`).

---

## 13. Frontend Findings

- **F-04 (P1):** `apps/web/app/queue/page.tsx:188-196` client sort duplicates backend sorting (violates AGENTS "no duplicated business logic in clients"), claims "Sort per DM-SS03" in a comment, and implements the **same inverted logic** as the backend: exam proximity applied to all bands, `days ASC` (spec: DESC), NULL→999 (spec: NULL FIRST), no `created_at`/`case_id` tie-breakers. See §15 for fixture-level evidence.
- **F-08 (P2):** `api.ts` types `trigger_events: string[]` while backend (`schemas.py:151`) and model (`models/intervention.py:21`) are `list[dict]`; `05:286` says "Array of event IDs". The generic client casts `as T` with no runtime validation; live rows would render `"[object Object]"` through `getEventLabels().join()`.
- **F-06 (P2):** No route/role gating (see §9).
- **F-12 (P3):** After approve, `queue/page.tsx:171-173` hardcodes local status `"ACTIVE"` instead of refetching; other fields (days-since-action, trigger events) go stale; mentor notes are accepted by the API but never shown in the UI.
- **F-18 (P3, pre-existing carried):** Hardcoded `75%` attendance threshold displayed at `queue/page.tsx:286` — contradicts configuration-driven `institution_rules` (AGENTS hard rule).
- **F-19 (P3, pre-existing carried):** `"Resolved 12 // mock"` rendered as a metric (line ~200) — mock data presented as fact.
- DESIGN.md: approve/decline controls use existing Button/badge primitives; no new visual tokens required — visual conformance not machine-verifiable here (see §24).

---

## 14. Data / Migration Findings

- **Zero schema changes** in the slice (no migration, no model edits) — correct: migration `009_intervention.sql` already created `intervention_plans`, `case_status_history`, `mentor_notes`.
- Concurrency-relevant observation: `intervention_plans` has **no version column and no lock hint**, which is the root enabler of F-03.
- The `cases` table has no `version`/`locked_at` either; `case_status_history` is not written by the approve path (history rows only via earlier flows) — status history for approval exists solely inside the audit JSON (F-25).

---

## 15. Agent Authority Findings

- `rg` confirms **only** `app/services/case_service.py` mutates `case.status` — single choke point held.
- No `app/agents/` directory exists; no Supervisor or specialist agents exist to violate authority boundaries.
- No LLM imports anywhere in the slice files; `LLMService` untouched; no `LLMService`/OpenRouter call paths added.
- Event name `INTERVENTION_PLAN_APPROVED` has **no agent consumer** (per ADR-002: "No v1 agent trigger") — 06 note correctly documents this.
- Engines untouched (attendance/eligibility still computed deterministically; no eligibility decision anywhere in the approve path).

---

## 16. Scope Creep Findings

**None material.** The diff contains exactly:

1. The approved slice artifacts (event contract, service, route, client, queue UI, tests, docs).
2. Four **disclosed pre-existing bug fixes** in `cases.py` (bare-int raises, `StudentTask` missing import, `plan.status="APPROVED"`, `EDITED→PLAN_PROPOSED`) — all verified against parent blobs in §20.

No migrations, no new endpoints, no dependency upgrades, no unrelated refactors, no test deletions, no changes outside owned folders (`apps/web`, `app/`, `tests/`, `docs/`, `contracts/`).

---

## 17. Pre-existing Bug Fix Audit (Parent `82a36d8`)

Verified by `git show 82a36d8:app/api/routers/cases.py`:

| Claimed fix | Parent evidence | Current state | Verdict |
|---|---|---|---|
| Bare-int raises → 500s | Lines 159/162/172: `raise 404`-style bare ints (`TypeError` → 500) | Proper `HTTPException(404/403/400/409)` + tests | ✅ True, tested |
| `StudentTask` NameError → 500 on non-empty queue | Used at lines 91–94, never imported | Import added; works | ✅ True — but **untested** (queue tests use empty list only) |
| `plan.status="APPROVED"` violated 05 §9 | Line 179 assigned directly | Status unchanged; `mentor_decision` carries verdict; asserted in tests | ✅ True, tested |
| Old `EDITED → PLAN_PROPOSED` | Line 183 (pre-§10.2 semantics) | `→ ACTIVE` per §10.2; tested | ✅ True, tested |

No regressions introduced by these fixes; no other pre-existing behavior was silently altered (diff review of `cases.py` 43/28 accounted for).

---

## 18. Regression Results

| # | Command | Result |
|---|---|---|
| 1 | `git status --short` | Only `.opencode/`, `*.docx` untracked — clean |
| 2 | `git show --stat cb300da` | 16 files, +1350/−201, parent `82a36d8` |
| 3 | `python -m pytest tests/ -q` | **46 passed** in ~1.4s (16 engines / 17 API / 8 service / 5 events) |
| 4 | `npm run typecheck` | **Clean** (web + shared workspaces) |
| 5 | `npm run lint` | **Clean** (eslint .) |
| 6 | `npm run build` | **Success** — 7 routes built |
| 7 | `python scripts/generate_openapi.py` + `git diff contracts/openapi.json` | 11 paths; **diff empty → no drift** |
| 8 | SQLAlchemy repro (in-memory, 2 plans on one case) | **`RAISED: MultipleResultsFound`** — F-01 proven |
| 9 | `python -m mypy app --ignore-missing-imports` | **Blocked:** numpy `.pyi` uses `type` statements; `[tool.mypy] python_version = "3.11"` → 1 syntax error prevents checking (pre-existing config/env issue) |
| 10 | `python -m ruff check app tests` (repo config) | **278 errors** repo-wide — pre-existing debt; ruff is **not** in CI or gate scripts |
| 11 | `python -m ruff format --check app tests` | 38 files would reformat (pre-existing, non-gating) |
| 12 | GH Actions | Not runnable locally; `ci.yml` inspected statically (typecheck/lint/build only) |

**Ruff delta on touched Python files** (isolated, identical rules `E,F,I,UP,W`, line-length 100):

| File | Parent | Current | Δ |
|---|---|---|---|
| `app/api/routers/cases.py` | 34 | 24 | **−10 (improved)** |
| `app/api/deps.py` | 6 | 6 | 0 |
| `app/api/schemas.py` | 25 | 26 | +1 |
| `app/main.py` | 1 | 2 | +1 |
| `tests/test_api_routers.py` | 43 | 50 | +7 |
| New files: `events.py` 1, `case_service.py` 2, `test_events.py` 1, `test_case_service.py` 4 | — | 8 | +8 |

Net slice-attributable lint debt ≈ +17 (mostly E501/style in new tests) while `cases.py` improved by 10. Non-gating (F-27).

**Could not run:** real-DB integration/E2E (no Supabase stack — OQ-A02), live JWKS token auth, mypy (blocked above), GH Actions, browser/visual checks.

---

## 19. Findings by Severity

### P0 — Blocking

**None.** No finding stops the demo loop or breaks a frozen decision irrecoverably.

### P1 — High

**F-01 — Approve endpoint 500s on multi-plan cases (latent, proven)**
- Location: `app/api/routers/cases.py:181-186`
- Expected: `select(InterventionPlan).where(case_id).order_by(created_at.desc())` + **`.limit(1)`** before `scalar_one_or_none()`.
- Actual: no limit → SQLAlchemy raises `MultipleResultsFound` when a case has ≥2 plans → unhandled → HTTP 500.
- Evidence: executed repro against SQLAlchemy 2.0.50 printed `RAISED: MultipleResultsFound - Multiple rows were found when one or none was required`. Latent only because no plan-creation code/seed exists in production (plans are only constructed in tests) — the first reject→replan cycle makes it deterministic.
- Impact: approve permanently broken for any case with an edit-history plan; violates §8.1 "at most one plan" implicit assumption.
- Recommended next action: add `.limit(1)` (and decide newest-vs-approved selection explicitly); add a two-plan regression test. *(Do not implement in audit mode.)*

**F-02 — Canonical catalog row contradicts ADR-002 emission rule**
- Location: `docs/03_SYSTEM_SPEC.md:327` vs `ADR-002 §2/§5` and `app/services/case_service.py:34`
- Expected: catalog row states emission occurs when a mentor approves/edits a plan (rejection = audit only).
- Actual: row says "Mentor approves/edits/**rejects** a plan — published after commit", implying rejection publishes too; ADR + code emit only for APPROVED/EDITED.
- Evidence: ADR §2 table row: "After a mentor approval (decision APPROVED/EDITED)…"; service `_APPROVAL_DECISIONS = {"APPROVED","EDITED"}`; rejection test asserts `events == []`.
- Impact: a future consumer built from the canonical catalog (the doc most likely to be read) would await a `INTERVENTION_PLAN_APPROVED` event on rejection and hang/miss state; the slice's central documentation deliverable is self-inconsistent with its own ADR.
- Recommended next action: amend `03:327` to name APPROVED/EDITED only and state explicitly that rejection emits no domain event (audit-only). Clarify §8.1 "Amends" line if needed.

**F-03 — Concurrent double-approval possible (state-machine race)**
- Location: `app/api/routers/cases.py:173-199` + `app/services/case_service.py:83-147`; `db/migrations/009_intervention.sql` (no version/lock columns)
- Expected: exactly one approval wins a race; loser gets 409; one audit row with correct `previous_state`; one event.
- Actual: both requests read `PENDING_APPROVAL` (no `FOR UPDATE`, no CAS/version), both validate, both mutate, both commit → duplicate audit row (second has wrong `previous_state`), duplicate events, §10.2 double-transition.
- Evidence: code review of service (plain `select` → mutate → commit); migration DDL has no version column; no lock/`with_for_update` anywhere in repo.
- Impact: integrity violation of the frozen state machine + duplicate audit trail on a human-authority decision endpoint.
- Recommended next action: `SELECT … FOR UPDATE` on the case row inside the transaction, or an optimistic `version` column with CAS UPDATE returning 409 on conflict; add a two-session concurrency test.

**F-04 — Frozen queue ordering (DM-SS03) violated in shipped code**
- Location: backend `app/api/routers/cases.py:135-141` (pre-existing, untouched by slice) and frontend `apps/web/app/queue/page.tsx:188-196` (rewritten **inside** `cb300da` with comment "Sort per DM-SS03")
- Expected per 03 §6.2 (FROZEN): band first; within URGENT only → exam ASC (NULL LAST) then days-since-action DESC (NULL FIRST); ATTENTION/MONITOR → days DESC only, exam ignored; final tie-breakers `created_at` ASC, `case_id` ASC.
- Actual (both layers): exam proximity applied to **all** bands; days **ASC** (inverted); NULL→999 = NULLS LAST (inverted); no tie-breakers.
- Evidence vs frozen `08_EVALS.md` §9 fixtures: **PQ-03 fails** (older-untouched must come first; ASC puts acted-1d first), **PQ-06 fails** (NULL must be first; 999 puts it last), **PQ-07/PQ-08 fail** (exam must be ignored outside URGENT), **PQ-09 fails** (no tie-breaker → nondeterministic). PQ-01/02/04/05 pass. 5/9 frozen fixtures fail. Zero PQ fixture tests exist (F-07).
- Impact: frozen-decision violation; mentor sees wrong work order; duplicated client sort also breaks the "one shared core, no duplicated business logic" rule; false compliance comment in code.
- Recommended next action: implement one correct sort server-side (single source of truth), delete/derive the client sort, add the 9 PQ fixtures as executable tests before any queue-API merge per 08 §9. Provenance: backend half pre-existing; frontend half in-slice and must be fixed.

### P2 — Medium

**F-05 — No plan-status validation before approval**
- Location: `app/services/case_service.py:76-107` (validates decision + case status only)
- Expected: only `plan.status ∈ {ACCEPTED, CUSTOMIZED, PROPOSED}` (per intended contract) may be approved; `DECLINED`/`SUPERSEDED` plans must not become the basis of an ACTIVE case.
- Actual: any plan row for the case can be approved if the case is `PENDING_APPROVAL`.
- Evidence: no plan-status check in service; no test constructs a DECLINED plan + PENDING_APPROVAL case.
- Impact: inconsistent data (possible after future replan flows) silently produces an ACTIVE case from a dead plan.
- Next action: reject non-approvable plan statuses with 409; add test.

**F-06 — No client-side authorization or route gating**
- Location: `apps/web` — no `middleware.ts`, no login page, `WebLayout` static, Sidebar role-less; `queue/page.tsx:262,329` renders Approve/Decline unconditionally
- Expected: unauthorized users cannot access the control (audit §16 least-privilege); routes gated by session/role client-side with server as final authority.
- Actual: any visitor sees working controls; server correctly 401/403s.
- Evidence: `glob` shows no middleware; layout/sidebar greps show no role logic.
- Impact: permission-confusion UX; spec/audit expectation unmet (server security intact).
- Next action: middleware guard + session check once sign-in lands (currently blocked on auth UX decision — surface to team lead).

**F-07 — Test gaps creating false confidence**
- Location: `tests/test_api_routers.py` (`test_approve_requires_auth`), `tests/test_case_service.py`, absence of PQ/multi-plan/concurrency tests
- Actual: role dependency removable without failing the suite; F-01/F-03/F-04 all untested; non-empty queue path untested.
- Evidence: detailed in §12.
- Next action: add student/faculty **403** tests, two-plan test, rollback test, duplicate-request test, and the 9 PQ fixtures.

**F-08 — `trigger_events` type mismatch across three layers**
- Location: `apps/web/app/lib/api.ts` (typed `string[]`, cast `as T`), `app/api/schemas.py:151` (`list[dict]`), `app/models/intervention.py:21`, `docs/05_DATA_API_CONTRACTS.md:286` ("Array of event IDs")
- Expected: one consistent contract.
- Actual: Pydantic/model are `list[dict]`; 05 doc says IDs; frontend says `string[]`. Unchecked cast hides it; live rows render `[object Object]` in `getEventLabels().join()`.
- Next action: reconcile (likely frontend → `Array<Record<string,string>>` or backend → `list[str]`), fix 05:286 either way.

**F-09 — CI does not enforce pytest or OpenAPI drift (DM-API01 claim unmet)**
- Location: `.github/workflows/ci.yml`
- Expected: DM-API01 frozen decision — CI fails on contract drift; slice claims "regenerated contract" verified.
- Actual: job runs only typecheck/lint/build (Node 20); no pytest, no openapi-diff.
- Evidence: workflow file contents; regression #7 verified drift only **locally**.
- Next action: add pytest + `generate_openapi.py && git diff --exit-code` steps to CI.

### P3 — Low

| ID | Finding | Location | Next action |
|---|---|---|---|
| F-10 | Journey §2.1 Step-5 downstream effects (student notification, follow-up) not implemented; event has zero consumers — ADR-documented deferral | `02_USER_JOURNEYS.md:228-231`, ADR-002 §4 | Implement consumers before P0 demo |
| F-11 | Pure-HOD approve branch unreachable (`require_mentor_or_admin` blocks HOD before `cases.py:177`); HOD authority ambiguous vs 07 matrix ("Escalations") and §10.2 actor=Mentor | `cases.py:177`, `deps.py:207`, 07 §2 | Decide HOD policy; remove dead branch or align deps |
| F-12 | Post-approve status hardcoded locally (`"ACTIVE"`); no queue refetch; mentor notes never displayed | `queue/page.tsx:171-173` | Refetch queue; show notes |
| F-13 | Dev token in client bundle/localStorage → audit attribution = token subject; shared token = spoofing surface (lead-approved dev risk) | `api.ts` fallback, env var | Replace with real sign-in before production |
| F-14 | 409/400 documented description-only; no error body schema | `contracts/openapi.json` | Add `{detail}` schemas |
| F-15 | `PLAN_REJECTED_BY_MENTOR` absent from 07 §4 mandatory-events table | `docs/07_SECURITY_TRUST.md` §4 | Add row (schema already free-text) |
| F-16 | Service imports HTTP layer (`app.api.deps.log_audit`) — inverted layer direction (ARCH-04 nit) | `case_service.py:15` | Move `log_audit` to a domain/audit module |
| F-17 | AI_WORKING_STATE claims "7 new router tests" — actual 8 (46 total verified) | `docs/AI_WORKING_STATE.md` | Correct count |
| F-18 | Hardcoded 75% attendance threshold in UI (pre-existing carried) vs config-driven rules | `queue/page.tsx:286` | Read `institution_rules` via API |
| F-19 | Mock metric "Resolved 12" shown as fact (pre-existing carried) | `queue/page.tsx:~200` | Label as mock or remove |
| F-20 | Non-idempotent approve retry → 409 UX despite persisted mutation | `cases.py:149-210` | Idempotency key or GET-before-error |
| F-21 | 404/403 existence oracle (UUIDs → negligible) | `cases.py:177` | Accept |
| F-22 | Crash-after-commit loses event (no outbox) — **known ARCH-02 limitation**, not a contract violation | `case_service.py:131-150` | Document in ADR; outbox only if bus moves |
| F-23 | JWKS unset + token → unhandled `ValueError` → 500 (pre-existing) | `deps.py:57-58` | Catch `ValueError` → 401/503 |
| F-24 | CORS `*` + credentials (pre-existing) | `main.py:39-44` | Configure origins |
| F-25 | Case-status change not separately audited (only inside plan audit JSON) | `case_service.py:117-127` | Optional second audit row or split entities |
| F-26 | Historical doc conflicts: T-061 design (PATCH route, `EDITED_APPROVED`, 422), journey REPLAN→IN_REVIEW vs §10.2, 05:286 event-ID wording | `10_TASKS.md`, `02`, `05:286` | Mark T-061 superseded; align journey; fix 05 wording |
| F-27 | Slice-attributable ruff debt ≈ +17 issues (E501/style in new tests) while `cases.py` improved −10; ruff non-gating | new test files, `schemas.py`, `main.py` | Run `ruff --fix` on new files; add ruff to CI |

---

## 20. What Is Correct

1. **Engines untouched** — no deterministic-rule changes; attendance/eligibility still engine-computed; no eligibility decision in the approve path.
2. **No agent/LLM authority violation** — no agent code exists; only `case_service` mutates `case.status`; no LLM imports added; event has zero agent consumers per ADR.
3. **RBAC server-authoritative** — RS256/JWKS → ACTIVE user → roles from `user_role_assignments` with validity window; per-case scope check; client cannot supply actor/status/role (body = `decision` + `mentor_notes` only).
4. **Transaction order exact** — authorize → validate decision → validate state → mutate → audit (same session) → commit → emit; commit failure skips emit (tested); audit+mutation atomic (tested).
5. **Emission contract matches ADR-002** — APPROVED/EDITED only; rejection audited but silent; `data_version=1`, `source_id=plan.id`, correct audit-vs-domain naming split (`PLAN_APPROVED_BY_MENTOR` ≠ `INTERVENTION_PLAN_APPROVED`).
6. **State machine per §10.2** — single-transition guard `ILLEGAL_TRANSISION` → 409, tested; APPROVED leaves `plan.status=ACCEPTED` per 05 §9; `mentor_decision` carries verdict.
7. **All runnable gates green** — 46/46 tests, tsc clean, eslint clean, build success, OpenAPI regen zero-drift, no test deletions (purely additive suite).
8. **Thin router, real service** — all logic in `case_service`; router only maps errors → HTTP; dependency injection of `get_event_bus` is testable (event-capture fixture used).
9. **No scope creep** — 16 files, disclosed pre-existing fixes only, no migrations/dependencies/unrelated refactors, no business logic in clients beyond the (defective) queue sort and derived status.
10. **Pre-existing 500s fixed correctly** — bare-int raises, `StudentTask` NameError, illegal `plan.status` write, pre-§10.2 EDITED transition — all four verified against parent blobs (§17).
11. **Agent/eval documentation updated honestly** — ADR-002 ACCEPTED with the actual in-chat directive as context; 06 note; AI_WORKING_STATE phase/tasks/blockers (one count nit, F-17).
12. **Freeze discipline otherwise held** — no hardcoded *eligibility* thresholds added; config-driven claims unaffected by the slice (the 75% string is pre-existing, F-18).

---

## 21. What Could Not Be Verified

1. **Live database behavior** — no Supabase/Postgres stack (OQ-A02); all DB paths are mocks; F-01 proven via SQLite repro instead, F-03 via code analysis only (no two-session test possible without a real DB).
2. **Real auth E2E** — no live JWKS/token; auth exercised only through `get_auth_context` mocks/missing-token paths. F-13 attribution behavior untested against a real Supabase token.
3. **Browser/UI behavior** — no Playwright run; queue rendering, approve flow click-path, and DESIGN.md visual conformance are static-review only.
4. **GH Actions CI** — not runnable locally; ci.yml inspected statically (F-09).
5. **mypy strict gate** — blocked by numpy stub syntax vs `python_version = 3.11` config (pre-existing env/config issue); backend typing verified only via tests.
6. **Supervisor/agent routing** — agent layer does not exist; nothing to verify.
7. **Queue ordering with real data** — PQ fixtures are unimplemented (F-07); verdict on F-04 rests on literal comparison of code vs frozen spec text and fixture expectations.
8. **Performance/scale** — out of scope; no perf harness exists.

---

## 22. Final Verdict

# FAIL — FIX REQUIRED

**Rationale:** The slice's engineering core is sound — transaction order, audit atomicity, emission-after-commit, RBAC, engines/agents boundaries, and the regression gate all hold — but four P1 defects block acceptance:

1. **F-02** — the slice's own canonical contract deliverable (`03:327`) misstates the emission rule versus its ADR and code;
2. **F-04** — a frozen decision (DM-SS03) is violated in shipped code, including frontend code written in this very commit under a false compliance comment (5/9 frozen PQ fixtures fail);
3. **F-03** — the approval mutation has zero concurrency control, enabling state-machine double-transitions and corrupt audit trails;
4. **F-01** — the primary endpoint deterministically 500s as soon as a case has two plans (repro executed), with no test covering that shape.

None require architectural change: add `.limit(1)` (+test), correct one catalog row, add a row lock or CAS version (+test), and implement the frozen sort server-side with its 9 fixtures. P2s (role-gate test, plan-status validation, client gating, `trigger_events` typing, CI enforcement) should follow in the same remediation pass. Until the four P1s are fixed and the PQ fixtures pass, the slice does not meet the standard of "engines calculate, humans decide, specs are source of truth."

**Audit status:** Evidence gathering complete; report produced; **no code was modified.** Stopping here per mandate.
