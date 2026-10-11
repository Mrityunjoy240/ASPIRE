# ASPIRE AI WORKING STATE
# docs/AI_WORKING_STATE.md

> This file is the mutable handoff document for AI coding agents.
> Read it before starting any major task. Keep it concise.
> Update it whenever phase, task, or blockers change.

---

### Current Phase

**Mother System / Mother Application Foundation**

ASPIRE is structured as ONE unified product ecosystem:
1. **ASPIRE Mother Application (Web):** The primary human-facing operational & management control application (System Admin, Institution Admin, HOD, Faculty, Mentors) built in Next.js 15 App Router.
2. **ASPIRE Core Platform (Backend & Intelligence):** Centralized FastAPI service, database persistence, deterministic rule engines, LangGraph agent orchestrator, and OpenAPI contracts.
3. **Clients (Web & Native Android):** Student Web, Faculty Web, and external Native Android applications (Kotlin/Compose built separately in Android Studio).

---

## Current Implementation Owner

- **OpenCode:** Primary implementation agent for the Mother Application (Web), all Web Clients, Backend/Core Platform, Database Migrations, Rule Engines, Agents, and API contracts.
- **Android Studio (External):** Native Android clients (`apps/android` / separate studio project) developed after core API contracts stabilize.

---

## Authoritative Documents

| Document | Purpose |
|---|---|
| `docs/CONSTITUTION.md` | Engineering and product principles (UNDER REVIEW — not yet FROZEN) |
| `docs/ASPIRE_APPLICATION_BOUNDARIES.md` | **FROZEN** Ecosystem model, Mother App (Web), Core Platform, OpenCode vs Android Studio boundaries |
| `docs/ASPIRE_MOTHER_APPLICATION_SPECIFICATION.md` | **FROZEN** Mother Application role workspaces, management capabilities & UX |
| `docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md` | **FROZEN** Mother System architecture specification |
| `docs/decisions/ADR-002_INTERVENTION_PLAN_APPROVED_EVENT.md` | **ACCEPTED** `INTERVENTION_PLAN_APPROVED` domain event, payload & emission rule (amends 03 §8.2) |
| `docs/decisions/ADR-003_CORE_PLATFORM_RECONCILIATION.md` | **RECONCILIATION BASELINE (11 Oct 2026)** facts vs docs vs code; open lead decisions (§6); do-not-touch list |
| `docs/11_ROADMAP.md` | **PROPOSED ordering authority** — Core Platform checklist + ordered slices R1–R15 (pending lead ratification; supersedes `10_TASKS.md` statuses) |
| `DESIGN.md` | **FROZEN** Linear-inspired UI/UX design system, semantic truth tokens, layout rules |
| `docs/01_PRD.md` | Product scope, P0/P1 features, demo story |
| `docs/02_USER_JOURNEYS.md` | User flows (student risk, mentor queue, data conflict) |
| `docs/03_SYSTEM_SPEC.md` | Deterministic engines: attendance, assessment, tasks, events, cases |
| `docs/04_ARCHITECTURE.md` | **FROZEN** Stack, service boundaries, folder structure, service map |
| `docs/05_DATA_API_CONTRACTS.md` | PostgreSQL schema, API boundary rules |
| `docs/06_AGENT_SPEC.md` | Agent contracts, tools, forbidden actions, degradation |
| `docs/07_SECURITY_TRUST.md` | Auth, RBAC, prompt injection, audit |
| `docs/08_EVALS.md` | Test fixture suites for all engines and agents |
| `docs/09_EDGE_CASES.md` | Adversarial scenarios catalogue |
| `docs/10_TASKS.md` | Build order — task IDs, prompts, acceptance criteria |

---

## Frozen Decisions (Do Not Reverse Without Team Lead Approval)

| ID | Decision |
|---|---|
| ADR-001 | Mother System Layered Modular Monolith (FastAPI) + LangGraph agent orchestration + in-process async event dispatch + 5m hybrid scheduler. Zero client-side business logic. |
| APP-BOUND-01 | ASPIRE is ONE product. Mother Application is a human-facing Web management/control app (`apps/web`). Core Platform is backend/engines. Native Android apps are built in Android Studio as external API consumers. |
| DM-NEW-ORM01 | SQLAlchemy 2.x (async) + psycopg3 + repository layer. Prisma removed. `db/migrations/*.sql` is the ONLY schema authority. |
| DM-API01 | FastAPI + Pydantic → generated `contracts/openapi.json`. No manual edits. CI fails on drift. |
| DM-LLM01 | `Agent → LLMService → OpenRouter`. LIVE and MOCK modes only. One bounded retry. Schema-validate all output. No silent cross-model fallback. |
| DM-AG03 | Hybrid scheduler: startup + every 5 minutes. Idempotent. Never directly mutates business state. Never calls agents/LLMs. |
| DM-SS02 | `OVERDUE` is a derived display state (deadline < now AND PENDING). Not persisted as a status column. |
| DM-SS03 | Mentor queue sort: Urgency Band → Exam Proximity → Days Since Last Mentor Action. Staleness = visible badge, not sort key. |
| DM-ASSESS01 | Assessment component structure is configuration-driven (`assessment_components` table). OQ-06 is resolved: components defined in DB, not hardcoded. |
| DM-NEW-LATE01 | `LATE` attendance status is reserved but unsupported in v1. `attendance_status` enum includes it but no business logic handles it yet. |
| E-06 | PRs ≤ 300 changed lines. Docs-only sync commits exempt. |
| E-07 | `main` is the canonical branch. Feature branches: `feature/<id>-<name>`. No direct work on `main`. Branch rename from `master` to `main` is deferred to repository finalization. |
| OQ-A01 | Single FastAPI process in v1. |
| OQ-A02 | Next.js + FastAPI run natively. Supabase CLI local stack for DB/Auth/Storage. No custom Compose. |
| OQ-A03 | TypeScript Zod (frontend) + Python Pydantic (backend). Compatibility via generated OpenAPI contract + tests. |
| ARCH-01 | LangGraph frozen as agent graph engine (ADR-001). |
| ARCH-02 | Asyncio in-process event bus for v1; no Redis/Kafka/Temporal in v1 (ADR-001). |
| ARCH-04 | Layered Modular Monolith inside FastAPI (ADR-001). |
| OQ-AG02 | Asynchronous background execution for event-triggered agent workflows + synchronous ad-hoc endpoints (ADR-001). |
| OQ-AG03 | In-process asyncio worker loop at startup + every 5 minutes (ADR-001). |
| ADR-002 | `INTERVENTION_PLAN_APPROVED` is a distinct catalog event (mentor approval → case ACTIVE, emitted post-commit). `PLAN_ACCEPTED`/`PLAN_DECLINED` remain student-only. Audit action stays `PLAN_APPROVED_BY_MENTOR` (07 §4) and is separate from the event. |

---

## Current Architecture (Summary)

```
       ASPIRE MOTHER APPLICATION (Web / Next.js)
                         │
       ASPIRE CLIENT APPS (Student Web / Native Android)
                         │ (HTTPS / Supabase JWT)
             FastAPI API Gateway (Mother System Core)
                         │
          ┌──────────────┴──────────────┐
     Rule Engines                 Agent Orchestrator
    (pure Python)                 (LangGraph state graph)
          │                              │
          │                         LLM Service (→ OpenRouter)
          │                              │
    SQLAlchemy Repositories (async)
          │
    PostgreSQL + pgvector (Supabase)
```

---

## Current Task

**Phase-0 Architecture Reconciliation — DONE (11 Oct 2026, docs-only, lead-directed).**
Read-only audit of docs + code + GitHub; produced `docs/decisions/ADR-003_CORE_PLATFORM_RECONCILIATION.md` (facts/recommendations/lead decisions), `docs/11_ROADMAP.md` (checklist + slices R1–R15, PROPOSED pending ratification), a Phase-0 addendum in `docs/04_ARCHITECTURE.md` (§9; four-client map + actual `app/` module map superseding the stale `services/` tree), and a staleness banner in `docs/10_TASKS.md`. No application code, migrations, CI, or git state touched. Verdict: Layered Modular Monolith (ADR-001) confirmed correct and preserved. **Awaiting lead:** ratify roadmap ordering + P0 security slice (R1) — ADR-003 §6.2/§6.3.

**Vertical Slice 1 — Mentor Plan Approval (DONE, branch `feature/vertical-slice-case-approval`).**
Full loop: domain → API → UI → state change → event → audit → tests.

