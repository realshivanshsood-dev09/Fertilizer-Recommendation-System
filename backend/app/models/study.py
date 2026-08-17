"""Study model — research dataset provenance for Track B."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid


class Study(TimestampMixin, Base):
    """
    Provenance record for research datasets and field trial publications.
    Every FieldTrialObservation must trace back to a Study.
    """
    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    authors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publication: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True,
        comment="Digital Object Identifier"
    )
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    geographic_scope: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    crop: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dataset_license: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False,
        comment="unverified | under_review | verified | rejected"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    field_trials: Mapped[list["FieldTrialObservation"]] = relationship(back_populates="study")

    def __repr__(self) -> str:
        return f"<Study(id={self.id!r}, title={self.title!r}, institution={self.institution!r})>"
