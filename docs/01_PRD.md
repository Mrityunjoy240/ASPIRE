# 01_PRD.md
# EduGen AI / ASPIRE — Product Requirements Document

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Source:** Master Product Engineering Book v1.0 + Constitution review decisions
**Date:** 02 October 2026
**Version:** 1.0

---

## 1. The Problem We Are Solving

### 1.1 What is actually broken at BCREC (and colleges like it)?

A student at BCREC is simultaneously managing:
- 6–8 subjects with separate attendance requirements
- CIA/PCIA components across those subjects with different deadlines
- Lab records, assignments, and project milestones
- Academic calendar events, exam schedules, and routine changes
- A mentor who has 4–10 mentees and no prioritized workload view
- Notices published on a website that may or may not be checked
- Career goals with no structured roadmap
- Co-curricular activity requirements they may not fully understand

**The result:**
- A student with 73% attendance in one subject doesn't know they're 2 classes away from being ineligible for ESE — until it's too late.
- A mentor gets a list of 10 students with no indication of who needs attention most, or why.
- Faculty spend time on administrative tasks that could be automated without sacrificing accuracy.
- Students don't know which topic to study next, so they study randomly.
- Warnings come from humans reactively — not from a system proactively.

**The root cause is not data shortage. It is fragmentation.**
Attendance is in one place. Marks in another. Notices on a website. No single system
connects them, derives meaning from the combination, and proactively acts.

### 1.2 What we are NOT claiming to solve
- We are not fixing BCREC's internal administration.
- We are not replacing ERP/EMS systems.
- We are not replacing faculty judgment.
- We are not automating disciplinary or counselling decisions.
- We are not building a placement/exam cell system.

---

## 2. Product Identity

| Field | Value |
|---|---|
| Product name | **EduGen AI** |
| System name | **ASPIRE** |
| Full name | An Agentic Student Progress, Intelligence and Resource Engine for Higher Education |
| Version | 1.0 baseline |
| Reference institution | Dr. B. C. Roy Engineering College (BCREC), Durgapur |
| Deployment model | BCREC-first. Institution-configurable architecture. Not multi-tenant SaaS in v1. |
| Primary channel | Mobile (student). Web (student + all staff roles). |

---

## 3. Users

### 3.1 Primary User — Student

**Who:** B.Tech students at BCREC (initially).
**Device:** Mobile-first. Web supported.
**Pain:** Fragmented academic information. Reactive warnings. No guided next step.
**What they need from ASPIRE:**
- "Where do I stand right now, across all subjects?"
- "What is urgent and what happens if I ignore it?"
- "What should I do next, and why?"
- "Help me understand this topic."
- "Track my project/internship/activities."

**What they must NOT experience:**
- Being told a zero when data is missing.
- Receiving authoritative instructions based on low-confidence parsed data.
- Feeling surveilled without any benefit.
- Getting spammed with low-priority notifications.

---

### 3.2 Supporting Users

**Subject Faculty**
- Owns course-level academic operations.
- Enters/corrects attendance and assessment data.
- Publishes materials and proposed notices.
- Sees subject-level analytics for their course only.

**Class Teacher (CT)**
- Owns class-wide operations across subjects.
- Views class attendance and admin operations.
- Manages class calendar, assignments, notices within policy.

**Mentor**
- Supports assigned mentees (typically 4–10 students).
- Receives a priority queue — not a raw list.
- Approves or edits intervention plans proposed by agents.
- Escalates unresolved cases.

**HOD**
- Department-level oversight only.
- Sees aggregated trends, mentor workload, escalated cases.
- Does not have routine access to individual student confidential data.

### 3.3 System Role

**Admin**
- Configures institution rules, academic scheme, user/role mappings.
- Manages imports and integrations.
- Does not make academic judgments.

### 3.4 Future Roles (NOT in v1 — do not build)
- Exam Cell
- Training & Placement Cell
- Parent portal

---

## 4. The Core Product Promise

> A student should be able to answer, from one place:
> **"Where do I stand, what is urgent, what should I do next, why, and what happens if I don't act?"**
>
> A mentor should be able to answer:
> **"Which of my students needs attention, why, what has been tried, and what should I review?"**

**The system behavior is:**
```
Observe → Understand → Detect → Plan → Assist → Verify → Replan → Escalate
```

**This is not a chatbot.** It does not just answer questions.
It maintains state, tracks outcomes, replans on new data, and escalates when human judgment is required.

---

## 5. Scope

### 5.1 P0 — Must Ship (Core Demo Story)

These are required for a meaningful final demo and for the product to have a story.
Nothing in P1 or P2 is touched until all P0 items have a working vertical slice.

