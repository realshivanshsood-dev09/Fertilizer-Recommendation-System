"""
Soil Health Card Integration Service
====================================
Orchestrates client lookups, validation, and status wrapping.
"""

from __future__ import annotations

from typing import Optional
import structlog

from app.integrations.shc.client import SHCClientBase
from app.integrations.shc.mock_client import MockSHCClient
from app.integrations.shc.schemas import NormalizedSoilHealthCard, SHCLookupResponse

log = structlog.get_logger(__name__)


class SHCIntegrationService:
    """High-level service managing Soil Health Card lookups."""

    def __init__(self, client: Optional[SHCClientBase] = None) -> None:
        self.client = client or MockSHCClient()

    async def lookup_card(self, card_number: str) -> SHCLookupResponse:
        if not card_number or len(card_number.strip()) < 3:
            return SHCLookupResponse(
                card_number=card_number or "",
                status="invalid_card_number",
                is_mock=True,
                source="SIH_DEMO_MOCK_SHC",
                error_message="Invalid Soil Health Card number format.",
            )

        card = await self.client.get_soil_health_card(card_number)
        if card is None:
            return SHCLookupResponse(
                card_number=card_number,
                status="not_found",
                is_mock=True,
                source="SIH_DEMO_MOCK_SHC",
                error_message=f"Soil Health Card '{card_number}' not found in mock database.",
            )

        status = "found" if card.is_complete else "incomplete"
        return SHCLookupResponse(
            card_number=card.card_number,
            status=status,
            is_mock=card.is_mock,
            source=card.source,
            card=card,
        )
