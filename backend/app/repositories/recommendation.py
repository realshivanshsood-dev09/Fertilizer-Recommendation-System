"""
Recommendation repository.
Handles persistence and retrieval of Recommendation records with full provenance chain.
"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.models.recommendation_item import RecommendationItem
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    async def get_with_provenance(self, recommendation_id: str) -> Optional[Recommendation]:
        """
        Fetch a recommendation with its full provenance chain eagerly loaded:
          Recommendation → items, soil_test, stcr_config, model_version, location, farmer
        """
        result = await self._session.execute(
            select(Recommendation)
            .where(Recommendation.id == recommendation_id)
            .options(
                selectinload(Recommendation.items),
                selectinload(Recommendation.soil_test),
                selectinload(Recommendation.stcr_config),
                selectinload(Recommendation.model_version),
                selectinload(Recommendation.location),
                selectinload(Recommendation.farmer),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_crop(self, crop: str, limit: int = 100) -> Sequence[Recommendation]:
        """Return recommendations filtered by crop."""
        result = await self._session.execute(
            select(Recommendation)
            .where(Recommendation.crop == crop)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_with_items(
        self,
        recommendation: Recommendation,
        items: list[RecommendationItem],
    ) -> Recommendation:
        """
        Persist a recommendation and its associated items atomically.
        The items must already have recommendation_id set.
        """
        self._session.add(recommendation)
        await self._session.flush()  # assigns recommendation.id if not pre-set
        for item in items:
            item.recommendation_id = recommendation.id
            self._session.add(item)
        await self._session.flush()
        return recommendation
