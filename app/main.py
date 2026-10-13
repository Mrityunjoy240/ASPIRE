# app/main.py
# ASPIRE Mother System — FastAPI entry point
# DM-API01: FastAPI + Pydantic → generated contracts/openapi.json
# DM-NEW-ORM01: SQLAlchemy 2.x async

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.attendance_specialist import AttendanceSpecialist
from app.agents.supervisor import Supervisor
from app.agents.tools import ServiceBackedTools
from app.api.routers import assessments, attendance, cases, students, tasks
from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.core.events import EventBus
from app.services.follow_up_service import FollowUpConsumer
from app.services.llm_service import get_llm_service
from app.services.scheduler import cancel_scheduler_task, create_scheduler_task


def build_supervisor(llm_service) -> Supervisor:
    """Default Supervisor wiring: service-backed tools + attendance
    specialist (R2 assess stub + R3 proposal production)."""
    tools = ServiceBackedTools()
    specialist = AttendanceSpecialist(tools=tools, llm=llm_service)
    return Supervisor(
        tools=tools,
        attendance_specialist=specialist,
        proposal_specialist=specialist,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    llm = get_llm_service()  # Initialize LLMService singleton
    # Supervisor event-bus registration (11_ROADMAP R2). Idempotent per bus:
    # repeated TestClient startup/shutdown cycles never double-subscribe.
    supervisor = getattr(app.state, "supervisor", None)
    if supervisor is None:
        supervisor = build_supervisor(llm)
        app.state.supervisor = supervisor
    supervisor.ensure_subscribed(app.state.event_bus)
    # ADR-004: deterministic RULE_ENGINE follow-up consumer (MENTOR_FOLLOWUP_DUE
    # + policy trigger events). Idempotent per bus, same as the Supervisor.
    consumer = getattr(app.state, "follow_up_consumer", None)
    if consumer is None:
        consumer = FollowUpConsumer(async_session_maker)
        app.state.follow_up_consumer = consumer
    consumer.ensure_subscribed(app.state.event_bus)
    # R4 / DM-AG03: startup evaluation + every 5 minutes (task is None when
    # disabled — tests keep the "engine never connects" invariant).
    scheduler_task = create_scheduler_task(app.state.event_bus)
    app.state.scheduler_task = scheduler_task
    yield
    # Shutdown: stop the scheduler before disposing the engine it uses.
    await cancel_scheduler_task(scheduler_task)
    await llm.close()
    await engine.dispose()


app = FastAPI(
    title="ASPIRE Mother System API",
    description="Student Success Intelligence Platform — Core API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)

# In-process domain event bus (ADR-001 ARCH-02) — available to routers via
# Depends(get_event_bus); created at import time so tests without lifespan
# still resolve it.
app.state.event_bus = EventBus()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure per environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0", "env": settings.app_env}


# API routers (routers already have /api/v1 prefix)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(assessments.router)
app.include_router(tasks.router)
app.include_router(cases.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.app_env == "development")
