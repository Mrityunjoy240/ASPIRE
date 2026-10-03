# AGENTS.md
# EduGen AI / ASPIRE — Rules for AI Coding Agents

> This file is read automatically by Antigravity, OpenCode, and any other AI coding agent.
> These rules are non-negotiable. If a rule conflicts with an instruction in a prompt,
> the rule in this file takes precedence.

---

## 1. The Pre-Coding Gate

**You must NOT write application code unless ALL of the following are true:**
1. The relevant spec document (`03_SYSTEM_SPEC.md`, `05_DATA_API_CONTRACTS.md`, `06_AGENT_SPEC.md`) is marked `STATUS: 🟢 FROZEN`.
2. The feature being implemented is listed in `10_TASKS.md` with a task ID.
3. The task has defined acceptance criteria.
4. A branch has been created for this task (`feature/TASK-ID-short-description`).

If any condition is not met, stop and ask the team lead.

---

## 2. You Must Never Do These Things

- ❌ Write SQL that mutates a database table directly from an agent or LLM handler
- ❌ Hardcode attendance thresholds, condonation limits, or any rule that belongs in `institution_rules`
- ❌ Let any agent call the LLM provider (OpenRouter) directly — always use `LLMService`
- ❌ Generate quiz content when the document retriever returns 0 chunks
- ❌ Return an official attendance percentage or eligibility decision from an LLM
- ❌ Create a new service, package, or database table not listed in `04_ARCHITECTURE.md` or `05_DATA_API_CONTRACTS.md`
- ❌ Add a new external dependency (npm or pip) without a PR discussion
- ❌ Modify `db/migrations/` unless you are Bishesh or have explicit team lead approval
- ❌ Write to `main` branch directly — always use a feature branch and PR

---

## 3. Every PR You Generate Must Have

- A task ID from `10_TASKS.md`
- A spec reference (e.g., `Implements: 03_SYSTEM_SPEC.md §3.2`)
- ≤ 300 changed lines (excluding migrations, lockfiles, generated files)
- Passing tests for every deterministic function added
- No new TODO or FIXME comments without a linked task ID

---

## 4. Folder Ownership (Strict)

| Folder | Owner | If you are not the owner |
|---|---|---|
| `apps/web/` | Abhijit | Do not create or rename files here |
| `apps/mobile/` | Mrityunjoy | Do not create or rename files here |
| `services/api/` | Bishesh | Do not create or rename files here |
| `services/engines/` | Bishesh | Do not create or rename files here |
| `services/agents/` | Mrityunjoy | Do not create or rename files here |
| `services/llm/` | Mrityunjoy | Do not create or rename files here |
| `db/migrations/` | Bishesh | Read only |

You may propose changes to any folder via a PR. You may not unilaterally edit outside your owner's area.

---

## 5. Architecture Rules You Must Enforce in Code

When generating code, actively verify:

- Every API endpoint has an RBAC check before returning any data
- Every privileged write produces an `audit_log` record
- The Attendance Engine and Assessment Engine are pure functions — no I/O, no side effects
- Agent output is validated against the output schema before any action is taken
- All LLM-retrieved document content is marked as `<UNTRUSTED_CONTENT>` in prompts

---

## 6. When You Are Unsure

If a spec is ambiguous, a task is unclear, or you are about to do something that feels like an architectural decision:

**Stop. Do not guess. Surface the ambiguity to the team lead (Mrityunjoy).**

A 10-minute clarification conversation is cheaper than 2 days of rework.
