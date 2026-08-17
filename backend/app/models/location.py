"""Location model — geographic reference for all entities."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Location(TimestampMixin, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    state: Mapped[str] = mapped_column(String(100), default="Punjab", nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    block: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    village: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # PostGIS geometry — production only (PostgreSQL + PostGIS)
    # geom column is added via Alembic migration for PostgreSQL deployments.
    # Not represented here to avoid SQLite import errors.

    # Relationships
    farmers: Mapped[list["Farmer"]] = relationship(back_populates="location")
    soil_tests: Mapped[list["SoilTest"]] = relationship(back_populates="location")
    weather_observations: Mapped[list["WeatherObservation"]] = relationship(back_populates="location")
    field_trials: Mapped[list["FieldTrialObservation"]] = relationship(back_populates="location")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="location")

    __table_args__ = (
        Index("ix_locations_district_block", "district", "block"),
    )

    def __repr__(self) -> str:
        return f"<Location(id={self.id!r}, district={self.district!r}, block={self.block!r})>"
