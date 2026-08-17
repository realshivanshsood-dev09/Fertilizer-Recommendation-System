"""
Fertilizer Translation Service
================================
Translates abstract N/P/K doses (kg/ha) into specific commercial fertilizer
products available in the Malwa region (e.g. Urea, DAP, MOP, SSP).

⚠️  PLACEHOLDER — Product list, pricing, and splitting logic are not yet
    populated.  See docs/science_status.md §4.

The eventual logic will:
  1. Select the most economical product mix to meet N/P/K targets
  2. Apply split-application rules per crop × growth stage
  3. Use current market prices from a configurable price database
"""

from __future__ import annotations

import structlog
from typing import List, Optional

from app.core.constants import Crop
from app.schemas.response import ApplicationTiming, FertilizerProduct

log = structlog.get_logger(__name__)


# ── Placeholder product catalogue ─────────────────────────────────────────────
# ⚠️  PLACEHOLDER — real product list and prices not yet loaded.
# Each entry: {name, nutrient_pct: {N, P2O5, K2O}, price_inr_per_50kg_bag}
_PRODUCT_CATALOGUE: list[dict] = [
    # {
    #     "name": "Urea (46-0-0)",
    #     "nutrient_pct": {"N": 46.0, "P2O5": 0.0, "K2O": 0.0},
    #     "price_inr_per_50kg_bag": None,   # PLACEHOLDER
    # },
    # {
    #     "name": "DAP (18-46-0)",
    #     "nutrient_pct": {"N": 18.0, "P2O5": 46.0, "K2O": 0.0},
    #     "price_inr_per_50kg_bag": None,   # PLACEHOLDER
    # },
    # {
    #     "name": "MOP (0-0-60)",
    #     "nutrient_pct": {"N": 0.0, "P2O5": 0.0, "K2O": 60.0},
    #     "price_inr_per_50kg_bag": None,   # PLACEHOLDER
    # },
]


class FertilizerTranslationService:
    """
    Converts N/P/K kg/ha doses into commercial product quantities.

    Returns empty lists and None costs until the product catalogue and
    pricing are populated.
    """

    def translate(
        self,
        crop: Crop,
        N_kg_per_ha: Optional[float],
        P2O5_kg_per_ha: Optional[float],
        K2O_kg_per_ha: Optional[float],
    ) -> tuple[List[FertilizerProduct], Optional[float]]:
        """
        Returns (product_list, total_cost_inr_per_ha).
        Both will be empty / None until the catalogue is populated.
        """
        log.info(
            "fertilizer_translation",
            crop=crop.value,
            N=N_kg_per_ha,
            P=P2O5_kg_per_ha,
            K=K2O_kg_per_ha,
        )

        if not _PRODUCT_CATALOGUE:
            log.warning(
                "fertilizer_translation_placeholder",
                reason="Product catalogue is empty — translation not implemented.",
            )
            return [], None

        # Future: optimal blending logic here
        return [], None

    def get_application_timing(self, crop: Crop) -> ApplicationTiming:
        """
        Returns crop-specific split-application schedule.
        ⚠️  PLACEHOLDER — timing tables not yet loaded.
        """
        return ApplicationTiming(
            splits=None,
            apply_before=None,
            notes=(
                f"PLACEHOLDER — application timing for {crop.value} not yet loaded. "
                "PAU crop-stage fertilizer schedules required."
            ),
        )
