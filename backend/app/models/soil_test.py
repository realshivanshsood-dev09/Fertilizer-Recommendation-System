"""SoilTest model — laboratory or estimated soil measurements with provenance."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class SoilTest(TimestampMixin, Base):
    """
    Soil test record.

    soil_source is a free string to support extensible categories:
      soil_health_card, government_lab, icar_kvk, pau_lab,
      research_trial, district_average, questionnaire_fallback

    is_lab_measured must be True ONLY for actual laboratory results.
    Questionnaire-derived data must NEVER have is_lab_measured=True.
    """
    __tablename__ = "soil_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    farmer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("farmers.id"), nullable=True
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )
    soil_source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Provenance category: soil_health_card, government_lab, icar_kvk, pau_lab, research_trial, district_average, questionnaire_fallback"
    )
    test_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    nitrogen_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phosphorus_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    potassium_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    organic_carbon_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_identifier: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="E.g. Soil Health Card number, lab report ID"
    )
    units_note: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="Description of measurement units and methods"
    )
    is_lab_measured: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True only for actual laboratory results"
    )
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    farmer: Mapped[Optional["Farmer"]] = relationship(back_populates="soil_tests")
    location: Mapped[Optional["Location"]] = relationship(back_populates="soil_tests")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="soil_test")

    def __repr__(self) -> str:
        return (
            f"<SoilTest(id={self.id!r}, source={self.soil_source!r}, "
            f"N={self.nitrogen_kg_per_ha}, P={self.phosphorus_kg_per_ha}, K={self.potassium_kg_per_ha})>"
        )
