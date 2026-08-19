"""
/recommend endpoint
====================
Accepts a farmer request and returns a deterministic fertilizer recommendation
with commercial product translation and application timing.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import _session_factory
from app.schemas.request import RecommendRequest
from app.schemas.response import RecommendResponse
from app.services.pipeline import run_pipeline

log = structlog.get_logger(__name__)
router = APIRouter()


async def get_optional_db_session() -> Optional[AsyncSession]:
    """Provides an active DB session if database is initialized, otherwise None."""
    if _session_factory is None:
        yield None
        return
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            yield None


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fertilizer Recommendation",
    description=(
        "Runs the deterministic fertilizer recommendation pipeline: "
        "Soil Resolution → Verified STCR Baseline → Commercial Fertilizer Translation → Application Schedule."
    ),
)
async def recommend(
    request: RecommendRequest,
    session: Optional[AsyncSession] = Depends(get_optional_db_session),
) -> RecommendResponse:
    log.info(
        "recommend_request",
        crop=request.crop.value,
        district=request.district.value,
        soil_source=request.soil_source.value,
        target_yield=request.target_yield_q_ha,
    )
    try:
        response = await run_pipeline(request, session=session)
        return response
    except ValueError as val_err:
        log.warning("recommend_validation_error", error=str(val_err))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        log.error("recommend_pipeline_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {exc}",
        ) from exc
