# README.md
# EduGen AI — ASPIRE

**An Agentic Student Progress, Intelligence and Resource Engine for Higher Education**

**Reference Institution:** Dr. B.C. Roy Engineering College (BCREC), Durgapur
**Team:** Mrityunjoy Kapat · Abhijit Ghosh · Bishesh Ghosh
**Status:** Active Development — Phase 0 (Spec + Foundation)

---

## What is ASPIRE?

ASPIRE is an agentic academic intelligence platform that connects fragmented student data (attendance, assessments, deadlines, learning materials) into a single proactive system that detects problems early, proposes evidence-backed recovery plans, routes them through mentor approval, and verifies outcomes.

**It is not a chatbot. It is not a dashboard. It is a closed-loop intervention system.**

The system behavior:
```
Observe → Understand → Detect → Plan → Assist → Verify → Replan → Escalate
```

---

## The Demo Story (P0 North Star)

> Student S-204, DBMS attendance at 73%, exam in 8 days, assessment trend declining.
> ASPIRE detects the risk, proposes a recovery plan, routes it to the mentor, the student accepts,
> completes a targeted quiz from their own uploaded notes, and the case closes when attendance recovers.

**If this flow works cleanly, the product has a story.**

---

## ⚠️ Read Before You Touch Anything

1. **Read [`AGENTS.md`](./AGENTS.md)** — if you are an AI agent (OpenCode, Antigravity), start here.
2. **Read [`docs/CONSTITUTION.md`](./docs/CONSTITUTION.md)** — the non-negotiable engineering rules.
3. **Read [`docs/10_TASKS.md`](./docs/10_TASKS.md)** — pick your task from here, not from your imagination.
4. **No application code is written without a task ID from `10_TASKS.md`.**

---

## Technology Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy |
| LLM Gateway | OpenRouter (via internal `LLMService`) |
| Testing | Vitest |
| CI | GitHub Actions |

---

## Monorepo Structure

```
apps/web/        ← Mentor, admin, faculty web workspace (Next.js 15)
apps/mobile/     ← Student mobile app (Next.js 15 PWA)
packages/
  database/      ← db/migrations (SQL schema) + services/api/db (SQLAlchemy); seeds in db/seeds/
  shared/        ← Engines, agents, LLMService, audit (shared TypeScript)
docs/            ← All spec documents (source of truth)
```

See [`docs/04_ARCHITECTURE.md`](./docs/04_ARCHITECTURE.md) for the full architecture.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Mrityunjoy240/ASPIRE.git
cd ASPIRE

# 2. Install
npm install

# 3. Setup environment
cp .env.example .env
# Fill in your DATABASE_URL, LLM_API_KEY and the frozen Supabase keys:
# NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, SUPABASE_JWKS_URI

# 4. Local Supabase stack (Supabase CLI: Postgres/Auth/Storage/Data API/Studio)
supabase start
# Next.js and FastAPI run natively — no second Supabase Docker Compose stack

# 5. Database setup
# apply SQL migrations (db/migrations/*.sql) to the local Supabase Postgres
# (ASPIRE-controlled runner — db/migrations is the only schema authority)
# apply SQL seeds (db/seeds/*.sql)

# 6. Run
npm run dev --workspace=apps/web      # Web app: http://localhost:3000
npm run dev --workspace=apps/mobile   # Mobile app: http://localhost:3001
```

Regenerate the API contract (DM-API01 — FastAPI/Pydantic is source of truth; the committed `contracts/openapi.json` is generated, never hand-edited; CI fails on drift):

```bash
uv run python scripts/generate_openapi.py   # writes contracts/openapi.json
```

---

## Documentation Index

| Doc | Purpose | Status |
|---|---|---|
| [`CONSTITUTION.md`](./docs/CONSTITUTION.md) | Non-negotiable engineering + product principles | 🟡 UNDER REVIEW |
| [`AI_WORKING_STATE.md`](./docs/AI_WORKING_STATE.md) | Current phase, task, blockers — AI agent handoff | 🔄 LIVE |
| [`ASPIRE_APPLICATION_BOUNDARIES.md`](./docs/ASPIRE_APPLICATION_BOUNDARIES.md) | Ecosystem structure, Mother App (Web), Core Platform, OpenCode vs Android Studio | 🟢 FROZEN |
| [`DESIGN.md`](./DESIGN.md) | UI/UX design system, color tokens, component patterns | 🟢 FROZEN |
| [`ADR-001`](./docs/decisions/ADR-001_MOTHER_SYSTEM_ARCHITECTURE.md) | Mother System Architecture specification | 🟢 FROZEN |
| [`01_PRD.md`](./docs/01_PRD.md) | What we build, who for, why, success criteria | 🟡 UNDER REVIEW |
| [`02_USER_JOURNEYS.md`](./docs/02_USER_JOURNEYS.md) | Exact step-by-step flows for every user type | 🟡 UNDER REVIEW |
| [`03_SYSTEM_SPEC.md`](./docs/03_SYSTEM_SPEC.md) | Deterministic engines — math, state machines, logic | 🟡 UNDER REVIEW |
| [`04_ARCHITECTURE.md`](./docs/04_ARCHITECTURE.md) | Tech stack, frozen decisions (DM-*, ADR-001), service map | 🟢 FROZEN |
| [`05_DATA_API_CONTRACTS.md`](./docs/05_DATA_API_CONTRACTS.md) | PostgreSQL schema + API endpoint shapes | 🔴 DRAFT |
| [`06_AGENT_SPEC.md`](./docs/06_AGENT_SPEC.md) | Agent contracts, tools, boundaries, degradation | 🟡 UNDER REVIEW |
| [`07_SECURITY_TRUST.md`](./docs/07_SECURITY_TRUST.md) | Auth, RBAC, prompt injection, audit requirements | 🔴 DRAFT |
| [`08_EVALS.md`](./docs/08_EVALS.md) | Test fixtures, eval scenarios, pass/fail criteria | 🔴 DRAFT |
| [`09_EDGE_CASES.md`](./docs/09_EDGE_CASES.md) | Edge cases for data, agents, ingestion | 🔴 DRAFT |
| [`10_TASKS.md`](./docs/10_TASKS.md) | Task queue — build order (review prompts before use) | 🔴 DRAFT |
| [`AGENTS.md`](./AGENTS.md) | Concise quick-reference for AI coding agents | 🟡 UNDER REVIEW |

---

## Team

| Member | Role | Domain |
|---|---|---|
| **Mrityunjoy Kapat** | Team Lead | Agentic AI, Supervisor, LLMService, Integration, Evaluation |
| **Abhijit Ghosh** | Product / UX / Frontend | Figma, Design System, Student App, Mentor Web UI |
| **Bishesh Ghosh** | Backend / Database / Data | PostgreSQL, Student State, Data Ingestion, Rule Engines, API |

---

*EduGen AI / ASPIRE — Built for BCREC. Designed for every college.*
