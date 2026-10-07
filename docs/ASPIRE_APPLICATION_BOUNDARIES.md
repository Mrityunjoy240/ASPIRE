# ASPIRE Application Boundaries & Ecosystem Architecture
# `docs/ASPIRE_APPLICATION_BOUNDARIES.md`

**STATUS: 🟢 FROZEN**
**Date:** 07 October 2026
**Author:** Mrityunjoy Kapat (Team Lead)
**Contributors:** Abhijit Ghosh, Bishesh Ghosh

---

## 1. Executive Summary & Mental Model

**ASPIRE is ONE single product ecosystem.** It is NOT a fragmented collection of four or five independent products.

Underneath the entire ecosystem sits the **Shared ASPIRE Core Platform** and the human-facing **ASPIRE Mother Application (Web)**, serving specialized client applications across Web and Native Android.

```
                             ASPIRE ECOSYSTEM
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
       ASPIRE MOTHER APPLICATION             ASPIRE CORE PLATFORM
          (Human-Facing Web)                (Backend Engine & Core)
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    │
                        Shared API / Data Contracts
                       (`contracts/openapi.json`)
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
    STUDENT CLIENTS          FACULTY CLIENTS          INSTITUTION CLIENTS
    ├── Web (Next.js)        ├── Web (Next.js)        └── Web (Next.js)
    └── Android (Native)     └── Android (Native)
```

---

## 2. Core Concepts & Definitions

### 2.1 What is the ASPIRE Mother Application? (WEB)
The **Mother Application** is NOT merely the backend API. 
The Mother Application is the **primary human-facing management, control, and operational web application** through which the ASPIRE platform is administered, monitored, configured, and reviewed.

- **Stack:** Next.js 15+ (App Router), TypeScript, Tailwind CSS, consumed via standard OpenAPI contracts.
- **Implemented By:** **OpenCode** within the web workspace (`apps/web/`).
- **Target Users & Roles:**
  - System Administrators
  - Institution Administrators & Management
  - Heads of Department (HOD)
  - Class Teachers, Faculty & Mentors
  - Academic Coordinators & Reviewers

#### Operational Capabilities Managed in the Mother Application:
- Student & Faculty Lifecycle Management
- Departments, Batches & Academic Structures
- Course Catalogs, Runs & Syllabus Indexing
- Attendance & Assessment Ingestion, Provenance & Quarantine
- Institutional Rule Configuration (`institution_rules` weights/thresholds)
- Intervention Case Lifecycle & Human-in-the-Loop Approvals
- Agent Orchestration Status, Policy & Performance Monitoring
- System Audit Logs, Security Trails & System Health Reports

> [!IMPORTANT]
> **Design Principle:** The Mother Application is NOT "one giant monolithic dashboard." It utilizes **Role-Based Access Control (RBAC)** and **Progressive Disclosure** (drawers, detail views, contextual action sheets, and modal flows) so each role sees an uncluttered, tailored operational interface.

---

### 2.2 What is the ASPIRE Core Platform? (Backend & Intelligence Core)
The **Core Platform** provides the foundational backend intelligence, persistence, and business rule evaluation underneath all human-facing applications.

- **Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x (Async), PostgreSQL + pgvector (Supabase), LangGraph agent graphs, and `LLMService` (OpenRouter).
- **Implemented By:** **OpenCode** within `services/` and `app/`.
- **Core Platform Responsibilities:**
  - **Database & Persistence:** Authoritative schema authority via `db/migrations/*.sql`.
  - **Security, Auth & RBAC:** Supabase asymmetric JWKS token verification + `user_role_assignments`.
  - **Deterministic Rule Engines:** Pure Python attendance math, recovery calculators, assessment trend analyzers, and priority queues (zero LLM in calculations).
  - **Event Bus & Lifecycle:** In-process async domain events + 5-minute periodic scheduler.
  - **Agent Orchestrator:** LangGraph state machine executing Supervisor and Specialist agents.
  - **LLM Gateway Service:** `LLMService` with `LIVE` and `MOCK` modes, bounded retries, and strict schema validation.
  - **API Contract Authority:** FastAPI routes exporting `contracts/openapi.json`.
  - **Audit & Provenance:** Immutable `audit_log` records for all privileged mutations.

