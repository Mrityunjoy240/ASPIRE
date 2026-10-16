# app/core/database.py
# SQLAlchemy 2.x async engine & session (DM-NEW-ORM01)

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with psycopg3 driver."""
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        poolclass=NullPool,  # Supabase handles pooling; avoid double-pooling
        future=True,
    )


engine: AsyncEngine = create_engine()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """FastAPI dependency for DB session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_context():
    """Context manager for non-FastAPI usage (engines, agents)."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
