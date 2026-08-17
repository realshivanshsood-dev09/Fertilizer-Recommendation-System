"""
Data validation schemas proxy for Track A data ingestion.
"""
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.ingestion.schemas import (
    ConflictPreservationRecord,
    CropEnum,
    DatasetFormat,
    DatasetRegistryEntry,
    FieldTrialData,
    ProvenanceRecord,
    SoilMeasurementData,
    SourceRegistryEntry,
    SourceType,
    STCREquationData,
    STCRNutrientCoefficients,
    VerificationStatus,
)

__all__ = [
    "ConflictPreservationRecord",
    "CropEnum",
    "DatasetFormat",
    "DatasetRegistryEntry",
    "FieldTrialData",
    "ProvenanceRecord",
    "SoilMeasurementData",
    "SourceRegistryEntry",
    "SourceType",
    "STCREquationData",
    "STCRNutrientCoefficients",
    "VerificationStatus",
]
