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
| `docs/CONSTITUTION.md` | Engineering and product principles |
| `docs/ASPIRE_APPLICATION_BOUNDARIES.md` | **FROZEN** Ecosystem model, Mother App (Web), Core Platform, OpenCode vs Android Studio boundaries |
| `docs/ASPIRE_MOTHER_APPLICATION_SPECIFICATION.md` | **FROZEN** Mother Application role workspaces, management capabilities & UX |
| `docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md` | **FROZEN** Mother System architecture specification |
| `docs/decisions/ADR-002_INTERVENTION_PLAN_APPROVED_EVENT.md` | **ACCEPTED** `INTERVENTION_PLAN_APPROVED` domain event, payload & emission rule (amends 03 §8.2) |
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
- **F-03 (no row lock):** `_case_for_approval_query(...).with_for_update()` is the first execute in approve — PostgreSQL row lock serializes concurrent approvals; blocked second request re-reads committed state → 409. No new infra (no Redis/outbox). Covered by FOR UPDATE compile test + sequential double-approval test. **Implementation verified; true concurrent two-connection test pending** (needs real Postgres, OQ-A02) — F-03 must not be represented as fully production-verified until such a test exists.
- **F-04 (client/server sort divergence):** canonical DM-SS03 order now lives only in `PriorityEngine.sort_mentor_queue(list[QueueEntry])`; router builds entries, sorts, returns that order; queue page no longer re-ranks (renders as-is); `DEMO_ROWS` authored in canonical order. PQ-01…PQ-09 regression fixtures + band/NULL handling tests all pass; proof script shows old sorts fail PQ-03/06/07/08/09.
- **Gates after remediation:** pytest **69/69** (+23) · typecheck 0 · lint 0 (ESLint) · build ✓ (6 routes) · OpenAPI regenerated + idempotent (409/400 description updates) · ruff per-file counts ≤ baseline (only style-consistent `timezone.utc` additions).

