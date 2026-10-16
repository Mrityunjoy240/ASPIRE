# 04_ARCHITECTURE.md
# EduGen AI / ASPIRE — System Architecture

**STATUS: 🟢 FROZEN (core, via ADR-001, 07 Oct 2026) + Phase-0 RECONCILED (11 Oct 2026, via ADR-003)** — the ADR-001 architecture is confirmed against the implemented codebase; §9 Addendum supersedes the §6 target folder tree and extends the §1 system map to the four-client ecosystem. Decisions in ADR-003 §6 remain OPEN and require team-lead approval.
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 07 October 2026 (v2.0 frozen) · 11 October 2026 (v2.1 Phase-0 reconciliation addendum)
**Version:** 2.1 (frozen core + reconciliation addendum)

> [!IMPORTANT]
> This document defines **service boundaries, ownership, and communication contracts**.
> No team member may introduce a new service, database, or inter-service call
> without a corresponding update to this document first.

---

## 1. System Map (High-Level)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ASPIRE SYSTEM                                   │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   MOBILE APP    │    │    WEB APP       │    │  ADMIN / STAFF WEB      │  │
│  │  Next.js 15     │    │   Next.js 15     │    │     Next.js 15          │  │
│  │  PWA            │    │  (App Router)    │    │     (App Router)        │  │
│  │                 │    │                  │    │                         │  │
│  │  Primary:       │    │  Primary:        │    │  Primary:               │  │
│  │  Student        │    │  Student (web)   │    │  Faculty/CT/Mentor      │  │
│  └────────┬────────┘    └────────┬─────────┘    │  HOD / Admin            │  │
│           │                     │               └──────────┬──────────────┘  │
│           └─────────────────────┴──────────────────────────┘                 │
│                                 │ HTTPS                                       │
│                        ┌────────▼─────────┐                                  │
│                        │   API GATEWAY    │                                  │
│                        │   FastAPI        │                                  │
│                        │   (Python)       │                                  │
│                        └──┬──────────┬───┘                                  │
│                           │          │                                       │
│              ┌────────────▼───┐  ┌───▼────────────────┐                     │
│              │  RULE ENGINES  │  │  AGENT ORCHESTRATOR │                     │
│              │  (Pure Python) │  │  (LangGraph)        │                     │
│              │                │  │                     │                     │
│              │  · Attendance  │  │  · Supervisor Agent │                     │
│              │  · Assessment  │  │  · Attendance Agent │                     │
│              │  · Priority    │  │  · Learning Agent   │                     │
│              │  · Task        │  │  · Intervention     │                     │
│              └───────┬────────┘  └──────────┬──────────┘                     │
│                      │                      │                                │
│                      │     ┌────────────────▼──────┐                         │
│                      │     │    LLM SERVICE         │                        │
│                      │     │  (Internal Abstraction)│                        │
│                      │     │    → OpenRouter        │                        │
│                      │     └───────────────────────┘                         │
│                      │                                                       │
│              ┌────────▼────────────────────────┐                             │
│              │        SUPABASE                  │                            │
│              │  · PostgreSQL + pgvector         │                            │
│              │  · Supabase Auth                 │                            │
│              │  · Supabase Storage (docs)       │                            │
│              └──────────────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Ownership

| Service | Language / Framework | Owner | Description |
|---|---|---|---|
| Mobile App | Next.js 15 (installable PWA) | Mrityunjoy | Student-primary mobile experience (PWA only in P0) |
| Web App | Next.js 15 (App Router) | Abhijit | Student web + faculty/CT/admin workspace |
| API Gateway | Python + FastAPI | Bishesh | Single entry point. Auth, RBAC, routing |
| Rule Engines | Python (pure, no I/O) | Bishesh | Attendance, assessment, priority engines |
| Agent Orchestrator | Python + LangGraph | Mrityunjoy | Supervisor + specialist agents |
| LLM Service | Python (internal class) | Mrityunjoy | Wraps OpenRouter. No agent calls provider directly |
| Database | PostgreSQL via Supabase | Bishesh | Schema, migrations, pgvector |

---

## 3. Data Flow — The P0 North Star Scenario

Tracing the "Student S-204 at risk" scenario through the full stack.