Completed this slice:
- **Docs (lead's contract-first sequence):** `docs/decisions/ADR-002_INTERVENTION_PLAN_APPROVED_EVENT.md` (payload, producer/consumer, emission rule); catalog row added to `docs/03_SYSTEM_SPEC.md §8.2`; no-consumer note in `docs/06_AGENT_SPEC.md` (Supervisor routing unchanged).
- **Backend:** `app/core/events.py` (asyncio in-process bus, ARCH-02, Minimal Event Contract §8.1), `app/services/case_service.py` (sole owner of §10.2 mentor transitions; refuses non-`PENDING_APPROVAL` with 409; audit row via `log_audit` → commit → emit, rejection = audit only), `cases.py` approve endpoint now thin (fixed pre-existing bare-int raises + missing `StudentTask` import), `get_event_bus` dependency, `app.state.event_bus` at import, `CaseApproveRequest.decision` tightened to `Literal[...]`.
- **UI:** `apps/web/app/lib/api.ts` (typed client, Bearer from `localStorage aspire_token` → `NEXT_PUBLIC_ASPIRE_DEV_TOKEN`, `NEXT_PUBLIC_API_URL`); queue page fetches live `/cases/queue` (demo-row fallback with visible notice), Approve button only on `PENDING_APPROVAL` rows, POSTs real approval, updates row to `ACTIVE`, surfaces errors honestly.
- **Schema-conformance fix:** approval no longer writes `plan.status = "APPROVED"` (not in `PROPOSED|ACCEPTED|CUSTOMIZED|DECLINED|SUPERSEDED` — 05 §9 / migration 009); verdict stays in `mentor_decision`.
- **Tests:** 46/46 (`tests/test_events.py` ×5, `tests/test_case_service.py` ×8, 7 new router tests incl. 200/401/403/404/400/409/422). `contracts/openapi.json` regenerated (11 paths; +409/+400 responses, decision enum).
- **Gates:** typecheck 0 · lint 0 · build ✓ (7 routes) · pytest 46/46 · openapi drift test ✓.

Known limitation (accepted): browser→API E2E needs the Supabase local stack (OQ-A02); verified via TestClient + contract tests here.

**P1 remediation of forensic audit (cb300da) — DONE this task, branch `feature/vertical-slice-case-approval`.**
Forensic audit (`audit/vertical_slice_forensic_audit_cb300da.md`, verdict FAIL) found four P1s; all four fixed with regression tests that fail against the old implementations:
- **F-01 (500 on plan history):** router fetches *all* plans via `_plans_for_case_query` (never `scalar_one_or_none`); Case Approval Service selects the single plan awaiting mentor verdict (`ACCEPTED|CUSTOMIZED` AND `mentor_decision IS NULL`, ADR-002 §5). 0 → `NO_PLAN` 400; >1 → `AMBIGUOUS_PLAN` 409 (§10.2 refuses ambiguity, never picks an arbitrary row). Validation order: decision → state → plan selection (double-approval attempt 2 → 409, not 400).
- **F-02 (spec contradiction):** `03_SYSTEM_SPEC §8.2` catalog row now states emission happens only after APPROVED/EDITED commits `PENDING_APPROVAL → ACTIVE`; rejection = audit only. ADR-002 Amends line corrected to §8.2.
- **F-03 (no row lock):** `_case_for_approval_query(...).with_for_update()` is the first execute in approve — PostgreSQL row lock serializes concurrent approvals; blocked second request re-reads committed state → 409. No new infra (no Redis/outbox). Covered by FOR UPDATE compile test + sequential double-approval test. **Implementation verified; genuine two-connection test LATER landed in slice 3** (`tests/test_concurrent_student_decisions_pg.py`, DSN-gated — passed on py3.11/py3.14 against real PostgreSQL).
- **F-04 (client/server sort divergence):** canonical DM-SS03 order now lives only in `PriorityEngine.sort_mentor_queue(list[QueueEntry])`; router builds entries, sorts, returns that order; queue page no longer re-ranks (renders as-is); `DEMO_ROWS` authored in canonical order. PQ-01…PQ-09 regression fixtures + band/NULL handling tests all pass; proof script shows old sorts fail PQ-03/06/07/08/09.
- **Gates after remediation:** pytest **69/69** (+23) · typecheck 0 · lint 0 (ESLint) · build ✓ (6 routes) · OpenAPI regenerated + idempotent (409/400 description updates) · ruff per-file counts ≤ baseline (only style-consistent `timezone.utc` additions).

**Pre-next-slice P2 gate review (F-05 / F-08 / F-09 / F-03) — DONE, commit `chore(quality): close pre-next-slice P2 gates`.**
- **F-05 → NON-BLOCKING P2.** Audit of the only implemented transition family (mentor rows, §10.2): validates current case state, plan state (`ACCEPTED|CUSTOMIZED` + `mentor_decision IS NULL`, delivered by F-01), plan identity (queried under the case), actor authority (`require_mentor_or_admin` + explicit mentor/HOD check), and transition legality (whitelisted mapping). Plan *version* column does not exist in migration 009 (schema authority) — none applicable today. All other §10.2 transitions (`OPEN → IN_REVIEW` … `RESOLVED → CLOSED`) have **no implementation yet**; their state/plan/actor validation is acceptance criteria for their own future slices, not pre-work. Remaining F-05 delta (evidence gap closed here, no production code changed): +2 regression tests proving DECLINED/SUPERSEDED-only plans are refused `NO_PLAN` with zero mutation/event (`test_f05_dead_plan_cannot_authorize_approval`). Note: audit suggested 409 for dead plans; existing contract keeps missing/awaiting-plan failures at 400 (`NO_PLAN`) and reserves 409 for state/ambiguity — unchanged, documented.
- **F-08 → BLOCKER FOR NEXT SLICE, FIXED.** Canonical type determined: **array of event-ID strings** — evidence: migration 009 comment "Array of event IDs", `05 §intervention_cases` "Array of event IDs", engine `TriggerEvent.event_type: str` + `reason_codes: list[str]`, demo rows `string[]`, frontend `string[]`/`getEventLabels(events: string[])`. The outliers were the two backend type hints (`schemas.py` `list[dict]`, model `list[dict[str, Any]]`) — with a real producer (next slice's `create_intervention_case`), string rows would have failed response validation → queue 500, and dict rows would render `[object Object]`. Fixed: both hints → `list[str]`; `05:286` clarified "(strings)"; OpenAPI regenerated (`items: {type: string}`). No event names invented, no event-catalog (§8.2) change — this aligns code with the already-documented contract, not an amendment.
- **F-09 → IMPLEMENT NOW, DONE.** `.github/workflows/ci.yml` gains a `backend` job (existing `ci` Node job untouched): setup-python 3.11 → `pip install -e ".[dev]"` → `python -m pytest tests/ -q` → `generate_openapi.py` + `git diff --exit-code contracts/openapi.json` (DM-API01 "CI fails on drift"). No secrets: dummy `DATABASE_URL` env (NullPool engine never connects during tests/generation — validated by running the whole suite with `.env` removed). Triggers/jobs otherwise unchanged.
- **F-03 → IMPLEMENTATION VERIFIED / CONCURRENCY TEST NOW EXISTS (slice 3).** Re-verified all five claims by code reading: lock acquired inside the request transaction (SELECT FOR UPDATE is the first case read, held to service commit); authoritative `intervention_cases` row locked; state re-evaluated on the locked read (READ COMMITTED re-fetch after lock), so the §10.2 check runs on post-lock data; loser blocked → re-reads `ACTIVE` → `ILLEGAL_TRANSITION` → 409 → rollback (no second successful transition; no second audit/event). Genuine two-connection test **now exists and passed** against real PostgreSQL: `tests/test_concurrent_student_decisions_pg.py` (slice 3, `024369c`) — races two sessions on the student-decision path, which shares the same `_case_row_for_update` locking pattern; mentor-path variant still covered by the compile + sequential tests.
- **Gate validation:** pytest **71/71** (69 + 2 F-05) in clean env (no `.env`, dummy `DATABASE_URL` — exact CI simulation) and normal env · typecheck 0 · lint 0 · build ✓ · OpenAPI regen idempotent, byte-identical with and without `.env` · ci.yml parses as valid YAML · ruff: no new issues on touched lines.

**CI gate verification (F-09 proven live) — DONE, head `5f88157`.** Feature-branch pushes never run CI (triggers are push/pull_request to `[main, master]` only), so runs were driven through draft **PR #1** (`feature/vertical-slice-case-approval` → `master`; exists solely to trigger the workflow — not for review/merge, lead may close it):
- Run `38029199890` (head `511411a`): **backend FAILED** — clean install resolved `sqlalchemy>=2.0.30` → 2.1.4 where greenlet ships only via `sqlalchemy[asyncio]` (`ModuleNotFoundError`); latent second defect: `tests/test_api_routers.py` used `uuid.UUID` annotation with only `uuid4` imported (NameError on Python 3.11; masked on local 3.14 by PEP 649 deferred annotations). Node `ci` job green.
- Fix commit `5f88157` (`fix(ci): restore backend CI contract on clean installs`): `sqlalchemy[asyncio]>=2.0.30` in pyproject, `import uuid` in the test, `contracts/openapi.json` regenerated under CI-resolved deps (fastapi 0.143.0 / pydantic 2.14.0 / sqlalchemy 2.1.4 — byte-identical on Python 3.11.15 and 3.14.4).
- Run `38030328306` (head `5f88157`): **SUCCESS both jobs** — backend `71 passed` + drift clean; Node typecheck/lint/build green. Phase-1 gate satisfied with observed remote evidence.

**Vertical Slice 2 — Student Plan Acceptance (DONE, commit `7e0faf3`, branch `feature/vertical-slice-case-approval`).**
Team-lead scope decision: **acceptance rows only** — `PLAN_PROPOSED → PENDING_APPROVAL` for `ACCEPTED` and `CUSTOMIZED`. Decline (`→ REPLAN_REQUIRED`, event `PLAN_DECLINED`), agent proposal production (`IN_REVIEW → PLAN_PROPOSED`), Supervisor wiring, journey Step 7 task materialization and UI are deferred to their own slices.
- **Service:** `app/services/student_action_service.py` — Student Action Service (03 §8.2 catalog producer) is the sole owner of the student transition rows: decision validation (decline arrives as `INVALID_DECISION`) → §10.2 state guard (409) → authoritative plan selection (exactly one `status='PROPOSED' AND student_decision IS NULL`; 0→`NO_PLAN` 400, >1→`AMBIGUOUS_PLAN` 409; decided/dead history never selected) → payload rules (`CUSTOMIZED` requires non-empty `plan_actions`, `ACCEPTED` forbids them — journeys 1.1 Step 6) → plan (`student_decision`/`decided_at`/`status`, `plan_actions` rewrite for CUSTOMIZED) + case mutation → audit row (`PLAN_ACCEPTED`, 07 §4; `source_system='STUDENT_APP'`) → **commit → emit** `PLAN_ACCEPTED` (Minimal Event Contract §8.1).
- **Endpoint:** `POST /api/v1/cases/{case_id}/student-decision` — `require_roles(STUDENT)`; real own-data check (`StudentProfile.user_id` → `case.student_id`, 403 without existence oracle); case row locked `FOR UPDATE` (shared helper renamed `_case_row_for_update`); concurrent double-POST serializes → one transition/audit/event, loser 409.
- **Schema:** `StudentDecisionRequest` (Literal `ACCEPTED|CUSTOMIZED` + model-level payload rules → 422) / `StudentDecisionResponse`.
- **Tests:** +18 service, +14 router → suite **71 → 103**; covers happy/customized, illegal state, invalid & deferred decline, no/dead/ambiguous plans, plan-history selection, state-guard ordering, audit contract, minimal event contract, idempotent re-decision, 401/403/404/400/409/422 matrix, double-POST, FOR UPDATE compile.
- **Contract:** `contracts/openapi.json` regenerated (12 paths, purely additive, byte-identical on py3.11/py3.14).
- **CI:** run `38032011350` (head `7e0faf3`) — **SUCCESS both jobs**, backend `103 passed` + drift clean (observed).

**Vertical Slice 3 — Student Plan Decline + Genuine PG Concurrency Test (DONE, commit `024369c`, branch `feature/vertical-slice-case-approval`).**
Scope delivered exactly as specified: decline row of `03 §10.2`, genuine two-connection PostgreSQL concurrency test, and the `STUDENT_APP` audit-source doc gap.
- **Decline:** `decide_plan` now accepts `DECLINED` → case `PLAN_PROPOSED → REPLAN_REQUIRED`, `plan.status = DECLINED`, optional `reason` stored **only** on `plan.student_reason` (verbatim; no content rules specified in 02/05) — never copied into audit state JSON or the event payload (07 §4 UUID/status-only). Emits `PLAN_DECLINED` post-commit (catalog producer, emit only — no consumer wiring). Audit `action_type` is decision-specific (`PLAN_ACCEPTED`/`PLAN_DECLINED`). `reason` may only accompany `DECLINED` (schema validator → 422 + service re-check `INVALID_REQUEST`); `plan_actions` remain CUSTOMIZED-only.
- **Endpoint/schema:** `POST /cases/{case_id}/student-decision` passes `reason`; `StudentDecisionRequest.decision = Literal["ACCEPTED","CUSTOMIZED","DECLINED"]` + optional `reason`.
- **Genuine concurrency test:** `tests/test_concurrent_student_decisions_pg.py` (marker `integration`) — two independent NullPool `AsyncSession`s on one throwaway PostgreSQL (`aspire-it-pg`, pgvector pg16, port 55432, db `aspire_test`) race the real `_case_row_for_update` FOR UPDATE path with `asyncio.Event` handshakes; loser must be `ILLEGAL_TRANSITION` (409) while winner holds the lock; asserts exactly 1 plan/1 audit row/1 event total, loser 0 events, audit action + `STUDENT_APP` actor, no PII/free text in state JSONs. **Skips when `ASPIRE_TEST_PG_DSN` unset (CI default); FAILS if the DSN database name does not end in `_test` (safety guard).** Fixture builds the schema from `db/migrations/*.sql` in a unique schema and drops only that schema.
- **Defect the test exposed & fixed:** `AuditLog.id` had no client/server default → real-PostgreSQL flush failed `FlushError: NULL identity key` (column omitted from INSERT, no RETURNING). `app/models/audit.py` now sets `server_default=text("gen_random_uuid()")` mirroring migration 007 — this also fixes the latent mentor-approval audit path.
- **Doc gap closed (comment-only, no schema change):** `05 §7` value list + `007_audit_log.sql` comment now read `CSV_IMPORT | MENTOR_WEB | RULE_ENGINE | AGENT | STUDENT_APP` (plain TEXT, no CHECK).
- **Found, then fixed (commit `f42ed52`):** `InterventionPlan.reason_codes` was ORM `JSON` but migration 009 `TEXT[]` — ORM INSERTs would have failed on real PostgreSQL; models are not schema authority (DM-NEW-ORM01), so slice 3 seeded via Core literal with `ARRAY(String)` and reported it. The model now declares `ARRAY(Text).with_variant(JSON, "sqlite")` — see the dedicated section below.
- **Tests:** suite **103 → 121** (+12 service, +6 router; decline transition/emit/reason rules, 422 matrix, decline 409/400, persisted reason); with `ASPIRE_TEST_PG_DSN` set → **123**. CI-parity py3.11 venv: 121 passed + 2 skipped (no DSN), and the PG file alone **2 passed with DSN**.
- **Contract:** OpenAPI regenerated (12 paths, +16/−4), byte-identical regen on py3.11/py3.14.
- **Lint:** no new debt — per-file counts vs HEAD baselines equal (cases 22, schemas 25, audit 1, service 0, router tests 6, service tests 0, new PG test 0). Unrelated `ruff --fix` churn in `cases.py`/`schemas.py` was reverted; only slice edits remain.
- **CI (observed):** run `38037438277` (head `024369c`) — **SUCCESS both jobs** (`backend` pytest `121 passed, 2 skipped` + drift clean; Node `ci` green). Local gates: typecheck 0 · lint 0 · build exit 0.
- **PG teardown:** container `aspire-it-pg` left running (port 55432) for reuse; safe to `docker rm -f aspire-it-pg` — the test skips without the DSN.

---

**`InterventionPlan.reason_codes` ORM/schema correction (DONE, commit `f42ed52`, branch `feature/vertical-slice-case-approval`).**
Narrow persistence-contract fix; migration 009 untouched, no new migration (live catalog inspection of `aspire_test` showed no pre-existing `intervention_plans` — 0 rows — so the real schema was never inconsistent with the migration).
- **Evidence of the mismatch:** `db/migrations/009_intervention.sql:38` `reason_codes TEXT[] NOT NULL` vs `app/models/intervention.py` `mapped_column(JSON, nullable=False)` — **type only**; nullability already matched (both NOT NULL) and neither side declared a default.
- **Correction:** `ARRAY(Text).with_variant(JSON, "sqlite"), nullable=False` (SQLAlchemy 2.1.4) — renders `TEXT[]` on PostgreSQL (exact migration match; `pg_catalog.format_type` = `text[]`), `JSON` on SQLite so the F-01 in-memory real-query test (`Base.metadata.create_all`, which cannot compile a PostgreSQL ARRAY — proven `UnsupportedCompilationError`) keeps running in CI. No custom TypeDecorator, no generic cross-database type.
- **Call-site inspection:** no JSON operators/filters/in-place mutations anywhere; engine `InterventionPlanData` is a separate DTO; no Pydantic schema exposes `reason_codes` → **no public contract change, OpenAPI regen byte-identical (nothing committed)**.
- **New tests:** `tests/test_intervention_plan_reason_codes.py` (3 static, CI-runnable: ORM compiles to `TEXT[]` + NOT NULL + no default; migration line == `reason_codes TEXT[] NOT NULL,`; sqlite variant `JSON`) and `tests/test_intervention_plan_reason_codes_pg.py` (3 live: ORM insert → separate-session read-back with values/order preserved → update; empty `[]` persists with `IS NULL = false` while SQL NULL is refused `IntegrityError`; `pg_catalog` `text[]` + `attnotnull` + no default tied to the migration text). Shared fixtures (`DSN guard`, `pg_engine`, `pg_seed`) extracted to `tests/conftest.py`; `pg_seed` now seeds `reason_codes` via the ORM — the Core `literal(..., ARRAY(String))` workaround was removed as obsolete.
- **Execution (actual):** local py3.14 **124 passed, 5 skipped** (no DSN) and **129 passed** (+DSN, 7.31s — all 5 integration tests against real PostgreSQL); CI-parity py3.11 **124 passed, 5 skipped**, integration-only with DSN **5 passed** (6.61s). CI (observed): run **`38038621673`** (head `f42ed52`) **SUCCESS both jobs** — backend runs the same suite (expected `124 passed, 5 skipped`; CI log download was denied by API permissions so the count line was not read from the remote log — conclusion observed via API, counts verified locally on the same commit). Lint: per-file counts equal HEAD baselines (model 5 → 5 pre-existing, concurrency test 0, new files 0).
- **Remaining discrepancy (superseded by `faa49a7`):** the JSON-vs-JSONB observation below was fixed for the three intervention columns in the next task; six other JSONB columns (migrations 007/011/012) remain JSON in the ORM — see the JSONB correction section.

---

**JSONB ORM correction for intervention columns (DONE, commit `faa49a7`, branch `feature/vertical-slice-case-approval`).**
Scope: exactly the three fields reported from the previous task's audit; migration 009 untouched, no new migration (fresh disposable container had no pre-existing tables, so the live schema could not disagree with the migration).
- **Evidence (audited, not assumed):** migration 009 `trigger_events JSONB,` (line 18, no NOT NULL) vs ORM `InterventionCase.trigger_events = JSON, nullable=True`; `plan_actions JSONB NOT NULL,` (line 37) vs `JSON, nullable=False`; `evidence JSONB NOT NULL,` (line 39) vs `JSON, nullable=False` — **type only**; nullability matched on all three, no defaults anywhere. Migration 001 (`001_enable_pgvector.sql`) contains no JSON columns.
- **Correction:** `JSONB().with_variant(JSON, "sqlite")` on all three (SQLAlchemy 2.1.4, PostgreSQL-dialect `JSONB` as required — renders `JSONB` on PG, `JSON` on SQLite). The sqlite variant is required by the existing F-01 test (`Base.metadata.create_all` of these two tables on SQLite, where JSONB cannot compile) — same pattern as `reason_codes`. Nullability/defaults untouched; no custom TypeDecorator; no Mutable tracking added (every write site is a whole-attribute assignment: `plan.plan_actions = ...` in `student_action_service`, `case.trigger_events` never written in production yet; no JSON operators/indexing/containment anywhere in app code).
- **Call-site inspection:** reads are `case.trigger_events or []` (router response mapping) and test assertions on decoded values — all Python-level, unaffected by the type swap; engine `InterventionPlanData.evidence: list[str]` remains a separate DTO (note: ORM/DB `evidence` shape in tests is a dict — domain-shape question untouched by this type fix).
- **New tests:** `tests/test_intervention_plan_jsonb.py` (4 static, CI-runnable: JSONB compile + nullability + no default + migration line per column; sqlite variants all `JSON`) and `tests/test_intervention_plan_jsonb_pg.py` (3 live: `plan_actions`/`evidence` insert(seed) → separate-session read-back → full replacement → fresh read with nested structure preserved; `trigger_events` None ↔ `[]` ↔ populated list with raw `IS NULL` checks proving empty≠NULL; `pg_catalog` `jsonb` + `attnotnull` true/true/false + no defaults for all three, tied to migration text).
- **Execution (actual):** local py3.14 **128 passed, 8 skipped** (no DSN) and **136 passed** (+DSN, 15.55s — all 8 integration tests on real PostgreSQL: 2 concurrency + 3 reason_codes + 3 jsonb); CI-parity py3.11 **128 passed, 8 skipped**, integration-only with DSN **8 passed** (14.85s). Focused runs: static 4 + F-01 = 5 passed; jsonb PG file 3 passed. Docker had to be restarted this task and `aspire-it-pg` recreated (fresh container; `CREATE EXTENSION vector WITH SCHEMA public` re-applied — migration 001's `IF NOT NULL`… `IF NOT EXISTS` then no-ops across throwaway-schema teardowns).
- **Lint:** `app/models/intervention.py` 5 → 5 (pre-existing E501/F821, line-shift only); new files 0 errors. **OpenAPI:** regen byte-identical → no contract change, nothing committed.
- **Remote CI (observed):** run **`38053851770`** (head `faa49a7`) **SUCCESS both jobs** (backend pytest + drift; Node `ci` green). As before, only the conclusion was read via API — expected backend count on this commit is `128 passed, 8 skipped` (verified locally; CI log download denied).
- **Remaining discrepancies (superseded by `0bb26ca`):** the six JSONB columns below were corrected in the consolidated audit; the `evidence` shape question remains held for a lead decision — see the section after this one.

---

**Consolidated ORM/DB contract audit — remaining six JSONB columns + evidence gate (DONE, commit `0bb26ca`, branch `feature/vertical-slice-case-approval`).**

- **Audit inventory (all six verified against migrations; migration files untouched):**

  | Column | Migration (authority) | ORM before | Nullability | Defaults | Call sites |
  |---|---|---|---|---|---|
  | `audit_log.previous_state` | 007:13 `previous_state JSONB` | `JSON, nullable=True` | matched (nullable) | none | constructor kwargs in `deps.log_audit`, `security.auth`, `case_service`, `student_action_service`; test reads `.keys()` / `json.dumps` / indexing |
  | `audit_log.new_state` | 007:14 `new_state JSONB` | `JSON, nullable=True` | matched | none | same as previous_state |
  | `data_conflicts.existing_value` | 011:9 `existing_value JSONB NOT NULL` | `JSON, nullable=False` | matched | none | **no call sites** (model-only; registry has no writer/reader yet) |
  | `data_conflicts.incoming_value` | 011:10 `incoming_value JSONB NOT NULL` | `JSON, nullable=False` | matched | none | no call sites |
  | `data_conflicts.resolution` | 011:15 `resolution JSONB` | `JSON, nullable=True` | matched | none | no call sites |
  | `institution_rules.value` | 012:12 `value JSONB NOT NULL` | `JSON, nullable=False` | matched | none | whole-column `select(InstitutionRule.value)` ×2 in attendance router; no writers |

  Classification: all six = **confirmed type-only mismatches** (migration JSONB vs ORM JSON). No JSON operators (`astext`/`jsonb_path`/containment) or in-place mutations anywhere — all writes are whole-value assignments; no column-level indexes/constraints on these six (indexes target other columns). **No sqlite variant added:** the only `create_all` in the repo is the F-01 test with `tables=[InterventionCase, InterventionPlan]`, so SQLite never compiles these three tables (unlike the intervention pair); plain `JSONB` renders on PostgreSQL per task rule "reuse `with_variant` only where required".
- **Correction — `JSONB(none_as_null=True)`:** type aligned to migration JSONB (nullability/defaults/Python annotations unchanged). `none_as_null=True` was added because **live verification proved** SQLAlchemy's default persists Python `None` as JSON `null`: raw `IS NULL` checks came back false on nullable columns, and a `None` insert into NOT NULL `existing_value` was accepted (JSON null is a value, not a NULL violation). With `none_as_null=True`, `None` → SQL NULL: nullable columns (007/011) hold true SQL NULL, NOT NULL columns (011/012) reject `None` with `IntegrityError` — both now tested. The same flag was applied to the three `faa49a7` intervention JSONB columns (`trigger_events`/`plan_actions`/`evidence`) for identical contract semantics — type unchanged, Python read behavior unchanged (JSON null and SQL NULL both decode to `None`); all prior tests stayed green.
- **`evidence` shape — HELD FOR LEAD DECISION (no shape-changing code modification):** authoritative sources genuinely disagree. Migration 009 + `05_DATA_API_CONTRACTS:303` say only `JSONB NOT NULL` (shape-agnostic). `06_AGENT_SPEC` attendance-specialist output contract (L142–147) defines `evidence` as an **object** (`{attendance_percentage, threshold, required_to_recover, exam_days_remaining}`), with `{}` at L108/L260; `02_USER_JOURNEYS:93` and `10_TASKS:1539` define a **string array** (`["attendance 73%", "threshold 75%", "exam 8d"]`); engine DTO `InterventionPlanData.evidence: list[str]` builds human-readable strings; ORM `Mapped[dict[str, Any]]` (tests seed `evidence={}`). No production producer exists — nothing constructs `InterventionPlan(...)` (only the class definition), no Pydantic/API schema exposes `evidence` — so **no runtime conflict today**; the clash will surface when the agent-proposal slice persists plans. Interpretation: primarily **(3) unresolved domain decision**, with elements of **(1) cross-spec inconsistency** (spec vs spec, not just code vs spec). **Smallest decision needed from the lead:** for the plan-creation producer, is canonical persisted `evidence` the agent-spec **object** or the engine/user-journey **string array**? The database needs no migration either way (JSONB); afterwards align ORM annotation + engine DTO + test seeds + the losing spec document inside that slice. No canonical format was invented here. [RESOLVED: DEC-01 APPROVED (structured entries, C-lite) and implemented — see Architecture Decision Gate / DEC implementation record below.]
- **Other discrepancies discovered (NOT fixed — out of scope):** (a) `institution_rules.institution_id` — migration 012:8 is **nullable** (no `NOT NULL`) but ORM `Mapped[UUID]` infers NOT NULL: ORM stricter than schema. (b) Latent flush risk: `data_conflicts.id` and `institution_rules.id` lack `server_default=gen_random_uuid()` although both migrations define `DEFAULT gen_random_uuid()` — `audit.py` documents that this exact shape without a server_default fails real-PG flush with "NULL identity key" (first surfaced by the concurrency test); unproven here because neither table has a production writer yet, and the new tests set `id` explicitly to work around it. Both need a lead decision (schema-conformance scope), not silent fixes.
- **New tests:** `tests/test_jsonb_audit_rules_conflicts.py` (3 static, CI-runnable: all 6 columns → `isinstance(JSONB)`, PG compile `JSONB`, nullability, no defaults, exact migration line 007/011/012) and `tests/test_jsonb_audit_rules_conflicts_pg.py` (5 live: audit-log round-trip insert→separate-session read→full replacement→fresh read with nested list preserved, `None`→raw `IS NULL` true; conflict round-trip with `resolution` NULL→value→NULL; NOT NULL `IntegrityError` for `existing_value=None`; institution-rule round-trip incl. the attendance-router-shaped `select(InstitutionRule.value)`; `pg_catalog` `jsonb` + `attnotnull` (F,F,T,T,F,T) + no defaults for all six). `pg_seed` gained `institution_id` (additive, existing tests unaffected).
- **Execution (actual):** focused static+F-01 **11 passed**; focused live PG (2 jsonb files + reason_codes + concurrency) **13 passed** (21.46s). Full suite py3.14 **144 passed** (+DSN, 22.16s) / **131 passed, 13 skipped** (no DSN); CI-parity py3.11 **131 passed, 13 skipped** (no DSN), integration-only +DSN **13 passed** (22.97s). Lint: audit 1→1, conflicts 1→1, rules 5→5, intervention 5→5 (all pre-existing), conftest 0, both new files 0 errors. OpenAPI regen **byte-identical** → no contract change, nothing committed. Frontend gates not run locally (no shared-contract/generated-artifact change; OpenAPI byte-identical) — Node CI job green.
- **Remote CI (observed):** run **`38055651515`** (head `0bb26ca`) **SUCCESS both jobs** (backend pytest + drift; Node `ci`). Only the conclusion was read via the API — CI log download remains denied; the backend count on this commit is expected `131 passed, 13 skipped` (verified locally on the same commit, **not** read from the remote log).

---

## Architecture Decision Gate — DEC-01/DEC-02/DEC-03 (decided 2026-10-10, APPROVED + implemented)

**Gate phase note (historical):** no runtime, ORM, migration, or API changes were made *in the evidence-gathering phase*. Verification probe ran against a disposable throwaway schema inside `aspire_test` (created, probed, dropped; server `PostgreSQL 16.15`, `gen_random_uuid()` available). Read-only suite re-run after that phase: full no-DSN **131 passed, 13 skipped** (exit 0), focused PG **13 passed** (exit 0). **Status now: all three decisions are APPROVED by the team lead (via the implementation task) and implemented — see the "DEC implementation record" below.**

### DEC-01 — Canonical `InterventionPlan.evidence` persisted shape — `Lead approval: APPROVED (option C-lite)`

1. **Question:** which JSON shape is canonical for the `intervention_plans.evidence` JSONB column when the plan-creation producer lands?
2. **Verified facts (source → shape):** migration `009:39` + `05_DATA_API_CONTRACTS:303` = `JSONB NOT NULL`, **shape unspecified** (authority covers existence/nullability only). Constitution `CONSTITUTION.md:120-123` (A-05) requires `evidence` in the structured envelope, **type unspecified**; `:33-36` (P-03) requires evidence to exist. Design docs conflict: `06_AGENT_SPEC.md:142-147` (Attendance Specialist = the plan-proposing agent) = **flat object** `{attendance_percentage, threshold, required_to_recover, exam_days_remaining}`; `06:108` and `06:260` = `{}` placeholders in *non-plan* envelopes (Supervisor routing, Intervention follow-up — not persisted plan rows); `02_USER_JOURNEYS.md:91-101` (plan JSON, Step 5) = **string array**; `10_TASKS.md:1535-1545` "Parse the LLM output into this EXACT structured format (CONSTITUTION A-05)" = **`evidence: string[]`**. Code: engine DTO `app/engines/intervention.py:36` `list[str]` (built at `:112-147`); ORM `app/models/intervention.py:63-65` `dict[str, Any]` (seeds `evidence={}`); **no producer** — `InterventionPlanData(` constructed only at `engines/intervention.py:149` with zero callers, no `POST /cases/{id}/plans` (only approve `cases.py:177` and student-decision `cases.py:241`), no `InterventionPlan(...)` outside tests; **no API/UI consumer** — no `evidence` field in `app/api/schemas.py`, zero hits in `apps/web`; **built student client mock** `apps/mobile/app/plan/page.tsx:17-22` = **array of entries** `{id, label, value, source, timestamp}` rendered at `:173-178`, with actions carrying `evidenceRefs: ["e1","e2"]` (`:33,:44,:55`). `03_SYSTEM_SPEC.md` never mentions evidence. **No migration impact either way (JSONB).**
3. **Nature of conflict:** cross-spec inconsistency (06 object vs 02/10 string[]) plus a fourth, presentation-driven shape (implemented mock) — unresolved domain decision, zero runtime conflict today (no producer).
4. **Options:** **A — flat object** (06:142): typed facts, matches ORM dict + `{}` seeds, but attendance-specific fields don't generalize across agents, no stable ids for `evidenceRefs`, contradicts 10_TASKS "EXACT" + 02:93 + engine DTO. **B — string array** (10:1539/02:93): matches the LLM parse target and engine DTO, simplest, but loses `source`/`timestamp`/`id` — cannot natively feed the journey Step-3-style panel (`02:67-79` includes "Data freshness") or the built mock's `evidenceRefs` without ad-hoc parsing; contradicts 06:142 + ORM dict. **C — structured evidence entries (recommended, versioning deferred):** canonical persisted shape = JSON array of entry objects `{id, label, value, source, timestamp}` exactly as the implemented mock; 06:142's four fields map 1:1 onto entries (`attendance_percentage→e1`, `threshold→e2`, `exam_days_remaining→e3`, …) so agent-object→entries conversion is trivial; `string[]` remains only the LLM/agent-layer parse format per 10_TASKS:1539 (converted at the producer boundary); engine facts remain the source of truth.
5. **Recommendation: Option C without a version field** (the "versioned" machinery of the full C is **not** justified at single-consumer stage — add only if/when a second producer or shape evolution appears). Rationale: the only concrete rendering implementation requires ids/refs/provenance; P-03/07 explainability is served by `source`/`timestamp`; conversion from both existing spec shapes is lossless-or-cheap; zero migration cost; decision now costs nothing because no producer exists.
6. **Consequences / follow-ups (only after approval):** producer builds entries from engine facts; ORM annotation `dict → list[dict]` + test seeds `{}` → `[]`; correct `06_AGENT_SPEC.md:142-147` (and clarify `:108/:260` are non-persisted); confirm/adjust `02:93` and `10_TASKS:1539` wording to state string[] = LLM parse format, entries = persisted form; typed Pydantic model for the entry at the future `POST /cases/{id}/plans`.
7. **Required tests:** producer round-trip (persisted shape → fresh read → UI entry fields intact); Pydantic schema validation rejecting malformed entries; static test pinning ORM annotation/seed shape; migration untouched (009 line unchanged); OpenAPI drift check when the endpoint lands.
8. **Missing for a defensible final call:** team-lead ratification of which design doc is authoritative between `06:142` and `10:1539/02:93`; confirmation that the mobile mock (`apps/mobile/app/plan/page.tsx`) represents approved design (only Screen 03 was approved per prior state — plan screen approval status unknown).
9. **Lead approval: `APPROVED`** — DEC-01 option C-lite, implemented (Commit A).

### DEC-02 — `institution_rules.institution_id` nullability / global rules — `Lead approval: APPROVED (option B)`

1. **Question:** does ASPIRE support institution-independent (global) rules, or must every rule belong to an institution?
2. **Verified facts:** migration `012:8` `institution_id UUID REFERENCES institutions(id) ON DELETE RESTRICT` — **nullable**; `05_DATA_API_CONTRACTS.md:366` identical (contract and migration **agree** — nullable); ORM `app/models/rules.py:16` `Mapped[UUID]` → NOT NULL (**stricter than schema**). Spec intent everywhere is institution-owned: hierarchy `03_SYSTEM_SPEC.md:29-55` `Institution → … → Rule` (rule example `:36-50` has no institution-free concept; `:52-55` "Eligibility scope must come from the active **institutional** rule configuration"); `05:396` `/institution-rules` Admin-managed; `10_TASKS.md:574,579` T-020 seed = "BCREC institution + config rules"; grep across `docs/` for `global rule|platform-level|system-wide|global default` → **zero hits**; `scope_level` enum `05:368` = `INSTITUTION | BATCH | PROGRAMME | SEMESTER` (no GLOBAL level); `UNIQUE (institution_id, rule_id, scope_level, scope_id, version)` `012:20` — NULLs in UNIQUE are distinct (PG15+ `NULLS DISTINCT` default), so "global" rows could silently duplicate. Consumer: the **only** reader is `app/api/routers/attendance.py:149-196` `_get_attendance_threshold`, filtering `InstitutionRule.institution_id == institution_id` (`:168,:184`) — SQL equality never matches NULL → global rows would be **silently unreachable**; it checks INSTITUTION scope **before** BATCH scope (institution rule wins if present — precedence not documented anywhere); filters `status == ACTIVE` but **not** `effective_from/effective_to` (contrary to `10_TASKS.md:806` "versioned/effective-dated"); `scalar_one_or_none()` with `order_by(version.desc())` would raise if two ACTIVE versions coexist. No rows exist anywhere (no seed files — `db/seeds/` absent; no INSERTs in migrations; no Python writers). **Related discovered defect (separate from nullability):** `attendance.py:155` selects `StudentProfile.institution_id`, a column that exists in **neither** migration `004`, nor `05:136-145`, nor `app/models/student.py:14-22` → that helper would fail on real PostgreSQL; all tests patch `_get_attendance_threshold` (`tests/test_api_routers.py:95`), so it never executes against a real schema. Probe confirmed the DB accepts `institution_id NULL` inserts.
3. **Nature of risk:** ORM stricter-than-schema (annotation lies about the contract) while the domain (per all specs) actually wants the opposite direction — institution-ownership — and the schema accidentally permits NULLs the domain doesn't model.
4. **Options:** **A — global rules supported:** not supported by any spec; would require new scope modelling, NULL-safe lookup, precedence rules, and UNIQUE redesign — rejected for lack of evidence of intent. **B — every rule institution-owned (recommended):** matches all specs, consumer, and seeds; end-state = tighten migration 012 to `NOT NULL` (safe: zero rows exist) via the project's migration process + explicit justification; ORM already expresses this and stays unchanged. **C — explicit multi-scope modelling:** only warranted if a platform/global tier is intended — no evidence found; revisit only if the lead introduces a platform tier.
5. **Recommendation: Option B** — domain is institution-owned configuration; tighten schema in a dedicated, approved migration (e.g., `013_institution_rules_not_null.sql`), do **not** flip nullability silently.
6. **Consequences / follow-ups (only after approval):** new migration `ALTER TABLE institution_rules ALTER COLUMN institution_id SET NOT NULL;` (fresh disposable DB + upgrade path note); keep ORM as-is; fix institution resolution in `_get_attendance_threshold` (DEC-02 related defect — resolve via `users.institution_id` / `batch→institution` chain since `student_profiles` has none); decide and document precedence (batch-override vs institution-default) and add effective-date filtering per `10_TASKS:806`; clarify whether ORM should relax to `Mapped[UUID | None]` in the interim instead — lead call.
7. **Required tests:** migration-applies cleanly test + `pg_catalog` `attnotnull=true` for `institution_id`; rule-resolution tests covering precedence and effective dating against real PG; a test that executes `_get_attendance_threshold` **unpatched** against the migrated schema (would currently fail — pins the related defect); seed/BCREC row insert path (T-020).
8. **Missing for a defensible final call:** lead confirmation that institution-owned-only is the product intent (no platform tier); decision on interim posture (ORM mirror-now vs migration-first); ownership of the `StudentProfile.institution_id` router defect (outside this gate's change scope).
9. **Lead approval: `APPROVED`** — DEC-02 option B, implemented (Commit B).

### DEC-03 — UUID generation for `data_conflicts.id` and `institution_rules.id` — `Lead approval: APPROVED (option A)`

1. **Question:** who owns id generation for these two PKs, and is the previously-reported risk real?
2. **Verified facts per table:** **migrations** `011:6` and `012:7` both `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` — DB-side generation defined; **project convention** `05_DATA_API_CONTRACTS.md:28`: "**All tables have:** `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`" — DB-generated for all tables; **ORM** `app/models/conflicts.py:15` and `app/models/rules.py:15` = `mapped_column(primary_key=True)` with **no** `server_default` (and no client default) — metadata diverges from both migration and 05 convention; **precedent** `app/models/audit.py:19` carries `server_default=text("gen_random_uuid()")` with comment `:15-18` documenting that the same shape without it fails real-PG flush (first surfaced by the concurrency test). **Persistence call sites:** zero production writers for both tables (model-only; my tests set `id` explicitly). **Live probe (throwaway schema, PG 16.15):** raw `INSERT` omitting `id` **succeeds** for both tables with id populated (server default works; `gen_random_uuid` present); ORM insert omitting `id` **fails** for both — `FlushError: … NULL identity key` (+ SQLAlchemy `SAWarning: … no Python-side or server-side default generator…`), while ORM `AuditLog` insert omitting `id` **succeeds** (server_default path works).
3. **Conclusion per table (confirmed vs possible vs disproved):** for **both** tables — ORM-metadata defect: **CONFIRMED** (reproduced on real PostgreSQL under the actual migrated schema); DB-side generation itself: **DISPROVED as broken** (works); production/user-visible failure: **NOT YET REALIZED (latent)** — no writer exists, so no incident has occurred; the first un-id-setting ORM insert will fail flush (safe-but-broken, not corrupting).
4. **Options:** **A — database-generated (recommended):** mirror the migration with `server_default=text("gen_random_uuid()")` on both ORM ids (audit.py precedent; matches 05:28 convention; `gen_random_uuid()` built-in since PG13 — verified on deployed 16.15). **B — application-generated:** client-side `default=uuid4` — works but creates a second source of truth diverging from the documented DB convention (05:28) and from migration defaults. **C — caller-supplied:** matches current test practice only; contradicts 05:28 "all tables" and leaves every future writer responsible — rejected as the *system* contract, though callers may still pass ids.
5. **Recommendation: Option A for both tables** — smallest fix, restores the documented convention, requires **no migration** (schema already correct), zero behavior change for readers.
6. **Consequences / follow-ups (only after approval):** add `server_default=text("gen_random_uuid()")` to `conflicts.py` and `rules.py` ids; optionally drop now-redundant explicit `id=` in tests (keep if harmless); update `test_jsonb_audit_rules_conflicts_pg.py` to insert at least one row per table **omitting** `id` and assert DB-populated id; no migration, no OpenAPI change.
7. **Required tests:** ORM insert omitting id → succeeds with populated id (both tables, real PG); id uniqueness/round-trip; existing static tests extended to assert `server_default is not None` for these two ids (current static test asserts `atthasdef=false` at catalog level for the JSONB columns — unrelated to PK defaults); full suite ±DSN.
8. **Missing for a defensible final call:** nothing material — evidence is complete; only lead sign-off that Option A is the intended convention (05:28 already says so).
9. **Lead approval: `APPROVED`** — DEC-03 option A for both tables, implemented (Commit C).

### DEC implementation record (2026-10-10, all three approved decisions shipped)

Commits: **A `4d4d0be`** (DEC-01), **B `60f9453`** (DEC-02), **C `2de0dc1`** (DEC-03), **D** = this file.

- **DEC-01 implemented (Commit A):** canonical schema documented in `05_DATA_API_CONTRACTS.md` §`intervention_plans` → "Evidence entry contract" (array of `{id, label, value, source, timestamp}`; `value` = string/number/boolean preserved typed; `timestamp` = tz-aware ISO-8601; `id` = UUID string, unique per array; versioning deferred). Conversion/validation boundary: `app/services/evidence.py` — `EvidenceEntry` (Pydantic, extra="forbid"), `EvidenceProvenance` (required, backend-supplied), `convert_llm_evidence` (LLM `list[str]` → entries; **raises** without provenance or on unsupported items — no fabricated `source`/`timestamp`), `build_evidence_entry` (typed backend facts keep their type), `validate_evidence_entries`/`dump_evidence_entries`. ORM `app/models/intervention.py` `evidence: Mapped[list[dict[str, Any]]]` (migration 009 `JSONB NOT NULL` untouched). Spec reconciliation: 05 (canonical contract + conversion rule), 06 (agent `evidence` object = pre-persistence fact bundle; `{}` envelopes = non-plan), 02 Step 5 (string[] = LLM parse format, entries = persisted/rendered form), 10:1539 (string[] = parse target, inline pointer). Test seeds `evidence={}` → `[]` in 5 files. **Producer integration PENDING** (no plan-creation producer exists; wire `convert`/`build` into the agent-proposal slice — engine DTO stays `list[str]`).
- **DEC-02 implemented (Commit B):** `db/migrations/013_institution_rules_require_institution.sql` — DO-block preflight raises `DEC-02 preflight failed: …` (actionable, refuses, no delete/reassign/invent) while any `institution_id IS NULL` row exists, else `SET NOT NULL`; preserves FK/UNIQUE/indexes. ORM `institution_id: Mapped[UUID]` (already non-null) + DEC-02 comment. Router defect fixed: `_get_attendance_threshold` now resolves institution via the verified chain **`student_profiles.batch_id → batches.institution_id`** (003/004) with a join — the nonexistent `StudentProfile.institution_id` select is gone; no columns added, no auth changes. **Rule precedence (INSTITUTION checked before BATCH) and missing `effective_from/effective_to` filtering were deliberately left unchanged** — both remain undocumented/contradictory (`10_TASKS:806` vs router) and are open questions for the lead, recorded again below. `05` institution_rules block updated (`NOT NULL` + DEC-02 note). New tests: `tests/test_institution_rules_ownership_pg.py` (preflight-refusal on a partial 001–012 chain with a real NULL row; full-chain `attnotnull=true`; NULL insert → `IntegrityError`; owned insert+query; unique constraint intact — note: 012's inline `UNIQUE (...)` is **unnamed**, so PG auto-generated a name; the ORM-declared name `unique_institution_rule` exists only in model metadata — behavior intact, naming discrepancy recorded) and `tests/test_attendance_router_pg.py` (helper institution-scope/batch-scope/default + full `GET /attendance/{id}/what-if` endpoint over real PostgreSQL with dependency overrides — pre-fix this 500s with `UndefinedColumn`).
- **DEC-03 implemented (Commit C):** `server_default=text("gen_random_uuid()")` on `DataConflict.id` and `InstitutionRule.id` (mirrors migrations 011:6/012:7 + `05:28` convention + `audit.py:19` precedent). **No migration** (schema already correct). Explicit-id inserts remain compatible (existing tests unchanged, plus an explicit-id case in the new tests). Tests: `tests/test_uuid_server_default.py` (static, CI-runnable: server_default present + migration line agreement) and `tests/test_uuid_server_default_pg.py` (live: insert-without-id → flush/commit → generated UUID → reload by id → distinct second id → explicit id, for both models).
- **Verification (local, on the final tree):** Python **3.14.4** — full suite `python -m pytest tests -q` **+DSN: 193 passed** (exit 0, 18.56s; all 24 integration tests actually executed against PostgreSQL 16.15 in `aspire_test` via throwaway schemas), **no-DSN: 169 passed, 24 skipped** (exit 0). Python **3.11.15** (`…Temp\opencode\civenv311`) — no-DSN **169 passed, 24 skipped** (exit 0, CI parity), `-m integration` +DSN **24 passed** (exit 0, 21.35s). Lint: `python -m ruff check app tests scripts` → working tree **232 errors vs 233 at HEAD** (net −1; all new/rewritten files 0 errors; touched-file counts unchanged: attendance 19, intervention 5, conflicts 1, rules 5, api_routers 6, case_service 5 — all pre-existing). OpenAPI: `python scripts/generate_openapi.py` → `git diff --exit-code contracts/openapi.json` exit **0** (byte-identical; no public contract change → frontend gates not required, no shared/generated artifact affected).
- **Observations / remaining items:** (1) **Producer integration pending** for DEC-01 (agent-proposal slice must call `convert_llm_evidence`/`build_evidence_entry` at persistence). (2) Rule precedence (institution-before-batch) and effective-date filtering remain **undocumented and unchanged** — lead decision needed before altering lookup behavior. (3) ORM `UniqueConstraint(name="unique_institution_rule")` vs auto-named DB constraint (012 unnamed) — cosmetic metadata/DB divergence, behavior verified intact. (4) `attendance.py` pre-existing lint debt (19 errors incl. unused `engine` variable) untouched — out of scope. (5) `StudentProfile` intentionally still has no `institution_id` (DEC-02 fix uses the batch chain).

---

**R1 — P0 security/correctness hardening (DONE in working tree, 11 Oct 2026; branch `feature/vertical-slice-case-approval`; NOT yet committed/pushed — awaiting lead commit/PR instruction).**
Scope executed exactly per `11_ROADMAP.md` §3 + ADR-003 §6.3. All Phase-0 doc changes in the same working tree are preserved untouched.
- **Ownership helper implemented (`app/api/deps.py`):** `require_student_self_or_mentor` now performs the real record-level check (07 §2 matrix, DM-NEW-ORM01(3)): loads `StudentProfile` + `Batch.institution_id` by path `student_id`; allows (1) own data (`profile.user_id == auth.user_id`), (2) ADMIN same institution, (3) MENTOR assigned mentee (`mentor_id`), (4) CLASS_TEACHER own class (`class_teacher_id`), (5) FACULTY with an assigned course run for the student's batch (`course_runs.faculty_id` — migration 003; the previously-reported "no schema support" blocker does NOT exist); HOD and all other roles fail closed (07 §2/§5: HOD = aggregates/escalations only, never individual records). One constant denial detail (`STUDENT_SCOPE_DENIED`) for every failure mode incl. missing profile — no existence oracle.
- **Route wiring fixed:** malformed `Depends(lambda auth=Depends(): …)` / `Depends(lambda: Depends(get_auth_context)())` in `assessments.py` replaced with `Depends(require_student_self_or_mentor)`; the same ownership dependency now guards `attendance` summary + what-if, `assessments` summary, `tasks/student/{id}`, and `students/{id}` (former `require_roles` gates including HOD removed — the helper is the single matrix authority; 401 preserved via `get_auth_context`).
- **All int-raises (`raise status.HTTP_XXX`) replaced with `HTTPException`:** assessments (3×404), students `/me` (403/404) + `/{id}` (404), tasks complete/snooze (404/400), attendance what-if (404). Previously these returned 500.
- **Task ownership filter corrected:** `complete`/`snooze` compared `StudentTask.student_id` (a `student_profiles.id` FK) against `auth.user_id` (a `users.id`) — real students could never complete their own tasks (always 404). Now resolves the caller's profile first and filters by profile id; no-profile student → 403 with the constant detail.
- **Cases institution scoping:** queue admin/HOD path now joins `student_profiles → batches` and filters `batches.institution_id = auth.institution_id` (Admin = all within own institution; NULL institution matches nothing → fail closed); approve now requires admin/HOD to be same-institution (student→batch→institution) with the same constant 403 detail as mentor-mismatch (`Not authorized for this case`); assigned-mentor path unchanged. Student-decision endpoint (approved slice) untouched.
- **Dead duplicate auth module deleted:** `app/security/auth.py` removed (evidence: zero imports of `app.security`/`security.auth` repo-wide; only self-references and a historical doc mention). Single auth path = `app/api/deps.py`.
- **Tests:** new `tests/test_authz_r1.py` (+38: 401 matrix ×7 routes; ownership matrix student/mentor/CT/admin/faculty/HOD; no-oracle equality; int-raise 4xx regressions; queue institution-filter SQL compile; approve cross-institution/unassigned-mentor 403; real JWT→JWKS(RS256, local RSA key, mocked fetch)→`get_auth_context`→ownership chain incl. expired/tampered/wrong-aud/missing-kid 401s, Supabase `role` claim ignored (EC-USR-01), suspended user 403, zero role assignments 403). Suite **169 → 207 passed / 24 DSN-skipped** (local, dummy DATABASE_URL — exact CI env).
- **Contract regen notes (`contracts/openapi.json`, 12 paths, bug-fix corrections):** assessments summary LOST the two bogus required query params `args`/`kwargs` (artifacts of the malformed lambda wiring that FastAPI exposed as required query params — the endpoint was uncallable without them) and GAINED `security: HTTPBearer`; four docstring updates. No response-schema changes.
- **Lint:** repo total ruff **232 → 218** (dead-module removal); per-file on touched files all ≤ baseline (deps 5→6→5 after EOF fix, assessments 19→19, students 4→3, tasks 11→6, attendance 18→17, cases 22→21, new test file 0).
- **Not done (deliberately, needs lead/infra):** RLS verification against real local Supabase JWTs (`11_ROADMAP.md` §1.A last item — requires the OQ-A02 Supabase CLI stack; application-level authorization is fully covered here); HOD queue-escalations-only semantics (pre-existing HOD+mentor/admin reach into the queue is institution-scoped now but not escalation-filtered — follow-up question); validity-window filtering of `user_role_assignments` is SQL-side (mocked in unit tests) — DSN-gated coverage exists only via future integration tests; CI run via PR not triggered (no commit/push without lead instruction).

---

## Next Major Task

**R1 implemented in working tree (see record above) — commit/PR/CI still pending lead instruction.** Next recommended slice: **R2 — Supervisor wiring on the event bus** (`11_ROADMAP.md` §3: subscribe to existing catalog events; MOCK LLMService; create case `OPEN → IN_REVIEW`; route to attendance specialist stub) per the roadmap ordering (ADR-003 §6.2, still PROPOSED pending formal ratification). After R2: agent proposal production (R3). Candidate pool and closures from prior state: agent proposal production (`IN_REVIEW → PLAN_PROPOSED` / `REPLAN_REQUIRED → PLAN_PROPOSED` creating `PROPOSED` plans — needs Supervisor/LLMService), Supervisor wiring to the in-process event bus, DM-AG03 scheduler emitting time-based events, queue page attendance/CRUD, plan `CUSTOMIZED`/decline follow-on consumers. Closed: **R1 (this task)**, F-08 (`trigger_events` type), F-09 (CI pytest + drift — live runs green through `0bb26ca`), slice-2 acceptance path, **slice-3 decline row**, **F-03 genuine two-connection Postgres test** (`tests/test_concurrent_student_decisions_pg.py`, DSN-gated), **`STUDENT_APP` doc-comment gap (comment-only)**, **`InterventionPlan.reason_codes` ORM type** (`ARRAY(Text)`, live round-trip verified), **intervention JSONB columns** (`trigger_events`/`plan_actions`/`evidence`, live round-trip + catalog verified), **remaining six JSONB columns** (`audit_log`/`data_conflicts`/`institution_rules.value` per 007/011/012 — live round-trip + catalog + `none_as_null` NULL-contract verified). F-05 remains a NON-BLOCKING P2 (mentor path + student decision rows validated; unimplemented transitions validate within their own slices). Also pending: **DEC-01/DEC-02/DEC-03 — APPROVED and implemented (see DEC implementation record above; remaining follow-ups: DEC-01 producer integration in the agent-proposal slice, rule-precedence/effective-date documentation decision — ADR-003 §6.4)**, remaining audit findings (F-06 client gating, F-07 test gaps, ~23 P3s), Stitch screens 17–20 review (only Screen 03 approved) and Constitution sign-offs (FINAL FREEZE not granted).

---

## Android Implementation Note

Native Android development is deferred to **Android Studio** after the shared core and API contracts stabilize. No native Android code is built in this web repository.

---

## Do Not Do

- Do NOT build native Android Kotlin/Compose projects in this web workspace
- Do NOT duplicate business rules or calculation logic across clients
- Do NOT treat Mother Application and Core Platform as separate disconnected products
- Do NOT introduce Redis, Kafka, Temporal, or Celery in v1
- Do NOT invent BCREC institutional rules or data
- Do NOT rewrite frozen decisions without team lead approval
- Do NOT bypass `LLMService` or call model providers directly from agents
- Do NOT perform raw SQL queries from agents


---

## Blockers

| ID | Blocker | Owner |
|---|---|---|
| OQ-05 | BCREC real data sample contact — needed for ingestion validation | All |
| OQ-07 | MAR points calculation rules | Abhijit |
| OQ-08 | BCREC roll number format | Bishesh |
| OQ-SS01 | `ATTENDANCE_WATCH` margin value — team must agree before implementing | All |
| OQ-AG01 | Default production LLM model — must be selected via evaluation, not reputation | Mrityunjoy |
| OQ-A02 | Browser→API E2E needs Supabase local stack (DB + JWKS); API verified via tests/contracts until then | Bishesh |

---

## Open Questions

| ID | Question |
|---|---|
| ARCH-03 | `master` → `main` branch rename: deferred to repository finalization. Current branch is `master`. |

---

## Do Not Do

- Do NOT duplicate business logic into frontend client apps
- Do NOT introduce Redis, Kafka, Temporal, or Celery in v1
- Do NOT invent BCREC institutional rules or data
- Do NOT rewrite frozen decisions without team lead approval
- Do NOT bypass `LLMService` or call model providers directly from agents
- Do NOT perform raw SQL queries from agentsn and freeze architecture first
- Do NOT push unfinished documentation

---

## Expected Output (Current Task)

- `AGENTS.md` — concise, current ✅
- `docs/AI_WORKING_STATE.md` — this file ✅
- All doc statuses accurate
- All frozen decisions identifiable
- All open questions recorded
- Repository pushed, clean git state

---

## Verification

Before claiming a slice done:
- [x] No doc contradicts a frozen decision (F-02 catalog row + ADR-002 Amends line corrected)
- [x] Contract-first sequence followed (ADR → catalog → contracts → code)
- [x] `AI_WORKING_STATE.md` complete and current
- [x] `git diff` has no accidental files (`.opencode/`, `*.docx` excluded)
- [x] typecheck / lint / build / pytest / openapi drift all green **on GitHub Actions** — run `38055651515` (head `0bb26ca`, six-column JSONB audit fix): SUCCESS both jobs; prior run `38053851770` (head `faa49a7`, intervention JSONB fix): SUCCESS both jobs; earlier `38038899877` (head `286523b`, state docs): SUCCESS, `38038621673` (head `f42ed52`, reason_codes fix): SUCCESS both jobs; `38037438277` (head `024369c`): backend `121 passed, 2 skipped` + drift clean, Node job green (observed); earlier `38032170945`/`38032011350` (`deab7b6`/`7e0faf3`) `103 passed`, `38030328306` (`5f88157`) `71 passed`
- [x] local pytest **124 passed, 5 skipped** (no DSN) on Python 3.14.4 **and** the CI-parity Python 3.11.15 venv; **129 passed with `ASPIRE_TEST_PG_DSN`** and **5 passed** integration-only on 3.11 (all against real PostgreSQL); prior milestone 121/123; OpenAPI artifact byte-identical across both (regen produced no diff — contract unchanged by the reason_codes fix)
- [x] ruff: per-file counts equal to HEAD baselines (no new debt); unrelated `--fix` churn reverted
- [x] pushed to origin (this slice branch) — slice `cb300da`, P1 `72c6a85`, P2 `511411a`, CI fix `5f88157`, slice 2 `7e0faf3`, docs `deab7b6`, slice 3 `024369c`, state `1d093f4`, reason_codes fix `f42ed52`, state `286523b`, intervention JSONB fix `faa49a7`, state `05aabb6`, six-column JSONB audit fix `0bb26ca`

---

## Git State

- **Branch:** `feature/vertical-slice-case-approval` (created from `feature/frontend-ui-core` @ `82a36d8`)
- **Remote:** `origin` to `https://github.com/Mrityunjoy240/ASPIRE.git` — commits on this branch: slice `cb300da`, P1 remediation `72c6a85`, P2 gate close `511411a`, CI contract fix `5f88157`, student acceptance slice `7e0faf3`, docs `deab7b6`, decline + PG concurrency slice `024369c`, state `1d093f4`, reason_codes fix `f42ed52`, state `286523b`, intervention JSONB fix `faa49a7`, state `05aabb6`, **six-column JSONB audit fix `0bb26ca`**
- **CI:** workflows trigger only on push/pull_request to `main`/`master`; draft **PR #1** (`→ master`) is the standing `pull_request` trigger for this branch — observe runs under Actions before claiming green. Latest observed: run `38055651515` (head `0bb26ca`) **SUCCESS both jobs** (prior `38053851770` head `faa49a7`, `38038899877` head `286523b`, `38038621673` head `f42ed52`, `38037671448` head `1d093f4`, `38037438277` head `024369c`)
- **Prior UI batch:** `82a36d8` on `feature/frontend-ui-core` (32 files)
- **Untracked, kept out of commits:** `.opencode/` (only `config.json` gitignored), `EduGen_AI_ASPIRE_Master_Product_Engineering_Book_v1.0.docx` (`audit/` is versioned — committed with the P1 remediation)

---

## Handoff Notes

- `docs/decisions/` is no longer empty (ADR-001, ADR-002). Adding any new catalog event requires the lead's sequence: ADR → `03 §8.2` row → agent-contract check → code.
- The approve endpoint now enforces `03 §10.2` (409 on illegal transitions) and no longer writes an `APPROVED` plan status (not in 05 §9 / migration 009); the verdict lives in `mentor_decision`.
- After P1 remediation: plan history is expected on cases — the router passes *all* plans to the service, which selects the awaiting one (`ACCEPTED/CUSTOMIZED` + `mentor_decision IS NULL`). Do not reintroduce `scalar_one_or_none` on plan queries.
- Queue order is computed server-side only (`PriorityEngine.sort_mentor_queue`); clients must render it as-is (DM-SS03). The approve path locks the case row `FOR UPDATE` — do not remove it (F-03).
- `intervention_cases.trigger_events` is an **array of event-ID strings** (migration 009 + `05 §intervention_cases` + engine `TriggerEvent.event_type: str`) — backend hints are `list[str]`, frontend `string[]`. Do not reintroduce `list[dict]`; OpenAPI `items` must stay `type: string`.
- `docs/10_TASKS.md` task prompts predate the tech-selection reset — statuses are stale (DONE/READY/BLOCKED markings no longer reflect reality); `docs/11_ROADMAP.md` is the ordering authority pending lead ratification. Do not execute 10_TASKS prompts as frozen implementation instructions.
- `docs/04_ARCHITECTURE.md` is FROZEN (v2.1): ADR-001 core + Phase-0 reconciliation addendum (§9, 11 Oct 2026 — four-client map and actual `app/` module map supersede the old §6 `services/` target tree). Earlier handoff claims that it was a "RED DRAFT" are outdated.
- Student acceptance slice scope (team lead, 10 Oct 2026): **acceptance rows only** — superseded for decline by slice 3 (`024369c`): `DECLINED` is now implemented (`→ REPLAN_REQUIRED`, event `PLAN_DECLINED`, optional decline-only `reason` persisted on `plan.student_reason` only). Journey Step 7 task materialization from accepted plans is still out of scope (future `PLAN_ACCEPTED` consumer).
- `audit_log.source_system` for student rows is `STUDENT_APP`; the illustrative value list in `05 §7` and migration `007_audit_log.sql` now include it — **comment-only edit landed in slice 3** (plain TEXT, no CHECK, no schema change; task-sanctioned, not a frozen-doc semantic change).
- Decline `reason` handling: stored **verbatim** on `plan.student_reason` (no content rules exist in 02/05), never placed in audit state JSON or event payloads (07 §4: no free text/PII). `reason` is refused on non-`DECLINED` decisions (422 schema + service `INVALID_REQUEST`).
- Real-PostgreSQL caveat for audit inserts: `AuditLog.id` now carries `server_default=text("gen_random_uuid()")` (mirrors migration 007) — without it `log_audit` fails with `FlushError: NULL identity key` on real PG (SQLite tests never surfaced it). Do not remove.
- `InterventionPlan.reason_codes`: **fixed in `f42ed52`** — ORM now `ARRAY(Text).with_variant(JSON, "sqlite")` matching migration 009 `TEXT[] NOT NULL`; verified by static + live PostgreSQL round-trip tests (`tests/test_intervention_plan_reason_codes*.py`). Do not revert to `JSON`; do not hand-edit migration 009.
- `InterventionCase.trigger_events` / `InterventionPlan.plan_actions` / `evidence`: **fixed in `faa49a7`** — ORM now `JSONB(none_as_null=True).with_variant(JSON, "sqlite")` (the `none_as_null` flag added in `0bb26ca`) matching migration 009 `JSONB` columns; verified by static + live PostgreSQL round-trip/catalog tests (`tests/test_intervention_plan_jsonb*.py`). Do not revert to `JSON`.
- Six remaining JSONB columns (`audit_log.previous_state`/`new_state` per 007, `data_conflicts.existing_value`/`incoming_value`/`resolution` per 011, `institution_rules.value` per 012): **fixed in `0bb26ca`** — ORM now `JSONB(none_as_null=True)`; verified by `tests/test_jsonb_audit_rules_conflicts*.py` (static + live round-trip/catalog/NOT NULL). No JSON operators or in-place mutations exist for them. Do not revert to `JSON`.
- **Held for lead decision → DEC-01/DEC-02/DEC-03 — now APPROVED and implemented** (Architecture Decision Gate + DEC implementation record above): `evidence` canonical shape = structured entries (DEC-01 C-lite, conversion boundary `app/services/evidence.py`), `institution_rules.institution_id` NOT NULL via migration 013 + router batch-chain fix (DEC-02 B), `data_conflicts`/`institution_rules` id generation = DB-side with ORM `server_default` mirror (DEC-03 A — live probe confirmed the pre-fix NULL-identity-key failure; post-fix live tests confirm generated ids). Remaining: DEC-01 producer integration (agent-proposal slice), rule-precedence/effective-date documentation decision.
- Plan history applies to student decisions too: the service picks the single `PROPOSED` plan and refuses ambiguity — never reintroduce `scalar_one_or_none` on plan queries (same rule as the mentor path).
