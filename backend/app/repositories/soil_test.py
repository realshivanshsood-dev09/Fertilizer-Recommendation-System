"""
SoilTest repository.
"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soil_test import SoilTest
from app.repositories.base import BaseRepository


class SoilTestRepository(BaseRepository[SoilTest]):
    model = SoilTest

    async def list_by_farmer(self, farmer_id: str) -> Sequence[SoilTest]:
        """Return all soil tests for a given farmer."""
        result = await self._session.execute(
            select(SoilTest).where(SoilTest.farmer_id == farmer_id)
        )
        return result.scalars().all()

    async def list_by_source(self, soil_source: str, limit: int = 100) -> Sequence[SoilTest]:
        """Return soil tests filtered by provenance source."""
        result = await self._session.execute(
            select(SoilTest)
            .where(SoilTest.soil_source == soil_source)
            .limit(limit)
        )
        return result.scalars().all()
