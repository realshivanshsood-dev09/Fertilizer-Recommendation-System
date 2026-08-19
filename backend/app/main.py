"""
SIH 2026 — Fertilizer Recommendation System
FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, integrations, recommend, validation
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import close_db, init_db

configure_logging()
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info(
        "application_startup",
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        ml_enabled=settings.ML_ENABLED,
    )
    await init_db()
    log.info(
        "database_ready",
        url_scheme=settings.DATABASE_URL.split("://")[0],
    )

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await close_db()
    log.info("application_shutdown")


def create_application() -> FastAPI:
    application = FastAPI(
        title="Fertilizer Recommendation System — SIH 2026",
        description=(
            "Deterministic STCR agronomic recommendation and empirical validation engine "
            "for the Malwa region of Punjab with mock Soil Health Card & DigiLocker adapters."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — restrict in production via environment variable
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api/v1", tags=["Health"])
    application.include_router(recommend.router, prefix="/api/v1", tags=["Recommend"])
    application.include_router(validation.router, prefix="/api/v1", tags=["Validation"])
    application.include_router(integrations.router, prefix="/api/v1", tags=["Integrations"])

    return application


app = create_application()
