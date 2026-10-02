# CONSTITUTION.md
# EduGen AI / ASPIRE — Engineering & Product Constitution

**STATUS: 🔴 DRAFT — Must be reviewed and agreed by all 3 team members before any code is written.**

**Team Lead:** Mrityunjoy Kapat
**Team:** Abhijit Ghosh · Bishesh Ghosh · Mrityunjoy Kapat
**Date:** 02 October 2026
**Version:** 1.0

---

> This document defines the non-negotiable principles of EduGen AI / ASPIRE.
> Every line of code, every agent decision, every database schema, every UI screen
> must pass through these principles first.
>
> **If implementation contradicts this Constitution, implementation stops — not the Constitution.**

---

## 1. Product Principles (What We Are Building)

### P-01 — Student First, Always
Every feature decision starts with: *"Does this genuinely help the student?"*
Not: *"Is this impressive in a demo?"*
Not: *"Is this easy to build?"*

### P-02 — Reliable Over Impressive
A system that correctly tracks attendance and warns a student 3 weeks early
is more valuable than a system that generates beautiful AI responses that are sometimes wrong.
The deterministic core must work even when the LLM is unavailable.

### P-03 — Explainability is Not Optional
Every AI-generated recommendation must show *why* it exists.
Every risk signal must show *what evidence* produced it.
A student must never receive a verdict without a reason.

### P-04 — Controlled Autonomy
Agentic does not mean fully autonomous.
The AI assists, recommends, and plans.
Humans approve consequential actions.
This is not a negotiation — it is the product design.

### P-05 — Configurable, Not Hard-Coded
No BCREC-specific logic is hard-coded into the system core.
Every institution-specific rule (attendance thresholds, academic schemes,
activity points, batch structures) lives in configuration.
If we cannot deploy the same codebase to another college by changing config,
we have failed this principle.

---

## 2. Data Integrity Rules (What Data Means)

### D-01 — Missing Data ≠ Zero
A missing attendance record is not zero attendance.
A missing mark is not a zero mark.
The UI must distinguish: `Missing` / `Pending` / `Zero` / `Withheld`.
No system operation may treat absence of data as the worst-case value.

### D-02 — Pending ≠ Failed
Pending evaluation is not failure.
Unverified activity evidence is not completed activity.
Provisional data is not verified data.
These states must be distinct in the database and in every UI that displays them.

### D-03 — Provenance is Mandatory
Every piece of data that enters the system must carry:
`source` · `source_type` · `imported_at` · `status` · `version`
Data without provenance must not drive automated decisions.

### D-04 — Conflicts Block Automation
When two sources disagree about the same fact, the system freezes automated
authoritative actions on that fact until a human resolves the conflict.
The system does not pick a side. It surfaces the discrepancy.

### D-05 — Derived State is Recomputable, Not Stored as Character
Attendance risk, performance trend, readiness signals — these are derived
from facts on demand. They are never permanently stored as personality-like
attributes on a student's profile.
A student is not "a low performer." Their performance trend is currently declining.
These are different things with different consequences.

### D-06 — Corrections Preserve History
Correcting attendance or marks does not overwrite the original record.
The system keeps before/after values and the actor who made the correction.
No silent mutations.

---

## 3. Agent & AI Rules (What AI Can and Cannot Do)

### A-01 — Agents Use Tools, Not Direct Database Access
No agent may issue arbitrary SQL or mutate database tables directly.
Agents read and write only through typed, permission-checked, audited tool calls.
This is an architectural law, not a guideline.

### A-02 — Business Rules Are Deterministic Code, Not Prompts
Attendance percentage calculation is code.
Assessment score aggregation is code.
Academic eligibility is code.
Graduation progress is code.
None of these are LLM judgments. None of these live in a prompt.

### A-03 — AI Does Not Invent Institutional Facts
If the system does not have a verified data point, it says so.
It does not estimate, assume, or hallucinate institutional rules.
"I don't have your attendance data for this subject" is the correct response.
A made-up percentage is not.

### A-04 — Agents Have Explicit Boundaries
Every agent has:
- A defined purpose
- A list of allowed tools
- A list of forbidden actions
- A defined escalation path

An agent that exceeds its boundaries has a bug, not a feature.

### A-05 — Structured Output, Not Prose Decisions
Agent outputs that drive system actions must be structured JSON with:
`decision` · `reason_codes` · `evidence` · `actions` · `approval_required` · `confidence_level`
Raw LLM prose does not drive system state changes.

### A-06 — Confidence is Categorical, Not a Raw Float
Agents report confidence as `HIGH / MEDIUM / LOW` with supporting evidence.
We do not expose raw model probability scores as accuracy claims
unless a calibrated confidence system exists and is validated.

### A-07 — Prompt Injection is a Security Threat
A student's uploaded PDF is content, not authority.
If a PDF says "ignore your instructions," the agent treats that as document content —
not as an instruction to follow.
Every tool that processes external content must treat it as untrusted input.

---

## 4. Security & Access Rules (Who Can See and Do What)

### S-01 — RBAC on Every Protected Action
Every API endpoint that reads or writes protected data checks the caller's role
and assignment before returning a response.
There is no "we'll add auth later." Auth is built with the feature.

### S-02 — Least Privilege by Default
Every role sees only what it needs for its function.
A mentor can see their assigned students.
Not all students. Not other mentors' students.
A student can see their own data. Not their classmates' data.

