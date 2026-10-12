# 11_ROADMAP.md — Core Platform Completion Checklist & Implementation Roadmap
# `docs/11_ROADMAP.md`

**STATUS: 🟡 PROPOSED — ordering authority pending team-lead ratification (see ADR-003 §6.2)**
**Author:** OpenCode (Phase-0 reconciliation, 11 October 2026)
**Replaces for ordering purposes:** `docs/10_TASKS.md` (historical; statuses stale — see banner there).
**Basis:** ADR-001/002/003; actual state at `feature/vertical-slice-case-approval` @ `d78ffca`.

> Effort: **S** ≤ 0.5 day · **M** 1–2 days · **L** 3–5 days.
> Rule: one vertical slice at a time; contract-first for new events/endpoints; a slice is DONE only when gates below pass.

---

## 1. Core Platform Completion Checklist (verifiable acceptance criteria)

### A. Security & Authorization
- [x] No route uses malformed auth dependencies; every protected route has a tested auth dependency. *(R1: `Depends(lambda…)` wrappers removed from assessments; 401 matrix tested in `tests/test_authz_r1.py`)*
- [x] `require_student_self_or_mentor` performs a real ownership check via `StudentProfile`. *(R1: student A denied on student B's data, identical 403 to nonexistent id — no existence oracle)*
- [x] Students/attendance/tasks/assessments reads enforce own-data or scoped-role rules per `07 §2` permission matrix. *(R1: own data / assigned mentee / own class / same-institution admin / assigned-run faculty; HOD denied — matrix tests per role)*
- [x] Dead auth duplicate (`app/security/auth.py`) removed; single auth path (`app/api/deps.py`). *(R1: deleted; grep evidence zero imports)*
- [x] Scope-entity checks (course-run for Faculty, batch for CT, mentee list for Mentor) implemented where the matrix requires them. *(R1: `course_runs.faculty_id` same-batch, `class_teacher_id`, `mentor_id`; admin institution chain via batch)*
- [ ] RLS verification executed against local Supabase Auth JWTs per frozen `07 §2` protocol. *(evidence: test log with real test-user JWTs — needs OQ-A02 Supabase local stack; still open)*

### B. Domain & State Machines
- [ ] All §10.2 transitions implemented in owning services with 409 illegal-transition + ambiguity refusal. *(tests per row of the table)*
- [ ] Case creation producer (Supervisor/risk path) emits catalog events only; OPEN→IN_REVIEW covered. *(R2: OPEN→IN_REVIEW implemented + tested via `app/services/case_intake.py`; producer emits **no** catalog event — none exists for case creation; adding one needs the ADR-002 process)*
- [x] Plan-creation producer persists DEC-01 evidence entries via `convert_llm_evidence`/`build_evidence_entry`. *(round-trip test)* *(R3: `app/services/plan_proposal_service.py` + `app/agents/proposal.py` — entries rebuilt via `build_evidence_entry` + backend `EvidenceProvenance` before persistence; producer round-trip + canonical fresh-read tests pass; in working tree, not yet committed)*
- [ ] Task engine endpoints (create/assign/update) exist with audit rows; OVERDUE stays derived (DM-SS02).
- [ ] Rule precedence + effective-date filtering implemented **only after** ADR-003 §6.4 decision. *(precedence + dating tests against real PG)*

### C. Events, Scheduler, Agents
- [ ] Scheduler: startup + 5-minute loop, idempotent, emits only, never mutates (DM-AG03). *(deterministic clock tests; duplicate-tick idempotency test)*
- [ ] Supervisor graph consumes catalog events, routes per `06`, uses tools = typed FastAPI calls only. *(boundary tests: no SQL, no provider calls)* *(R2 partial: consumes + routes per the frozen `06 §1` table over all 8 catalog triggers, boundary tests pass; tools are injected **service-backed callables** (`app/agents/tools.py`), not typed FastAPI self-calls — deliberate per R2 brief "no bypass of domain services"; typed-HTTP-tool ideal deferred to the LangGraph slice)*
- [ ] LLMService wired into agents; MOCK-mode E2E plan-generation test; schema-rejection test. *(pytest without network)* *(R2: LLMService wired into the attendance specialist stub; MOCK round-trip + schema-rejection + LLM-unavailable-degradation tests pass. R3: MOCK-mode E2E plan **generation + persistence** tests pass — full proposal round-trip (specialist → MOCK LLM → validation → service → plan PROPOSED + case PLAN_PROPOSED + canonical DEC-01 evidence + SYSTEM_AGENT audit row) covered in `tests/test_plan_proposal.py` + `tests/test_plan_proposal_pg.py`; in working tree, not yet committed)*
- [x] LLM audit metadata (`request_id`, `prompt_version`, `model`, `outcome`, …) persisted per `06 §5`. *(R3-audit: migration `014_llm_attempt_audit` + `05 §7` declaration + lead-approved **pre-attempt `IN_PROGRESS` lifecycle** — `SqlLLMAuditSink.begin` commits an `IN_PROGRESS` row **before** each dispatch (no dispatch without it; one row per retry), `finish` flips the same row to the terminal outcome (latency/real tokens) after the attempt; fail-closed at both ends via `LLMAuditError` (`AUDIT_PERSISTENCE_FAILED` refusal / assess unavailable), no automatic retries to recover audit writes; taxonomy + failure-path regression tests in `tests/test_llm_audit.py` (initial-audit failure → provider never called; terminal failure → output never consumed + `IN_PROGRESS` row remains + retry blocked), PG round-trip + initial/terminal failure tests incl. inspectable `IN_PROGRESS` row in `tests/test_plan_proposal_pg.py`; `IN_PROGRESS` = initiated, terminal outcome not durably known (crash window documented); in working tree, not yet committed)*
- [ ] Prompt-injection defense tests per `07 §3` (untrusted document content cannot alter tool args). *(fixture suite from `08_EVALS`)*

### D. Data Ingestion & Learning Workspace
- [ ] CSV attendance ingestion with validation → conflict → quarantine → freeze semantics (`03 §11`), incl. LATE rejection (DM-NEW-LATE01). *(fixture-based engine tests + conflict path)*
- [ ] `data_conflicts` writer/resolver flow with human-resolution API + audit. *(tests incl. freeze-scope narrowing)*
- [ ] Learning workspace: document upload, chunking, BGE-M3 embeddings into `vector(1024)`, retrieval with evidence grounding, quiz generation with ≥1 retrieved chunk enforced. *(retrieval tests; zero-chunk refusal test)*
- [ ] Seed strategy defined: `db/seeds/` dev-only BCREC-shaped fixtures (no invented real rules); applied via controlled runner. *(fresh-DB bootstrap test)*

### E. Clients
- [ ] Student website (`apps/mobile`) talks to live API with real auth token; all mock data removed; PWA manifest/icons fixed. *(E2E with local Supabase stack)*
- [ ] Faculty website (`apps/web`): role workspaces (Admin/HOD/Faculty/CT/Mentor) with progressive disclosure; students list + badges live; `/settings` either built or link removed.
- [ ] Student Android (Android Studio, external): consumes `contracts/openapi.json`; auth via Supabase; no local academic math.
- [ ] Class Teacher Android (Android Studio, external): same contract; CT-scoped views only.

### F. Platform Hygiene
- [ ] Integration PG suite runs in CI (service container or self-hosted runner) — currently skipped.
- [ ] CI triggers on the canonical default branch (post any rename); feature-branch strategy documented.
- [ ] `10_TASKS.md` retired or archived after roadmap ratification; CONSTITUTION FINAL FREEZE obtained.
- [ ] Observability: structured request logging + request IDs; LLM attempt audit rows; scheduler tick logs.

---

## 2. Ordered Roadmap

| # | Slice | Effort | Risk | Depends on | Test evidence required |
|---|---|---|---|---|---|
| R1 | **P0 security/correctness hardening** (ADR-003 §6.3: broken `Depends`, int-raises, ownership stub, dead auth module) | S | Low — regression-guarded | — | New/updated router tests: 401/403 matrix incl. cross-student denial; full suite green; OpenAPI regen (4xx shape may change — document); CI run via PR |
| R2 | **Supervisor wiring on the event bus** (subscribe to existing catalog events; MOCK LLMService; create case OPEN→IN_REVIEW; route to attendance specialist stub) | M | Medium — first agent code; keep tools read-only + case-create only | R1 (auth path stable) | Agent boundary tests (no SQL/provider), MOCK round-trip, event ordering, audit row per agent run; suite + CI green | *(committed `0a5a655` on `feature/vertical-slice-case-approval`, GitHub CI run #15 green both jobs — 12 Oct 2026; +35 unit +4 PG-integration tests; case-ensure = attendance WARNING/CRITICAL only and initial urgency CRITICAL→URGENT/WARNING→ATTENTION both confirmed against 03 §6.1/§10.2 + 02 §1.1; "audit row per agent run" scoped to privileged writes only per `07 §4`; service-backed tools, not HTTP self-calls — see `AI_WORKING_STATE.md` R2 record)* |
| R3 | **Agent proposal production** (`IN_REVIEW/REPLAN_REQUIRED → PLAN_PROPOSED`; DEC-01 producer integration; plan rows with evidence entries) | M | Medium — persistence + LLM contract | R2 | Producer round-trip (persisted shape → fresh read), malformed-LLM rejection, zero-fabrication tests; OpenAPI unchanged (no new HTTP surface) or drift-regenerated | *(implemented in working tree 12 Oct 2026, `feature/vertical-slice-case-approval` at `0a5a655`; NOT committed/pushed — awaiting lead review; +41 unit +12 PG-integration tests, suite 323/0 with DSN, 283/40 no-DSN, ruff touched-files clean @ repo baseline 209, OpenAPI regen byte-identical; strict LLM schema + semantic validation in `app/agents/proposal.py`, service in `app/services/plan_proposal_service.py`, optional Supervisor hook; see `AI_WORKING_STATE.md` R3 record)* |
| R4 | **Scheduler (DM-AG03)** (startup + 5-min loop; TASK_OVERDUE / EXAM_APPROACHING / MENTOR_FOLLOWUP_DUE emission only) | M | Low-medium — idempotency critical | R2 | Clock-injected tests; duplicate-tick no-op; no business mutation assertion |
| R5 | **Remaining §10.2 transitions + follow-up consumers** (ACTIVE→MONITORING→RESOLVED/CLOSED, REPLAN consumers) | M | Medium — RULE_ENGINE actor semantics | R3, R4 | Per-row transition tests; concurrency lock test pattern reuse |
| R6 | **Student website live client** (auth flow, replace mocks, attendance/tasks/plan from API) | M | Low | R1, contract stable | Component + E2E against local Supabase (needs OQ-A02 stack standing) |
| R7 | **Queue-page live data + CRUD** (attendance display, students list, remove demo fallback) | S-M | Low | R1 | UI tests optional; API integration tests; visual demo check |
| R8 | **CSV ingestion + conflicts** (T-050 scope; `ingestion_jobs` contract gap → small ADR first) | L | High — schema gap + freeze semantics | R4 (events) | Fixture suites `08_EVALS`; conflict/quarantine paths on real PG |
| R9 | **Learning workspace + RAG + quiz** (T-070/071) | L | High — embeddings infra, injection surface | R2 (specialist tools) | Retrieval grounding, zero-chunk refusal, injection tests |
| R10 | **Rule precedence/effective dating** (only after §6.4 decision) | S-M | Low | Lead decision | Precedence + dating tests on real PG |
| R11 | **Faculty workspaces (Mother App expansion)** | L | Medium | R1, role-scoping done | Per-role route access tests |
| R12 | **Android student client** (external repo; contract-driven) | L | Medium | R6 patterns + stable contracts | Contract conformance tests; no local math (code review gate) |
| R13 | **Android CT client** (external) | L | Medium | R12 template | Same as R12, CT scoping |
| R14 | **CI integration-PG job + observability** (can pull earlier if concurrency/JSONB confidence drops) | M | Low | — (parallelizable after R1) | CI log evidence of integration run |
| R15 | **Repository finalization** (branch rename per ARCH-03, PR #1 disposition, `10_TASKS` archive, CONSTITUTION freeze) | S | Low | Lead approval §6.1/6.8 | CI green on renamed default branch |

**Parallelization note:** R12/R13 (Android, external) may proceed in Android Studio once contracts for their screens are stable (after R6/R11 surfaces), independent of R8–R11. No other parallel dependent tracks — per one-slice-at-a-time rule.

---

## 3. Recommended first slice after lead approval

**R1 — P0 security/correctness hardening** (S, lowest risk, unblocks everything) — ✅ **DONE; committed as `94cd568` on `feature/vertical-slice-case-approval`, GitHub CI run #14 green on that SHA (11 Oct 2026);** implementation record in `docs/AI_WORKING_STATE.md`:

- Files: `app/api/routers/assessments.py`, `app/api/routers/students.py`, `app/api/routers/tasks.py`, `app/api/routers/attendance.py` (own-data check), `app/api/deps.py` (implement ownership helper), delete `app/security/auth.py`, tests in `tests/test_api_routers.py` (+ new focused files if needed).
- Acceptance: all §1.A checklist items for the touched routes; suite green ±DSN; OpenAPI regenerated if response shapes change; ruff per-file ≤ baseline; CI green via draft-PR pattern; `AI_WORKING_STATE.md` updated.
- Rollback: single revert commit; no schema, contract-breaking, or event changes intended (4xx corrections are bug-fix contract changes — call out in regen notes).
