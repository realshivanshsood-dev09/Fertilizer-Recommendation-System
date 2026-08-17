"""
/recommend endpoint
====================
Accepts a farmer request and returns a fertilizer recommendation.

Phase 1 status:
  - Pipeline runs end-to-end
  - All numerical doses are None (STCR coefficients are placeholders)
  - ML correction is disabled
  - is_placeholder=True in all responses
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status

from app.schemas.request import RecommendRequest
from app.schemas.response import RecommendResponse
from app.services.pipeline import run_pipeline

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Fertilizer Recommendation",
    description=(
        "Runs the two-layer fertilizer recommendation pipeline "
        "(STCR baseline + ML correction). "
        "**Phase 1**: All numerical doses are None — STCR coefficients are placeholders. "
        "`is_placeholder=true` in every response until real STCR data is loaded."
    ),
)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    log.info(
        "recommend_request",
        crop=request.crop.value,
        district=request.district.value,
        soil_source=request.soil_source.value,
    )
    try:
        response = await run_pipeline(request)
        return response
    except Exception as exc:
        log.error("recommend_pipeline_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {exc}",
        ) from exc
