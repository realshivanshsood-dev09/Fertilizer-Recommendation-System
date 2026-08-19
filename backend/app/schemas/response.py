"""
Pydantic response schemas for the /recommend and /validation endpoints.
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
        "ICAR / PAU Soil Fertility Classification Guidelines",
        description="Source of the interpretation thresholds",
    )


class CalculationStep(BaseModel):
    """Detailed step-by-step arithmetic proof for a nutrient prescription."""

    nutrient: str = Field(description="N | P2O5 | K2O")
    equation_formula: str = Field(description="Algebraic formulation, e.g. 'FN = 3.78*T - 0.96*SN'")
    target_yield_q_ha: float
    soil_value_kg_ha: float
    raw_calculated_dose: float
    final_clipped_dose: float
    step_explanation: str = Field(description="Formatted calculation string, e.g. '3.78 × 50 - 0.96 × 120 = 73.8 kg N/ha'")


class STCRBaseline(BaseModel):
    """
    STCR (Soil Test Crop Response) fertilizer dose computed from the
    agronomic science layer.
    """

    N_kg_per_ha: Optional[float] = Field(
        None,
        description="Prescribed Nitrogen dose (kg N/ha) from STCR equation",
    )
    P2O5_kg_per_ha: Optional[float] = Field(
        None,
        description="Prescribed Phosphorus dose as P₂O₅ (kg P2O5/ha) from STCR equation",
    )
    K2O_kg_per_ha: Optional[float] = Field(
        None,
        description="Prescribed Potassium dose as K₂O (kg K2O/ha) from STCR equation",
    )
    target_yield_q_ha: Optional[float] = Field(
        None,
        description="Target yield (q/ha) used for STCR calculation",
    )
    equation_version: str = "PLACEHOLDER — equation not yet loaded"
    data_source: str = "PLACEHOLDER — PAU/ICAR STCR coefficients required"
    dataset_id: Optional[str] = None
    source_id: Optional[str] = None
    provenance_status: Optional[str] = None
    calculation_steps: List[CalculationStep] = Field(
        default_factory=list,
        description="Step-by-step algebraic breakdown of nutrient calculations",
    )
    is_placeholder: bool = Field(
        False,
        description="True if STCR calculation could not be performed or used unverified data",
    )
    notes: str = ""


class MLAdjustment(BaseModel):
    """
    Correction factors output by the ML layer.
    These are ADDITIVE corrections on top of the STCR baseline, not absolute doses.

    ⚠️ ML model is not yet active. ML_ENABLED=False in config.
    """

    model_config = ConfigDict(protected_namespaces=())

    N_correction_kg_per_ha: Optional[float] = Field(
        None,
        description="ML correction for N (kg/ha)",
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
    nutrient_type: str = Field(description="N | P | K | complex | micronutrient")
    quantity_kg_per_ha: Optional[float] = Field(
        None,
        description="Physical quantity of commercial product in kg/ha",
    )
    bags_per_ha: Optional[float] = Field(
        None,
        description="Standard commercial bags required per hectare",
    )
    bag_size_kg: Optional[float] = Field(
        None,
        description="Standard bag weight in kg (e.g. 45 kg for Urea, 50 kg for DAP/MOP)",
    )
    n_contribution_kg_ha: Optional[float] = Field(
        None,
        description="Nitrogen supplied by this product (kg N/ha)",
    )
    p2o5_contribution_kg_ha: Optional[float] = Field(
        None,
        description="Phosphorus supplied by this product (kg P2O5/ha)",
    )
    k2o_contribution_kg_ha: Optional[float] = Field(
        None,
        description="Potassium supplied by this product (kg K2O/ha)",
    )
    unit_cost_inr_per_kg: Optional[float] = None
    total_cost_inr: Optional[float] = None
    source_standards: Optional[str] = Field(
        None,
        description="Specification standard (e.g. Fertiliser Control Order 1985 / PAU)",
    )
    notes: str = ""


class BiofertilizerRecommendation(BaseModel):
    """
    Biofertilizer / bio-inoculant recommendations.
    """

    recommended: List[str] = Field(
        default_factory=list,
        description="List of recommended biofertilizers",
    )
    application_timing: Optional[str] = None
    data_source: str = "PAU biofertilizer recommendations"


class ApplicationTiming(BaseModel):
    """Split and timing recommendations for fertilizer application."""

    splits: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of application events with timing and dose split",
    )
    apply_before: Optional[str] = Field(
        None,
        description="Recommended crop stage or calendar date for first application",
    )
    notes: str = "Application timing guidelines"


class EvidenceMetadata(BaseModel):
    """Agronomic evidence and field verification metadata."""

    evidence_status: str = Field(
        "unsupported",
        description="calibration_verified | calibration_and_malwa_validated | unsupported_awaiting_calibration",
    )
    calibration_source: Optional[str] = None
    validation_sources: List[str] = Field(default_factory=list)
    malwa_validation_available: bool = False
    evidence_strength: str = Field(
        "insufficient_calibration",
        description="high_with_regional_malwa_verification | moderate_alluvial_calibration | insufficient_calibration",
    )
    notes: Optional[str] = None


class Explanation(BaseModel):
    """Human-readable explanation of the recommendation and its provenance."""

    soil_source_used: SoilSource
    soil_is_lab_measured: bool = Field(
        False,
        description="True only when soil N/P/K were directly measured in a laboratory",
    )
    soil_status: str = Field(
        "unknown",
        description="measured | prior_estimate | qualitative_only | insufficient_data",
    )
    baseline_method: str = "STCR"
    ml_used: bool = False
    summary: str = ""
    caveats: List[str] = Field(default_factory=list)
    calculation_walkthrough: List[str] = Field(
        default_factory=list,
        description="Programmatic explanation of how each nutrient dose was derived",
    )
    evidence: Optional[EvidenceMetadata] = Field(
        None,
        description="Field verification and regional evidence metadata",
    )
    shap_top_features: Optional[Dict[str, float]] = None


class RecommendationSummary(BaseModel):
    """
    Concise machine-readable summary optimized for user interfaces.
    """

    crop: Crop
    district: District
    season: Season
    target_yield_q_ha: Optional[float] = None
    total_cost_inr_per_ha: Optional[float] = None
    recommended_products: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of products with name, bags/ha, and kg/ha",
    )
    nutrient_requirements: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Prescribed N, P2O5, and K2O doses in kg/ha",
    )
    soil_confidence: float = Field(
        0.0,
        description="Reliability confidence score of the input soil measurements [0, 1]",
    )
    recommendation_confidence: Optional[float] = Field(
        None,
        description="Overall pipeline confidence [0, 1]",
    )
    data_provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Verification identifiers, citations, and standard codes",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Actionable cautions or limitations for the farmer",
    )


# ── Top-level response ─────────────────────────────────────────────────────────

class RecommendResponse(BaseModel):
    """
    Complete recommendation response.
    """

    crop: Crop
    district: District
    season: Season
    soil_source: SoilSource
    target_yield_q_ha: Optional[float] = Field(
        None,
        description="Target yield evaluated (q/ha)",
    )
    soil_N_kg_ha: Optional[float] = Field(
        None,
        description="Soil available Nitrogen (kg/ha) used in calculation",
    )
    soil_P_kg_ha: Optional[float] = Field(
        None,
        description="Soil available Phosphorus (kg/ha) used in calculation",
    )
    soil_K_kg_ha: Optional[float] = Field(
        None,
        description="Soil available Potassium (kg/ha) used in calculation",
    )

    summary: RecommendationSummary = Field(
        default_factory=lambda: RecommendationSummary(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
        ),
        description="Concise UI-optimized summary card",
    )

    nutrient_status: NutrientStatus
    stcr_baseline: STCRBaseline
    ml_adjustment: MLAdjustment
    final_recommendation: FinalRecommendation

    fertilizers: List[FertilizerProduct] = Field(
        default_factory=list,
        description="Commercial product translation",
    )
    biofertilizer: BiofertilizerRecommendation = Field(
        default_factory=BiofertilizerRecommendation,
    )
    estimated_cost_inr: Optional[float] = Field(
        None,
        description="Total estimated fertilizer cost (INR/ha)",
    )
    application_timing: ApplicationTiming = Field(
        default_factory=ApplicationTiming,
    )
    evidence: Optional[EvidenceMetadata] = Field(
        None,
        description="Agronomic calibration and Malwa verification evidence",
    )
    explanation: Explanation
    pipeline_version: str = "0.2.0-stcr-live"
    is_placeholder: bool = Field(
        False,
        description="True when any part of the recommendation uses unverified placeholder data",
    )


class HealthResponse(BaseModel):
    status: str
    version: str
    ml_enabled: bool
    environment: str
    database: str
