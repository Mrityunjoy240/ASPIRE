# ASPIRE Mother Application Specification
# `docs/ASPIRE_MOTHER_APPLICATION_SPECIFICATION.md`

**STATUS: 🟢 FROZEN**
**Date:** 07 October 2026
**Author:** Mrityunjoy Kapat (Team Lead)
**Contributors:** Abhijit Ghosh, Bishesh Ghosh

---

## 1. Purpose & System Role

The **ASPIRE Mother Application** is the primary human-facing operational and management web environment for the entire ASPIRE ecosystem.

It is built as a **high-density, role-governed web application** in Next.js 15 App Router (`apps/web/`), allowing institutional administrators, academic leadership (HODs), mentors, faculty, and operational staff to administer, monitor, configure, and operate the ASPIRE platform.

```
                         ASPIRE ECOSYSTEM
                                │
             ┌──────────────────┴──────────────────┐
             │                                     │
      MOTHER APPLICATION                      CORE PLATFORM
     (Human Web Workspace)                (FastAPI / Engines / DB)
             │                                     │
             └──────────────────┬──────────────────┘
                                │
                    Shared OpenAPI REST API
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
         Student Web      Student Android   Faculty/Mentor
         (Client)         (Android Studio)  (Clients)
```

---

## 2. Target Users & Role-Based Workspaces

The Mother Application serves distinct institutional roles via strict **Role-Based Access Control (RBAC)** and **Progressive Disclosure**:

| Role | Primary Responsibilities in Mother App | Key Views & Interfaces |
|---|---|---|
| **System Admin** | Global platform health, tenant config, audit log inspection, agent policy & LLM gateway monitoring | System Monitoring, Security & Audit Logs, Global Configuration |
| **Institution Admin** | College-level rules (`institution_rules`), academic calendar, department setup, data ingestion pipelines | Ingestion Hub, Academic Structure, Rule Weights & Thresholds Manager |
| **Head of Department (HOD)** | Departmental overview, chronic risk escalations, faculty mentor assignments, case overrides | Department Risk Matrix, Escalation Inbox, Mentor Performance |
| **Faculty / Class Teacher** | Course run records, attendance verification, continuous assessment entry, data discrepancy review | Course Roster, Attendance Batch Grid, Conflict Quarantine Drawer |
| **Academic Mentor** | Student success triage, case reviews, intervention plan approvals, progress verification | Priority Triage Queue (DM-SS03), Student Success Inspector, Approval Actions |

---

## 3. Core Operational Capabilities

### 3.1 Academic Structure & User Management
- **Institutions & Batches:** Program definitions, semester batches, section allocations.
- **Student & Faculty Roster:** Profile directory, roll number lookup, mentor assignments.
- **Courses & Curriculum Indexing:** Course runs, syllabus units, and topic embeddings.

### 3.2 Ingestion & Conflict Quarantine Hub
- **Batch CSV/Excel Ingestion:** Upload interface for attendance sheets and examination registers.
- **Data Provenance Ledger:** Displays source metadata, import timestamp, actor, and version.
- **Conflict Resolution Workspace:** Side-by-side discrepancy resolver when multiple sources disagree (Constitution D-04).

### 3.3 Rule Configuration & Policy Governance
- **Institutional Rule Editor:** Dynamic configuration for attendance thresholds (e.g. 75% mandatory, 65% condonation minimum), assessment component weights, and margin values.
- **Config-Driven:** Changes write versioned records to `institution_rules` — zero hardcoded institutional math.

### 3.4 Intelligence, Cases & Agent Oversight
- **Priority Triage Queue (DM-SS03):** Unified mentor queue sorted strictly by `Urgency Band → Exam Proximity → Days Since Action`.
- **Intervention Case Lifecycle:** Inspection of agent proposals, student acceptance state, and mentor approval triggers.
- **Agent Trace Inspector:** Live inspection of LangGraph agent decisions, retrieved context, and `LLMService` structured outputs (with zero PII leakage).

### 3.5 Governance, Auditing & System Monitoring
- **Immutable Audit Trail:** Comprehensive searchable log of all privileged mutations, overrides, approvals, and imports.
- **System Health:** FastAPI status, database connection pool, LLM gateway latency, and periodic scheduler execution ticks.

---

## 4. UX Design Philosophy & Information Architecture

Following the **Linear-inspired design discipline** defined in [`DESIGN.md`](file:///c:/Users/ANAMIKA/DEV/Temp/ASPIRE/DESIGN.md):

```
       CLEAN SURFACE ───► CONTEXT ───► DETAIL ───► ACTION
```

1. **Information-Dense, Zero Clutter:** Compact rows with monospace roll numbers and semantic risk badges.
2. **Side-by-Side Triage:** List/detail split view so mentors can review student evidence without losing context in the triage queue.
3. **Semantic Truth Indicators:** Clear visual distinction between **VERIFIED** institutional data, **DERIVED** engine calculations, and **PROPOSED** agent plans.
4. **Progressive Disclosure:** Essential data shown upfront; deeper analytics, audit history, and trace logs expand in slide-over drawers on demand.

---

## 5. Relationship with Core Platform and Client Applications

1. **Centralized Domain Authority:** The Mother Application never performs local calculation of attendance percentages, recovery requirements, or urgency scores. It renders the exact derived state computed by the Core Platform.
2. **Single Contract Surface:** All operations execute through authenticated REST calls against `contracts/openapi.json`.
3. **Precedence for Downstream Clients:** Changes approved in the Mother Application (e.g. approved intervention plans, resolved data conflicts) immediately update central database state, which downstream Student Web and Android Studio native clients consume.