---

### 2.3 Web Clients vs. Native Android Clients

| Client | Platform | Workspace / Environment | Implementation Tool | Tech Stack |
|---|---|---|---|---|
| **Mother Application** | Web | `apps/web/` | **OpenCode** | Next.js 15, TypeScript, Tailwind CSS |
| **Student Web Client** | Web | `apps/web/` / `apps/mobile/` (PWA) | **OpenCode** | Next.js 15, TypeScript, Tailwind CSS |
| **Faculty / Mentor Web** | Web | `apps/web/` | **OpenCode** | Next.js 15, TypeScript, Tailwind CSS |
| **Student Native App** | Android | **Separate Android Project** | **Android Studio** | Kotlin, Jetpack Compose, Material 3, Coroutines/Flow, StateFlow |
| **Faculty Native App** | Android | **Separate Android Project** | **Android Studio** | Kotlin, Jetpack Compose, Material 3, Coroutines/Flow, StateFlow |

---

## 3. Development Workflow & Tooling Ownership

### 3.1 OpenCode Scope (This Repository)
**OpenCode** is the primary coding agent responsible for everything maintained in this monorepo:
1. The **ASPIRE Mother Application** (Web management & operational control).
2. All **Web Clients** (Student Web, Faculty Web, Mentor Web).
3. The **ASPIRE Core Platform** (FastAPI backend, database migrations, deterministic engines, security middleware, repositories).
4. The **Agent Orchestrator & AI Gateway** (LangGraph graphs, `LLMService`, prompts, tool contracts).
5. **Shared API Contracts & Schemas** (`contracts/openapi.json`, `packages/shared/`).
6. **Tests & CI/CD Pipelines** (Unit tests, engine tests, API integration tests, GitHub Actions).

### 3.2 Android Studio Scope (External Native Projects)
**Native Android applications are developed separately in Android Studio:**
1. Do NOT build native Kotlin/Jetpack Compose Android apps inside the Next.js/web workspace.
2. Android projects are **pure consumers** of the ASPIRE Core Platform API.
3. Android applications must strictly adhere to the frozen contracts in `contracts/openapi.json`, domain terminology, truth-state semantics, and `DESIGN.md` design language.
4. Native Android development begins only after the backend API and domain contracts are frozen and verified.

---

## 4. The Shared Core Principle (Zero Business Logic Duplication)

**The Core Platform is the ONLY Source of Truth.** No client application (Web, PWA, or Android) may independently calculate academic rules or mutate business state.

```
       CORRECT ARCHITECTURE:                      INCORRECT (FORBIDDEN):

   Client App (Web / Android)                  Client App (Web / Android)
               │                                           │
               ▼                                           ▼
     ASPIRE API (FastAPI)                     [ Independent Local Logic ]
               │                              (Calculates Attendance %,
               ▼                               Generates Own Statuses,
     Deterministic Engines                      Makes Unverified Decisions)
               │                                           │
               ▼                                           ▼
      PostgreSQL Database                         Inconsistent State & Drift
```

### Strictly Centralized (Must NEVER be duplicated on clients):
- Attendance percentage and required recovery class calculations.
- Assessment score aggregation, weighted trend analysis, and grade eligibility.
- Urgency band calculations and priority triage sorting (DM-SS03).
- Intervention case state transitions (`PENDING_APPROVAL` $\rightarrow$ `ACTIVE` $\rightarrow$ `RESOLVED`).
- Role assignment and RBAC enforcement.
- LLM prompt orchestration and agent graph state.
- Audit log entry creation.

---

## 5. Architectural Communication Contract

1. **Authentication:** All clients authenticate with Supabase Auth to obtain a JWT, then pass `Authorization: Bearer <JWT>` to the ASPIRE Core API.
2. **Authorization:** Core API validates JWT signature asymmetrically using Supabase JWKS (`SUPABASE_JWKS_URI`), then resolves user roles from `user_role_assignments`.
3. **API Contract:** All clients interface through HTTP REST endpoints documented in `contracts/openapi.json`.
4. **Data Presentation:** Clients render derived states returned by the backend engines. UI states (such as `OVERDUE`) are derived purely from backend deadlines and status fields without persisting alternative client statuses.
