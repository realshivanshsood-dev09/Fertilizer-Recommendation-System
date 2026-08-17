"""
Base repository with common CRUD operations.
All concrete repositories inherit from this class.
"""
from __future__ import annotations

from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository providing basic CRUD for a SQLAlchemy model.
    Subclass and set `model` to the concrete ORM class.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, record_id: str) -> Optional[ModelT]:
        """Fetch a single record by primary key; returns None if not found."""
        return await self._session.get(self.model, record_id)

    async def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Return a paginated list of records ordered by primary key."""
        result = await self._session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def add(self, instance: ModelT) -> ModelT:
        """Persist a new record. Session commit is the caller's responsibility."""
        self._session.add(instance)
        await self._session.flush()  # assigns DB-generated values without committing
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete a record. Session commit is the caller's responsibility."""
        await self._session.delete(instance)
        await self._session.flush()
