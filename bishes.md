# Instructions for Bishesh & Coding Agent
# `bishes.md` — ASPIRE Handover & Workspace Guide

> **To Bishesh's AI Coding Agent (Cursor, Windsurf, Claude Code, OpenCode, etc.):**
> Read this document first, then immediately read:
> 1. [`AGENTS.md`](./AGENTS.md) — Non-negotiable architectural rules and system invariants.
> 2. [`DESIGN.md`](./DESIGN.md) — Linear-inspired UI design system, colors, tokens, and density rules.
> 3. [`docs/ASPIRE_MOTHER_APPLICATION_SPECIFICATION.md`](./docs/ASPIRE_MOTHER_APPLICATION_SPECIFICATION.md) — Mother Application role specifications (Faculty, Mentor, HOD, Admin).
> 4. [`docs/05_DATA_API_CONTRACTS.md`](./docs/05_DATA_API_CONTRACTS.md) — Database schema (108 BCREC entities in `db/institutional/` + ASPIRE case tables).
> 5. [`docs/AI_WORKING_STATE.md`](./docs/AI_WORKING_STATE.md) — Up-to-date execution state and completed tasks.

---

## 1. Quick Repository Setup

```bash
# 1. Clone the repository
git clone https://github.com/Mrityunjoy240/ASPIRE.git
cd ASPIRE

# 2. Check out the active feature branch
git checkout feature/vertical-slice-case-approval
git pull origin feature/vertical-slice-case-approval

# 3. Install Web dependencies
cd apps/web
npm install

# 4. Start the Web Dev Server (Faculty / Mother Application)
npm run dev
# The Mother Application runs on http://localhost:3000

# 5. (Optional) Run the FastAPI Core Backend from project root in a second terminal
cd ../..
python -m venv venv
# On Windows: .\venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

---

## 2. What is ASPIRE? (Mental Model)

ASPIRE is **ONE unified Student Success Intelligence Platform** for colleges (reference institution: B.C. Roy Engineering College - BCREC, Durgapur).

The autonomous cycle is:
```
OBSERVE → UNDERSTAND → DETECT → PLAN → ASSIST → VERIFY → REPLAN → ESCALATE
```

### Monorepo Structure & Ecosystem Roles:
- **`apps/web/` (YOUR WORKSPACE)**: The **ASPIRE Mother Application** — High-density, Linear-style operational control web app for **Faculty / Class Teachers, Academic Mentors, HODs, and Institution Admins**.
- **`apps/mobile/` (MRITYUNJOY'S WORKSPACE)**: The **Student Web App & PWA** — For students to track attendance, use the "What-If" recovery calculator, view approved 14-day study plans, and take remedial quizzes.
- **`db/institutional/`**: Production BCREC college database (108 entities covering IAM, Governance, Courses, Faculty, Attendance sessions, Marks, and Exams).
- **`db/migrations/`**: ASPIRE Core intelligence and intervention case tables.
- **`contracts/openapi.json`**: Authoritative REST API contracts consumed by all web and Android clients.

---

## 3. What is Already Built & Working in `apps/web/`

The Mother Application in `apps/web/` is fully functional, styled with Linear-inspired dark theme and mid-density scale:

1. **Global Linear UI Layout**:
   - Deep canvas (`#08090A`), card panels (`#0D0E10` / `#141517`), hairline borders (`border-white/[0.08]`), and Linear purple (`#5E6AD2`).
   - Sizing: Balanced mid-density (buttons `h-8` 32px, text 13px, badges 11px font-mono).
   - Global Command Palette (`Cmd+K` / `Ctrl+K`) for instant navigation and student lookup.
