# 04_ARCHITECTURE.md
# EduGen AI / ASPIRE — System Architecture

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Primary Reviewer:** Abhijit Ghosh (Architecture)
**Date:** 03 October 2026
**Version:** 1.0

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
│  │  React Native   │    │   Next.js 15     │    │     Next.js 15          │  │
│  │  + Expo         │    │  (App Router)    │    │     (App Router)        │  │
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
| Mobile App | React Native + Expo | Mrityunjoy | Student-primary mobile experience |
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
- **API → Rule Engines:** Direct in-process function calls. Rule engines are pure Python modules, not microservices. No HTTP between them.
- **API → Agent Orchestrator:** Direct in-process call in v1. (Can be extracted to a queue later).
- **Agents → Database:** Agents NEVER call Supabase/PostgreSQL directly. They call typed FastAPI tool endpoints which enforce RBAC.
- **Agents → LLM:** Agents call `LLMService` class only. `LLMService` calls OpenRouter.
- **No agent-to-agent HTTP calls.** All agent coordination goes through LangGraph graph state.

---

## 5. Technology Decisions (ADR Summary)

| Decision | Choice | Reason |
|---|---|---|
| LLM Gateway | OpenRouter | Already used in EduGen. Provider-agnostic. |
| Agent Framework | LangGraph | Supports stateful, cyclical agent graphs. Fits the Observe→Replan loop. |
| Database | PostgreSQL (Supabase) | pgvector support. Auth included. RLS for RBAC. |
| Embeddings | BGE-M3 (1024-dim) | Multilingual, strong retrieval. Swappable via config. |
| Mobile | React Native + Expo | Cross-platform. Expo Router for navigation. |
| Web | Next.js 15 App Router | Server components. TypeScript native. Vercel deploy. |
| API | FastAPI | Async. Auto-generated OpenAPI docs. Python for ML interop. |

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
│   └── mobile/                 ← React Native + Expo (Mrityunjoy owns)
│       ├── app/                ← Expo Router
│       └── components/
├── services/
│   ├── api/                    ← FastAPI (Bishesh owns)
│   │   ├── routers/
│   │   ├── middleware/
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
│   ├── schemas/                ← Shared TypeScript types + Zod schemas
│   └── ui/                     ← Shared component library
├── db/
│   ├── migrations/             ← Supabase migrations (Bishesh owns)
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

## 8. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-A01 | Should the API and Agents run as a single FastAPI process in v1 or separate services? | Mrityunjoy + Bishesh | 🔴 OPEN — decide before `10_TASKS.md` |
| OQ-A02 | What is the local dev setup? (Docker Compose? Each service independently?) | Bishesh | 🔴 OPEN — blocks onboarding |
| OQ-A03 | Shared `packages/schemas` — TypeScript only or Python Pydantic models too? | All | 🔴 OPEN |
