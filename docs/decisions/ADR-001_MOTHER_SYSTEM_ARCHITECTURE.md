# ADR-001: ASPIRE Mother System Architecture

**STATUS: 🟢 FROZEN**
**Date:** 07 October 2026
**Author:** Mrityunjoy Kapat (Team Lead)
**Contributors:** Abhijit Ghosh, Bishesh Ghosh

---

## 1. Context & Problem Statement

ASPIRE is designed around a single autonomous core ("The Mother System") that serves multiple current and future client applications (Mentor/Admin Web Dashboard, Student Mobile PWA, future native mobile apps, and communication adapters).

Prior to building client applications or individual sub-modules, the system required an authoritative architectural specification defining:
1. The exact boundaries and internal layers of the Mother System.
2. The runtime topology and deployment model for v1.
3. The event dispatch, scheduler, and deterministic-to-agent lifecycle.
4. The client integration contract ensuring zero business-logic leakage into clients.
5. Final resolution on previously open architectural items (`ARCH-01`, `ARCH-02`, `ARCH-04`, `OQ-AG02`, `OQ-AG03`).

---

## 2. Decision Summary

### 2.1 Mother System Boundaries & Responsibilities

The **Mother System** encompasses all intelligence, rules, persistence, and business state:
- **Identity & RBAC:** Supabase JWT validation via asymmetric JWKS + ASPIRE `user_role_assignments` role mapping.
- **Data & Migration Authority:** PostgreSQL + pgvector. SQL files in `db/migrations/*.sql` are the single schema authority (DM-NEW-ORM01).
- **Ingestion & Data Provenance:** CSV/Excel ingestion pipeline with data conflict detection, quarantine mechanisms, and provenance metadata (`source`, `imported_at`, `status`, `version`).
- **Deterministic Rule Engines (`services/engines/`):** Pure functional Python modules with zero I/O, zero network calls, zero LLM dependencies. Responsible for attendance math, assessment trends, urgency band calculations, eligibility, and task status derivations.
- **Event & State Machine Loop:** Event registry mapping domain triggers (`ATTENDANCE_RISK_CRITICAL`, `TASK_OVERDUE`, etc.) to orchestration workflows, enforcing human-in-the-loop approval gates before privileged state transitions.
- **Agent Orchestration Engine (`services/agents/`):** LangGraph-based stateful agent graph (Supervisor Agent + Attendance, Learning, Intervention Specialists) operating strictly via typed FastAPI tool endpoints.
- **LLM Gateway Service (`services/llm/`):** Central `LLMService` supporting `LIVE` (OpenRouter) and `MOCK` (deterministic fixtures) modes with bounded retries and strict Pydantic structured output validation (DM-LLM01).
- **Audit & Provenance Ledger:** Immutable `audit_log` recording all privileged writes, plan creations, approvals, overrides, and agent invocations.
- **Contract Surface:** FastAPI router exporting OpenAPI 3.x schema (`contracts/openapi.json`) which generates TypeScript client contracts for all frontends (DM-API01).

### 2.2 Internal Topology: Layered Modular Monolith (ARCH-04 Resolved)

