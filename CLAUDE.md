# ASPIRE - AI Project Guide

This guide provides the essential context for any AI agent working on the ASPIRE project. To maintain architectural integrity and prevent regressions, **always adhere to the rules in this file and the `docs/` directory.**

## 🎯 Project Essence
ASPIRE is a Student Success Intelligence platform. It uses a closed-loop agentic workflow: 
`OBSERVE → UNDERSTAND → DETECT → PLAN → ASSIST → VERIFY → REPLAN → ESCALATE`.

## 🛠 Tech Stack
- **Backend:** FastAPI (Python 3.12+), PostgreSQL (with pgvector), SQLAlchemy (Async).
- **Frontend:** Next.js 15+ (App Router), TypeScript, Tailwind CSS.
- **AI Orchestration:** LangGraph, OpenRouter (via `LLMService`).
- **Infrastructure:** Docker, Git.

## 🚫 The "Golden Rules" (Non-Negotiable)
1. **Deterministic First:** AI agents **propose**; Deterministic Engines **calculate**. Never let an LLM decide a student's risk status or eligibility.
2. **Abstraction Layers:** 
   - Never call LLM providers directly $\rightarrow$ Use `LLMService`.
   - Never write raw SQL mutations from agents $\rightarrow$ Use FastAPI endpoints.
3. **Security First:** 
   - No cross-institution data access (Strict Tenant Isolation).
   - HODs cannot approve cases unless they are in `ESCALATION_REQUIRED` status.
   - Every privileged write MUST produce an `audit_log` record.
4. **Configuration-Driven:** Rules (thresholds, weights) must be read from the `institution_rules` table, never hardcoded.

## 📜 Architecture Map
- `app/services/`: Domain logic and state transitions.
- `app/engines/`: Pure Python deterministic rule engines.
- `app/agents/`: LangGraph supervisors and specialists.
- `app/api/`: FastAPI routers and dependency injection.
- `db/migrations/`: Sole authority for the PostgreSQL schema.

## 🏃 Development Workflow
### Testing
- Run a specific test: `pytest tests/test_file.py`
- Run all backend tests: `pytest tests/`
- Ensure `PYTHONPATH=.` is set.

### State Management
Before starting any task, read `docs/AI_WORKING_STATE.md` to understand the current phase, completed tasks, and immediate next steps.

### Commits
- Feature branches only. No direct pushes to `master`.
- Commit messages should follow: `type(scope): description` (e.g., `feat(replan): implement rejection loop`).
