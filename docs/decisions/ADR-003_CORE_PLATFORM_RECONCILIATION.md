# ADR-003: Phase-0 Architecture Reconciliation

**STATUS: ✅ RECONCILIATION RECORD — architectural baseline confirmed; items in §6 await team-lead approval**
**Date:** 11 October 2026
**Author:** OpenCode (reconciliation agent)
**Authority:** Lead directive — reconcile architecture before further feature work; preserve proven implementation.
**Supersedes:** nothing. **Amends:** `docs/04_ARCHITECTURE.md` §6 (folder tree) via the Phase-0 Addendum in that file; confirms ADR-001/ADR-002 remain valid.

---

## 1. Scope & Method

Read-only reconciliation of documented intent (`AGENTS.md`, `CONSTITUTION`, `02`–`10`, ADR-001/002, boundaries & mother-application specs, `AI_WORKING_STATE.md`) against the actual repository at `feature/vertical-slice-case-approval` @ `d78ffca` (synced 0/0 with origin), the external Android Studio scaffold at `C:\Users\ANAMIKA\AndroidStudioProjects\ASPIRE`, and live GitHub state (default `master`, draft PR #1, CI green run 38063351921). Findings are classified **A** (fact), **B** (recommended decision), **C** (requires lead approval). No application code, migrations, dependencies, CI, or git state were modified.

**Note on requested paths:** the prompt referenced `docs/02_DOMAIN_MODEL.md` and `docs/05_SECURITY_TRUST.md`. Neither exists; the actual authoritative files are `docs/02_USER_JOURNEYS.md` and `docs/07_SECURITY_TRUST.md`. Verified, not assumed.

---

## 2. Verdict: The Layered Modular Monolith Remains Correct

**A.** The implemented Core Platform is exactly the ADR-001 shape: a single FastAPI process with in-process layers — routers (`app/api/`), auth deps (`app/api/deps.py`), domain services (`app/services/`), deterministic engines (`app/engines/`), async SQLAlchemy models (`app/models/`), in-process asyncio event bus (`app/core/events.py`), and a `LLMService` gateway (`app/services/llm_service.py`, MOCK default). No microservice, queue, or extra infrastructure exists or is needed at current scale. **B. Keep the Layered Modular Monolith. Do not rewrite, re-platform, or extract services.** The only structural debt is cosmetic: the code lives in `app/` while `04_ARCHITECTURE.md` §6 still draws a `services/` target tree — resolved by the Phase-0 Addendum in `04_ARCHITECTURE.md` (actual layout is now the documented target; renaming code to match an old sketch would be unjustified churn).

---

## 3. Verified Architecture (Facts — Class A)

### 3.1 Component map: implemented vs missing

| Component (ADR-001 layer) | State | Evidence |
|---|---|---|
| API & Security (Layer 1) | **Implemented** (defects §5) | 12 paths in `contracts/openapi.json`; Supabase JWKS verify in `app/api/deps.py:54-108`; roles from `user_role_assignments` with validity windows (`deps.py:138-149`) |
| Ingestion & Quarantine (Layer 2) | **Schema only** | `data_conflicts` model + migration 011; zero writers/readers |
| Deterministic Engines (Layer 3) | **Implemented, uneven tests** | `app/engines/{attendance,assessment,priority,tasks,intervention}.py`; assessment-trend and intervention-engine tests shallow/absent |
| Event & Lifecycle (Layer 4) | **Partially implemented** | EventBus + commit-then-emit in case/student services; **no scheduler**, no event consumers |
| Agent Orchestration (Layer 5) | **Specification only** | No `langgraph` dependency; no `app/agents/`; `06_AGENT_SPEC.md` UNDER REVIEW |
| LLM Gateway (Layer 6) | **Implemented, unused** | `llm_service.py` LIVE/MOCK, bounded retry, schema validation; only lifespan init calls it |
| Data & Repository (Layer 7) | **Implemented and verified** | 13 migrations ↔ 21 models 1:1; JSONB/ARRAY/UUID corrections landed; DEC-01/02/03 implemented |
| Learning Workspace / RAG | **Schema only** | Migration 010 (`vector(1024)`); no ingestion, no retrieval, no quiz generation |

### 3.2 Vertical slices proven (preserve; do not redo)

Mentor plan approval (`case_service.py`, FOR UPDATE, 409 on illegal/ambiguous), student acceptance + decline (`student_action_service.py`), events `INTERVENTION_PLAN_APPROVED`/`PLAN_ACCEPTED`/`PLAN_DECLINED` (ADR-002), evidence contract (`app/services/evidence.py`, DEC-01 C-lite), institution-owned rules (migration 013, DEC-02), DB-side UUIDs (DEC-03). Tests: 169 unit passing (re-verified 11 Oct), 24 DSN-gated PG integration tests (previously run against PG 16.15; skip in CI by design).

### 3.3 Identity & authorization (matches product intent in shape)

**A.** One user → many `user_role_assignments` rows (role + `scope_entity_type/id` + `valid_from/valid_to`), `AuthContext.roles: list[UserRole]`, `require_roles(*any-of)`. Multi-hat (faculty + mentor + HOD) is **structurally supported** — this already satisfies "one person may hold multiple responsibilities" at the identity layer. Missing: scope-aware checks (course-run/batch/mentee ownership) on most read endpoints; `valid_from/valid_to` filtering exists in deps but no writer/admin UI manages assignments yet.

### 3.4 Four-client ecosystem vs repository reality

**A.** Product intent (lead, 11 Oct): Student Android, Class Teacher Android, Student website, Faculty website — all on one Core Platform. Repository reality: `apps/web` = staff-side mentor workspace prototype (live queue + approve; hardcoded students page); `apps/mobile` = 100%-mock Next.js student PWA shell (design reference only, broken PWA manifest); **no Android code in the repo**; external Compose scaffold (Home/Attendance/Assessments/Tasks/Workspace, Room, mock repositories, no network layer, not git-versioned) exists at `C:\Users\ANAMIKA\AndroidStudioProjects\ASPIRE`. **B.** Documented mapping: Student website = evolve `apps/mobile` into a live-API Next.js client; Faculty website = evolve `apps/web` into role-workspaced Mother Application; both Android apps stay external Android Studio consumers of `contracts/openapi.json` (per FROZEN `ASPIRE_APPLICATION_BOUNDARIES.md`). The existing Compose scaffold is a design/UX prototype, not a Core Platform client, and must not be treated as the Student Android deliverable until it consumes the real API.

### 3.5 Contracts, schema authority, events

**A.** `db/migrations/*.sql` = only schema authority (held by practice: no model-only drift left after the JSONB/ARRAY/UUID campaign). `contracts/openapi.json` = only API artifact, CI drift-guarded. Minimal Event Contract + catalog (`03 §8.1/8.2`) enforced through ADR-002 process. Commit-then-emit ordering proven by tests. **Gap (A):** events currently have zero consumers; the bus is a no-op fan-out until Supervisor/scheduler wiring lands.

### 3.6 Testing, CI, local dev

**A.** CI = Node job (typecheck/lint/build) + backend job (pytest, no DSN, drift check) on push/PR to `main`/`master` only; feature branches require the draft-PR trigger pattern. Integration PG tests exist, safety-guarded (`_test` database-name check, throwaway schemas), never run in CI. Local dev per OQ-A02 (native processes + Supabase CLI) — Supabase stack not yet standing (OQ-A02 blocker for browser E2E and RLS verification). `uv.lock` referenced in `04 §5` does not exist; `pyproject.toml` has `[tool.uv]` metadata but the environment is plain pip. `db/seeds/`, `evals/` do not exist.

---

## 4. Inconsistencies Found and Their Resolution

| # | Inconsistency | Resolution |
|---|---|---|
| 1 | `04 §6` target tree says `services/api`, `services/engines`, …; code is `app/api`, `app/engines`, `app/services`, `app/models`, `app/core` | **Resolved in this ADR:** actual `app/` layout is canonical; `04` gains a Phase-0 Addendum. No code move. |
| 2 | `04 §1` system map shows PWA + two web boxes, no Android clients | **Resolved in this ADR:** four-client map in the `04` addendum + boundaries doc remains the ecosystem authority. |
| 3 | Handoff note in `AI_WORKING_STATE.md` claimed `04` is "RED DRAFT"; `04` is actually FROZEN v2.0 | **Resolved:** stale note corrected in `AI_WORKING_STATE.md`. |
| 4 | `10_TASKS.md` statuses (T-001 READY, T-010 BLOCKED, …) contradict reality (everything through T-061 largely built on the feature branch); prompts predate tech reset | **Resolved:** staleness banner added; `docs/11_ROADMAP.md` is the ordering authority going forward. Historical task text preserved, not erased. |
| 5 | E-07/ARCH-03: docs say `main` canonical; live default branch is `master` | **Open — §6.1** (lead call; deferred rename already recorded). |
| 6 | `pyproject`/docs reference `uv.lock`; no lockfile exists | **Open — §6.6** (tooling decision; not blocking). |
| 7 | `assessments.py:27,32` malformed `Depends` + int-`raise status.HTTP_*` bugs in `students.py`/`tasks.py`/`assessments.py` (500s, broken auth wiring) | **Open — §6.3, P0.** Highest-risk correctness defect; first slice candidate. |
| 8 | `require_student_self_or_mentor` is a no-op stub; attendance summary lacks own-data check | **Open — §6.3** (same security slice). |
| 9 | Rule precedence (INSTITUTION before BATCH) and missing effective-date filtering contradict `10_TASKS:806` | **Open — §6.4** (held for lead since `0bb26ca`; correctly not silently fixed). |
| 10 | `06_AGENT_SPEC` evidence object vs engine `list[str]` vs persisted entries | **Resolved** by DEC-01 (C-lite, implemented); producer integration pending in agent slice. |
| 11 | Dead duplicate auth module `app/security/auth.py` (unused, latent bug) | **Open — §6.3** (delete in security slice). |
| 12 | Android scaffold outside git; unversioned | **Open — §6.7** (recommend initializing a repo; lead decision on hosting). |
| 13 | CONSTITUTION still UNDER REVIEW (sign-offs pending) | **Open — §6.8** (process, not technical). |

---

## 5. What Must Be Preserved (do-not-touch list)

1. The vertical-slice lineage `cb300da → d78ffca` and its tests (26 commits, CI-green at HEAD).
2. FOR UPDATE locking, plan-selection rules (never `scalar_one_or_none` on plan history), server-side DM-SS03 queue sort, commit-then-emit ordering, `AuditLog.id` server_default, JSONB/ARRAY ORM types with sqlite variants, `none_as_null=True`, migration 013, evidence conversion boundary.
3. Untracked `.opencode/` and `EduGen_AI_ASPIRE_Master_Product_Engineering_Book_v1.0.docx` (kept out of commits by convention).
4. Frozen decisions: ADR-001, ADR-002, APP-BOUND-01, DM-NEW-ORM01, DM-API01, DM-LLM01, DM-AG03, DM-SS02/03, DM-ASSESS01, DM-NEW-LATE01, DEC-01/02/03.

---

## 6. Decisions Awaiting Team-Lead Approval (Class C)

Each: options → recommendation → urgency → blocks development?

### 6.1 Default branch & PR integration
- **Options:** (a) rename `master`→`main` now, update CI triggers, merge PR #1 to `main`; (b) keep `master`, drop `main` language from docs; (c) defer rename, leave PR #1 open as standing CI trigger.
- **Recommendation:** (c) short-term — zero risk, current pattern works; schedule (a) at repository finalization as ARCH-03 already states.
- **Urgency:** Low. **Blocks:** no.

### 6.2 Next vertical slice selection
- **Options (from `AI_WORKING_STATE`):** agent proposal production; Supervisor wiring; scheduler; queue-page attendance/live data; plan follow-on consumers. Plus this reconciliation's P0 candidate: security/correctness hardening (§6.3).
- **Recommendation:** security/correctness slice FIRST (smallest, unblocks safe multi-role work), then Supervisor event wiring (first agent slice, no LLM calls needed beyond MOCK).
- **Urgency:** High — blocks all further feature slices conceptually. **Blocks:** yes.

### 6.3 P0 security/correctness defects (scope of recommended first slice)
- **Scope:** fix malformed `Depends` + int-raises (`assessments.py`, `students.py`, `tasks.py`); implement `require_student_self_or_mentor` ownership check; own-data check on attendance summary; delete dead `app/security/auth.py`; regression tests per fix.
- **Recommendation:** approve as-is.
- **Urgency:** High. **Blocks:** safe exposure of those endpoints; yes for anything touching student data.

### 6.4 Institution-rule precedence & effective dating
- **Options:** (a) BATCH override wins over INSTITUTION default, both filtered by `effective_from/effective_to` (matches `10_TASKS:806`); (b) INSTITUTION wins (current code); (c) leave, document current behavior.
- **Recommendation:** (a) — standard config-override semantics — but requires a documented decision + tests before code changes; do not flip silently.
- **Urgency:** Medium. **Blocks:** only the attendance-threshold consumer slice; current behavior is safe (single-rule seeds absent anyway).

### 6.5 Four-client naming & Mother Application scope
- **Fact:** boundaries doc says "Faculty Native App"; product intent says "Class Teacher Android". Same slot, different name.
- **Recommendation:** treat CT Android as the second Android client (Android Studio scope), faculty/mentor/HOD/admin all live in the Faculty website (`apps/web` Mother Application) via role workspaces; update boundaries doc wording at next docs PR by the lead.
- **Urgency:** Low. **Blocks:** no.

### 6.6 Python tooling (`uv.lock`)
- **Options:** (a) adopt uv properly and commit `uv.lock`; (b) drop uv references from docs, pin via `pyproject` only.
- **Recommendation:** (b) for now (CI uses pip and is green); revisit when a second Python consumer appears.
- **Urgency:** Low. **Blocks:** no.

### 6.7 Android scaffold stewardship
- **Recommendation:** initialize a git repo in `AndroidStudioProjects/ASPIRE` (or move under a dedicated folder) and push to a new GitHub repo before further Android work; keep it API-mock until contracts stabilize.
- **Urgency:** Low-medium (risk of losing work). **Blocks:** no.

### 6.8 Process sign-offs
- CONSTITUTION FINAL FREEZE (pending Abhijit/Bishesh), Stitch screens 17–20 review (only Screen 03 approved), OQ-SS01 (`ATTENDANCE_WATCH` margin), OQ-AG01 (production LLM model via evaluation), OQ-05/07/08 (BCCREC data contact, MAR rules, roll format).
- **Blocks:** respective features only (attendance watch band, live LLM, ingestion validation, MAR display).

---

## 7. Target Architecture Flow (four clients + Core Platform)

```
Student Android ─┐                     ┌─ Class Teacher Android
(Student Web)    │   HTTPS + Supabase  │  (CT Web later)
(Faculty Web ────┼──► JWT ──► FastAPI Core Platform ──► PostgreSQL+pgvector
 Mother App)     │                    │    │
                 │                    │    ├─ Auth deps (JWKS + user_role_assignments, scoped)
                 │                    │    ├─ Domain services (state machines, audit, emit-after-commit)
                 │                    │    ├─ Deterministic engines (attendance/assessment/priority/tasks)
                 │                    │    ├─ Event bus (+ future 5-min scheduler → events only)
                 │                    │    ├─ Agent orchestrator (LangGraph, later) → LLMService → OpenRouter
                 │                    │    └─ Repositories (SQLAlchemy async)
                 └────────────────────┘
All clients: presentation only; contracts/openapi.json is the sole integration surface; zero business logic client-side.
```

AuthZ model (unchanged, confirmed): JWT establishes identity only; roles from `user_role_assignments` (multi-role, scoped, time-boxed); every protected operation = identity + role + explicit row/scope filter + audit where required.

---

## 8. Consequences

- One consistent source of truth: `04_ARCHITECTURE.md` (+this addendum) for structure, `11_ROADMAP.md` for ordering, `AI_WORKING_STATE.md` for session handoff, this ADR for the reconciliation baseline.
- `10_TASKS.md` becomes historical reference; no status edits retro-applied (banner only).
- No code, schema, or CI changes result from this ADR.
