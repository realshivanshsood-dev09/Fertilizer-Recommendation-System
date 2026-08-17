"""
Track A Ingestion & Provenance Tests
====================================
Validates:
  - Source registry schemas and integrity
  - Dataset registry schemas and referential integrity
  - Cryptographic checksum calculation and enforcement
  - Raw path immutability and directory separation policy
  - Explicit scientific unit declarations
  - Duplicate detection across composite keys
  - Source conflict preservation (no automatic destructive merges)
  - PDF-extracted table provenance
  - STCR, Soil, and Field Trial data modeling
  - CSV & JSON dataset readers
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_source_dict():
    return {
        "source_id": "SRC-PAU-2023-STCR-01",
        "institution": "Punjab Agricultural University",
        "source_type": "university",
        "title": "Fertilizer Recommendations for Kharif and Rabi Crops of Punjab",
        "publication": "PAU Ludhiana Research Bulletin",
        "publication_year": 2023,
        "geographic_scope": "Punjab (Malwa Region)",
        "crop": "wheat",
        "data_type": "stcr_coefficients",
        "license": "Academic / PAU Extension",
        "verification_status": "unverified",
        "notes": "Official PAU fertilizer guide.",
    }


@pytest.fixture
def valid_dataset_dict():
    return {
        "dataset_id": "DS-PAU-2023-WHEAT-STCR-01",
        "source_id": "SRC-PAU-2023-STCR-01",
        "original_filename": "pau_wheat_stcr_2023.csv",
        "local_path": "data/raw/pau/pau_wheat_stcr_2023.csv",
        "format": "csv",
        "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "retrieval_date": "2024-01-15",
        "processing_script": "scripts/ingest_pau.py",
        "processing_version": "1.0.0",
        "geographic_scope": "Punjab (Malwa)",
        "crop": "wheat",
        "variables": ["target_yield", "soil_n", "dose_n"],
        "units": {
            "target_yield": "Mg/ha",
            "soil_n": "kg/ha",
            "dose_n": "kg/ha",
        },
        "verification_status": "unverified",
    }


# ── Checksum Tests ────────────────────────────────────────────────────────────

class TestChecksumUtils:
    def test_compute_sha256_bytes(self):
        digest = compute_sha256(b"test content")
        assert len(digest) == 64
        assert digest == compute_sha256(b"test content")

    def test_compute_sha256_file(self, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("scientific data", encoding="utf-8")
        digest = compute_sha256(file)
        assert len(digest) == 64

    def test_verify_checksum_success(self, tmp_path: Path):
        file = tmp_path / "data.csv"
        file.write_text("N,P,K\n10,20,30", encoding="utf-8")
        expected = compute_sha256(file)
        assert verify_checksum(file, expected) is True

    def test_verify_checksum_mismatch(self, tmp_path: Path):
        file = tmp_path / "data.csv"
        file.write_text("N,P,K\n10,20,30", encoding="utf-8")
        with pytest.raises(ValueError, match="Checksum mismatch"):
            verify_checksum(file, "0000000000000000000000000000000000000000000000000000000000000000")


# ── Source Registry Validation Tests ──────────────────────────────────────────

class TestSourceRegistryValidation:
    def test_valid_source_entry(self, valid_source_dict):
        entry = validate_source_entry(valid_source_dict)
        assert entry.source_id == "SRC-PAU-2023-STCR-01"
        assert entry.source_type == SourceType.UNIVERSITY
        assert entry.verification_status == VerificationStatus.UNVERIFIED

    def test_missing_required_fields_fails(self, valid_source_dict):
        invalid = valid_source_dict.copy()
        del invalid["institution"]
        with pytest.raises(ValidationError, match="institution"):
            validate_source_entry(invalid)

    def test_invalid_source_type_fails(self, valid_source_dict):
        invalid = valid_source_dict.copy()
        invalid["source_type"] = "random_blog"
        with pytest.raises(ValidationError):
            validate_source_entry(invalid)

    def test_invalid_source_id_format(self, valid_source_dict):
        invalid = valid_source_dict.copy()
        invalid["source_id"] = "invalid id with spaces!"
        with pytest.raises(ValidationError):
            validate_source_entry(invalid)


# ── Dataset Registry Validation Tests ─────────────────────────────────────────

class TestDatasetRegistryValidation:
    def test_valid_dataset_entry(self, valid_dataset_dict):
        entry = validate_dataset_entry(
            valid_dataset_dict,
            known_source_ids={"SRC-PAU-2023-STCR-01"}
        )
        assert entry.dataset_id == "DS-PAU-2023-WHEAT-STCR-01"
        assert entry.format == DatasetFormat.CSV
        assert entry.units["target_yield"] == "Mg/ha"

    def test_unknown_source_id_fails(self, valid_dataset_dict):
        with pytest.raises(ValidationError, match="unknown source_id"):
            validate_dataset_entry(
                valid_dataset_dict,
                known_source_ids={"DIFFERENT-SOURCE-ID"}
            )

    def test_invalid_checksum_format(self, valid_dataset_dict):
        invalid = valid_dataset_dict.copy()
        invalid["checksum"] = "not-a-valid-sha256-hex"
        with pytest.raises(ValidationError):
            validate_dataset_entry(invalid)

    def test_local_path_must_be_in_data_raw_or_metadata(self, valid_dataset_dict):
        invalid = valid_dataset_dict.copy()
        invalid["local_path"] = "outside/random_dir/file.csv"
        with pytest.raises(ValidationError, match="data/raw/ or data/metadata/"):
            validate_dataset_entry(invalid)


# ── Unit Declaration & Path Separation Tests ──────────────────────────────────

class TestUnitAndPathValidators:
    def test_all_variables_have_units(self):
        variables = ["soil_n", "soil_p", "yield"]
        units = {"soil_n": "kg/ha", "soil_p": "kg/ha", "yield": "Mg/ha"}
        validate_unit_declarations(variables, units)

    def test_missing_unit_raises_validation_error(self):
        variables = ["soil_n", "soil_p", "yield"]
        units = {"soil_n": "kg/ha", "soil_p": "kg/ha"}  # missing yield
        with pytest.raises(ValidationError, match="Missing declared scientific units"):
            validate_unit_declarations(variables, units)

    def test_path_separation_valid(self):
        raw = "data/raw/pau/wheat.csv"
        processed = "data/processed/wheat_clean.csv"
        validate_path_separation(raw, processed)

    def test_path_separation_same_file_forbidden(self):
        same = "data/raw/pau/wheat.csv"
        with pytest.raises(ValidationError, match="must never be identical"):
            validate_path_separation(same, same)


# ── Duplicate Detection Tests ─────────────────────────────────────────────────

class TestDuplicateDetection:
    def test_detects_duplicates_on_composite_keys(self):
        records = [
            {"crop": "wheat", "district": "Bathinda", "year": 2022, "val": 10},
            {"crop": "wheat", "district": "Mansa", "year": 2022, "val": 15},
            {"crop": "wheat", "district": "Bathinda", "year": 2022, "val": 20},  # duplicate key
        ]
        dups = detect_duplicates(records, key_fields=["crop", "district", "year"])
        assert len(dups) == 1
        assert dups[0]["val"] == 20

    def test_no_duplicates(self):
        records = [
            {"crop": "wheat", "district": "Bathinda", "year": 2022},
            {"crop": "rice", "district": "Bathinda", "year": 2022},
        ]
        dups = detect_duplicates(records, key_fields=["crop", "district", "year"])
        assert len(dups) == 0


# ── Source Conflict Preservation Tests ────────────────────────────────────────

class TestConflictPreservation:
    def test_preserves_competing_sources_without_loss(self):
        competing = [
            {
                "source_id": "SRC-PAU-2023",
                "recommended_n_kg_per_ha": 120.0,
                "basis": "PAU recommendation",
            },
            {
                "source_id": "SRC-ICAR-2022",
                "recommended_n_kg_per_ha": 135.0,
                "basis": "AICRP-STCR trial",
            },
        ]
        conflict = preserve_source_conflict(
            conflict_id="CONF-WHEAT-N-2024",
            entity_type="stcr_coefficients",
            crop="wheat",
            district="Bathinda",
            competing_records=competing,
            notes="PAU and ICAR report slightly different N targets for Malwa zone.",
        )
        assert conflict.conflict_id == "CONF-WHEAT-N-2024"
        assert len(conflict.competing_records) == 2
        assert conflict.resolution_status == "unresolved_pending_scientific_review"

    def test_single_source_cannot_be_conflict(self):
        with pytest.raises(ValidationError, match="at least 2 competing"):
            preserve_source_conflict(
                conflict_id="CONF-01",
                entity_type="stcr",
                competing_records=[{"source_id": "SRC-1"}],
            )


# ── Readers Tests ─────────────────────────────────────────────────────────────

class TestIngestionReaders:
    def test_read_csv_with_checksum(self, tmp_path: Path):
        csv_file = tmp_path / "trial.csv"
        csv_file.write_text("crop,district,yield\nwheat,Bathinda,4.5\n", encoding="utf-8")
        
        expected_hash = compute_sha256(csv_file)
        result = read_csv_dataset(csv_file, expected_checksum=expected_hash)
        assert result["record_count"] == 1
        assert result["records"][0]["crop"] == "wheat"
        assert result["checksum"] == expected_hash

    def test_read_json_dataset(self, tmp_path: Path):
        json_file = tmp_path / "metadata.json"
        json_file.write_text(json.dumps({"source": "PAU", "verified": False}), encoding="utf-8")
        
        result = read_json_dataset(json_file)
        assert result["data"]["source"] == "PAU"

    def test_register_pdf_extracted_table(self, tmp_path: Path):
        dummy_pdf = tmp_path / "pau_bulletin_2023.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 dummy pdf content for testing")

        extracted_rows = [
            {"target_yield_mg": 5.0, "n_dose": 120, "soil_n_test": 150},
        ]
        registered = register_pdf_extracted_table(
            raw_pdf_path=dummy_pdf,
            extracted_table_data=extracted_rows,
            table_identifier="Table 4: STCR equations for Wheat in alluvial soils",
            page_number=18,
            extraction_method="manual_double_transcription",
        )
        assert registered["format"] == DatasetFormat.PDF_TABLE
        assert registered["page_number"] == 18
        assert registered["record_count"] == 1


# ── STCR, Soil, and Field Trial Models Tests ───────────────────────────────────

class TestAgronomicDataModels:
    def test_stcr_equation_data_model(self):
        provenance = ProvenanceRecord(
            source_id="SRC-PAU-2023",
            document_title="PAU Research Bulletin 2023",
            verification_status=VerificationStatus.UNVERIFIED,
        )
        stcr_data = STCREquationData(
            crop="wheat",
            geographic_scope="Malwa, Punjab",
            soil_type="Alluvial Loam",
            season="rabi",
            stcr_model_type="ramamoorthy_linear",
            formula_template="FN = a*T - b*SN",
            nutrients={
                "N": STCRNutrientCoefficients(
                    a=4.5,
                    b=0.48,
                    fue=0.50,
                    soil_test_method="Alkaline KMnO4",
                    units={"a": "kg N / Mg yield", "b": "dimensionless", "dose": "kg/ha"},
                )
            },
            provenance=provenance,
        )
        assert stcr_data.crop == "wheat"
        assert stcr_data.nutrients["N"].a == 4.5
        assert stcr_data.nutrients["N"].units["dose"] == "kg/ha"

    def test_soil_measurement_data_model(self):
        prov = ProvenanceRecord(source_id="SRC-SHC-2024")
        soil = SoilMeasurementData(
            location_district="Bathinda",
            location_block="Talwandi Sabo",
            soil_source_type="soil_health_card",
            nitrogen=145.0,
            phosphorus=16.5,
            potassium=190.0,
            ph=7.6,
            organic_carbon=0.45,
            testing_methodology={
                "nitrogen": "Alkaline KMnO4",
                "phosphorus": "Olsen method",
                "potassium": "1N Ammonium Acetate",
            },
            declared_units={
                "nitrogen": "kg/ha",
                "phosphorus": "kg/ha",
                "potassium": "kg/ha",
                "organic_carbon": "%",
            },
            is_lab_measured=True,
            provenance=prov,
        )
        assert soil.is_lab_measured is True
        assert soil.declared_units["nitrogen"] == "kg/ha"

    def test_field_trial_data_model(self):
        prov = ProvenanceRecord(source_id="SRC-ICAR-2022")
        trial = FieldTrialData(
            trial_id="TRIAL-PB-01",
            study_id="STUDY-AICRP-2022",
            location_district="Faridkot",
            crop="cotton",
            season="kharif",
            year=2022,
            soil_n=130.0,
            applied_n_kg_per_ha=150.0,
            observed_yield_mg_per_ha=2.4,
            replications=3,
            provenance=prov,
        )
        assert trial.crop == "cotton"
        assert trial.replications == 3


# ── Registry Loader Integration Tests ─────────────────────────────────────────

class TestRegistryLoaderIntegration:
    def test_load_source_registry_default(self):
        sources = load_source_registry(DEFAULT_SOURCE_REGISTRY_PATH)
        assert isinstance(sources, dict)

    def test_load_dataset_registry_default(self):
        datasets = load_dataset_registry(DEFAULT_DATASET_REGISTRY_PATH)
        assert isinstance(datasets, dict)

    def test_load_and_validate_all_registries(self):
        registries = load_and_validate_all_registries(
            DEFAULT_SOURCE_REGISTRY_PATH,
            DEFAULT_DATASET_REGISTRY_PATH,
        )
        assert registries.sources is not None
        assert registries.datasets is not None
