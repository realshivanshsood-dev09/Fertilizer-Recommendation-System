"""
Domain constants — districts, crops, seasons, soil-source categories.
All values are authoritative and correspond to real administrative/agronomic categories.
"""

from __future__ import annotations

from enum import Enum


class District(str, Enum):
    BATHINDA = "Bathinda"
    MANSA = "Mansa"
    MUKTSAR = "Muktsar"
    MOGA = "Moga"
    FARIDKOT = "Faridkot"


class Crop(str, Enum):
    WHEAT = "wheat"
    RICE = "rice"
    COTTON = "cotton"


class Season(str, Enum):
    RABI = "rabi"      # Oct–Mar  (wheat)
    KHARIF = "kharif"  # Jun–Nov  (rice, cotton)
    ZAID = "zaid"      # Mar–Jun  (minor summer crops)


class IrrigationType(str, Enum):
    TUBE_WELL = "tube_well"
    CANAL = "canal"
    RAINFED = "rainfed"
    DRIP = "drip"
    SPRINKLER = "sprinkler"


class SoilSource(str, Enum):
    """
    Provenance of the soil data.
    The system must carry this through to the final response.
    Different sources have different reliability:
      soil_health_card  → lab-measured N/P/K (highest reliability)
      district_average  → aggregated block/district mean (medium reliability)
      questionnaire_fallback → derived from farmer observations (lowest reliability)
    """
    SOIL_HEALTH_CARD = "soil_health_card"
    DISTRICT_AVERAGE = "district_average"
    QUESTIONNAIRE_FALLBACK = "questionnaire_fallback"


# Crop × Season validity matrix (agronomically valid combinations for Malwa)
VALID_CROP_SEASONS: dict[Crop, list[Season]] = {
    Crop.WHEAT: [Season.RABI],
    Crop.RICE: [Season.KHARIF],
    Crop.COTTON: [Season.KHARIF],
}