**Pre-next-slice P2 gate review (F-05 / F-08 / F-09 / F-03) — DONE, commit `chore(quality): close pre-next-slice P2 gates`.**
- **F-05 → NON-BLOCKING P2.** Audit of the only implemented transition family (mentor rows, §10.2): validates current case state, plan state (`ACCEPTED|CUSTOMIZED` + `mentor_decision IS NULL`, delivered by F-01), plan identity (queried under the case), actor authority (`require_mentor_or_admin` + explicit mentor/HOD check), and transition legality (whitelisted mapping). Plan *version* column does not exist in migration 009 (schema authority) — none applicable today. All other §10.2 transitions (`OPEN → IN_REVIEW` … `RESOLVED → CLOSED`) have **no implementation yet**; their state/plan/actor validation is acceptance criteria for their own future slices, not pre-work. Remaining F-05 delta (evidence gap closed here, no production code changed): +2 regression tests proving DECLINED/SUPERSEDED-only plans are refused `NO_PLAN` with zero mutation/event (`test_f05_dead_plan_cannot_authorize_approval`). Note: audit suggested 409 for dead plans; existing contract keeps missing/awaiting-plan failures at 400 (`NO_PLAN`) and reserves 409 for state/ambiguity — unchanged, documented.
- **F-08 → BLOCKER FOR NEXT SLICE, FIXED.** Canonical type determined: **array of event-ID strings** — evidence: migration 009 comment "Array of event IDs", `05 §intervention_cases` "Array of event IDs", engine `TriggerEvent.event_type: str` + `reason_codes: list[str]`, demo rows `string[]`, frontend `string[]`/`getEventLabels(events: string[])`. The outliers were the two backend type hints (`schemas.py` `list[dict]`, model `list[dict[str, Any]]`) — with a real producer (next slice's `create_intervention_case`), string rows would have failed response validation → queue 500, and dict rows would render `[object Object]`. Fixed: both hints → `list[str]`; `05:286` clarified "(strings)"; OpenAPI regenerated (`items: {type: string}`). No event names invented, no event-catalog (§8.2) change — this aligns code with the already-documented contract, not an amendment.
- **F-09 → IMPLEMENT NOW, DONE.** `.github/workflows/ci.yml` gains a `backend` job (existing `ci` Node job untouched): setup-python 3.11 → `pip install -e ".[dev]"` → `python -m pytest tests/ -q` → `generate_openapi.py` + `git diff --exit-code contracts/openapi.json` (DM-API01 "CI fails on drift"). No secrets: dummy `DATABASE_URL` env (NullPool engine never connects during tests/generation — validated by running the whole suite with `.env` removed). Triggers/jobs otherwise unchanged.
- **F-03 → IMPLEMENTATION VERIFIED / CONCURRENCY TEST PENDING.** Re-verified all five claims by code reading: lock acquired inside the request transaction (SELECT FOR UPDATE is the first case read, held to service commit); authoritative `intervention_cases` row locked; state re-evaluated on the locked read (READ COMMITTED re-fetch after lock), so the §10.2 check runs on post-lock data; loser blocked → re-reads `ACTIVE` → `ILLEGAL_TRANSITION` → 409 → rollback (no second successful transition; no second audit/event). Real two-connection Postgres test **not run** (no Postgres here) — tracked as OQ-A02 follow-up; wording above is mandatory in all future status reports.
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

---

## Next Major Task

**Next vertical slice (awaiting team-lead selection).** Candidates: student **decline** row (`PLAN_PROPOSED → REPLAN_REQUIRED` + `PLAN_DECLINED` event, deferred from slice 2), agent proposal production (`IN_REVIEW → PLAN_PROPOSED` / `REPLAN_REQUIRED → PLAN_PROPOSED` creating `PROPOSED` plans — needs Supervisor/LLMService), Supervisor wiring to the in-process event bus, DM-AG03 scheduler emitting time-based events, queue page attendance/CRUD. Closed: F-08 (`trigger_events` type), F-09 (CI pytest + drift — live runs green through `7e0faf3`), slice-2 acceptance path. F-05 remains a NON-BLOCKING P2 (mentor path + student acceptance validated; unimplemented transitions validate within their own slices). Also pending: remaining audit findings (F-06 client gating, F-07 test gaps, ~23 P3s), F-03 two-connection Postgres test (OQ-A02), Stitch screens 17–20 review (only Screen 03 approved) and Constitution sign-offs (FINAL FREEZE not granted).

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
- [x] typecheck / lint / build / pytest / openapi drift all green **on GitHub Actions** — run `38032011350` (head `7e0faf3`): backend `103 passed` + drift clean, Node job green (observed); prior run `38030328306` (`5f88157`) `71 passed`
- [x] local pytest 103/103 on Python 3.14.4 **and** the CI-parity Python 3.11.15 venv (CI-resolved dep set); OpenAPI artifact byte-identical across both
- [x] pushed to origin (this slice branch) — slice `cb300da`, P1 `72c6a85`, P2 `511411a`, CI fix `5f88157`, slice 2 `7e0faf3`

---

## Git State

- **Branch:** `feature/vertical-slice-case-approval` (created from `feature/frontend-ui-core` @ `82a36d8`)
- **Remote:** `origin` to `https://github.com/Mrityunjoy240/ASPIRE.git` — commits on this branch: slice `cb300da`, P1 remediation `72c6a85`, P2 gate close `511411a`, CI contract fix `5f88157`, student acceptance slice `7e0faf3`
- **CI:** workflows trigger only on push/pull_request to `main`/`master`; draft **PR #1** (`→ master`) is the standing `pull_request` trigger for this branch — observe runs under Actions before claiming green
- **Prior UI batch:** `82a36d8` on `feature/frontend-ui-core` (32 files)
- **Untracked, kept out of commits:** `.opencode/` (only `config.json` gitignored), `EduGen_AI_ASPIRE_Master_Product_Engineering_Book_v1.0.docx` (`audit/` is versioned — committed with the P1 remediation)

---

## Handoff Notes

- `docs/decisions/` is no longer empty (ADR-001, ADR-002). Adding any new catalog event requires the lead's sequence: ADR → `03 §8.2` row → agent-contract check → code.
- The approve endpoint now enforces `03 §10.2` (409 on illegal transitions) and no longer writes an `APPROVED` plan status (not in 05 §9 / migration 009); the verdict lives in `mentor_decision`.
- After P1 remediation: plan history is expected on cases — the router passes *all* plans to the service, which selects the awaiting one (`ACCEPTED/CUSTOMIZED` + `mentor_decision IS NULL`). Do not reintroduce `scalar_one_or_none` on plan queries.
- Queue order is computed server-side only (`PriorityEngine.sort_mentor_queue`); clients must render it as-is (DM-SS03). The approve path locks the case row `FOR UPDATE` — do not remove it (F-03).
- `intervention_cases.trigger_events` is an **array of event-ID strings** (migration 009 + `05 §intervention_cases` + engine `TriggerEvent.event_type: str`) — backend hints are `list[str]`, frontend `string[]`. Do not reintroduce `list[dict]`; OpenAPI `items` must stay `type: string`.
- `docs/10_TASKS.md` task prompts predate the tech-selection reset — team lead must review before treating them as frozen implementation instructions.
- `docs/04_ARCHITECTURE.md` is marked `RED DRAFT` but contains many frozen decisions; status should be `UNDER REVIEW` at minimum.
- Student acceptance slice scope (team lead, 10 Oct 2026): **acceptance rows only** — decline is refused as `INVALID_DECISION` (service) / 422 (schema Literal) and is a candidate slice, not a bug. Journey Step 7 task materialization from accepted plans is also out of scope (future `PLAN_ACCEPTED` consumer).
- `audit_log.source_system` for student rows is `STUDENT_APP`; the illustrative value list in `05 §7` and the migration `007_audit_log.sql` comment still read `CSV_IMPORT | MENTOR_WEB | RULE_ENGINE | AGENT` (plain TEXT, no CHECK — no schema change needed). **Doc-comment update pending team lead** — do not silently edit frozen docs.
- Plan history applies to student decisions too: the service picks the single `PROPOSED` plan and refuses ambiguity — never reintroduce `scalar_one_or_none` on plan queries (same rule as the mentor path).