| ID | Feature | Why P0 |
|---|---|---|
| P0-01 | Student State (360 view) — attendance, marks, deadlines, enrollment, derived risk signals | Foundation of everything else |
| P0-02 | Attendance Intelligence — rule engine, what-if projection, recovery plan | Highest student pain point |
| P0-03 | Assessment tracking — CIA/PCIA components, missing/pending/zero distinction | Core academic data |
| P0-04 | Academic calendar + task generation — deadlines, events, obligations | Connects data to action |
| P0-05 | Unified obligation stream — one task list for student from all sources | Without this, students ignore the system |
| P0-06 | Learning Workspace — upload docs, source-grounded Q&A, quizzes, flashcards | Existing EduGen capability, retained |
| P0-07 | Adaptive Learning Agent — detect weak topic, build practice plan, update learning state | Differentiates from a dashboard |
| P0-08 | Supervisor + Specialist Agent loop — event → supervisor → academic/attendance agent → plan | Core agentic behavior |
| P0-09 | Mentor case management + priority queue — urgency-driven, evidence-backed, not a raw list | Proves the system benefits humans, not just students |
| P0-10 | RBAC — role checks on every protected action | Non-negotiable (see Constitution S-01) |
| P0-11 | Data provenance + audit trail — source, version, actor on every record | Non-negotiable (see Constitution D-03, S-04) |
| P0-12 | Auth — login, session management, role assignment | Table stakes |
| P0-13 | Institution configuration — attendance threshold, academic scheme, batch | Enables P-05 (configurable, not hard-coded) |
| P0-14 | CSV/Excel import pipeline — for attendance, marks, enrollment, calendar data | BCREC won't have an API; this is how data enters |
| P0-15 | Student mobile app — home, academic health, attendance, learning workspace, tasks, AI guidance | Mobile is the primary student channel |

---

### 5.2 P1 — Strongly Desired (After P0 Vertical Slice Works)

| ID | Feature | Why P1 |
|---|---|---|
| P1-01 | Notice intelligence — fetch public BCREC pages, parse, classify, version, map to audience | High value but complex NLP pipeline |
| P1-02 | Career intelligence — goals, skills, readiness signals, roadmap | High student value, builds on career features in EduGen |
| P1-03 | Project tracking — state machine, milestones, guide assignment, evidence | Important for final-year students |
| P1-04 | Internship tracking — milestones, certificate/report upload, verification | Paired with P1-03 |
| P1-05 | Activity/MAR tracking — configurable rules, evidence, verification, dedup | Needed for complete student 360 |
| P1-06 | Faculty/CT dashboards — operational views for assigned roles | Needed for real institutional adoption |
| P1-07 | HOD analytics — department aggregates, mentor workload, case outcomes | Needed to sell to institutions |
| P1-08 | Push notifications | Without this, mobile app engagement drops |
| P1-09 | Intervention Agent — full case lifecycle, replan on failure, escalation | Extends P0-08 Supervisor loop |
| P1-10 | Career Agent — roadmap tasks, skill gap identification, resource suggestions | Extends P0-07 Learning Agent |

---

### 5.3 P2 — Future (Do Not Build. Do Not Stub. Do Not Reference in UI.)

| Feature | Reason excluded |
|---|---|
| Full Exam Cell workflow | Different domain, different actors, significant complexity |
| Full Training & Placement workflow + placement eligibility | Different domain, significant legal/process complexity |
| Official ERP/EMS/API integration | Requires institutional agreements; not a student-team deliverable |
| Hostel, fees, library management | Unrelated to academic intelligence |
| Parent portal | Different user, different relationship model |
| Automated disciplinary action | Never. See Constitution S-06. |
| Confidential counselling automation | Never. See Constitution S-06. |

> [!CAUTION]
> If any P2 feature appears in the UI as a placeholder, disabled button, or "coming soon" label,
> it implies it is in scope. Remove it. A product that implies it does things it doesn't is dishonest.

---

## 6. Success Criteria

These are the metrics that prove ASPIRE works. "AI feels smart" is not a success criterion.

### 6.1 Student-facing

| Metric | What we're measuring | Target (to be validated) |
|---|---|---|
| Early warning lead time | How many days before a problem becomes critical does the system flag it? | ≥7 days for attendance risk |
| False alert rate | What % of alerts are irrelevant to the student? | <20% |
| Recommendation acceptance rate | What % of AI-generated plans does the student accept? | >50% |
| Intervention completion rate | Of accepted plans, what % result in the student completing the actions? | >60% |
| Replanning success | When Plan A fails/is rejected, does Plan B improve outcomes? | Measurable improvement vs no-plan baseline |
| Learning outcome | Pre/post assessment score improvement after an AI-driven study plan | Positive delta on targeted weak topics |

