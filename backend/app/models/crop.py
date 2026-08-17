"""Crop metadata model."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, generate_uuid


class CropRecord(TimestampMixin, Base):
    """Database record for crop metadata. Named CropRecord to avoid collision with the Pydantic Crop enum."""
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    scientific_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CropRecord(name={self.name!r}, season={self.season!r})>"
