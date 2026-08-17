"""Farmer model — minimal farmer record without sensitive personal data."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Farmer(TimestampMixin, Base):
    __tablename__ = "farmers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True,
        comment="External farmer registry ID (future integration)"
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )
    consent_recorded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    location: Mapped[Optional["Location"]] = relationship(back_populates="farmers")
    soil_tests: Mapped[list["SoilTest"]] = relationship(back_populates="farmer")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="farmer")

    def __repr__(self) -> str:
        return f"<Farmer(id={self.id!r}, external_id={self.external_id!r})>"