```
1. Admin uploads CSV (new attendance data)
          ↓
2. FastAPI /import/upload endpoint
          ↓
3. Ingestion Service (Bishesh): parse → validate → match → conflict check
          ↓ (no conflict)
4. attendance_records written to PostgreSQL
          ↓
5. Rule Engine: Attendance Engine runs
          ↓
6. attendance_derived_state updated (73%, CRITICAL band)
          ↓
7. ATTENDANCE_RISK_CRITICAL event emitted
          ↓
8. LangGraph Supervisor Agent picks up event
          ↓
9. Supervisor routes to Attendance Specialist Agent
          ↓
10. Agent reads derived state (read-only tool call to DB via API)
          ↓
11. Agent calls LLM Service (via internal LLMService, not OpenRouter directly)
          ↓
12. LLM produces structured recovery plan JSON
          ↓
13. Intervention Case created (via API tool call, NOT direct SQL)
          ↓
14. Plan written to intervention_plans table
          ↓
15. Student task created in student_tasks (PENDING_APPROVAL state)
          ↓
16. Push notification sent to student's mobile app
          ↓
17. Student reviews evidence → accepts plan
          ↓
18. Plan status → ACCEPTED. Tasks become PENDING.
          ↓
19. Mentor queue updated (priority engine recomputes urgency band)
          ↓
20. Mentor reviews case on web → approves
          ↓
21. Case status → ACTIVE
          ↓
22. Follow-up timer created per intervention policy
          ↓
23. On next attendance data update → Rule Engine reruns → 
    Case RESOLVED or REPLAN_REQUIRED
```

---

## 4. Service Communication Rules

- **Frontend → API:** HTTPS REST only. All requests carry a JWT (Supabase Auth token).
- **Authentication:** Supabase Auth only. FastAPI validates the incoming Supabase JWT asymmetrically (JWKS: signature, iss, aud, exp, sub, nbf/iat) to establish caller identity, then resolves ASPIRE roles from `user_role_assignments`. The application never stores passwords and never issues its own tokens.
- **API → Database:** FastAPI uses a server-side service connection that carries **no JWT/`auth.uid()` context**. Application authorization (`require_role` + explicit query scoping) is mandatory and authoritative for FastAPI requests; RLS protects non-privileged client/data-access paths (`07_SECURITY_TRUST.md` §2 v1 strategy). A successful SQLAlchemy query is **not** authorization: every protected database operation requires (1) authenticated identity, (2) ASPIRE role authorization, (3) explicit row/scope filtering, (4) audit/provenance where required (DM-NEW-ORM01 — `07_SECURITY_TRUST.md` §2).
- **API → Rule Engines:** Direct in-process function calls. Rule engines are pure Python modules, not microservices. No HTTP between them.
- **API → Agent Orchestrator:** Direct in-process call in v1. (Can be extracted to a queue later).
- **Agents → Database:** Agents NEVER call Supabase/PostgreSQL directly. They call typed FastAPI tool endpoints which enforce RBAC.
- **Agents → LLM (DM-LLM01 — FROZEN):** The call path is `Agent → internal LLMService → OpenRouter`. Agents call `LLMService` only — **no agent calls OpenRouter or any model provider directly.** The service exposes exactly two modes — **`LIVE`** and **`MOCK`** (no other production modes are invented). `MOCK` responses come from explicit deterministic fixtures and are for tests/evaluation only; mock mode must never silently become a production answer source. **Failure boundary:** `LLMService` distinguishes timeout, transient provider/API failure, rate limit, invalid structured output, exhausted retry/failover, and unavailable service. Transient failures and rate limits get **one bounded retry with bounded backoff** — never an unbounded retry loop. OpenRouter provider-level failover may operate normally, but ASPIRE **never silently switches to a different application-selected model** — provider failover and model fallback are different mechanisms; model fallback requires a separate frozen decision. Every structured response is schema-validated before business logic consumes it; invalid/partial/malformed output is rejected — never accepted partially, coerced, or completed with invented fields.
- **No agent-to-agent HTTP calls.** All agent coordination goes through LangGraph graph state.
- **Time-based scheduler (DM-AG03 — FROZEN):** The application runs one scheduler evaluation at startup, then every **5 minutes**. Execution is idempotent (missed/delayed cycles recover from current DB state; no duplicate logical events) and the scheduler **never directly mutates business state** — it never calls agents/LLMs and never persists `OVERDUE` (DM-SS02).

```text
periodic scheduler
  → time-condition evaluation
  → domain event emission
  → existing event-driven processing / RULE_ENGINE
```

