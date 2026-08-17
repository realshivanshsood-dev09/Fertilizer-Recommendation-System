"""
Track A Agronomic Data Ingestion, Provenance & Validation Framework
"""

from app.ingestion.checksum import compute_sha256, verify_checksum
from app.ingestion.readers import (
    RawDataPolicyError,
    read_csv_dataset,
    read_json_dataset,
    register_pdf_extracted_table,
    validate_raw_path_policy,
)
from app.ingestion.registry_loader import (
    DEFAULT_DATASET_REGISTRY_PATH,
    DEFAULT_SOURCE_REGISTRY_PATH,
    MasterRegistries,
    load_and_validate_all_registries,
    load_dataset_registry,
    load_source_registry,
)
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
from app.ingestion.validators import (
    ValidationError,
    detect_duplicates,
    preserve_source_conflict,
    validate_dataset_entry,
    validate_path_separation,
    validate_source_entry,
    validate_unit_declarations,
)

__all__ = [
    "SourceType",
    "VerificationStatus",
    "DatasetFormat",
    "CropEnum",
    "SourceRegistryEntry",
    "DatasetRegistryEntry",
    "ProvenanceRecord",
    "STCRNutrientCoefficients",
    "STCREquationData",
    "SoilMeasurementData",
    "FieldTrialData",
    "ConflictPreservationRecord",
    "compute_sha256",
    "verify_checksum",
    "RawDataPolicyError",
    "validate_raw_path_policy",
    "read_csv_dataset",
    "read_json_dataset",
    "register_pdf_extracted_table",
    "ValidationError",
    "validate_source_entry",
    "validate_dataset_entry",
    "validate_unit_declarations",
    "validate_path_separation",
    "detect_duplicates",
    "preserve_source_conflict",
    "DEFAULT_SOURCE_REGISTRY_PATH",
    "DEFAULT_DATASET_REGISTRY_PATH",
    "MasterRegistries",
    "load_source_registry",
    "load_dataset_registry",
    "load_and_validate_all_registries",
]
