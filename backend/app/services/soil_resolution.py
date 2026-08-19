"""
Soil Resolution Service
=======================
Resolves a SoilProfile following the strict Track B1 hierarchy:
  Level A: Farmer Soil Health Card record (lab-measured N/P/K)
        ↓
  Level B: Verified SHC district prior (if populated with verified survey data)
        ↓
  Level C: Explicit questionnaire / qualitative fallback (N/P/K unknown)
        ↓
  Level D: Unknown / Insufficient data

Every resolved profile exposes:
  - source: SoilSource enum
  - is_lab_measured: bool (True ONLY for verified farmer laboratory tests)
  - confidence: float score in [0.0, 1.0]
  - status: 'measured' | 'prior_estimate' | 'qualitative_only' | 'insufficient_data'
  - provenance: descriptive text and source reference
  - reliability_note: plain-language explanation of reliability and limitations.
"""

from __future__ import annotations

import structlog
from typing import Optional

from app.core.constants import District, SoilSource
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
        is_lab_measured: bool = False,
        confidence: float = 0.0,
        status: str = "unknown",
        provenance: Optional[str] = None,
    ) -> None:
        self.nitrogen = nitrogen
        self.phosphorus = phosphorus
        self.potassium = potassium
        self.ph = ph
        self.organic_carbon = organic_carbon
        self.source = source
        self.reliability_note = reliability_note
        self.is_lab_measured = is_lab_measured
        self.confidence = confidence
        self.status = status
        self.provenance = provenance

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
            f"status={self.status}, lab_measured={self.is_lab_measured}, "
            f"N={self.nitrogen}, P={self.phosphorus}, K={self.potassium}, "
            f"pH={self.ph}, OC={self.organic_carbon}, conf={self.confidence})"
        )


class SoilResolutionService:
    """
    Resolves the best available soil profile for a given request.
    Resolution priority:
      1. Soil Health Card (supplied by caller with lab measurements)
      2. District prior (loaded from YAML if verified data exists)
      3. Questionnaire fallback (qualitative symptoms only)
      4. Insufficient data state
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
            return self._from_soil_health_card(request.soil, request.district)

        if request.soil_source == SoilSource.DISTRICT_AVERAGE:
            return self._from_district_average(request.district)

        # QUESTIONNAIRE_FALLBACK
        return self._from_questionnaire(request)

    # ── private helpers ────────────────────────────────────────────────────

    def _from_soil_health_card(self, soil: SoilInput, district: District) -> SoilProfile:
        # Check if farmer provided explicit measurements
        has_npk = all(
            v is not None for v in [soil.nitrogen, soil.phosphorus, soil.potassium]
        )

        if has_npk:
            return SoilProfile(
                nitrogen=soil.nitrogen,
                phosphorus=soil.phosphorus,
                potassium=soil.potassium,
                ph=soil.ph,
                organic_carbon=soil.organic_carbon,
                source=SoilSource.SOIL_HEALTH_CARD,
                is_lab_measured=True,
                confidence=0.95,
                status="measured",
                provenance="Farmer Soil Health Card (individual lab test)",
                reliability_note=(
                    "Soil Health Card — laboratory-measured values. "
                    "Highest reliability source for STCR calculation."
                ),
            )

        # Farmer chose SHC but values are missing: attempt Level B fallback to district prior
        log.warning(
            "soil_resolution_shc_incomplete_attempting_fallback",
            district=district.value,
        )
        district_profile = self._from_district_average(district)
        if district_profile.is_complete_for_stcr():
            district_profile.reliability_note = (
                f"Soil Health Card was incomplete; fell back to district prior for {district.value}."
            )
            return district_profile

        # Level D: insufficient data
        return SoilProfile(
            nitrogen=soil.nitrogen,
            phosphorus=soil.phosphorus,
            potassium=soil.potassium,
            ph=soil.ph,
            organic_carbon=soil.organic_carbon,
            source=SoilSource.SOIL_HEALTH_CARD,
            is_lab_measured=False,
            confidence=0.0,
            status="insufficient_data",
            provenance="Farmer Soil Health Card (missing N/P/K)",
            reliability_note=(
                "Soil Health Card was selected but N/P/K values are missing and "
                f"district prior for {district.value} is not yet populated. "
                "STCR baseline cannot be evaluated."
            ),
        )

    def _from_district_average(self, district: District) -> SoilProfile:
        vals = self._district_data.get_soil_values(district.value)
        has_data = any(v is not None for v in vals.values())
        has_complete_npk = all(
            vals.get(k) is not None for k in ["nitrogen", "phosphorus", "potassium"]
        )

        if has_complete_npk:
            return SoilProfile(
                nitrogen=vals.get("nitrogen"),
                phosphorus=vals.get("phosphorus"),
                potassium=vals.get("potassium"),
                ph=vals.get("ph"),
                organic_carbon=vals.get("organic_carbon"),
                source=SoilSource.DISTRICT_AVERAGE,
                is_lab_measured=False,
                confidence=0.60,
                status="prior_estimate",
                provenance=f"District soil survey prior ({district.value})",
                reliability_note=(
                    f"District average for {district.value} — aggregate prior estimate. "
                    "Not directly measured on farmer's field."
                ),
            )

        # Placeholder / unpopulated district values
        return SoilProfile(
            nitrogen=vals.get("nitrogen"),
            phosphorus=vals.get("phosphorus"),
            potassium=vals.get("potassium"),
            ph=vals.get("ph"),
            organic_carbon=vals.get("organic_carbon"),
            source=SoilSource.DISTRICT_AVERAGE,
            is_lab_measured=False,
            confidence=0.0,
            status="insufficient_data" if not has_data else "partial_data",
            provenance=f"District soil registry ({district.value})",
            reliability_note=(
                f"District average for {district.value} is a placeholder awaiting "
                "official Soil Health Card survey dataset."
            ),
        )

    def _from_questionnaire(self, request: RecommendRequest) -> SoilProfile:
        """
        Questionnaire answers cannot substitute for N/P/K measurements.
        """
        log.warning(
            "soil_resolution_questionnaire_fallback",
            district=request.district.value,
            message="Questionnaire fallback used. N/P/K are unknown.",
        )
        return SoilProfile(
            nitrogen=None,
            phosphorus=None,
            potassium=None,
            ph=None,
            organic_carbon=None,
            source=SoilSource.QUESTIONNAIRE_FALLBACK,
            is_lab_measured=False,
            confidence=0.20,
            status="qualitative_only",
            provenance="Farmer questionnaire / visual crop inspection",
            reliability_note=(
                "Questionnaire fallback — farmer-observable symptoms only. "
                "N/P/K are unknown. STCR dose cannot be computed."
            ),
        )
