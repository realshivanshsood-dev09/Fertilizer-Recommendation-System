"""
Alembic environment configuration.
Reads DATABASE_URL from application settings at runtime — never from alembic.ini.

Supports both:
  - async PostgreSQL (asyncpg) via run_async_migrations()
  - sync SQLite (for Alembic autogenerate and offline mode)
"""
from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Add backend/ to sys.path so app imports resolve ──────────────────────────
# env.py lives at: backend/alembic/env.py
# We need to import from: backend/app/...
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# ── Application imports ───────────────────────────────────────────────────────
from app.core.config import settings

# Import all models so Alembic can detect them for autogenerate
import app.models  # noqa: F401 — registers all models on Base.metadata
from app.db.base import Base

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with the actual DATABASE_URL from settings
# Strip +asyncpg or +aiosqlite for sync connections (Alembic offline / autogenerate)
_db_url = settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", _db_url)

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def _is_postgresql(url: str) -> bool:
    return "postgresql" in url


# ── Offline mode (emit SQL to stdout without connecting) ──────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script without DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online async mode (connects to real database) ────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg / aiosqlite)."""
    # For Alembic we need a sync-compatible URL when using run_sync
    # asyncpg → postgresql+asyncpg requires async; we use async_engine_from_config
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the real database."""
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
