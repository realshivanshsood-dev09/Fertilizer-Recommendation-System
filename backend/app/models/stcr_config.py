"""STCRConfiguration model — version and provenance tracking for STCR parameter sets."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class STCRConfiguration(TimestampMixin, Base):
    """
    Tracks which STCR configuration version was used for a recommendation.

    IMPORTANT: This table does NOT store numerical STCR coefficients.
    The YAML files in agronomy/stcr/ remain the scientific source of truth.
    This table records provenance: which version, when verified, by whom.
    """
    __tablename__ = "stcr_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    yaml_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="SHA-256 hash of the YAML file content for integrity verification"
    )
    crop: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geographic_scope: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    soil_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_document: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    units: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    coefficients_populated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True only when real PAU/ICAR coefficients are loaded"
    )
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="stcr_config")

    def __repr__(self) -> str:
        return f"<STCRConfiguration(version={self.version!r}, populated={self.coefficients_populated})>"
