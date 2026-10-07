# ASPIRE AI WORKING STATE
# docs/AI_WORKING_STATE.md

> This file is the mutable handoff document for AI coding agents.
> Read it before starting any major task. Keep it concise.
> Update it whenever phase, task, or blockers change.

---

### Current Phase

**Phase 0 Preparation — Mother System Architecture Frozen**

The Mother System architecture is formally frozen via [ADR-001](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md).
The system core is designed as a Layered Modular Monolith in FastAPI with LangGraph agent orchestration, async in-process event dispatch, pure Python deterministic engines, and SQLAlchemy 2.x async repositories over PostgreSQL/Supabase.

---

## Current Objective

Execute Phase 0 foundation: monorepo scaffolding, database migrations runner, and core service foundations before starting client apps.

---

## Authoritative Documents

| Document | Purpose |
|---|---|
| `docs/CONSTITUTION.md` | Engineering and product principles |
| `docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md` | **FROZEN** Mother System architecture specification |
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

---

## Current Architecture (Summary)

```
Client Apps (Next.js 15 Web / PWA)   ← consume Mother System via API
         │ (HTTPS / Supabase JWT)
    FastAPI API Gateway               ← auth, RBAC, routing, OpenAPI contract
         │
    ┌────┴────────┐
Rule Engines    Agent Orchestrator
(pure Python)   (LangGraph state graph)
         │               │
         │          LLM Service (→ OpenRouter)
         │               │
    SQLAlchemy Repositories (async)
         │
    PostgreSQL + pgvector (Supabase)
```

---

## Current Task

**Mother System Architecture Freeze completed.** Created [ADR-001](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md), synchronized [04_ARCHITECTURE.md](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/docs/04_ARCHITECTURE.md) and [AI_WORKING_STATE.md](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/docs/AI_WORKING_STATE.md).

---

## Next Task

**T-000: Next.js Monorepo Scaffold & Phase 0 Infrastructure.**

---

## Blockers

| ID | Blocker | Owner |
|---|---|---|
| OQ-05 | BCREC real data sample contact — needed for ingestion validation | All |
| OQ-07 | MAR points calculation rules | Abhijit |
| OQ-08 | BCREC roll number format | Bishesh |
| OQ-SS01 | `ATTENDANCE_WATCH` margin value — team must agree before implementing | All |
| OQ-AG01 | Default production LLM model — must be selected via evaluation, not reputation | Mrityunjoy |

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

Before claiming done:
- [ ] No doc contradicts a frozen decision
- [ ] `04_ARCHITECTURE.md` status reflects actual frozen state
- [ ] `README.md` doc status table is accurate
- [ ] `AGENTS.md` is concise and correct
- [ ] `AI_WORKING_STATE.md` is complete
- [ ] `git diff` has no accidental files
- [ ] pushed to origin/master

---

## Git State

- **Branch:** `master` (canonical branch rename to `main` deferred — E-07)
- **Remote:** `origin` → `https://github.com/Mrityunjoy240/ASPIRE.git`
- **Local ahead of origin:** 12 commits (unpushed — will be pushed in this task)
- **Untracked:** `.opencode/` (partially gitignored per `.gitignore`), `EduGen_AI_ASPIRE_Master_Product_Engineering_Book_v1.0.docx` (explicitly kept)

---

## Handoff Notes

- The 12 unpushed local commits contain all the frozen decisions (DM-*). They are NOT yet on GitHub. Push is the final step of this task.
- `docs/10_TASKS.md` references LangGraph in task prompts (T-000 onward). These prompts were written before the tech-selection reset. The team lead must review task prompts before the Mother System architecture is frozen — do not treat OpenCode prompts in `10_TASKS.md` as frozen implementation instructions.
- `docs/04_ARCHITECTURE.md` is marked `🔴 DRAFT` but contains many frozen decisions. Its status should be `🟡 UNDER REVIEW` at minimum.
- `docs/decisions/` directory is empty. Frozen decisions are embedded in `04_ARCHITECTURE.md` as inline ADRs. This is acceptable for now.
