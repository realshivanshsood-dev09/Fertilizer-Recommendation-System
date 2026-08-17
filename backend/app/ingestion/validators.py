"""
Track A Data Validation Framework
==================================
Performs structural, metadata, unit, duplicate, and conflict validation
for all ingested datasets without guessing or hardcoding biological values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
import structlog

from app.ingestion.schemas import (
    ConflictPreservationRecord,
    CropEnum,
    DatasetRegistryEntry,
    SourceRegistryEntry,
    SourceType,
    VerificationStatus,
)

log = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


# ── Metadata & Registry Validators ───────────────────────────────────────────

def validate_source_entry(entry_dict: Dict[str, Any]) -> SourceRegistryEntry:
    """
    Validates a raw source entry dictionary against SourceRegistryEntry schema.
    """
    try:
        return SourceRegistryEntry(**entry_dict)
    except Exception as exc:
        raise ValidationError(f"Invalid source registry entry '{entry_dict.get('source_id')}': {exc}") from exc


def validate_dataset_entry(
    entry_dict: Dict[str, Any],
    known_source_ids: Optional[Set[str]] = None,
) -> DatasetRegistryEntry:
    """
    Validates a dataset registry entry, checking schema compliance and source_id referential integrity.
    """
    try:
        entry = DatasetRegistryEntry(**entry_dict)
    except Exception as exc:
        raise ValidationError(f"Invalid dataset registry entry '{entry_dict.get('dataset_id')}': {exc}") from exc

    if known_source_ids is not None and entry.source_id not in known_source_ids:
        raise ValidationError(
            f"Dataset '{entry.dataset_id}' references unknown source_id '{entry.source_id}'."
        )

    return entry


# ── Unit Declaration Validators ───────────────────────────────────────────────

def validate_unit_declarations(
    variables: Iterable[str],
    declared_units: Dict[str, str],
) -> None:
    """
    Ensures that every measured or numerical variable has an explicitly declared scientific unit.
    Prevents unit ambiguity in agronomic data.
    """
    missing_units = []
    for var in variables:
        unit = declared_units.get(var)
        if not unit or not unit.strip():
            missing_units.append(var)

    if missing_units:
        raise ValidationError(
            f"Missing declared scientific units for variables: {missing_units}. "
            "All Track A variables must have explicit units (e.g. 'kg/ha', '%', 'mg/kg')."
        )


# ── Raw vs. Processed Path Separation ─────────────────────────────────────────

def validate_path_separation(raw_path: Union[str, Path], processed_path: Union[str, Path]) -> None:
    """
    Enforces the raw data immutability policy:
      - Raw files MUST reside in data/raw/
      - Processed files MUST reside in data/processed/ or data/interim/
      - Processed path must never point to the same file as raw path
    """
    raw_norm = str(Path(raw_path).resolve()).replace("\\", "/")
    proc_norm = str(Path(processed_path).resolve()).replace("\\", "/")

    if raw_norm == proc_norm:
        raise ValidationError(
            "Raw file path and processed file path must never be identical. Raw data must never be overwritten."
        )

    if "data/raw" not in raw_norm:
        raise ValidationError(f"Raw file path must be in 'data/raw/', got '{raw_path}'")

    if "data/processed" not in proc_norm and "data/interim" not in proc_norm:
        raise ValidationError(f"Processed file path must be in 'data/processed/' or 'data/interim/', got '{processed_path}'")


# ── Duplicate Detection ───────────────────────────────────────────────────────

def detect_duplicates(
    records: List[Dict[str, Any]],
    key_fields: List[str],
) -> List[Dict[str, Any]]:
    """
    Identifies duplicate records in a dataset based on composite key fields.
    Returns list of duplicate records.
    """
    seen: Set[Tuple[Any, ...]] = set()
    duplicates: List[Dict[str, Any]] = []

    for record in records:
        key = tuple(record.get(k) for k in key_fields)
        if key in seen:
            duplicates.append(record)
        else:
            seen.add(key)

    if duplicates:
        log.warning(
            "duplicate_records_detected",
            count=len(duplicates),
            key_fields=key_fields,
        )
    return duplicates


# ── Conflict Preservation ─────────────────────────────────────────────────────

def preserve_source_conflict(
    conflict_id: str,
    entity_type: str,
    competing_records: List[Dict[str, Any]],
    crop: Optional[str] = None,
    district: Optional[str] = None,
    notes: Optional[str] = None,
) -> ConflictPreservationRecord:
    """
    Creates a conflict record when competing authoritative sources yield differing
    results, ensuring no source is discarded or overwritten prior to scientific review.
    """
    if len(competing_records) < 2:
        raise ValidationError("Conflict preservation requires at least 2 competing source records.")

    log.info(
        "source_conflict_preserved",
        conflict_id=conflict_id,
        entity_type=entity_type,
        record_count=len(competing_records),
    )

    return ConflictPreservationRecord(
        conflict_id=conflict_id,
        entity_type=entity_type,
        crop=crop,
        district=district,
        competing_records=competing_records,
        reviewer_notes=notes,
    )
