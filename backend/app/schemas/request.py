"""
Pydantic request schemas for the /recommend endpoint.
Strong typing + validation for all farmer-supplied inputs.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import (
    Crop,
    District,
    IrrigationType,
    Season,
    SoilSource,
    VALID_CROP_SEASONS,
)


class SoilInput(BaseModel):
    """
    Laboratory or estimated soil measurements.

    IMPORTANT: All fields are optional because the source may be a questionnaire
    rather than a Soil Health Card. Missing values will be filled from district
    averages or clearly marked as unavailable. Do NOT assume null == 0.
    """

    nitrogen: Optional[float] = Field(
        None,
        ge=0,
        le=1000,
        description="Available nitrogen (kg/ha) — alkaline KMnO4 method",
    )
    phosphorus: Optional[float] = Field(
        None,
        ge=0,
        le=300,
        description="Available phosphorus P₂O₅ (kg/ha) — Olsen method",
    )
    potassium: Optional[float] = Field(
        None,
        ge=0,
        le=1500,
        description="Available potassium K₂O (kg/ha) — neutral 1N NH4OAc method",
    )
    ph: Optional[float] = Field(
        None,
        ge=3.0,
        le=10.5,
        description="Soil pH (1:2 water suspension)",
    )
    organic_carbon: Optional[float] = Field(
        None,
        ge=0,
        le=5.0,
        description="Organic carbon (%) — Walkley-Black method",
    )


class QuestionnaireInput(BaseModel):
    """
    Farmer-observable information used ONLY when soil lab data is absent.
    These answers cannot substitute for N/P/K measurements.
    They provide qualitative context only.
    """

    previous_fertilizer_timing: Optional[str] = Field(
        None,
        description=(
            "When was the last fertilizer applied? "
            "E.g. 'at_sowing', 'first_irrigation', 'not_applied'"
        ),
    )
    visible_symptoms: Optional[list[str]] = Field(
        default_factory=list,
        description=(
            "Observed crop symptoms, e.g. ['yellowing_lower_leaves', 'poor_tillering']. "
            "Used for qualitative context only — NOT equivalent to soil N/P/K."
        ),
    )
    irrigation_type: Optional[IrrigationType] = None


class RecommendRequest(BaseModel):
    """
    Complete farmer request payload for the recommendation pipeline.
    """

    crop: Crop
    district: District
    block: Optional[str] = Field(
        None,
        description="Sub-district block name for finer resolution (optional)",
    )
    season: Season
    soil_source: SoilSource = Field(
        ...,
        description=(
            "Provenance of the soil data. "
            "Must be explicitly supplied — the system never silently assumes a source."
        ),
    )
    soil: SoilInput = Field(default_factory=SoilInput)
    target_yield_q_ha: Optional[float] = Field(
        None,
        gt=0,
        le=150,
        description="Farmer's target grain/lint yield in quintals per hectare (q/ha)",
    )
    rice_residue_incorporated: bool = Field(
        False,
        description="True if rice residue (e.g. 6 t/ha) was incorporated before sowing wheat",
    )
    irrigation: Optional[IrrigationType] = None
    questionnaire: Optional[QuestionnaireInput] = None

    # ── Demonstration Integration Inputs ──────────────────────────────────────
    soil_input_mode: str = Field(
        "manual",
        description="Data acquisition path: 'manual' | 'shc_api' | 'digilocker'",
    )
    soil_health_card_number: Optional[str] = Field(
        None,
        description="Soil Health Card number for SHC API lookup (e.g. 'SHC-PB-BAT-2024-001')",
    )
    digilocker_document_id: Optional[str] = Field(
        None,
        description="DigiLocker document identifier (e.g. 'DOC-DL-SHC-BAT-001')",
    )

    @field_validator("soil_input_mode")
    @classmethod
    def validate_soil_input_mode(cls, v: str) -> str:
        allowed = {"manual", "shc_api", "digilocker"}
        if v not in allowed:
            raise ValueError(f"Invalid soil_input_mode '{v}'. Expected one of: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_crop_season(self) -> "RecommendRequest":
        valid_seasons = VALID_CROP_SEASONS.get(self.crop, [])
        if valid_seasons and self.season not in valid_seasons:
            raise ValueError(
                f"Crop '{self.crop.value}' is not typically grown in "
                f"season '{self.season.value}' in the Malwa region. "
                f"Expected: {[s.value for s in valid_seasons]}"
            )
        return self

    @model_validator(mode="after")
    def warn_questionnaire_without_soil(self) -> "RecommendRequest":
        """
        If soil_source is questionnaire_fallback, soil N/P/K must be null.
        Questionnaire answers do NOT provide N/P/K; they are qualitative hints only.
        """
        if self.soil_source == SoilSource.QUESTIONNAIRE_FALLBACK:
            if any(
                v is not None
                for v in [
                    self.soil.nitrogen,
                    self.soil.phosphorus,
                    self.soil.potassium,
                ]
            ):
                raise ValueError(
                    "When soil_source='questionnaire_fallback', soil N/P/K values "
                    "must be null. Questionnaire answers are qualitative only."
                )
        return self
