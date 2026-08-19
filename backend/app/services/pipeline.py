"""
Recommendation Pipeline
========================
Orchestrates the full recommendation pipeline:

  Farmer input
    → soil_resolution (Level A/B/C/D Fallback Hierarchy)
    → stcr_service (Deterministic STCR Baseline & Step-by-Step Arithmetic Proof)
    → ml_correction (Disabled / Additive Residual Correction)
    → fertilizer_translation (Commercial Products & Split Timing)
    → biofertilizer
    → cost_calculation (Verified Statutory/Subsidized Prices)
    → explanation & recommendation summary assembly
    → optional DB persistence
    → RecommendResponse
"""

from __future__ import annotations

import structlog
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Crop, SoilSource
from app.schemas.request import RecommendRequest
from app.schemas.response import (
    Explanation,
    FinalRecommendation,
    NutrientStatus,
    RecommendationSummary,
    RecommendResponse,
    STCRBaseline,
)
from app.services.biofertilizer import BiofertilizerService
from app.services.cost_calculation import CostCalculationService
from app.services.fertilizer_translation import FertilizerTranslationService
from app.services.ml_correction import MLCorrectionService
from app.services.recommendation_repository import persist_recommendation
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
    Interprets soil nutrient status against ICAR / PAU agronomic standards.
    """
    n_status = None
    if soil.nitrogen is not None:
        if soil.nitrogen < 280.0:
            n_status = "low"
        elif soil.nitrogen <= 560.0:
            n_status = "medium"
        else:
            n_status = "high"

    p_status = None
    if soil.phosphorus is not None:
        if soil.phosphorus < 10.0:
            p_status = "low"
        elif soil.phosphorus <= 25.0:
            p_status = "medium"
        else:
            p_status = "high"

    k_status = None
    if soil.potassium is not None:
        if soil.potassium < 118.0:
            k_status = "low"
        elif soil.potassium <= 280.0:
            k_status = "medium"
        else:
            k_status = "high"

    ph_status = None
    if soil.ph is not None:
        if soil.ph < 6.5:
            ph_status = "acidic"
        elif soil.ph <= 8.5:
            ph_status = "neutral_to_alkaline"
        else:
            ph_status = "highly_alkaline"

    oc_status = None
    if soil.organic_carbon is not None:
        if soil.organic_carbon < 0.50:
            oc_status = "low"
        elif soil.organic_carbon <= 0.75:
            oc_status = "medium"
        else:
            oc_status = "high"

    return NutrientStatus(
        nitrogen_status=n_status,
        phosphorus_status=p_status,
        potassium_status=k_status,
        ph_status=ph_status,
        organic_carbon_status=oc_status,
        interpretation_source="ICAR / PAU Soil Fertility Classification Guidelines",
    )


def _build_explanation(
    request: RecommendRequest,
    soil: SoilProfile,
    stcr: STCRBaseline,
    ml_used: bool,
) -> Explanation:
    caveats: list[str] = []

    if soil.status == "qualitative_only" or soil.source == SoilSource.QUESTIONNAIRE_FALLBACK:
        caveats.append(
            "Soil data from questionnaire only — N/P/K are unknown. "
            "STCR baseline cannot be computed."
        )
    elif soil.status == "prior_estimate" or soil.source == SoilSource.DISTRICT_AVERAGE:
        caveats.append(
            "District average soil profile used — aggregate prior estimate, not directly measured on farmer's field."
        )
    elif soil.status == "insufficient_data":
        caveats.append(
            "Soil nutrients unavailable — STCR baseline skipped."
        )

    if request.crop == Crop.COTTON:
        caveats.append(
            "STCR coefficients for cotton in Malwa are not yet available in Track A; doses are unpopulated."
        )
    elif request.crop == Crop.RICE:
        caveats.append(
            "Rice STCR equation is verified from 2021 PAU field validation; foundational calibration paper pending physical archival acquisition."
        )

    if not ml_used:
        caveats.append(
            "ML correction layer is disabled (model_enabled=False); deterministic STCR baseline is provided."
        )

    summary_text = (
        f"Deterministic STCR fertilizer prescription for {request.crop.value} in {request.district.value} "
        f"({request.season.value} season). "
    )
    if stcr.N_kg_per_ha is not None:
        summary_text += f"Prescribed nutrients: N={stcr.N_kg_per_ha} kg/ha, P2O5={stcr.P2O5_kg_per_ha} kg/ha, K2O={stcr.K2O_kg_per_ha} kg/ha."
    else:
        summary_text += "Nutrient calculation is unavailable / placeholder."

    calc_walkthrough = [step.step_explanation for step in stcr.calculation_steps]

    return Explanation(
        soil_source_used=soil.source,
        soil_is_lab_measured=soil.is_lab_measured,
        soil_status=soil.status,
        baseline_method="STCR",
        ml_used=ml_used,
        summary=summary_text,
        caveats=caveats,
        calculation_walkthrough=calc_walkthrough,
        shap_top_features=None,
    )


async def run_pipeline(
    request: RecommendRequest,
    session: Optional[AsyncSession] = None,
) -> RecommendResponse:
    log.info(
        "pipeline_start",
        crop=request.crop.value,
        district=request.district.value,
        season=request.season.value,
        soil_source=request.soil_source.value,
        target_yield=request.target_yield_q_ha,
    )

    # Step 1 — Soil resolution (Strict 4-level fallback)
    soil = _soil_resolver.resolve(request)
    log.debug("pipeline_step_soil_resolved", soil=repr(soil))

    # Step 2 — Nutrient status interpretation
    nutrient_status = _interpret_nutrient_status(soil)

    # Step 3 — STCR baseline (Deterministic agronomic calculation)
    stcr = _stcr_service.compute(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil=soil,
        target_yield_q_ha=request.target_yield_q_ha,
        rice_residue_incorporated=request.rice_residue_incorporated,
    )

    # Step 4 — ML correction (Disabled / deterministic residual)
    ml_adj = _ml_service.predict_correction(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil=soil,
        stcr=stcr,
        irrigation=request.irrigation,
    )

    # Step 5 — Combine STCR + ML → final doses
    if stcr.N_kg_per_ha is not None and not stcr.is_placeholder:
        final_n = round(stcr.N_kg_per_ha + (ml_adj.N_correction_kg_per_ha or 0.0), 2)
        final_p = round((stcr.P2O5_kg_per_ha or 0.0) + (ml_adj.P_correction_kg_per_ha or 0.0), 2)
        final_k = round((stcr.K2O_kg_per_ha or 0.0) + (ml_adj.K_correction_kg_per_ha or 0.0), 2)
        confidence = 0.95 if soil.is_lab_measured else 0.60
        is_placeholder_resp = False
    else:
        final_n = None
        final_p = None
        final_k = None
        confidence = None
        is_placeholder_resp = True

    final = FinalRecommendation(
        N_kg_per_ha=final_n,
        P2O5_kg_per_ha=final_p,
        K2O_kg_per_ha=final_k,
        confidence=confidence,
    )

    # Step 6 — Fertilizer product translation (Commercial products & bags/ha)
    products, total_cost = _translation_service.translate(
        crop=request.crop,
        N_kg_per_ha=final.N_kg_per_ha,
        P2O5_kg_per_ha=final.P2O5_kg_per_ha,
        K2O_kg_per_ha=final.K2O_kg_per_ha,
    )

    # Step 7 — Application timing (PAU crop-stage splits)
    timing = _translation_service.get_application_timing(request.crop)

    # Step 8 — Biofertilizer
    biofert = _biofertilizer_service.recommend(
        crop=request.crop, district=request.district
    )

    # Step 9 — Cost
    cost = _cost_service.calculate(products) if total_cost is None else total_cost

    # Step 10 — Explanation
    explanation = _build_explanation(request, soil, stcr, ml_used=ml_adj.model_enabled)

    # Step 11 — Machine-readable summary for frontend
    summary = RecommendationSummary(
        crop=request.crop,
        district=request.district,
        season=request.season,
        target_yield_q_ha=stcr.target_yield_q_ha,
        total_cost_inr_per_ha=cost,
        recommended_products=[
            {
                "product_name": p.product_name,
                "quantity_kg_per_ha": p.quantity_kg_per_ha,
                "bags_per_ha": p.bags_per_ha,
                "bag_size_kg": p.bag_size_kg,
                "total_cost_inr": p.total_cost_inr,
            }
            for p in products
        ],
        nutrient_requirements={
            "N_kg_per_ha": final.N_kg_per_ha,
            "P2O5_kg_per_ha": final.P2O5_kg_per_ha,
            "K2O_kg_per_ha": final.K2O_kg_per_ha,
        },
        soil_confidence=soil.confidence,
        recommendation_confidence=final.confidence,
        data_provenance={
            "source_id": stcr.source_id,
            "dataset_id": stcr.dataset_id,
            "equation_version": stcr.equation_version,
            "data_source": stcr.data_source,
            "soil_source": soil.source.value,
            "soil_status": soil.status,
            "is_lab_measured": soil.is_lab_measured,
        },
        warnings=explanation.caveats,
    )

    response = RecommendResponse(
        crop=request.crop,
        district=request.district,
        season=request.season,
        soil_source=soil.source,
        target_yield_q_ha=stcr.target_yield_q_ha,
        soil_N_kg_ha=soil.nitrogen,
        soil_P_kg_ha=soil.phosphorus,
        soil_K_kg_ha=soil.potassium,
        summary=summary,
        nutrient_status=nutrient_status,
        stcr_baseline=stcr,
        ml_adjustment=ml_adj,
        final_recommendation=final,
        fertilizers=products,
        biofertilizer=biofert,
        estimated_cost_inr=cost,
        application_timing=timing,
        explanation=explanation,
        pipeline_version="0.2.0-stcr-live",
        is_placeholder=is_placeholder_resp,
    )

    # Step 12 — Optional DB persistence (if session provided)
    if session is not None:
        await persist_recommendation(request, response, session)

    log.info("pipeline_complete", is_placeholder=is_placeholder_resp, total_cost=cost)
    return response