2. **Command Center (`/`)**: High-level institutional vitals, risk distribution, urgent action alert banners.
3. **Priority Triage Queue (`/queue`)**: DM-SS03 sorting (`Urgency Band → Exam Proximity → Days Since Action`) with quick-approve modal for mentor review.
4. **Student Success Inspector (`/students/[id]`)**: Full 360° student diagnostic view, attendance trend history, SGPA prediction, and slide-over intervention drawer with plan approval/rejection.
5. **Student Directory (`/students`)**: Roster search and filtering by risk band, department, semester.
6. **Risk Analytics (`/analytics`)**: Risk matrices, attendance distributions, and recovery velocity.
7. **Institutional Rules Editor (`/admin/institutions`)**: Dynamic thresholds (75% mandatory attendance, 65% condonation, rule weights).

---

## 4. Bishesh's Assignment: Faculty & Mentor Workspaces

Your primary focus is **Faculty / Class Teacher and Academic Mentor operational workflows** in `apps/web/`:

### Task 1: Faculty / Class Teacher Workspace (`/faculty/attendance` or `/classes`)
Class teachers are the daily source of truth. Build the screens/components where teachers interact with their assigned sections:
- **My Courses / Sections View**:
  - Show the faculty member's active course runs (e.g., `CS501 Operating Systems — 3rd Year Sec A`).
  - Student count, conducted lectures count, section attendance average.
- **Batch Attendance Grid**:
  - Grid/list of enrolled students with roll numbers, names, and one-click toggle: `Present` / `Absent` / `Late` / `Excused`.
  - Quick action: "Mark All Present", "Save & Sync to Core".
  - Live feedback showing if marking a student absent drops them below the 75% institutional threshold.
- **Continuous Assessment (CA) Entry**:
  - Tab or drawer to record CA1 (out of 25), CA2 (out of 25), and Lab assignment marks.

### Task 2: Data Discrepancy & Conflict Quarantine Resolver (`/faculty/conflicts`)
- As specified in Constitution Rule D-04: If biometric attendance logs a student absent, but class teacher marked them present (or vice-versa), the record enters quarantine.
- Provide a side-by-side discrepancy resolver so the teacher/mentor can confirm the verified record with provenance reason.

### Task 3: Mentor "My Mentees" & 1-on-1 Session Logger
- In `/queue` or `/students`, add a prominent toggle: **"All Students" vs. "My Mentees"** (filtering down to the mentor's assigned 15–25 students).
- In the Student Inspector (`/students/[id]`), add a **"Log Mentoring Meeting"** modal:
  - Date & duration.
  - Discussion summary & root cause category (health, academic, financial, personal).
  - Action items & scheduled follow-up date.

---

## 5. Non-Negotiable Coding Rules (Must Follow)

1. **Follow the Design System (`DESIGN.md`)**:
   - Use Tailwind CSS classes matching existing components in `apps/web/app/components/ui/`.
   - Use `Button.tsx`, `Card.tsx`, `StatusBadge.tsx` for consistent typography and sizes.
   - Dark theme only: background `#08090A`, card `#0D0E10`, border `border-white/[0.08]`.
2. **Engines Calculate. Agents Propose. Humans Approve Consequential Decisions**:
   - The UI must NEVER calculate attendance percentages or predict grades in client-side code. It must render backend/engine derived states or call FastAPI endpoints.
   - Highlight semantic truth badges: `VERIFIED` (institutional data), `DERIVED` (engine math), `PROPOSED` (agent suggestion).
3. **Verify Before Committing**:
   - Run `npx tsc --noEmit` and `npm run build` inside `apps/web` to ensure zero compilation or TypeScript errors.
   - Never push directly to `main`. Commit to your feature branch and push to GitHub.

---

## 6. Communication & Coordination

- **Student App Owner**: Mrityunjoy (`apps/mobile/`) is building the Student Web Experience (What-If calculator, approved plan execution, remedial quizzes).
- **Branch**: Keep working on `feature/vertical-slice-case-approval` (or create a sub-branch like `feature/faculty-attendance-workspace` branching from it).
- **If Unsure**: Ask Mrityunjoy before changing database schemas or introducing new global UI paradigms.
