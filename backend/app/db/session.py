"""Async database engine and session management."""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator, Optional

from app.core.config import settings

log = structlog.get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


async def init_db() -> None:
    global _engine, _session_factory
    connect_args = {}
    if _is_sqlite(settings.DATABASE_URL):
        connect_args["check_same_thread"] = False
    
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        connect_args=connect_args,
        **({}  if _is_sqlite(settings.DATABASE_URL) else {
            "pool_size": settings.DB_POOL_SIZE,
            "pool_pre_ping": True,
        }),
    )
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    log.info(
        "database_engine_created",
        url_scheme=settings.DATABASE_URL.split("://")[0],
        echo=settings.DB_ECHO,
    )


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        log.info("database_engine_disposed")
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    return _engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
