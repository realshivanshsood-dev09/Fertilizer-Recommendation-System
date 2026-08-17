"""
Recommendation Pipeline
========================
Orchestrates the full recommendation pipeline:

  Farmer input
    → soil_resolution
    → stcr_service
    → ml_correction
    → fertilizer_translation
    → biofertilizer
    → cost_calculation
    → explanation assembly
    → RecommendResponse
"""

from __future__ import annotations

import structlog

from app.core.constants import SoilSource
from app.schemas.request import RecommendRequest
from app.schemas.response import (
    Explanation,
    FinalRecommendation,
    NutrientStatus,
    RecommendResponse,
)
from app.services.biofertilizer import BiofertilizerService
from app.services.cost_calculation import CostCalculationService
from app.services.fertilizer_translation import FertilizerTranslationService
from app.services.ml_correction import MLCorrectionService
from app.services.soil_resolution import SoilProfile, SoilResolutionService
from app.services.stcr_service import STCRService

log = structlog.get_logger(__name__)

# ── Service singletons ────────────────────────────────────────────────────────
_soil_resolver = SoilResolutionService()
_stcr_service = STCRService()
_ml_service = MLCorrectionService()
_translation_service = FertilizerTranslationService()
_biofertilizer_service = BiofertilizerService()
_cost_service = CostCalculationService()


def _interpret_nutrient_status(soil: SoilProfile) -> NutrientStatus:
    """
    ⚠️  PLACEHOLDER — ICAR critical limit thresholds not yet loaded.
    Real thresholds for alluvial soils of Punjab (Malwa) required.
    """
    return NutrientStatus(
        nitrogen_status=None,
        phosphorus_status=None,
        potassium_status=None,
        ph_status=None,
        organic_carbon_status=None,
        interpretation_source=(
            "PLACEHOLDER — ICAR/PAU critical soil fertility thresholds "
            "for Malwa alluvial soils not yet loaded."
        ),
    )


def _build_explanation(
    request: RecommendRequest,
    soil: SoilProfile,
    ml_used: bool,
) -> Explanation:
    caveats: list[str] = []

    if soil.source == SoilSource.QUESTIONNAIRE_FALLBACK:
        caveats.append(
            "Soil data from questionnaire only — N/P/K are unknown. "
            "STCR baseline cannot be computed."
        )
    if soil.source == SoilSource.DISTRICT_AVERAGE:
        caveats.append(
            "District average soil profile used — lab-measured SHC data preferred."
        )
    caveats.append(
        "STCR coefficients are placeholders — all numerical doses are None."
    )
    caveats.append(
        "ML correction layer is disabled — no trained model is available."
    )

    return Explanation(
        soil_source_used=soil.source,
        baseline_method="STCR",
        ml_used=ml_used,
        summary=(
            f"Recommendation for {request.crop.value} in {request.district.value} "
            f"({request.season.value} season). "
            "This is a Phase 1 scaffold — all numerical values are placeholders."
        ),
        caveats=caveats,
        shap_top_features=None,
    )


async def run_pipeline(request: RecommendRequest) -> RecommendResponse:
    log.info(
        "pipeline_start",
        crop=request.crop.value,
        district=request.district.value,
        season=request.season.value,
        soil_source=request.soil_source.value,
    )

    # Step 1 — Soil resolution
    soil = _soil_resolver.resolve(request)
    log.debug("pipeline_step_soil_resolved", soil=repr(soil))

    # Step 2 — Nutrient status interpretation
    nutrient_status = _interpret_nutrient_status(soil)

    # Step 3 — STCR baseline
    stcr = _stcr_service.compute(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil=soil,
    )

    # Step 4 — ML correction
    ml_adj = _ml_service.predict_correction(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil=soil,
        stcr=stcr,
        irrigation=request.irrigation,
    )

    # Step 5 — Combine STCR + ML → final doses
    def _add(a, b):
        if a is None and b is None:
            return None
        return (a or 0.0) + (b or 0.0)

    final = FinalRecommendation(
        N_kg_per_ha=_add(stcr.N_kg_per_ha, ml_adj.N_correction_kg_per_ha),
        P2O5_kg_per_ha=_add(stcr.P2O5_kg_per_ha, ml_adj.P_correction_kg_per_ha),
        K2O_kg_per_ha=_add(stcr.K2O_kg_per_ha, ml_adj.K_correction_kg_per_ha),
        confidence=None,  # placeholder
    )

    # Step 6 — Fertilizer product translation
    products, _ = _translation_service.translate(
        crop=request.crop,
        N_kg_per_ha=final.N_kg_per_ha,
        P2O5_kg_per_ha=final.P2O5_kg_per_ha,
        K2O_kg_per_ha=final.K2O_kg_per_ha,
    )

    # Step 7 — Application timing
    timing = _translation_service.get_application_timing(request.crop)

    # Step 8 — Biofertilizer
    biofert = _biofertilizer_service.recommend(
        crop=request.crop, district=request.district
    )

    # Step 9 — Cost
    cost = _cost_service.calculate(products)

    # Step 10 — Explanation
    explanation = _build_explanation(request, soil, ml_used=ml_adj.model_enabled)

    log.info("pipeline_complete", is_placeholder=True)

    return RecommendResponse(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil_source=soil.source,
        nutrient_status=nutrient_status,
        stcr_baseline=stcr,
        ml_adjustment=ml_adj,
        final_recommendation=final,
        fertilizers=products,
        biofertilizer=biofert,
        estimated_cost_inr=cost,
        application_timing=timing,
        explanation=explanation,
        pipeline_version="0.1.0-scaffold",
        is_placeholder=True,
    )
