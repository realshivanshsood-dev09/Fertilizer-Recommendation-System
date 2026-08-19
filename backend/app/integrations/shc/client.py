"""
Abstract SHC Client Interface
==============================
Defines the standard contract for Soil Health Card retrieval.
Production deployments can substitute live SOAP/REST credentials here without
affecting the recommendation pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from app.integrations.shc.schemas import NormalizedSoilHealthCard


class SHCClientBase(ABC):
    """Abstract client for querying Soil Health Card data."""

    @abstractmethod
    async def get_soil_health_card(self, card_number: str) -> Optional[NormalizedSoilHealthCard]:
        """Fetches and normalizes a Soil Health Card by card number."""
        pass
