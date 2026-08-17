"""FieldTrialObservation model — individual experimental observations for Track B ML training."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class FieldTrialObservation(TimestampMixin, Base):
    """
    Individual field trial observation.

    All measurement fields are nullable because different studies
    record different variables. The schema supports heterogeneous
    but well-documented field trials.

    Every observation should reference a Study for provenance.
    """
    __tablename__ = "field_trial_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    study_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("studies.id"), nullable=True
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )

    # Crop and season
    crop: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    season: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Soil measurements
    soil_n: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Available N (kg/ha)")
    soil_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Available P2O5 (kg/ha)")
    soil_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Available K2O (kg/ha)")
    ph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    organic_carbon: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Organic carbon (%)")

    # Fertilizer treatments
    fertilizer_n: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Applied N (kg/ha)")
    fertilizer_p2o5: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Applied P2O5 (kg/ha)")
    fertilizer_k2o: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Applied K2O (kg/ha)")
    organic_input_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    residue_input_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    irrigation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Yield
    target_yield_mg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observed_yield_mg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Nutrient uptake
    nutrient_uptake_n: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Total N uptake (kg/ha)")
    nutrient_uptake_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Total P uptake (kg/ha)")
    nutrient_uptake_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Total K uptake (kg/ha)")

    # Experimental details
    treatment_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replications: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    study: Mapped[Optional["Study"]] = relationship(back_populates="field_trials")
    location: Mapped[Optional["Location"]] = relationship(back_populates="field_trials")

    def __repr__(self) -> str:
        return (
            f"<FieldTrialObservation(id={self.id!r}, crop={self.crop!r}, "
            f"yield={self.observed_yield_mg_per_ha})>"
        )
