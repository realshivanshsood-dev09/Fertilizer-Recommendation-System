"""
Study repository (Track B field trial provenance).
"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import Study
from app.repositories.base import BaseRepository


class StudyRepository(BaseRepository[Study]):
    model = Study

    async def get_by_doi(self, doi: str) -> Optional[Study]:
        """Lookup a study by DOI (unique identifier)."""
        result = await self._session.execute(
            select(Study).where(Study.doi == doi)
        )
        return result.scalar_one_or_none()

    async def get_with_trials(self, study_id: str) -> Optional[Study]:
        """Fetch a study with all its field trial observations eagerly loaded."""
        result = await self._session.execute(
            select(Study)
            .where(Study.id == study_id)
            .options(selectinload(Study.field_trials))
        )
        return result.scalar_one_or_none()

    async def list_verified(self) -> Sequence[Study]:
        """Return all studies with verification_status = 'verified'."""
        result = await self._session.execute(
            select(Study).where(Study.verification_status == "verified")
        )
        return result.scalars().all()