- **Local development topology (Supabase local-dev strategy — FROZEN):** Next.js and FastAPI run **natively** as development processes. The **Supabase CLI local stack** provides Postgres, Auth, Storage, Data API (PostgREST), and Studio (container runtime underneath). Do **not** create a second custom Supabase Docker Compose stack. **Migration authority:** `db/migrations/*.sql` remains the ONLY authoritative ASPIRE schema source, applied to the CLI's local Postgres by an ASPIRE-controlled migration runner with deterministic ordering — no second `supabase/migrations/*.sql` authority tree, and `supabase db reset` (which replays `supabase/migrations`) is NOT the authoritative migration mechanism.
- **API contract (DM-API01 — FROZEN):** **FastAPI route definitions + Pydantic request/response models are the source of truth.** FastAPI generates the OpenAPI document from them; the committed generated artifact **`contracts/openapi.json`** is the reviewable API contract consumed by the TypeScript frontend toolchain. Authority hierarchy: `FastAPI routes + Pydantic → generated openapi.json → frontend generated TypeScript types`. **No developer may manually edit `openapi.json`**; no duplicate OpenAPI JSON/YAML contract files exist anywhere. CI regenerates the document and **FAILS if it differs** from the committed artifact (drift guard). Runtime `/openapi.json` MAY remain enabled and comes from the same app definition — never a handwritten runtime document. The OpenAPI version is whatever the pinned FastAPI/Pydantic toolchain emits. Generated TS types are compile-time contract types; frontend runtime validation stays on Zod (OQ-A03).

---

## 5. Technology Decisions (ADR Summary)

| Decision | Choice | Reason |
|---|---|---|
| LLM Gateway | OpenRouter | Already used in EduGen. Provider-agnostic. |
| Agent Framework | LangGraph | Supports stateful, cyclical agent graphs. Fits the Observe→Replan loop. |
| Database | PostgreSQL (Supabase) | pgvector support. Supabase Auth; RLS covers non-privileged data-access paths (07 §2). |
| Embeddings | BGE-M3 (1024-dim) | Multilingual, strong retrieval. Swappable via config. |
| Mobile | Next.js 15 (installable PWA) | One codebase with web. No React Native/Expo in P0. |
| Web | Next.js 15 App Router | Server components. TypeScript native. Vercel deploy. |
| API | FastAPI | Async. Auto-generated OpenAPI docs. Python for ML interop. |
| Python tooling | uv + root `pyproject.toml` + `uv.lock` | Fast, reproducible Python envs. Single package in v1 — no uv workspace. |
| **ADR-001 — Mother System Architecture = ✅ DECIDED** | Layered Modular Monolith (FastAPI) + LangGraph + in-process async event dispatch + 5m hybrid scheduler | Full specification in [ADR-001](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md). Single core serving all clients; zero business logic in clients. |
| **DM-NEW-ORM01 — ORM / DB access = ✅ DECIDED** | SQLAlchemy 2.x (async) + psycopg 3 + repository/service layer | SQL migrations in `db/migrations/` are the **authoritative schema source**; SQLAlchemy models mirror `05_DATA_API_CONTRACTS.md` for runtime access only (never a competing schema source). **Prisma removed.** No Alembic as a second schema/migration authority. Exact versions pinned via `uv.lock`. |
| **DM-API01 — API contract = ✅ DECIDED** | FastAPI routes + Pydantic → generated `contracts/openapi.json` → TS types | Single canonical committed artifact; no manual edits; no duplicate contract files; CI fails on drift. |
| **DM-LLM01 — LLM gateway & failure behavior = ✅ DECIDED** | `Agent → internal LLMService → OpenRouter`; modes `LIVE` / `MOCK` | No direct agent→provider calls; deterministic MOCK fixtures for tests only; one bounded retry (transient/rate-limit) with bounded backoff; structured-output validation before any business use; controlled unavailable result; per-attempt audit metadata. No silent cross-model fallback (evaluation still selects the production model). |
| **E-07 — Git branch convention = ✅ DECIDED** | `main` is canonical/default; branches `feature/<task-id>-<short-name>`, `fix/<task-id>-<short-name>`, `docs/<task-id>-<short-name>` | `main` is deployable/integratable, protected by reviewed PRs, and the CI target; no direct implementation work on `main`. `master` is NOT canonical; no separate `master`/`main` histories; no new `master` work. Actual branch rename deferred to repository finalization. |

> The production LLM model is **not frozen** until evaluation selects one. Development and CI must support **mock/disabled LLM** operation (`LLM_PROVIDER=mock`, the `MOCK` mode per DM-LLM01) so the platform runs without an LLM key.

---

## 6. Folder Structure (Target)

