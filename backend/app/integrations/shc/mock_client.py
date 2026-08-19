"""
Mock SHC Client Implementation
==============================
Loads deterministic sandbox fixtures from data/mock/shc/shc_records.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import structlog
import yaml

from app.integrations.shc.client import SHCClientBase
from app.integrations.shc.schemas import (
    NormalizedSoilHealthCard,
    SHCLocation,
    SHCSoilNutrients,
)

log = structlog.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_MOCK_SHC_PATH = _PROJECT_ROOT / "data" / "mock" / "shc" / "shc_records.yaml"


class MockSHCClient(SHCClientBase):
    """
    Mock client that reads local mock fixtures for sandbox demonstration.
    """

    def __init__(self, fixture_path: Optional[Path] = None) -> None:
        self._path = fixture_path or _MOCK_SHC_PATH
        self._records: Dict[str, Any] = {}
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if not self._path.exists():
            log.warning("mock_shc_fixture_not_found", path=str(self._path))
            return
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            self._records = data.get("records", {})
            log.info("mock_shc_fixtures_loaded", count=len(self._records))

    async def get_soil_health_card(self, card_number: str) -> Optional[NormalizedSoilHealthCard]:
        clean_num = card_number.strip().upper()
        raw = self._records.get(clean_num)
        if not raw:
            log.info("mock_shc_not_found", card_number=card_number)
            return None

        card = NormalizedSoilHealthCard(
            card_number=raw["card_number"],
            farmer_identifier=raw.get("farmer_identifier"),
            farmer_name=raw.get("farmer_name"),
            sample_id=raw.get("sample_id"),
            sample_date=raw.get("sample_date"),
            location=SHCLocation(
                state=raw.get("state", "Punjab"),
                district=raw.get("district", "Bathinda"),
                block=raw.get("block"),
                village=raw.get("village"),
            ),
            soil=SHCSoilNutrients(
                N_kg_ha=raw.get("soil_N_kg_ha"),
                P_kg_ha=raw.get("soil_P_kg_ha"),
                K_kg_ha=raw.get("soil_K_kg_ha"),
                pH=raw.get("pH"),
                organic_carbon=raw.get("organic_carbon"),
                electrical_conductivity=raw.get("electrical_conductivity"),
            ),
            source="SIH_DEMO_MOCK_SHC",
            verification_status=raw.get("verification_status", "verified_mock_record"),
            is_mock=True,
            is_complete=raw.get("is_complete", True),
        )
        log.info("mock_shc_retrieved", card_number=card_number, is_complete=card.is_complete)
        return card
