# ASPIRE AI WORKING STATE
# docs/AI_WORKING_STATE.md

> This file is the mutable handoff document for AI coding agents.
> Read it before starting any major task. Keep it concise.
> Update it whenever phase, task, or blockers change.

---

## Current Phase

**Documentation Reset & Consistency Audit — Pre-Mother-System**

All major spec documents exist. Many decisions have been frozen. The next phase is to design and freeze the Mother System architecture before any client implementation begins.

---

## Current Objective

Ensure the repository documentation is internally consistent, all frozen decisions are clearly identified, all open questions are recorded, and the Mother System starting point is unambiguous.

---

## Authoritative Documents

| Document | Purpose |
|---|---|
| `docs/CONSTITUTION.md` | Engineering and product principles |
| `docs/01_PRD.md` | Product scope, P0/P1 features, demo story |
| `docs/02_USER_JOURNEYS.md` | User flows (student risk, mentor queue, data conflict) |
| `docs/03_SYSTEM_SPEC.md` | Deterministic engines: attendance, assessment, tasks, events, cases |
| `docs/04_ARCHITECTURE.md` | Stack, frozen decisions, folder structure, service map |
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

---

## Current Architecture (Summary)

```
Client Apps (Next.js 15)         ← consume Mother System via API
         |
    FastAPI API Gateway           ← auth, RBAC, routing, OpenAPI contract
         |
   ┌─────┴──────┐
Rule Engines    Agent Orchestrator
(pure Python)   (framework TBD — LangGraph is a candidate, not frozen)
         |
    LLM Service (→ OpenRouter)
         |
   PostgreSQL + pgvector (Supabase)
```

**Mother System** = identity + RBAC + domain model + engines + events + agents + audit + API contracts.
**Client apps** = consumers of the Mother System. Do not duplicate business logic in clients.

---

## Current Task

**Documentation audit and consistency pass.** Finish `docs/AI_WORKING_STATE.md`, rewrite `AGENTS.md`, fix stale doc statuses, record all frozen decisions, record all open questions, push clean state.

---

## Next Task

**"Design and freeze the ASPIRE Mother System architecture before implementing client applications."**

This means: define the Mother System's internal structure, service boundaries, deployment topology, and event model as a standalone architectural decision — separate from client app design.

Do NOT begin this task until the current documentation audit is committed and pushed.

---

## Blockers

| ID | Blocker | Owner |
|---|---|---|
| OQ-05 | BCREC real data sample contact — needed for ingestion validation | All |
| OQ-07 | MAR points calculation rules | Abhijit |
| OQ-08 | BCREC roll number format | Bishesh |
| OQ-SS01 | `ATTENDANCE_WATCH` margin value — team must agree before implementing | All |
| OQ-AG01 | Default production LLM model — must be selected via evaluation, not reputation | Mrityunjoy |
| OQ-AG02 | Synchronous vs async agents — affects API design | Mrityunjoy + Bishesh |
| OQ-AG03 | Scheduler mechanism — cron job or event-driven? | Bishesh |

---

## Open Questions

| ID | Question |
|---|---|
| ARCH-01 | Agent framework: LangGraph is a candidate but NOT frozen. Mother System architecture phase must evaluate options against requirements (reliability, complexity, student-team feasibility, portability). Do not assume LangGraph is final. |
| ARCH-02 | n8n, Temporal, Inngest, Redis, Kafka — none are frozen. Do not introduce these until Mother System architecture is decided. |
| ARCH-03 | `master` → `main` branch rename: deferred to repository finalization. Current branch is `master`. |
| ARCH-04 | Mother System internal topology: single deployable, layered monolith, or extracted services? Not yet decided. |

---

## Do Not Do

- Do NOT start Android app, student web app, or any client UI implementation
- Do NOT introduce LangGraph, n8n, Temporal, Inngest, Redis, or Kafka until frozen
- Do NOT invent BCREC institutional rules or data
- Do NOT fabricate team approvals or sign-offs
- Do NOT rewrite frozen decisions without team lead approval
- Do NOT start Mother System implementation — only design and freeze architecture first
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
