"""BiofertilizerRecord model — biofertilizer/bio-inoculant catalog."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, generate_uuid


class BiofertilizerRecord(TimestampMixin, Base):
    """
    Biofertilizer / bio-inoculant record.
    All scientific values (dose, timing) are nullable until verified PAU data is loaded.
    """
    __tablename__ = "biofertilizer_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    organism: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="Species or strain, e.g. Rhizobium leguminosarum"
    )
    crop_applicability: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="Crop name or 'all'"
    )
    application_method: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    dose: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True,
        comment="Application rate with units"
    )
    timing: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    provenance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<BiofertilizerRecord(name={self.name!r}, organism={self.organism!r})>"
