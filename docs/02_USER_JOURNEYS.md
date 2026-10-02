# 02_USER_JOURNEYS.md
# EduGen AI / ASPIRE — User Journeys

**STATUS: 🔴 DRAFT**
**Author:** Mrityunjoy Kapat (Team Lead)
**Date:** 02 October 2026
**Version:** 1.0

> [!CAUTION]
> These journeys represent our current understanding of how BCREC students and staff work. 
> To move this document to FROZEN, we must validate these assumptions with real users.
> **[NEEDS VALIDATION]** from a BCREC contact (Open Item OQ-05).

---

## 1. Student Journeys

### 1.1 The P0 North Star: Academic Risk & Recovery
**Trigger:** Student falls below 75% attendance threshold in DBMS and has a declining assessment trend.
1. **Notification:** Student receives a push/in-app notification highlighting an academic risk.
2. **Review State:** Student opens the app to the Home / Academic Health screen and sees the specific risk signal (e.g., "Attendance Warning: DBMS").
3. **Understand:** Student clicks the warning to see the AI's explanation (e.g., "Your attendance is 73%. You need to attend 2 more classes to cross the 75% ESE eligibility threshold").
4. **What-If Projection:** Student checks the deterministic "what-if" projection to verify the exact math.
5. **AI Guidance & Plan:** Student views the AI-generated recovery plan (e.g., "Attend the next 2 DBMS classes, and schedule a 45-min study block for Unit 3").
6. **Acceptance:** Student clicks "Accept Plan". This sets their intention.
7. **Action (Tasks):** The plan is decomposed into tasks in the student's Unified Obligation stream.
8. **Action (Learning):** Student uses the Learning Workspace to upload DBMS notes and generate a practice quiz.
9. **Outcome:** System tracks the completion of tasks and attendance updates to verify recovery.

### 1.2 Routine Academic Check-In
**Trigger:** Student wants to know their overall standing before the weekend.
1. **Open App:** Student opens the mobile app Home screen.
2. **Snapshot:** Student views their current Student State (aggregated attendance, pending assignments, upcoming exams within 7 days).
3. **Tasks:** Student views the Unified Obligations list to see if anything is due on Monday.
4. **Decision:** Student decides to either relax (if clear) or complete a pending task.

### 1.3 Notice to Action (P1)
**Trigger:** College publishes an official notice about Exam Form Fill-up.
1. **Notice Ingestion:** System ingests, parses, and identifies the target audience.
2. **Task Generation:** System creates a task for the student with a specific deadline.
3. **Notification:** Student receives a targeted alert.
4. **Action:** Student acknowledges the task and marks it complete once done.

---

## 2. Mentor Journeys

### 2.1 P0 North Star: Managing the Case Queue
**Trigger:** A new intervention case is created for a student (e.g., Student S-204 from Journey 1.1).
1. **Dashboard Entry:** Mentor logs into the Web Workspace and opens the Priority Queue.
2. **Queue Review:** Mentor sees their assigned mentees ordered by urgency, not alphabetically. S-204 is marked "URGENT" due to the 73% attendance and upcoming exam.
3. **Case Inspection:** Mentor clicks on S-204 to open the Student 360 view and case details.
4. **Evidence Review:** Mentor reviews the deterministic facts (73% attendance, declining marks) and the AI's proposed recovery plan.
5. **Decision:** Mentor either clicks "Approve Plan", edits the plan to add a required 1:1 meeting, or rejects it.
6. **Follow-up:** System schedules a follow-up check for 3 days later, returning the case to the mentor's queue if the student has not recovered.

### 2.2 Case Escalation
**Trigger:** A student repeatedly ignores an accepted recovery plan, and the AI escalation policy is triggered.
1. **Queue Update:** Mentor sees the case marked as "ESCALATION REQUIRED".
2. **Review History:** Mentor reviews the history of the failed intervention.
3. **Action:** Mentor adds notes and escalates the case to the HOD or CT via the system.

---

## 3. Faculty / CT Journeys (P1)

### 3.1 Course Operational Snapshot (Subject Faculty)
**Trigger:** Faculty member wants to identify weak areas before the next CIA.
1. **Dashboard Entry:** Faculty logs into the Web Workspace.
2. **Subject Analytics:** Faculty views the analytics for their assigned course (e.g., DBMS).
3. **Insight:** Faculty sees that a significant portion of the class is struggling with "Unit 3".
4. **Action:** Faculty decides to upload supplementary materials to the system or propose a remedial class notice.

### 3.2 Class-Wide Attendance Review (CT)
**Trigger:** CT needs to submit the monthly attendance report.
1. **Dashboard Entry:** CT logs into the Web Workspace.
2. **Class View:** CT views aggregated attendance across all subjects for their assigned batch.
3. **Intervention:** CT identifies students consistently missing multiple subjects and can trigger a review request to those students' mentors.

---

## 4. HOD Journeys (P1)

### 4.1 Department Health Check
**Trigger:** HOD performs a weekly review of department operations.
1. **Dashboard Entry:** HOD logs into the Web Workspace.
2. **Trend Analysis:** HOD views department-level aggregates (overall attendance trends, missing assessment data).
3. **Mentor Workload:** HOD checks the mentor caseload distribution to ensure no mentor is overwhelmed with urgent cases.
4. **Escalation Review:** HOD reviews cases escalated by mentors (from Journey 2.2) and determines the institutional response.

---

## 5. System Journeys (Behind the Scenes)

### 5.1 Data Ingestion & Conflict Resolution
**Trigger:** A CSV of latest attendance is uploaded.
1. **Upload & Parse:** Admin uploads the file; system parses it.
2. **Schema & Cross-Record Check:** System validates the data against the institution config.
3. **Conflict Detection:** System detects that a student's attendance dropped significantly in a way that contradicts a previous manual correction.
4. **Freeze:** System freezes automated AI interventions for that student and marks the record status as "Conflict".
5. **Human Resolution:** Authorized human (Admin/Faculty) reviews the discrepancy, chooses the correct version, and the system recomputes the derived state.
