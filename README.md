# EduGen AI — ASPIRE
### An Agentic Student Progress, Intelligence and Resource Engine for Higher Education

**Team Lead:** Mrityunjoy Kapat
**Team:** Abhijit Ghosh · Bishesh Ghosh · Mrityunjoy Kapat
**Reference Institution:** Dr. B. C. Roy Engineering College (BCREC), Durgapur
**Version:** 1.0 — 02 October 2026

---

## What is ASPIRE?

ASPIRE is a student-first academic intelligence and agentic assistance platform.
It maintains a validated view of a student's academic state, detects actionable issues,
plans personalized next steps, tracks follow-through, verifies outcomes,
and routes unresolved cases to the appropriate human mentor or academic staff.

**Core loop:** `Observe → Understand → Detect → Plan → Assist → Verify → Replan → Escalate`

---

## Repository Structure

```
ASPIRE/
├── docs/
│   ├── CONSTITUTION.md          ← Start here. Non-negotiable engineering principles.
│   ├── 01_PRD.md                ← What we build, who it's for, why.
│   ├── 02_USER_JOURNEYS.md      ← What every user actually does.
│   ├── 03_SYSTEM_SPEC.md        ← Functional contracts for every module.
│   ├── 04_ARCHITECTURE.md       ← System boundaries and agent model.
│   ├── 05_DATA_API_CONTRACTS.md ← Entities, schema, API endpoints.
│   ├── 06_AGENT_SPEC.md         ← Agent contracts and tool boundaries.
│   ├── 07_SECURITY_TRUST.md     ← RBAC, privacy, audit.
│   ├── 08_EVALS.md              ← How we prove the system works.
│   ├── 09_EDGE_CASES.md         ← Adversarial test catalogue.
│   ├── 10_TASKS.md              ← Implementation tasks (after all above are FROZEN).
│   └── decisions/
│       └── ADR-XXX.md           ← Architecture Decision Records.
├── apps/
│   ├── web/                     ← Next.js 15 web app
│   └── mobile/                  ← React Native + Expo
├── services/
│   ├── api/                     ← FastAPI backend
│   ├── agents/                  ← LangGraph agent orchestration
│   ├── rules/                   ← Deterministic rule engines
│   ├── ingestion/               ← CSV/Excel import + notice crawling
│   └── notifications/           ← Push + in-app notifications
├── packages/
│   ├── schemas/                 ← Shared TypeScript types + Zod schemas
│   ├── ui/                      ← Shared component library
│   └── config/                  ← Institution configuration
├── db/
│   ├── migrations/
│   ├── seeds/
│   └── fixtures/
├── evals/
├── tests/
├── design/
│   └── design-system.md
├── AGENTS.md                    ← Rules for AI coding agents
└── README.md
```

---

## Pre-Coding Status

> **NO CODE IS WRITTEN UNTIL ALL RELEVANT SPEC SECTIONS ARE FROZEN.**

| Document | Status |
|---|---|
| `CONSTITUTION.md` | 🔴 DRAFT |
| `01_PRD.md` | ⬜ Not started |
| `02_USER_JOURNEYS.md` | ⬜ Not started |
| `03_SYSTEM_SPEC.md` | ⬜ Not started |
| `04_ARCHITECTURE.md` | ⬜ Not started |
| `05_DATA_API_CONTRACTS.md` | ⬜ Not started |
| `06_AGENT_SPEC.md` | ⬜ Not started |
| `07_SECURITY_TRUST.md` | ⬜ Not started |
| `08_EVALS.md` | ⬜ Not started |
| `09_EDGE_CASES.md` | ⬜ Not started |
| `10_TASKS.md` | ⬜ Not started |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Mobile | React Native + Expo |
| Backend API | Python + FastAPI |
| Agent Orchestration | LangGraph |
| Database | PostgreSQL (Supabase) + pgvector |
| Auth | Supabase Auth |
| Push Notifications | Firebase Cloud Messaging |
| LLM | Provider-agnostic (ADR-001) |
| Embeddings | BGE-M3 (swappable) |
| Hosting | Vercel (web) + managed API |

---

## Team

| Member | Primary Role |
|---|---|
| Mrityunjoy Kapat | Team Lead · Agentic AI · Integration · Mobile |
| Abhijit Ghosh | Product · System Architecture · Web UX |
| Bishesh Ghosh | Backend · Database · Data Ingestion · API |

---

*Read `docs/CONSTITUTION.md` before contributing anything.*
