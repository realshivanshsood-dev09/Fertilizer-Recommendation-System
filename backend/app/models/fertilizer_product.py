"""FertilizerProduct model — commercial fertilizer product catalog."""
from __future__ import annotations

from typing import Optional, List

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class FertilizerProductRecord(TimestampMixin, Base):
    """
    Commercial fertilizer product.
    Named FertilizerProductRecord to avoid collision with the Pydantic FertilizerProduct schema.
    """
    __tablename__ = "fertilizer_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    product_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    n_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    p2o5_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    k2o_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bag_size_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    prices: Mapped[List["FertilizerPrice"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return (
            f"<FertilizerProductRecord(name={self.product_name!r}, "
            f"N={self.n_pct}% P={self.p2o5_pct}% K={self.k2o_pct}%)>"
        )
