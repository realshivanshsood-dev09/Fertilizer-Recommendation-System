"""
STCR Baseline Service
=====================
Computes the agronomic fertilizer baseline using Soil Test Crop Response (STCR)
methodology as published by PAU Ludhiana / ICAR.

⚠️  PLACEHOLDER — This module is a STRUCTURAL STUB.
    The STCR equations, coefficients, and target yield values for wheat, rice,
    and cotton in the Malwa region of Punjab are NOT yet available in this
    codebase.  See docs/science_status.md for a complete list of what is needed.

    DO NOT USE THE OUTPUT OF THIS MODULE FOR ANY REAL AGRONOMIC DECISION.
    All STCRBaseline objects returned here have is_placeholder=True and
    numerical doses set to None.

Data source:
    Coefficients are loaded from agronomy/stcr/stcr_coefficients.yaml
    (SINGLE SOURCE OF TRUTH — no hardcoded duplicates in this module).
"""

from __future__ import annotations

import structlog
from typing import Optional

from app.core.constants import Crop, District, Season
from app.core.data_loader import STCRCoefficients, load_stcr_coefficients
from app.schemas.response import STCRBaseline
from app.services.soil_resolution import SoilProfile

log = structlog.get_logger(__name__)

# ── Load coefficients from YAML (single source of truth) ─────────────────────
_stcr_data: STCRCoefficients = load_stcr_coefficients()


def _stcr_dose(
    a: Optional[float],
    b: Optional[float],
    soil_test_value: Optional[float],
    target_yield: Optional[float],
    fue: Optional[float],
) -> Optional[float]:
    """
    Generic STCR dose formula (structure only).

    The standard STCR formula is:
        Dose (kg/ha) = (a × T − b × S) / FUE
    where:
        a   = nutrient requirement per unit target yield
        T   = target yield (Mg/ha)
        S   = soil test value (kg/ha, appropriate units)
        FUE = fertilizer use efficiency (fraction, 0–1)

    Returns None if any required parameter is None.
    """
    if any(v is None for v in [a, b, soil_test_value, target_yield, fue]):
        return None
    # Structural formula — will only execute once real coefficients are loaded
    dose = (a * target_yield - b * soil_test_value) / fue  # type: ignore[operator]
    return max(0.0, dose)  # doses cannot be negative


class STCRService:
    """
    Computes STCR fertilizer baseline doses.

    Returns an STCRBaseline with None values and a clear placeholder message
    until real coefficients are loaded.
    """

    def __init__(self, stcr_coefficients: Optional[STCRCoefficients] = None) -> None:
        self._coeffs = stcr_coefficients or _stcr_data

    def compute(
        self,
        crop: Crop,
        district: District,
        season: Season,
        soil: SoilProfile,
    ) -> STCRBaseline:
        log.info(
            "stcr_compute",
            crop=crop.value,
            district=district.value,
            soil_source=soil.source.value,
            soil_complete_for_stcr=soil.is_complete_for_stcr(),
            coefficients_populated=self._coeffs.is_populated,
        )

        if not soil.is_complete_for_stcr():
            log.warning(
                "stcr_skipped_incomplete_soil",
                reason=(
                    "STCR requires soil N, P, K.  "
                    f"Source '{soil.source.value}' did not provide them."
                ),
            )
            return STCRBaseline(
                N_kg_per_ha=None,
                P2O5_kg_per_ha=None,
                K2O_kg_per_ha=None,
                equation_version="PLACEHOLDER",
                data_source="STCR skipped — soil N/P/K not available",
                notes=(
                    f"Soil source '{soil.source.value}' did not provide N/P/K. "
                    "STCR cannot be evaluated."
                ),
            )

        # Map Crop enum to YAML key name
        crop_name = crop.value  # "wheat", "rice", "cotton"

        n_coeffs = self._coeffs.get_nutrient_coefficients(crop_name, "N")
        p_coeffs = self._coeffs.get_nutrient_coefficients(crop_name, "P")
        k_coeffs = self._coeffs.get_nutrient_coefficients(crop_name, "K")

        n_dose = _stcr_dose(
            n_coeffs.get("a"),
            n_coeffs.get("b"),
            soil.nitrogen,
            n_coeffs.get("target_yield_Mg_per_ha"),
            n_coeffs.get("FUE"),
        )
        p_dose = _stcr_dose(
            p_coeffs.get("a"),
            p_coeffs.get("b"),
            soil.phosphorus,
            p_coeffs.get("target_yield_Mg_per_ha"),
            p_coeffs.get("FUE"),
        )
        k_dose = _stcr_dose(
            k_coeffs.get("a"),
            k_coeffs.get("b"),
            soil.potassium,
            k_coeffs.get("target_yield_Mg_per_ha"),
            k_coeffs.get("FUE"),
        )

        source_note = self._coeffs.get_source_note(crop_name)

        is_populated = self._coeffs.is_populated
        equation_version = (
            f"STCR v{self._coeffs.metadata.get('schema_version', '?')}"
            if is_populated
            else "PLACEHOLDER — coefficients not yet loaded"
        )
        notes = (
            f"STCR baseline computed for {crop_name} using loaded coefficients."
            if is_populated
            else (
                "STCR coefficients are placeholders. "
                "All doses are None until real PAU/ICAR values are provided."
            )
        )

        return STCRBaseline(
            N_kg_per_ha=n_dose,
            P2O5_kg_per_ha=p_dose,
            K2O_kg_per_ha=k_dose,
            equation_version=equation_version,
            data_source=source_note,
            notes=notes,
        )