For v1, the Mother System is implemented as a **Layered Modular Monolith** within a single FastAPI application process:
- Eliminates distributed transaction complexity, network overhead between engines, and distributed queue maintenance during early development.
- Enforces strict unidirectional layer boundaries (Layers never call upwards or bypass intermediate domain layers).
- Decouples components cleanly via Python interfaces and repository classes, enabling seamless extraction into independent microservices if scale demands in future versions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT LAYER (Consumers)                        │
│   Web App (Next.js 15)  │  Mobile PWA (Next.js 15)  │  Future API Clients   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / Supabase JWT
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    MOTHER SYSTEM (Single FastAPI Process)                   │
│                                                                             │
│  [ Layer 1: API & Security ]                                               │
│    - FastAPI Routers & OpenAPI Exporter                                     │
│    - Supabase Auth JWKS Verifier + RBAC Middleware                          │
│                                                                             │
│  [ Layer 2: Ingestion & Quarantine ]                                        │
│    - Batch Ingestion, Conflict Quarantine, Data Provenance Tracker          │
│                                                                             │
│  [ Layer 3: Deterministic Rule Engines ] (Pure Python, 0 I/O)               │
│    - Attendance Engine  · Assessment Engine  · Priority Engine              │
│                                                                             │
│  [ Layer 4: Event & Lifecycle Engine ]                                      │
│    - Async In-Process Event Dispatcher                                      │
│    - 5-Minute Periodic Hybrid Scheduler (DM-AG03)                           │
│                                                                             │
│  [ Layer 5: Agent Orchestration Engine ]                                    │
│    - LangGraph State Machine (Supervisor + Specialists)                     │
│    - Typed Internal Tool Call Surface                                       │
│                                                                             │
│  [ Layer 6: LLM Gateway ]                                                   │
│    - LLMService (OpenRouter LIVE / MOCK, Pydantic Structured Output)        │
│                                                                             │
│  [ Layer 7: Data & Repository Layer ]                                       │
│    - SQLAlchemy 2.x (Async) + psycopg3 Repositories                         │
│    - Audit Logging & Historical Snapshot Engine                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Async Connection Pool
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                  PERSISTENCE (Supabase CLI / PostgreSQL 15+)                │
│    - PostgreSQL with pgvector extension                                     │
│    - Master migration source: db/migrations/*.sql                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Agent Framework & Execution Model (ARCH-01 & OQ-AG02 Resolved)

- **Framework (ARCH-01):** **LangGraph (Python)** is frozen as the agent graph orchestration engine. Its native support for cyclical graph flows, typed state checkpoints, and deterministic branching directly implements the `OBSERVE → DETECT → PLAN → ASSIST → VERIFY → REPLAN` loop.
- **Execution Model (OQ-AG02):**
  - **Asynchronous / Event-Triggered:** When domain events are emitted (e.g. following CSV ingestion or scheduler ticks), agent workflows run asynchronously as background tasks within FastAPI (`asyncio.create_task` managed by the event dispatcher).
  - **Synchronous Ad-Hoc:** On-demand exploratory queries (e.g., student asking what-if scenarios) execute within the request lifecycle with bounded timeouts (≤ 5.0s).
  - **Tool Enforcement:** Agents access platform state exclusively through typed internal service calls that enforce RBAC and record audit metadata. Direct SQL or raw DB pool access by agents is strictly prohibited.

### 2.4 Event Dispatch & Scheduler Architecture (ARCH-02 & OQ-AG03 Resolved)

- **Event Engine (ARCH-02):** In-process asynchronous event bus using Python's `asyncio` primitives for v1. No Redis, Kafka, or external broker is introduced for v1, avoiding unnecessary infrastructure complexity while keeping the event interface decoupled.
- **Scheduler Mechanism (OQ-AG03 / DM-AG03):** Hybrid scheduler running at system startup and every **5 minutes** via an in-process `asyncio` worker loop.
  - The scheduler evaluates time-based triggers (e.g., `TASK_OVERDUE`, `EXAM_APPROACHING`, `MENTOR_FOLLOWUP_DUE`).
  - The scheduler is **strictly idempotent** and **never directly mutates business state** or calls LLMs. It only emits domain events into the event dispatcher.

### 2.5 Multi-Client Decoupling & Contract Authority

- **Zero Client Logic:** Client applications (web/mobile) are strictly presentation and interaction layers. All calculations (attendance percentage, recovery class requirements, urgency bands, exam eligibility) are computed solely by Mother System engines.
- **API Authority:** FastAPI models + routes generate `contracts/openapi.json`. Frontend TypeScript types are generated from this committed artifact. CI blocks any PR introducing drift.
- **Authentication Handshake:**
  1. Client authenticates directly with Supabase Auth to obtain a Supabase access JWT.
  2. Client passes `Authorization: Bearer <JWT>` to the Mother System API Gateway.
  3. Mother System validates JWT signature via Supabase JWKS (asymmetric verification, no database lookup for validation).
  4. Mother System resolves user role assignments from internal `user_role_assignments` table.

---

## 3. Consequences & Guardrails

| Principle / Rule | Implementation Enforcement |
|---|---|
| Deterministic Source of Truth | Rule engines calculate; LLMs never compute statistics or eligibility. |
| Controlled Autonomy | Intervention plans created by agents default to `PENDING_APPROVAL`. Student or Mentor must explicitly approve. |
| Traceability & Audit | All state changes and agent decisions write an immutable record to `audit_log`. |
| Zero Secret Leakage | LLM keys and DB credentials live strictly within backend environment variables; never exposed to clients. |
