# AGENTS.md
# ASPIRE — AI Agent Quick Reference

> Read this file first. Read `docs/AI_WORKING_STATE.md` and `docs/ASPIRE_APPLICATION_BOUNDARIES.md` before starting any major task.
> These rules are non-negotiable. If a prompt conflicts with a rule here, this file wins.

---

## What is ASPIRE?

ASPIRE is **ONE unified Student Success Intelligence platform**. It is NOT multiple independent products.

Core loop: **OBSERVE → UNDERSTAND → DETECT → PLAN → ASSIST → VERIFY → REPLAN → ESCALATE**

Reference institution: BCREC, Durgapur. Target: P0 demo of the full loop for one at-risk student.

---

## Ecosystem Structure & Development Ownership

```
                         ASPIRE
                            │
                  ┌─────────┴─────────┐
                  │                   │
          MOTHER APPLICATION      CORE PLATFORM
             (Web / Next.js)       (FastAPI / Python)
                  │                   │
                  └─────────┬─────────┘
                            │
                     Shared API / Data
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
      Student Clients   Faculty Clients   Institution
      ├── Web (Next.js) ├── Web (Next.js) └── Web (Next.js)
      └── Android       └── Android
```

### 1. Mother Application (Web)
- The **main human-facing management and operational control application** (System Admin, Institution Admin, HOD, Faculty, Mentors).
- Built with **Next.js 15+ App Router, TypeScript, and Tailwind CSS** in `apps/web/`.
- Uses Role-Based Access Control and progressive disclosure (never one giant overloaded dashboard).

### 2. Core Platform (Backend & Intelligence)
- The centralized intelligence core: Database, Auth, Deterministic Rule Engines, Event Bus, LangGraph Agents, `LLMService`, and API contracts.

### 3. OpenCode vs. Android Studio Ownership
- **OpenCode** builds and maintains: Mother Application (Web), all Web Clients, Backend/Core Platform, Database Migrations, Rule Engines, Agents, and API contracts in this repository.
- **Android Studio** builds Native Android applications (Kotlin, Jetpack Compose) as **external clients** consuming the shared API contracts. **Do NOT build native Android apps in this repository.**

---

## Architecture Principles (Non-Negotiable)

- **Engines calculate. Agents propose. Humans approve consequential decisions.**
- **AI is never the source of truth.** Attendance %, grades, eligibility = deterministic engines only.
- **One shared core.** No duplicated business logic across clients. All clients consume the Core Platform.
- **Configuration-driven.** Institutional rules (thresholds, weights) live in `institution_rules` table — never hardcoded.
- **Audit everything.** Every privileged write produces an `audit_log` record.

---

## Hard Rules

| Never | Always |
|---|---|
| Call LLM provider directly from an agent | Use `LLMService` abstraction |
| Write SQL mutations from an agent | Call typed FastAPI endpoints |
| Hardcode thresholds/rules | Read from `institution_rules` |
| Generate quiz with 0 retrieved chunks | Fail gracefully |
| Return eligibility decision from LLM | Use deterministic engine output |
| Create tables/services not in `05_DATA_API_CONTRACTS.md` | Follow the schema |
| Duplicate core business logic in clients | Call the ASPIRE Core API |
| Build native Android apps in Next.js workspace | Build native Android separately in Android Studio |
| Push to `main` directly | Feature branch + PR only |
| Invent institutional rules or approvals | Surface ambiguity to team lead |

---

## Folder Ownership (In this Repository)

| Folder | Owner | Scope |
|---|---|---|
| `apps/web/` | Abhijit | Mother Application (Web) + Admin/Faculty/Mentor Workspace |
| `apps/mobile/` | Mrityunjoy | Student Web Client / Mobile PWA |
| `services/api/` / `app/api/` | Bishesh | FastAPI Gateway, Auth Middleware, Routers |
| `services/engines/` / `app/engines/` | Bishesh | Pure Python Deterministic Rule Engines |
| `services/agents/` | Mrityunjoy | LangGraph Agents (Supervisor + Specialists) |
| `services/llm/` / `app/services/` | Mrityunjoy | LLMService (OpenRouter + Mock fixtures) |
| `db/migrations/` | Bishesh | PostgreSQL migrations (sole schema authority) |

---

## Authoritative Documents

| Document | Authority |
|---|---|
| `docs/CONSTITUTION.md` | Product + engineering principles |
| `docs/ASPIRE_APPLICATION_BOUNDARIES.md` | Application boundaries, ecosystem model, and tooling ownership |
| `DESIGN.md` | UI/UX design system, tokens, palettes, component guidelines |
| `docs/03_SYSTEM_SPEC.md` | Deterministic engine contracts |
| `docs/04_ARCHITECTURE.md` | Tech stack, frozen decisions, service map |
| `docs/05_DATA_API_CONTRACTS.md` | PostgreSQL schema + API shapes |
| `docs/06_AGENT_SPEC.md` | Agent boundaries, tools, output contracts |
| `docs/07_SECURITY_TRUST.md` | RBAC, auth, audit rules |
| `docs/10_TASKS.md` | Build order — pick tasks from here only |
| `docs/AI_WORKING_STATE.md` | Current phase, task, blockers (read before starting) |

---

## When Unsure

Stop. Do not guess. Surface the ambiguity to the team lead (Mrityunjoy).
A 10-minute clarification is cheaper than 2 days of rework.

