"""ModelVersion model — ML model registry with full training provenance."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class ModelVersion(TimestampMixin, Base):
    """
    ML model version registry.

    Every trained model gets a version record so we can answer:
    'Which exact model produced this recommendation?'
    """
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    model_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="E.g. xgboost_correction, random_forest_correction"
    )
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    training_dataset_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    training_date: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    feature_schema_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment='Training metrics, e.g. {"rmse_N": 5.2, "r2_N": 0.87}'
    )
    artifact_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    git_commit: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True,
        comment="Git commit SHA that produced this model"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Only one model should be active per model_type at a time"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="model_version")

    def __repr__(self) -> str:
        return f"<ModelVersion(type={self.model_type!r}, version={self.version!r}, active={self.is_active})>"
