"""
Soil Resolution Service
=======================
Resolves a SoilProfile from one of three sources:
  1. Soil Health Card (SHC) — lab N/P/K
  2. District / block average
  3. Questionnaire fallback

The resolved profile carries its source so downstream services can record
provenance in the final response.

Data source:
    District averages are loaded from data/soil/district_averages.yaml
    (SINGLE SOURCE OF TRUTH — no hardcoded duplicates in this module).
"""

from __future__ import annotations

import structlog
from typing import Optional

from app.core.constants import Crop, District, SoilSource
from app.core.data_loader import DistrictAverages, load_district_averages
from app.schemas.request import RecommendRequest, SoilInput

log = structlog.get_logger(__name__)

# ── Load district averages from YAML (single source of truth) ────────────────
_district_data: DistrictAverages = load_district_averages()


class SoilProfile:
    """
    Normalised soil profile passed through the recommendation pipeline.
    """

    def __init__(
        self,
        nitrogen: Optional[float],
        phosphorus: Optional[float],
        potassium: Optional[float],
        ph: Optional[float],
        organic_carbon: Optional[float],
        source: SoilSource,
        reliability_note: str,
    ) -> None:
        self.nitrogen = nitrogen
        self.phosphorus = phosphorus
        self.potassium = potassium
        self.ph = ph
        self.organic_carbon = organic_carbon
        self.source = source
        self.reliability_note = reliability_note

    def is_complete_for_stcr(self) -> bool:
        """
        True only when the profile has the minimum fields required for
        STCR equation evaluation (N, P, K at minimum).
        """
        return all(
            v is not None for v in [self.nitrogen, self.phosphorus, self.potassium]
        )

    def __repr__(self) -> str:
        return (
            f"SoilProfile(source={self.source.value}, "
            f"N={self.nitrogen}, P={self.phosphorus}, K={self.potassium}, "
            f"pH={self.ph}, OC={self.organic_carbon})"
        )


class SoilResolutionService:
    """
    Resolves the best available soil profile for a given request.
    Resolution priority:
      1. Soil Health Card (supplied by caller)
      2. District average (loaded from YAML)
      3. Questionnaire fallback (qualitative only)
    """

    def __init__(self, district_averages: Optional[DistrictAverages] = None) -> None:
        self._district_data = district_averages or _district_data

    def resolve(self, request: RecommendRequest) -> SoilProfile:
        log.info(
            "soil_resolution_start",
            district=request.district.value,
            soil_source=request.soil_source.value,
        )

        if request.soil_source == SoilSource.SOIL_HEALTH_CARD:
            return self._from_soil_health_card(request.soil)

        if request.soil_source == SoilSource.DISTRICT_AVERAGE:
            return self._from_district_average(request.district)

        # QUESTIONNAIRE_FALLBACK
        return self._from_questionnaire(request)

    # ── private helpers ────────────────────────────────────────────────────

    def _from_soil_health_card(self, soil: SoilInput) -> SoilProfile:
        return SoilProfile(
            nitrogen=soil.nitrogen,
            phosphorus=soil.phosphorus,
            potassium=soil.potassium,
            ph=soil.ph,
            organic_carbon=soil.organic_carbon,
            source=SoilSource.SOIL_HEALTH_CARD,
            reliability_note=(
                "Soil Health Card — lab-measured values. "
                "Highest reliability source."
            ),
        )

    def _from_district_average(self, district: District) -> SoilProfile:
        vals = self._district_data.get_soil_values(district.value)
        has_data = any(v is not None for v in vals.values())

        return SoilProfile(
            nitrogen=vals.get("nitrogen"),
            phosphorus=vals.get("phosphorus"),
            potassium=vals.get("potassium"),
            ph=vals.get("ph"),
            organic_carbon=vals.get("organic_carbon"),
            source=SoilSource.DISTRICT_AVERAGE,
            reliability_note=(
                f"District average for {district.value} — loaded from YAML."
                if has_data
                else (
                    "District average — ⚠️ PLACEHOLDER. "
                    "Real PAU/ICAR district soil survey data not yet loaded."
                )
            ),
        )

    def _from_questionnaire(self, request: RecommendRequest) -> SoilProfile:
        """
        Questionnaire answers cannot provide N/P/K values.
        The profile will have None for all nutrient fields.
        The questionnaire context is logged for future model features.
        """
        log.warning(
            "soil_resolution_questionnaire_fallback",
            district=request.district.value,
            message=(
                "Questionnaire fallback used. N/P/K are unknown. "
                "STCR cannot be computed without soil nutrient data."
            ),
        )
        return SoilProfile(
            nitrogen=None,
            phosphorus=None,
            potassium=None,
            ph=None,
            organic_carbon=None,
            source=SoilSource.QUESTIONNAIRE_FALLBACK,
            reliability_note=(
                "Questionnaire fallback — farmer-observable symptoms only. "
                "N/P/K are unknown. STCR dose cannot be computed. "
                "Recommendation will be flagged as low-confidence."
            ),
        )
