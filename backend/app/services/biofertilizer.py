"""
Biofertilizer Recommendation Service
======================================
Recommends bio-inoculants (Rhizobium, Azotobacter, PSB, etc.) based on
crop type and district.

⚠️  PLACEHOLDER — Specific strains, product names, and doses recommended by
    PAU for wheat, rice, and cotton in Malwa are NOT yet loaded.
    See docs/science_status.md §5.

All returned values are None / empty until authoritative PAU data is loaded.

Data source:
    Biofertilizer data is loaded from data/agronomy/biofertilizers.yaml
    (SINGLE SOURCE OF TRUTH — no hardcoded duplicates in this module).
"""

from __future__ import annotations

import structlog
from typing import Optional

from app.core.constants import Crop, District
from app.core.data_loader import BiofertilizerData, load_biofertilizer_data
from app.schemas.response import BiofertilizerRecommendation

log = structlog.get_logger(__name__)

# ── Load biofertilizer data from YAML (single source of truth) ───────────────
_biofert_data: BiofertilizerData = load_biofertilizer_data()


class BiofertilizerService:
    """
    Returns biofertilizer recommendations for a given crop and district.
    All values are placeholder until PAU data is loaded.
    """

    def __init__(self, biofert_data: Optional[BiofertilizerData] = None) -> None:
        self._data = biofert_data or _biofert_data

    def recommend(self, crop: Crop, district: District) -> BiofertilizerRecommendation:
        log.info("biofertilizer_recommend", crop=crop.value, district=district.value)

        entry = self._data.get_crop(crop.value)
        return BiofertilizerRecommendation(
            recommended=entry.get("inoculants", []),
            application_timing=entry.get("timing"),
            data_source=(
                entry.get("source")
                or f"PLACEHOLDER — biofertilizer data for {crop.value} not loaded"
            ),
        )