### 6.2 Mentor-facing

| Metric | What we're measuring | Target |
|---|---|---|
| Priority queue usefulness | Does the queue surface genuinely urgent cases at the top? | Mentor agreement rate >70% in review |
| Human override rate | How often does the mentor override the AI's priority or plan? | Track as signal (not a target to minimize) |
| Case resolution time | Time from case open to outcome verified | Benchmark against no-system baseline |

### 6.3 System-level

| Metric | What we're measuring | Target |
|---|---|---|
| Attendance rule engine accuracy | Does the engine produce the correct percentage on all test fixtures? | 100% on curated suite |
| RBAC violations | Unauthorized access in test suite | 0 |
| Audit coverage | % of privileged writes that produce a traceable audit event | 100% |
| Agent tool boundary | Forbidden tool calls in adversarial tests | 0 |
| Data freshness | % of student state data within expected freshness window | Define per-data-type |

---

## 7. Key Constraints

### 7.1 Technical constraints

- **No official ERP API** — Data enters via authorized CSV/Excel imports and public web crawling. No authenticated ERP scraping in v1.
- **LLM is not always available** — The deterministic core (attendance engine, assessment engine, calendar engine) must remain operational even when the LLM provider is down. See Constitution P-02.
- **OpenRouter abstraction** — No agent calls any LLM provider directly. All LLM calls go through internal `LLMService`. See Constitution A-08.
- **BCREC attendance rules** — Initial configuration: 75% ESE threshold, 65–74.99% condonable under Academic Council approval, below 65% not condonable. These are configuration values, not constants in code.

### 7.2 Team constraints

- **3 people, 7 months** — P0 is the non-negotiable delivery. P1 is added only after P0 vertical slice is working end-to-end.
- **No premature multi-tenancy** — BCREC is the only institution in v1. The architecture must be configurable for other institutions, but we do not build a multi-college admin/SaaS experience.
- **Existing EduGen code** — Learning workspace features are reused and refactored. `CourseWorkspace.tsx` (46KB) must be broken up. No blind extension of the existing codebase.

### 7.3 Institutional constraints

- Real student data access must go through a BCREC contact (OQ-05 still open).
- Notice intelligence scraping is limited to public pages. No authenticated scraping.
- All imported data must be authorized by the institution.

---

## 8. What the Demo Must Prove (North Star for P0)

Use one realistic student case to prove the entire system.

**The scenario:**
- Student S-204, B.Tech CSE (AIML), Semester 5
- DBMS attendance: 73% (below 75% ESE threshold)
- End-semester exam: 8 days away
- Assessment trend: declining
- 2 pending assignments
- DBMS is the detected weak topic
- Student has uploaded DBMS notes to the Learning Workspace

**The flow that must work end-to-end:**
1. Attendance and assessment engines emit risk events.
2. Supervisor agent routes to Academic + Attendance specialists.
3. System creates an evidence-backed recovery plan.
4. Student sees the plan with reasons and evidence — not a bare instruction.
5. Student accepts the plan.
6. Mentor queue receives the case, sees urgency band + evidence.
7. Mentor reviews and approves/edits the plan.
8. Learning Agent uses student's DBMS sources to generate a targeted quiz.
9. Student completes the quiz; result feeds back into learning state.
10. System schedules a follow-up to check if attendance/task/learning state improved.
11. Case closes if improved. Replans and escalates if not.

**If this flow works cleanly, the product has a story.**
If this flow is broken or faked in the demo, nothing else matters.

---

## 9. Non-Goals (Explicit)

These are not failures. These are decisions.

- We are not building the best LLM chatbot.
- We are not replacing BCREC's existing ERP.
- We are not building a product that works without any human review.
- We are not automating decisions that require institutional authority.
- We are not trying to serve 10 colleges at launch.
- We are not building a beautiful product with no working backend.
- We are not building a backend with no usable frontend.

---

## 10. Open Items

| ID | Question | Owner | Status |
|---|---|---|---|
| OQ-05 | Who is the BCREC contact for real data access and validation? | All | 🔴 OPEN |
| OQ-06 | What is the exact CIA/PCIA component structure and weightings for autonomous batches at BCREC? | Bishesh | 🔴 OPEN — needed before `03_SYSTEM_SPEC.md` Assessment section is FROZEN |
| OQ-07 | What exactly constitutes a "MAR activity" and how are points calculated under autonomous rules? | Abhijit | 🔴 OPEN — needed before P1-05 spec is FROZEN |
| OQ-08 | What is the correct roll number for each team member? | All | 🔴 OPEN |

---

*Drafted from: Master Product Engineering Book v1.0 (02 October 2026) + Constitution decisions*
*Source of record for: what we build, who it is for, why, and what success looks like.*
