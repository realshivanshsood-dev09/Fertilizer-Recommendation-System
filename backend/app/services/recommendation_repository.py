"""
Recommendation Persistence Service
==================================
Persists completed recommendations and recommendation items to the database
using SQLAlchemy models.

Resilience:
  If the database is uninitialized, disconnected, or throws an error, the service
  logs the issue and returns cleanly without breaking deterministic API calculations.
"""

from __future__ import annotations

import structlog
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.recommendation import Recommendation
from app.models.recommendation_item import RecommendationItem
from app.models.soil_test import SoilTest
from app.schemas.request import RecommendRequest
from app.schemas.response import RecommendResponse

log = structlog.get_logger(__name__)


async def persist_recommendation(
    request: RecommendRequest,
    response: RecommendResponse,
    session: Optional[AsyncSession] = None,
) -> Optional[str]:
    """
    Persists recommendation, location, soil test record, and item lines.
    Returns the created Recommendation UUID, or None if skipped/errored.
    """
    if session is None:
        log.debug("db_persistence_skipped_no_session")
        return None

    try:
        # 1. Location record
        loc = Location(
            state="Punjab",
            district=response.district.value,
            block=request.block,
        )
        session.add(loc)

        # 2. Soil test record
        soil_test = SoilTest(
            location=loc,
            soil_source=response.soil_source.value,
            nitrogen_kg_per_ha=response.soil_N_kg_ha,
            phosphorus_kg_per_ha=response.soil_P_kg_ha,
            potassium_kg_per_ha=response.soil_K_kg_ha,
            is_lab_measured=response.explanation.soil_is_lab_measured,
            provenance=response.explanation.summary,
        )
        session.add(soil_test)

        # 3. Recommendation header
        rec = Recommendation(
            crop=response.crop.value,
            season=response.season.value,
            pipeline_version=response.pipeline_version,
            soil_source=response.soil_source.value,
            location=loc,
            soil_test=soil_test,
            stcr_n_kg_per_ha=response.stcr_baseline.N_kg_per_ha,
            stcr_p2o5_kg_per_ha=response.stcr_baseline.P2O5_kg_per_ha,
            stcr_k2o_kg_per_ha=response.stcr_baseline.K2O_kg_per_ha,
            ml_correction_n=response.ml_adjustment.N_correction_kg_per_ha,
            ml_correction_p=response.ml_adjustment.P_correction_kg_per_ha,
            ml_correction_k=response.ml_adjustment.K_correction_kg_per_ha,
            final_n_kg_per_ha=response.final_recommendation.N_kg_per_ha,
            final_p2o5_kg_per_ha=response.final_recommendation.P2O5_kg_per_ha,
            final_k2o_kg_per_ha=response.final_recommendation.K2O_kg_per_ha,
            confidence=response.final_recommendation.confidence,
            estimated_cost_inr=response.estimated_cost_inr,
            is_placeholder=response.is_placeholder,
            explanation_summary=response.explanation.summary,
            request_payload=request.model_dump(mode="json"),
        )
        session.add(rec)

        # 4. Recommendation product items
        for prod in response.fertilizers:
            item = RecommendationItem(
                recommendation=rec,
                item_type="fertilizer",
                product_name=prod.product_name,
                nutrient_type=prod.nutrient_type,
                quantity_kg_per_ha=prod.quantity_kg_per_ha,
                unit="kg/ha",
                unit_cost_inr=prod.unit_cost_inr_per_kg,
                total_cost_inr=prod.total_cost_inr,
                notes=prod.notes,
            )
            session.add(item)

        await session.flush()
        log.info("recommendation_persisted", recommendation_id=rec.id)
        return rec.id

    except Exception as exc:
        log.warning("db_persistence_failed_silently", error=str(exc))
        return None
