# ASPIRE — Antigravity Onboarding Prompt for Abhijit Ghosh
# Copy this entire prompt and paste it into your Antigravity chat.

---

## Paste this into Antigravity:

Hey Antigravity. I am Abhijit Ghosh, one of three developers on the ASPIRE project. I need you to read the project docs and help me with my review task.

**My role:** Product, System Architecture, Web UX. I own the `apps/web/` folder.

**The project:** ASPIRE (EduGen AI) is a student-first academic intelligence platform being built for Dr. B. C. Roy Engineering College (BCREC). It has a 7-month deadline to a working P0 demo. The team lead is Mrityunjoy Kapat.

**Current phase:** We are in the pre-coding spec phase. NO APPLICATION CODE IS WRITTEN YET. Before any code is written, every relevant spec must be marked STATUS: FROZEN. Read the AGENTS.md file in the root of the repository — those rules govern everything you do on this project.

**The repository is at:** `c:\Users\[YOUR_USERNAME]\DEV\ASPIRE` (clone from https://github.com/Mrityunjoy240/ASPIRE.git if you haven't already)

---

**YOUR TASK RIGHT NOW — Do these in order:**

**Step 1: Read these files completely before doing anything else:**
1. `AGENTS.md` (root) — the rules you must follow. Non-negotiable.
2. `docs/CONSTITUTION.md` — founding engineering principles. Read every section.
3. `docs/01_PRD.md` — what we are building, P0 vs P1 scope, demo story.
4. `docs/02_USER_JOURNEYS.md` — the exact step-by-step user flows.

**Step 2: Review this document and give me feedback:**
- `docs/04_ARCHITECTURE.md` — This is YOUR primary review document.

**For 04_ARCHITECTURE.md, tell me:**
1. Does the system map in Section 1 match your mental model of how Next.js + FastAPI + Supabase should connect?
2. Section 8 has 3 open questions (OQ-A01, OQ-A02, OQ-A03). I need your answers to all 3:
   - OQ-A01: Should the API and Agents run as a single FastAPI process in v1, or separate services?
   - OQ-A02: What is the local dev setup? Docker Compose for everything, or each service independently?
   - OQ-A03: Shared `packages/schemas/` — TypeScript Zod schemas only, or Python Pydantic models too?
3. Is the folder structure in Section 6 correct for how you want to structure `apps/web/`?
4. Is there anything architecturally wrong or missing?

**Step 3: Review the design direction**
- Read `docs/01_PRD.md` Section 8 (the Demo Story — Student S-204).
- The UI/UX direction is: **Student mobile app = Notion-inspired (calm, clean, whitespace)**. **Mentor/Staff web = Linear-inspired (dark, dense, operational)**.
- If you have a different opinion on the design direction, say so now before anyone builds anything.

---

**What you must NOT do:**
- Do not write any application code
- Do not create any files outside `docs/` at this stage
- Do not make architectural decisions without discussing with Mrityunjoy first

**When you are done with your review, write a summary of:**
1. Your answers to OQ-A01, OQ-A02, OQ-A03
2. Any corrections needed to `04_ARCHITECTURE.md`
3. Your opinion on the UI/UX direction

Send that summary back to Mrityunjoy on WhatsApp/chat so he can update the docs.