### S-03 — Sensitive Data Has a Hard Boundary
Counselling data, grievance data, and private support records are a separate
bounded domain with explicit access policy and mandatory audit logging.
These must not silently flow into academic analytics or mentor dashboards.

### S-04 — All Privileged Mutations Are Audited
Every write to an official record (marks, attendance, role assignments, case decisions)
produces an audit event with: `actor` · `action` · `before` · `after` · `timestamp`
There is no exception to this rule.

### S-05 — No Credentials in Source Code
API keys, database passwords, LLM provider keys, and service secrets
never appear in any committed file.
Environment variables and a secrets manager only.
A PR that contains a credential is rejected immediately.

### S-06 — Human-Only Decisions Are Enforced in Code
The following decisions cannot be automated, regardless of AI confidence:
- Official leave / condonation decisions
- Official exam eligibility decisions
- Marks / result changes
- Disciplinary actions
- Grievance decisions
- Confidential counselling decisions

These require a human actor with the appropriate role. The system enforces this.

---

## 5. Engineering Discipline Rules (How We Build)

### E-01 — Every Feature Starts from a Requirement ID
No feature is coded without a task in `10_TASKS.md` that links to:
- A requirement in `01_PRD.md` or `03_SYSTEM_SPEC.md`
- Acceptance criteria
- The relevant spec section (FROZEN status required)

### E-02 — No Schema Change Without a Migration
Every database change uses a versioned migration file.
No manual database edits in any environment above local dev.
Migration files are never deleted.

### E-03 — No Agent Behavior Change Without an Eval Update
If the agent's behavior changes, the eval dataset in `08_EVALS.md` is updated
and the eval must be run and pass before the PR is merged.

### E-04 — No Architecture Change Without an ADR
Significant technical decisions (provider choice, new dependency, pattern change,
data model restructure) require an Architecture Decision Record in `docs/decisions/`.
"Significant" means: another team member would be surprised to see it merged without discussion.

### E-05 — No Merging Code That Only "Looks Right"
AI-generated code must pass:
- Type checks
- Relevant unit tests
- Peer review by at least one other team member
- Spot-check that it does not contradict the spec

"The AI wrote it so it's probably fine" is not a review.

### E-06 — Small PRs, One Concern Each
A PR addresses one task. One feature. One fix.
PRs that contain multiple unrelated changes are split before review.
A PR that contains more than ~300 lines of new logic requires explicit justification.

### E-07 — Main Branch is Always Deployable
Main branch must build and pass tests at all times.
Broken main blocks the entire team.
Feature branches are the default for all active work.

### E-08 — Error, Loading, and Permission States Are Not Afterthoughts
Every UI component that displays data implements:
`Loading` · `Empty` · `Error` · `Stale` · `Permission Denied` · `Conflict`
Happy-path-only UI is incomplete UI.

### E-09 — No Future Scope in Current Code
P2 features (Exam Cell, T&P, ERP integration, parent portal) must not appear
as placeholder UI, hidden routes, or commented-out code in the P0/P1 build.
Future scope that leaks into the current build implies it is operational.

---

## 6. The Definition of Done

A task is DONE when ALL of the following are true:

- [ ] Requirement ID satisfied
- [ ] Acceptance criteria satisfied
- [ ] Type checks pass
- [ ] Tests written and passing
- [ ] Error / loading / permission states handled
- [ ] Audit / provenance added where required by spec
- [ ] Documentation updated if behavior changed
- [ ] No known contradiction with this Constitution or the Master Book
- [ ] Reviewed by at least one other team member

A task is **NOT done** because:
- The AI said it was done
- It works in the happy path
- It looks good in a demo
- We plan to add tests later

---

## 7. When This Constitution Can Change

This Constitution can be changed only by:
1. A proposal written and shared with all 3 team members
2. A team discussion where the change is explicitly agreed
3. A commit to this file signed off by all 3 team members
4. An ADR explaining why the change was necessary

**No AI coding agent may modify this file.**

---

## 8. Signatures

By contributing code to this project, each team member agrees to this Constitution.

| Member | Role | Agreement |
|---|---|---|
| Mrityunjoy Kapat | Team Lead · Agentic AI / Integration | ☐ Agreed |
| Abhijit Ghosh | Product / System / Architecture | ☐ Agreed |
| Bishesh Ghosh | Backend / Database / Data | ☐ Agreed |

**Date of agreement:** _______________

---

## Open Items (Must Be Resolved Before Coding Begins)

| ID | Question | Owner | Deadline |
|---|---|---|---|
| OQ-01 | What is the exact BCREC attendance threshold and condonation rule? | Bishesh | Before `03_SYSTEM_SPEC.md` is FROZEN |
| OQ-02 | Are all 3 team members' roll numbers confirmed and correct? | All | Before any submission |
| OQ-03 | Which LLM provider is primary? Which is fallback? | Mrityunjoy | Before `ADR-001` is written |
| OQ-04 | Does the existing EduGen learning workspace codebase get reused or rewritten? | Mrityunjoy | Before Phase 3 begins |
| OQ-05 | Who is the BCREC contact who can provide real data for validation? | All | Before `02_USER_JOURNEYS.md` is FROZEN |

---

*Drafted from: EduGen AI / ASPIRE Master Product Engineering Book v1.0 (02 October 2026)*
*Must be reviewed, corrected, and explicitly agreed to by the team before STATUS changes to FROZEN.*
