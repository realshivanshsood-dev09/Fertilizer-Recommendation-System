"""
Track A Agronomic Data Schemas & Provenance Models
===================================================
Defines schemas for:
- Source Registry entries (PAU, ICAR, Govt portals, peer-reviewed literature)
- Dataset Registry entries (raw and processed files with checksums)
- Generic and specific Provenance records
- STCR equation specifications (supporting regional/soil variation)
- Soil measurement data structures
- Field trial experimental observations
- Scientific conflict preservation structures
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class SourceType(str, Enum):
    GOVERNMENT = "government"
    UNIVERSITY = "university"
    ICAR = "ICAR"
    PEER_REVIEWED = "peer_reviewed"
    SOIL_HEALTH_CARD = "soil_health_card"
    FIELD_TRIAL = "field_trial"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DatasetFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    PDF_TABLE = "pdf_table"
    YAML = "yaml"


class CropEnum(str, Enum):
    WHEAT = "wheat"
    RICE = "rice"
    COTTON = "cotton"
    ALL = "all"


# ── Source Registry Schema ───────────────────────────────────────────────────

class SourceRegistryEntry(BaseModel):
    """
    Metadata for an authoritative scientific data source.
    Every dataset in Track A must point back to a valid source_id.
    """
    source_id: str = Field(
        ...,
        description="Unique identifier, e.g. 'SRC-PAU-2023-STCR-01'",
        pattern=r"^[A-Z0-9_\-]+$"
    )
    institution: str = Field(
        ...,
        description="Originating institution, e.g. 'Punjab Agricultural University'"
    )
    source_type: SourceType = Field(
        ...,
        description="Classification of institution/source"
    )
    title: str = Field(
        ...,
        description="Title of bulletin, document, report, or paper"
    )
    publication: Optional[str] = Field(
        None,
        description="Publisher, journal, or department"
    )
    publisher: Optional[str] = Field(
        None,
        description="Publishing or hosting organization (e.g. 'Indian Council of Agricultural Research')"
    )
    authors: Optional[Union[List[str], str]] = Field(
        None,
        description="Authors or committee responsible"
    )
    publication_year: Optional[int] = Field(
        None,
        ge=1950,
        le=2030,
        description="Year of publication"
    )
    doi: Optional[str] = Field(
        None,
        description="Digital Object Identifier if applicable"
    )
    url: Optional[str] = Field(
        None,
        description="Authoritative source URL"
    )
    retrieval_date: Optional[Union[date, str]] = Field(
        None,
        description="Date when source was accessed/obtained"
    )
    geographic_scope: str = Field(
        ...,
        description="Region applicability, e.g. 'Punjab (Malwa)' or 'Punjab (All)'"
    )
    crop: Optional[str] = Field(
        None,
        description="Applicable crop or 'all'"
    )
    data_type: str = Field(
        ...,
        description="Type of data, e.g. 'stcr_coefficients', 'soil_health_card', 'field_trial'"
    )
    license: Optional[str] = Field(
        None,
        description="Data license or access rights"
    )
    access_status: Optional[str] = Field(
        None,
        description="Access status if explicit license is not stated (e.g. 'Openly accessible via ICAR e-pubs')"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Scientific verification status"
    )
    verifier: Optional[str] = Field(
        None,
        description="Person/agent who validated the scientific content"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional context or caveats"
    )


# ── Dataset Registry Schema ──────────────────────────────────────────────────

class DatasetRegistryEntry(BaseModel):
    """
    Registry entry for a specific data file or extracted table.
    Ensures raw data integrity via SHA-256 checksum and path policy.
    """
    dataset_id: str = Field(
        ...,
        description="Unique identifier, e.g. 'DS-PAU-2023-WHEAT-STCR-01'",
        pattern=r"^[A-Z0-9_\-]+$"
    )
    source_id: str = Field(
        ...,
        description="Foreign reference to SourceRegistryEntry.source_id"
    )
    original_filename: str = Field(
        ...,
        description="Original name of the acquired file"
    )
    local_path: str = Field(
        ...,
        description="Path relative to repository root (e.g. 'data/raw/pau/stcr_wheat_2023.csv')"
    )
    format: DatasetFormat = Field(
        ...,
        description="File format"
    )
    checksum: str = Field(
        ...,
        description="SHA-256 checksum of the raw file",
        pattern=r"^[a-fA-F0-9]{64}$"
    )
    retrieval_date: Union[date, str] = Field(
        ...,
        description="Date the file was obtained"
    )
    processing_script: Optional[str] = Field(
        None,
        description="Path to script used to process this raw file"
    )
    processing_version: Optional[str] = Field(
        None,
        description="Version of ingestion/processing logic"
    )
    geographic_scope: str = Field(
        ...,
        description="Geographic boundary of the dataset"
    )
    crop: Optional[str] = Field(
        None,
        description="Crop applicability"
    )
    variables: List[str] = Field(
        default_factory=list,
        description="List of variable/column names present in the dataset"
    )
    units: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of variable name -> declared scientific unit"
    )
    missingness_notes: Optional[str] = Field(
        None,
        description="Documentation of nulls or missing fields"
    )
    extraction_method: Optional[str] = Field(
        None,
        description="Method used to extract data (e.g. 'manual_double_transcription_from_pdf_table_2')"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Scientific verification status of this dataset"
    )
    license: Optional[str] = Field(
        None,
        description="License governing dataset distribution"
    )
    access_status: Optional[str] = Field(
        None,
        description="Access availability (e.g. 'Openly accessible via ICAR e-pubs')"
    )

    @field_validator("local_path")
    @classmethod
    def validate_raw_path(cls, v: str) -> str:
        """Enforces that raw dataset paths stay within data/raw/ or data/metadata/."""
        normalized = v.replace("\\", "/")
        if not (normalized.startswith("data/raw/") or normalized.startswith("data/metadata/")):
            raise ValueError(f"local_path must reside in data/raw/ or data/metadata/, got '{v}'")
        return normalized


# ── Provenance Record ────────────────────────────────────────────────────────

class ProvenanceRecord(BaseModel):
    """
    Standard provenance attachment for every scientific fact or record.
    """
    source_id: str
    dataset_id: Optional[str] = None
    document_title: Optional[str] = None
    table_or_page: Optional[str] = None
    extraction_method: Optional[str] = None  # e.g. "manual_transcription", "csv_import"
    retrieved_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_notes: Optional[str] = None


# ── STCR Equation Data Model ──────────────────────────────────────────────────

class STCRNutrientCoefficients(BaseModel):
    """
    Nutrient-specific coefficients for STCR equations.
    Formula: Dose (kg/ha) = (a * Target_Yield - b * Soil_Test) / FUE
    """
    a: Optional[float] = Field(None, description="Requirement per yield target unit")
    b: Optional[float] = Field(None, description="Soil test calibration coefficient")
    target_yield_range: Optional[Dict[str, float]] = Field(
        None, description="Min and max valid target yield range"
    )
    fue: Optional[float] = Field(None, description="Fertilizer use efficiency fraction (0-1)")
    soil_test_method: Optional[str] = Field(
        None, description="e.g. Alkaline KMnO4 for N, Olsen's for P, Ammonium Acetate for K"
    )
    units: Dict[str, str] = Field(
        default_factory=dict,
        description="Explicit units for a, b, target_yield, dose"
    )


class STCREquationData(BaseModel):
    """
    STCR equation set for a specific crop, region, and soil type.
    Supports heterogeneous regional and soil variations without hardcoded assumptions.
    """
    crop: str
    geographic_scope: str
    soil_type: Optional[str] = None
    season: Optional[str] = None
    stcr_model_type: str = Field(
        default="ramamoorthy_1967",
        description="Equation formulation type (e.g. Ramamoorthy linear, quadratic)"
    )
    formula_template: Optional[str] = Field(
        None,
        description="Human-readable formula string"
    )
    nutrients: Dict[str, STCRNutrientCoefficients] = Field(
        default_factory=dict,
        description="Mapping of nutrient ('N', 'P', 'K') -> coefficients"
    )
    provenance: ProvenanceRecord


# ── Soil Measurement Data Model ──────────────────────────────────────────────

class SoilMeasurementData(BaseModel):
    """
    Structured soil measurement record preserving raw units and testing methodology.
    """
    location_district: str
    location_block: Optional[str] = None
    location_village: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sampling_date: Optional[Union[date, str]] = None
    soil_source_type: str  # e.g. soil_health_card, pau_lab, government_lab, district_average
    
    # Nutrients & properties
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    ph: Optional[float] = None
    organic_carbon: Optional[float] = None
    electrical_conductivity: Optional[float] = None
    zinc: Optional[float] = None
    iron: Optional[float] = None
    manganese: Optional[float] = None
    copper: Optional[float] = None

    # Methodology & Units
    testing_methodology: Dict[str, str] = Field(
        default_factory=dict,
        description="Testing methods for each parameter"
    )
    declared_units: Dict[str, str] = Field(
        default_factory=dict,
        description="Declared units (e.g. N: kg/ha, OC: %, pH: dimensionless)"
    )
    is_lab_measured: bool = False
    provenance: ProvenanceRecord


# ── Field Trial Data Model ───────────────────────────────────────────────────

class FieldTrialData(BaseModel):
    """
    Experimental observation from agricultural trials for Track B ML use.
    """
    trial_id: Optional[str] = None
    study_id: str
    location_district: str
    crop: str
    season: Optional[str] = None
    year: Optional[int] = None
    
    # Soil initial status
    soil_n: Optional[float] = None
    soil_p: Optional[float] = None
    soil_k: Optional[float] = None
    soil_ph: Optional[float] = None
    soil_oc: Optional[float] = None

    # Applied treatments
    applied_n_kg_per_ha: Optional[float] = None
    applied_p2o5_kg_per_ha: Optional[float] = None
    applied_k2o_kg_per_ha: Optional[float] = None
    organic_input_type: Optional[str] = None
    organic_input_kg_per_ha: Optional[float] = None
    irrigation_method: Optional[str] = None
    
    # Measured outcomes
    target_yield_mg_per_ha: Optional[float] = None
    observed_yield_mg_per_ha: Optional[float] = None
    nutrient_uptake_n: Optional[float] = None
    nutrient_uptake_p: Optional[float] = None
    nutrient_uptake_k: Optional[float] = None

    treatment_label: Optional[str] = None
    replications: Optional[int] = None
    provenance: ProvenanceRecord


# ── Source Conflict Preservation ─────────────────────────────────────────────

class ConflictPreservationRecord(BaseModel):
    """
    Preserves conflicting agricultural findings from multiple sources
    without automatic or destructive merging.
    """
    conflict_id: str
    entity_type: str  # e.g. "stcr_coefficients", "district_soil_average", "biofertilizer_dose"
    crop: Optional[str] = None
    district: Optional[str] = None
    competing_records: List[Dict[str, Any]] = Field(
        ...,
        description="List of conflicting records with their respective source provenance"
    )
    resolution_status: str = Field(
        default="unresolved_pending_scientific_review",
        description="Status of manual scientific review"
    )
    reviewer_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
