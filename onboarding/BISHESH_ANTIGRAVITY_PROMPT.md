# ASPIRE — Antigravity Onboarding Prompt for Bishesh Ghosh
# Copy this entire prompt and paste it into your Antigravity chat.

---

## Paste this into Antigravity:

Hey Antigravity. I am Bishesh Ghosh, one of three developers on the ASPIRE project. I need you to read the project docs and help me with my review task.

**My role:** Backend, Database, Data Ingestion, API. I own `services/api/`, `services/engines/`, `services/ingestion/`, and `db/migrations/`.

**The project:** ASPIRE (EduGen AI) is a student-first academic intelligence platform being built for Dr. B. C. Roy Engineering College (BCREC). It has a 7-month deadline to a working P0 demo. The team lead is Mrityunjoy Kapat.

**Current phase:** We are in the pre-coding spec phase. NO APPLICATION CODE IS WRITTEN YET. Before any code is written, every relevant spec must be marked STATUS: FROZEN. Read the AGENTS.md file in the root of the repository — those rules govern everything you do on this project.

**The repository is at:** `c:\Users\[YOUR_USERNAME]\DEV\ASPIRE` (clone from https://github.com/Mrityunjoy240/ASPIRE.git if you haven't already)

---

**YOUR TASK RIGHT NOW — Do these in order:**

**Step 1: Read these files completely before doing anything else:**
1. `AGENTS.md` (root) — the rules you must follow. Non-negotiable.
2. `docs/CONSTITUTION.md` — founding engineering principles. Read every section.
3. `docs/01_PRD.md` — what we are building, P0 vs P1 scope.
4. `docs/03_SYSTEM_SPEC.md` — the deterministic engines YOU will implement.
5. `docs/02_USER_JOURNEYS.md` — specifically Journey 5.1 (Data Ingestion) which you own.

**Step 2: Review this document and give me detailed feedback:**
- `docs/05_DATA_API_CONTRACTS.md` — This is YOUR primary review document.

**For 05_DATA_API_CONTRACTS.md, tell me:**

1. **Section 6 (Assessment Tables) is marked [PENDING OQ-06].** This is blocked on you. I need you to find out from the BCREC academic regulations:
   - What are the exact CIA component names for autonomous batches? (e.g., CIA-1, CIA-2, Lab Record, Assignment, Viva?)
   - What is the maximum marks and weightage for each component?
   - Are the components the same across all subjects, or subject-specific?

2. **Section 5 (Attendance Tables):** The `attendance_derived_state` table is written only by the Attendance Rule Engine, never by an agent or API call directly. Do you agree with this separation? Any technical problem you foresee?

3. **Section 11 (Data Conflict Registry):** This is where your ingestion pipeline logs conflicts. Does the schema match how you expect to handle a CSV import that conflicts with existing data?

4. **Section 12 (Institution Configuration):** The `institution_rules` table stores all academic thresholds. Does the schema support what you need for the rule engine queries?

5. **Section 13 (Internal API Boundary Rules):** Check the permission table. Are there any API routes that are missing or incorrectly permissioned?

6. **General:** Are there any tables missing that you would need for the P0 implementation? Are any column types wrong (e.g., should something be `TEXT` instead of `UUID`)?

**Step 3: The Roll Number question (OQ-08)**
- What is the exact format of a student roll number at BCREC? (e.g., `120308244001` — is this `YEAR + DEPT_CODE + BATCH + SEQUENCE`?)
- This affects the import validation and the student profile table.

---

**Key technical rules you must enforce when you eventually write code:**

1. **No agent writes SQL directly.** All agent actions go through typed FastAPI endpoints.
2. **The Attendance Engine and Assessment Engine are pure Python functions** — no I/O, no database calls inside the engine. They receive data, compute, return results. The API layer calls them and writes the results.
3. **Every privileged write produces an `audit_log` row.** This is non-negotiable.
4. **Soft deletes only.** No `DELETE` in any production table.
5. **BCREC configuration values (75% threshold, 65% condonation) live in `institution_rules` table, never hardcoded.**

---

**What you must NOT do:**
- Do not write any application code or migrations yet
- Do not create any new tables not in `05_DATA_API_CONTRACTS.md` without discussing with Mrityunjoy
- Do not touch `db/migrations/` yet — nothing is FROZEN

**When you are done with your review, write a summary of:**
1. Your answers to OQ-06 (CIA/PCIA component structure and weights)
2. Your answers to OQ-08 (Roll number format)
3. Any corrections or missing items in `05_DATA_API_CONTRACTS.md`
4. Any questions or blockers

Send that summary back to Mrityunjoy on WhatsApp/chat so he can update the docs before we start coding.