```
ASPIRE/
├── apps/
│   ├── web/                    ← Next.js 15 (Abhijit owns)
│   │   ├── app/
│   │   │   ├── (student)/      ← Student-facing pages
│   │   │   ├── (mentor)/       ← Mentor workspace
│   │   │   ├── (faculty)/      ← Faculty dashboard (P1)
│   │   │   └── (admin)/        ← Admin config panel
│   │   └── components/
│   └── mobile/                 ← Next.js 15 installable PWA (Mrityunjoy owns)
│       ├── app/                ← App Router (mobile-first)
│       └── components/
├── services/
│   ├── api/                    ← FastAPI (Bishesh owns)
│   │   ├── routers/
│   │   ├── middleware/
│   │   ├── db/                 ← SQLAlchemy 2.x async engine/session + models (mirror 05 — DM-NEW-ORM01)
│   │   ├── repositories/       ← Repository/service layer (DM-NEW-ORM01)
│   │   └── main.py
│   ├── engines/                ← Pure Python rule engines (Bishesh owns)
│   │   ├── attendance.py
│   │   ├── assessment.py
│   │   ├── priority.py
│   │   └── task.py
│   ├── agents/                 ← LangGraph agents (Mrityunjoy owns)
│   │   ├── supervisor.py
│   │   ├── attendance_agent.py
│   │   ├── learning_agent.py
│   │   └── intervention_agent.py
│   ├── llm/                    ← LLM abstraction (Mrityunjoy owns)
│   │   └── llm_service.py
│   └── ingestion/              ← CSV/Excel import pipeline (Bishesh owns)
│       └── importer.py
├── packages/
│   ├── schemas/                ← Shared TS types + Zod schemas (frontend)
│   │                             Backend mirrors via Pydantic — compat via generated contracts/openapi.json + tests (DM-API01)
│   └── ui/                     ← Shared component library
├── pyproject.toml              ← Python project config (uv) — single package, no uv workspace
├── uv.lock                     ← Locked Python dependencies
├── contracts/
│   └── openapi.json            ← Generated API contract artifact — DO NOT hand-edit (DM-API01)
├── db/
│   ├── migrations/             ← ASPIRE SQL migrations — AUTHORITATIVE schema source (Bishesh owns); applied to the Supabase CLI local Postgres via an ASPIRE-controlled runner
│   └── seeds/                  ← BCREC seed data for dev/testing
├── evals/                      ← Evaluation harness (P0-16)
└── tests/
    ├── engines/                ← Unit tests for rule engines
    ├── agents/                 ← Agent boundary tests
    └── api/                    ← API integration tests
```

---

## 7. Strict Ownership Rules

| Folder/Service | Owner | Others may |
|---|---|---|
| `apps/web/` | Abhijit | PR + review only |
| `apps/mobile/` | Mrityunjoy | PR + review only |
| `services/api/` | Bishesh | PR + review only |
| `services/engines/` | Bishesh | PR + review only |
| `services/agents/` | Mrityunjoy | PR + review only |
| `services/llm/` | Mrityunjoy | PR + review only |
| `services/ingestion/` | Bishesh | PR + review only |
| `db/migrations/` | Bishesh | Review only — no one else writes migrations |
| `packages/schemas/` | All (via PR) | Must be reviewed by all 3 |
| `docs/` | All (via PR) | Must be reviewed by all 3 |

---

## 8. Open Items & Frozen Architecture Resolutions

| ID | Item | Owner | Status |
|---|---|---|---|
| OQ-A01 | Should API and Agents run as a single FastAPI process in v1 or separate services? | Mrityunjoy + Bishesh | ✅ RESOLVED — Single FastAPI application/process in v1 (03 Oct 2026) |
| OQ-A02 | What is the local dev setup? (Docker Compose? Each service independently?) | Bishesh | ✅ RESOLVED — Next.js: native; FastAPI: native; Supabase (Postgres/Auth/Storage/Data API/Studio): Supabase CLI local stack; Docker Compose only for other local infra (03 Oct 2026) |
| OQ-A03 | Shared `packages/schemas` — TypeScript only or Python Pydantic models too? | All | ✅ RESOLVED — TypeScript Zod for frontend, Python Pydantic for backend; compatibility via OpenAPI contract + tests (03 Oct 2026) |
| ARCH-01 | Agent Framework Selection | Mrityunjoy | ✅ RESOLVED — LangGraph frozen via ADR-001 (07 Oct 2026) |
| ARCH-02 | Message Bus / Background Processing | Bishesh | ✅ RESOLVED — Asyncio in-process event bus for v1; no Redis/Kafka/Temporal in v1 (ADR-001) |
| ARCH-04 | Mother System Internal Topology | Mrityunjoy + Bishesh | ✅ RESOLVED — Layered Modular Monolith in single FastAPI container (ADR-001) |
| OQ-AG02 | Synchronous vs Async Agent Execution | Mrityunjoy | ✅ RESOLVED — Event-triggered async background tasks + ad-hoc sync query endpoints (ADR-001) |
| OQ-AG03 | Scheduler Implementation Mechanism | Bishesh | ✅ RESOLVED — In-process asyncio worker loop at startup + every 5 minutes (DM-AG03 / ADR-001) |

