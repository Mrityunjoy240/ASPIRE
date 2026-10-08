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
- **F-03 (no row lock):** `_case_for_approval_query(...).with_for_update()` is the first execute in approve — PostgreSQL row lock serializes concurrent approvals; blocked second request re-reads committed state → 409. No new infra (no Redis/outbox). True 2-connection race needs Postgres (OQ-A02); covered by FOR UPDATE compile test + sequential double-approval test.
- **F-04 (client/server sort divergence):** canonical DM-SS03 order now lives only in `PriorityEngine.sort_mentor_queue(list[QueueEntry])`; router builds entries, sorts, returns that order; queue page no longer re-ranks (renders as-is); `DEMO_ROWS` authored in canonical order. PQ-01…PQ-09 regression fixtures + band/NULL handling tests all pass; proof script shows old sorts fail PQ-03/06/07/08/09.
- **Gates after remediation:** pytest **69/69** (+23) · typecheck 0 · lint 0 (ESLint) · build ✓ (6 routes) · OpenAPI regenerated + idempotent (409/400 description updates) · ruff per-file counts ≤ baseline (only style-consistent `timezone.utc` additions).
- Remaining known findings are P2/P3 in the audit file (F-05…F-09, ~23 P3s) — **not fixed yet**, awaiting team-lead prioritization.

---

## Next Major Task

**Next vertical slice (awaiting team-lead selection).** Candidates: student plan acceptance (`PLAN_PROPOSED → PENDING_APPROVAL` + student events), Supervisor wiring to the in-process event bus, DM-AG03 scheduler emitting time-based events, queue page attendance/CRUD. Also pending: P2/P3 remediation from `audit/vertical_slice_forensic_audit_cb300da.md` (F-05 plan-status validation, F-06 client gating, F-07 test gaps, F-08 `trigger_events` type mismatch, F-09 CI lacks pytest/drift), Stitch screens 17–20 review (only Screen 03 approved) and Constitution sign-offs (FINAL FREEZE not granted).

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
- [x] typecheck / lint / build / pytest 69/69 / openapi drift test all green
- [x] pushed to origin (this slice branch) — P1 remediation commit pushed

---

## Git State

- **Branch:** `feature/vertical-slice-case-approval` (created from `feature/frontend-ui-core` @ `82a36d8`)
- **Remote:** `origin` to `https://github.com/Mrityunjoy240/ASPIRE.git` — slice commit `cb300da`, then P1 remediation commit (`fix(core): remediate vertical slice P1 findings`) both pushed on this branch
- **Prior UI batch:** `82a36d8` on `feature/frontend-ui-core` (32 files)
- **Untracked, kept out of commits:** `.opencode/` (only `config.json` gitignored), `EduGen_AI_ASPIRE_Master_Product_Engineering_Book_v1.0.docx`, `audit/` (forensic audit — staged with remediation if lead wants it versioned)

---

## Handoff Notes

- `docs/decisions/` is no longer empty (ADR-001, ADR-002). Adding any new catalog event requires the lead's sequence: ADR → `03 §8.2` row → agent-contract check → code.
- The approve endpoint now enforces `03 §10.2` (409 on illegal transitions) and no longer writes an `APPROVED` plan status (not in 05 §9 / migration 009); the verdict lives in `mentor_decision`.
- After P1 remediation: plan history is expected on cases — the router passes *all* plans to the service, which selects the awaiting one (`ACCEPTED/CUSTOMIZED` + `mentor_decision IS NULL`). Do not reintroduce `scalar_one_or_none` on plan queries.
- Queue order is computed server-side only (`PriorityEngine.sort_mentor_queue`); clients must render it as-is (DM-SS03). The approve path locks the case row `FOR UPDATE` — do not remove it (F-03).
- `docs/10_TASKS.md` task prompts predate the tech-selection reset — team lead must review before treating them as frozen implementation instructions.
- `docs/04_ARCHITECTURE.md` is marked `RED DRAFT` but contains many frozen decisions; status should be `UNDER REVIEW` at minimum.
