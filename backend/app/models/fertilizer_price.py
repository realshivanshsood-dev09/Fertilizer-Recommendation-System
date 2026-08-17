"""FertilizerPrice model — time-varying pricing with geographic scope."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class FertilizerPrice(TimestampMixin, Base):
    """
    Time-varying fertilizer price.
    Prices are separated from products because they change over time
    and vary by geography.
    """
    __tablename__ = "fertilizer_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fertilizer_products.id"), nullable=False
    )
    price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    bag_size_kg: Mapped[float] = mapped_column(Float, nullable=False)
    district: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Geographic scope — null means state-wide"
    )
    effective_from: Mapped[dt.date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    product: Mapped["FertilizerProductRecord"] = relationship(back_populates="prices")

    def __repr__(self) -> str:
        return (
            f"<FertilizerPrice(product_id={self.product_id!r}, "
            f"price={self.price_inr} INR, from={self.effective_from})>"
        )
