"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.response import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns application health status, version, and ML layer state.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        ml_enabled=settings.ML_ENABLED,
        environment=settings.APP_ENV,
        database=settings.DATABASE_URL.split("://")[0],  # type only, no credentials
    )
