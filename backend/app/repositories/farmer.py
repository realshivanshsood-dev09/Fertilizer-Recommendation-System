"""
Farmer repository.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farmer import Farmer
from app.repositories.base import BaseRepository


class FarmerRepository(BaseRepository[Farmer]):
    model = Farmer

    async def get_by_external_id(self, external_id: str) -> Optional[Farmer]:
        """Lookup a farmer by their external registry ID."""
        result = await self._session.execute(
            select(Farmer).where(Farmer.external_id == external_id)
        )
        return result.scalar_one_or_none()
