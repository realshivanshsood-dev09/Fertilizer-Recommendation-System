"""
ModelVersion repository.
Manages the ML model registry.
"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_version import ModelVersion
from app.repositories.base import BaseRepository


class ModelVersionRepository(BaseRepository[ModelVersion]):
    model = ModelVersion

    async def get_active(self, model_type: str) -> Optional[ModelVersion]:
        """Return the currently active model for a given model_type."""
        result = await self._session.execute(
            select(ModelVersion)
            .where(
                ModelVersion.model_type == model_type,
                ModelVersion.is_active == True,  # noqa: E712
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_type(self, model_type: str) -> Sequence[ModelVersion]:
        """Return all versions of a model type, newest first."""
        result = await self._session.execute(
            select(ModelVersion)
            .where(ModelVersion.model_type == model_type)
            .order_by(ModelVersion.created_at.desc())
        )
        return result.scalars().all()
