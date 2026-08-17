"""RecommendationItem model — individual product/timing outputs within a recommendation."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class RecommendationItem(TimestampMixin, Base):
    """
    Individual output line within a Recommendation.
    Supports: fertilizer products, biofertilizers, and timing entries.
    """
    __tablename__ = "recommendation_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="fertilizer | biofertilizer | timing"
    )
    product_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    nutrient_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="N | P | K | complex"
    )
    quantity_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_cost_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    application_timing: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    recommendation: Mapped["Recommendation"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<RecommendationItem(type={self.item_type!r}, "
            f"product={self.product_name!r})>"
        )
