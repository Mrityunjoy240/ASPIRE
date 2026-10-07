# AGENTS.md
# ASPIRE — AI Agent Quick Reference

> Read this file first. Read `docs/AI_WORKING_STATE.md` before starting any major task.
> These rules are non-negotiable. If a prompt conflicts with a rule here, this file wins.

---

## What is ASPIRE?

Student Success Intelligence platform. One core system ("Mother System") with multiple future clients.

Core loop: **OBSERVE → UNDERSTAND → DETECT → PLAN → ASSIST → VERIFY → REPLAN → ESCALATE**

Reference institution: BCREC, Durgapur. Target: P0 demo of the full loop for one at-risk student.

---

## Architecture Principles (Non-Negotiable)

- **Engines calculate. Agents propose. Humans approve consequential decisions.**
- **AI is never the source of truth.** Attendance %, grades, eligibility = deterministic engines only.
- **One shared core.** No duplicated business logic across clients. All clients consume the Mother System.
- **Configuration-driven.** Institutional rules (thresholds, weights) live in `institution_rules` table — never hardcoded.
- **Audit everything.** Every privileged write produces an `audit_log` record.

---

## Before Writing Any Code

1. Read `docs/AI_WORKING_STATE.md` — check current phase, task, and blockers.
2. Confirm the relevant spec is `🟢 FROZEN` (see `docs/`).
3. Find the task in `docs/10_TASKS.md` with a task ID and acceptance criteria.
4. Work on a feature branch: `feature/<task-id>-<short-name>` (branch off `main`).

**If any of the above is not true — stop and ask the team lead.**

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
| Push to `main` directly | Feature branch + PR only |
| Invent institutional rules or approvals | Surface ambiguity to team lead |

---

## Folder Ownership

| Folder | Owner |
|---|---|
| `apps/web/` | Abhijit |
| `apps/mobile/` | Mrityunjoy |
| `services/api/` | Bishesh |
| `services/engines/` | Bishesh |
| `services/agents/` | Mrityunjoy |
| `services/llm/` | Mrityunjoy |
| `db/migrations/` | Bishesh (others: read-only) |

---

## Authoritative Documents

| Document | Authority |
|---|---|
| `docs/CONSTITUTION.md` | Product + engineering principles |
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