---

## 9. Phase-0 Reconciliation Addendum (11 October 2026 — ADR-003)

> This addendum reconciles the frozen architecture with the **actual implemented codebase** at `feature/vertical-slice-case-approval` @ `d78ffca`. It does **not** reverse any ADR-001 decision. Full findings: `docs/decisions/ADR-003_CORE_PLATFORM_RECONCILIATION.md`. Ordering/roadmap: `docs/11_ROADMAP.md`.

### 9.1 Four-client system map (extends §1)

```
 ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
 │ STUDENT ANDROID    │  │ CLASS TEACHER      │  │ STUDENT WEBSITE  │  │ FACULTY WEBSITE  │
 │ (Android Studio,   │  │ ANDROID            │  │ (Next.js,        │  │ (Next.js —        │
 │  external repo)    │  │ (Android Studio,   │  │  apps/mobile)    │  │  apps/web:        │
 │                    │  │  external repo)    │  │                  │  │  Faculty/CT/      │
 │                    │  │                    │  │                  │  │  Mentor/HOD/Admin)│
 └─────────┬──────────┘  └─────────┬──────────┘  └────────┬─────────┘  └────────┬─────────┘
           └───────────────────────┴─────────────────────┴──────────────────────┘
                                           │ HTTPS + Supabase JWT (identity only)
                              ┌────────────▼────────────┐
                              │  ASPIRE CORE PLATFORM   │
                              │  FastAPI (app/) —       │
                              │  auth deps → routers →  │
                              │  services → engines →   │
                              │  event bus → SQLAlchemy │
                              └────────────┬────────────┘
                              PostgreSQL + pgvector (db/migrations/*.sql = schema authority)
```

Clients are presentation-only (zero business logic — §4 and `ASPIRE_APPLICATION_BOUNDARIES.md` remain authoritative). The external Compose scaffold at `C:\Users\ANAMIKA\AndroidStudioProjects\ASPIRE` is a mock-data UX prototype, **not** a contract-consuming client yet.

### 9.2 Actual module map (canonical — supersedes the §6 target tree)

The implementation lives in a single root Python package `app/` (not `services/`). §6 is retained above as historical target; this table is authoritative:

| Actual path | Layer (ADR-001) | State @ d78ffca |
|---|---|---|
| `app/main.py` | App assembly, lifespan, event-bus wiring | Implemented |
| `app/api/routers/` (students, attendance, assessments, tasks, cases) | API & Security | Implemented; assessments auth wiring defective (ADR-003 §6.3) |
| `app/api/deps.py`, `app/api/schemas.py` | JWKS auth + RBAC deps, Pydantic schemas | Implemented (ownership helper incomplete) |
| `app/services/` (case_service, student_action_service, evidence, llm_service) | Domain services + LLM gateway | Implemented (llm_service unused by agents yet) |
| `app/engines/` (attendance, assessment, priority, tasks, intervention) | Deterministic engines | Implemented (uneven test depth) |
| `app/models/` (21 entities) | Persistence models mirroring migrations | Implemented, 1:1 with migrations 001–013 |
| `app/core/` (config, database, events) | Settings, async engine/NullPool, in-process event bus | Implemented |
| `app/agents/` | Agent orchestration (Layer 5) | **Not present** (spec only) |
| `db/migrations/` 001–013 | Schema authority | Implemented |
| `contracts/openapi.json` | API contract artifact (DM-API01) | Generated, CI drift-guarded |
| `apps/web`, `apps/mobile`, `packages/shared` | Web clients + shared TS | Prototypes (mentor workspace; mock student PWA) |
| `tests/` (17 files, 7 DSN-gated `*_pg.py`) | Unit + integration | 169 unit green; PG integration local-only |
| `db/seeds/`, `evals/`, `uv.lock` | Seeds, eval harness, lockfile | **Not present** |

### 9.3 Verified flows & boundaries (confirmations)

- **AuthZ:** JWT = identity only; roles from `user_role_assignments` (multi-role, scoped, time-boxed) — matches §4 and `07 §2`; record-level scoping partially implemented (see ADR-003 §3.3).
- **Events:** commit-then-emit via in-process bus (ADR-002) — implemented; consumers and scheduler not yet built.
- **Schema/contract authority:** migrations + generated OpenAPI, both enforced in practice; drift guard live in CI.
- **Open structural items for lead (ADR-003 §6):** default-branch rename (ARCH-03), rule precedence/effective dating, `uv.lock`, P0 security slice approval, Android repo stewardship.

