"""Recommendation model — persisted recommendation with full provenance chain."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Recommendation(TimestampMixin, Base):
    """
    Persisted recommendation with complete provenance chain.

    Every recommendation is traceable to:
      Farmer → Location → SoilTest → STCRConfiguration → ModelVersion
    """
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Foreign keys — all nullable for flexibility
    farmer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("farmers.id"), nullable=True
    )
    location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )
    soil_test_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("soil_tests.id"), nullable=True
    )
    stcr_config_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stcr_configurations.id"), nullable=True
    )
    model_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("model_versions.id"), nullable=True
    )

    # Request context
    crop: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=False)
    soil_source: Mapped[str] = mapped_column(String(50), nullable=False)

    # STCR baseline
    stcr_n_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stcr_p2o5_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stcr_k2o_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ML corrections
    ml_correction_n: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_correction_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_correction_k: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Final recommendation
    final_n_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_p2o5_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_k2o_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Full request payload for auditability"
    )

    # Relationships
    farmer: Mapped[Optional["Farmer"]] = relationship(back_populates="recommendations")
    location: Mapped[Optional["Location"]] = relationship(back_populates="recommendations")
    soil_test: Mapped[Optional["SoilTest"]] = relationship(back_populates="recommendations")
    stcr_config: Mapped[Optional["STCRConfiguration"]] = relationship(back_populates="recommendations")
    model_version: Mapped[Optional["ModelVersion"]] = relationship(back_populates="recommendations")
    items: Mapped[List["RecommendationItem"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Recommendation(id={self.id!r}, crop={self.crop!r}, "
            f"placeholder={self.is_placeholder})>"
        )
