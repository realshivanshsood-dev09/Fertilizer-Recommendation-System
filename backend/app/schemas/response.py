"""
Pydantic response schemas for the /recommend endpoint.
All numerical placeholders are typed Optional[float] and documented clearly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import Crop, District, Season, SoilSource


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class NutrientStatus(BaseModel):
    """Interpreted soil fertility category per nutrient."""

    nitrogen_status: Optional[str] = Field(
        None,
        description="'low' | 'medium' | 'high' — based on ICAR thresholds",
    )
    phosphorus_status: Optional[str] = None
    potassium_status: Optional[str] = None
    ph_status: Optional[str] = Field(
        None,
        description="'acidic' | 'neutral' | 'alkaline'",
    )
    organic_carbon_status: Optional[str] = None
    interpretation_source: str = Field(
        "PLACEHOLDER — ICAR thresholds not yet loaded",
        description="Source of the interpretation thresholds",
    )


class STCRBaseline(BaseModel):
    """
    STCR (Soil Test Crop Response) fertilizer dose computed from the
    agronomic science layer.

    ⚠️ PLACEHOLDER: All values are None until authoritative PAU / ICAR STCR
    coefficients are loaded.  See docs/science_status.md for what is needed.
    """

    N_kg_per_ha: Optional[float] = Field(
        None,
        description="[PLACEHOLDER] Nitrogen dose (kg/ha) — STCR baseline",
    )
    P2O5_kg_per_ha: Optional[float] = Field(
        None,
        description="[PLACEHOLDER] Phosphorus dose as P₂O₅ (kg/ha) — STCR baseline",
    )
    K2O_kg_per_ha: Optional[float] = Field(
        None,
        description="[PLACEHOLDER] Potassium dose as K₂O (kg/ha) — STCR baseline",
    )
    equation_version: str = "PLACEHOLDER — equation not yet loaded"
    data_source: str = "PLACEHOLDER — PAU/ICAR STCR coefficients required"
    notes: str = (
        "STCR equations for wheat/rice/cotton in Malwa are not yet available. "
        "Do not use these values for any agronomic decision."
    )


class MLAdjustment(BaseModel):
    """
    Correction factors output by the ML layer.
    These are ADDITIVE corrections on top of the STCR baseline, not absolute doses.

    ⚠️ PLACEHOLDER: ML model is not yet trained.  ML_ENABLED=False in config.
    """

    model_config = ConfigDict(protected_namespaces=())

    N_correction_kg_per_ha: Optional[float] = Field(
        None,
        description="[PLACEHOLDER] ML correction for N (can be positive or negative)",
    )
    P_correction_kg_per_ha: Optional[float] = None
    K_correction_kg_per_ha: Optional[float] = None
    model_version: Optional[str] = None
    model_enabled: bool = False
    shap_explanation: Optional[Dict[str, Any]] = Field(
        None,
        description="SHAP feature contributions (populated when model is enabled)",
    )


class FinalRecommendation(BaseModel):
    """
    Final N/P/K doses after applying the ML correction.
    final = STCR_baseline + ML_correction
    """

    N_kg_per_ha: Optional[float] = None
    P2O5_kg_per_ha: Optional[float] = None
    K2O_kg_per_ha: Optional[float] = None
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Pipeline confidence score [0, 1]. None if STCR baseline is a placeholder.",
    )


class FertilizerProduct(BaseModel):
    """Translated commercial fertilizer product and quantity."""

    product_name: str
    nutrient_type: str = Field(description="N | P | K | complex")
    quantity_kg_per_ha: Optional[float] = None
    unit_cost_inr_per_kg: Optional[float] = None
    total_cost_inr: Optional[float] = None
    notes: str = ""


class BiofertilizerRecommendation(BaseModel):
    """
    Biofertilizer / bio-inoculant recommendations.
    ⚠️ PLACEHOLDER — specific strains and doses per crop not yet loaded.
    """

    recommended: List[str] = Field(
        default_factory=list,
        description="[PLACEHOLDER] List of recommended biofertilizers",
    )
    application_timing: Optional[str] = None
    data_source: str = "PLACEHOLDER — PAU biofertilizer recommendations required"


class ApplicationTiming(BaseModel):
    """Split and timing recommendations for fertilizer application."""

    splits: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="[PLACEHOLDER] List of application events with timing and dose split",
    )
    apply_before: Optional[str] = Field(
        None,
        description="Recommended crop stage or calendar date for first application",
    )
    notes: str = "PLACEHOLDER — application timing guidelines not yet loaded"


class Explanation(BaseModel):
    """Human-readable explanation of the recommendation and its provenance."""

    soil_source_used: SoilSource
    baseline_method: str = "STCR"
    ml_used: bool = False
    summary: str = ""
    caveats: List[str] = Field(default_factory=list)
    shap_top_features: Optional[Dict[str, float]] = None


# ── Top-level response ─────────────────────────────────────────────────────────

class RecommendResponse(BaseModel):
    """
    Complete recommendation response.
    Fields marked [PLACEHOLDER] will be None until the corresponding
    scientific data or ML model is available.
    """

    crop: Crop
    district: District
    season: Season
    soil_source: SoilSource

    nutrient_status: NutrientStatus
    stcr_baseline: STCRBaseline
    ml_adjustment: MLAdjustment
    final_recommendation: FinalRecommendation

    fertilizers: List[FertilizerProduct] = Field(
        default_factory=list,
        description="[PLACEHOLDER] Commercial product translation",
    )
    biofertilizer: BiofertilizerRecommendation = Field(
        default_factory=BiofertilizerRecommendation,
    )
    estimated_cost_inr: Optional[float] = Field(
        None,
        description="[PLACEHOLDER] Total estimated fertilizer cost (INR/ha)",
    )
    application_timing: ApplicationTiming = Field(
        default_factory=ApplicationTiming,
    )
    explanation: Explanation
    pipeline_version: str = "0.1.0-scaffold"
    is_placeholder: bool = Field(
        True,
        description="True when any part of the recommendation uses placeholder data",
    )


class HealthResponse(BaseModel):
    status: str
    version: str
    ml_enabled: bool
    environment: str
    database: str
