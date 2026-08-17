"""WeatherObservation model — weather data for location-based recommendations."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class WeatherObservation(TimestampMixin, Base):
    """
    Weather observation record.
    Structure only — no weather API integration yet.
    """
    __tablename__ = "weather_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    temp_max_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_min_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="E.g. IMD, OpenWeather"
    )
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    location: Mapped[Optional["Location"]] = relationship(back_populates="weather_observations")

    def __repr__(self) -> str:
        return (
            f"<WeatherObservation(district={self.district!r}, "
            f"at={self.observed_at}, rain={self.rainfall_mm}mm)>"
        )
