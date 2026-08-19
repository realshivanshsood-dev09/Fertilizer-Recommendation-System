"""
/validation endpoint
====================
Provides summary of agronomic validation studies, observation counts,
and regional Malwa verification status.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from typing import Any, Dict

from app.services.validation_service import ValidationSummaryService

log = structlog.get_logger(__name__)
router = APIRouter()

_validation_service = ValidationSummaryService()


@router.get(
    "/validation/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Agronomic Validation Summary",
    description="Returns aggregate validation evidence across registered Track A & B datasets.",
)
async def get_validation_summary() -> Dict[str, Any]:
    log.info("validation_summary_request")
    return _validation_service.get_summary()
