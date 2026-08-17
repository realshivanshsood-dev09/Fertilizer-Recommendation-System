"""
Tests for Track A Dataset 003: PAU Rice STCR Field Verification (Khosa et al., 2012)
====================================================================================
Validates:
  - Source registry entry SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012
  - Dataset registry entry DS-PAU-RICE-STCR-FIELD-VERIFICATION-2012
  - Raw source status recorded accurately as 'not_acquired' (no fake PDF)
  - Processed summary in pau_rice_stcr_verification_2012_summary.yaml
  - Track B ML assessment and external validation candidate classification
  - Explicit marking of malwa_direct_evidence as False
  - Independent coexistence of Datasets 001, 002, and 003
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from app.ingestion.registry_loader import load_and_validate_all_registries
from app.ingestion.schemas import VerificationStatus

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_SUMMARY_PATH = _REPO_ROOT / "data" / "processed" / "pau_rice_stcr_verification_2012_summary.yaml"
TRACK_B_STUDY_PATH = _REPO_ROOT / "ml" / "registry" / "khosa_2012_rice_stcr_verification.yaml"
PROVENANCE_TRACE_PATH = _REPO_ROOT / "data" / "metadata" / "rice_stcr_provenance_trace.yaml"


class TestDataset003Registries:
    def test_source_registry_metadata(self):
        registries = load_and_validate_all_registries()
        assert "SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012" in registries.sources
        src = registries.get_source("SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012")
        assert src is not None
        assert src.institution == "Punjab Agricultural University, Ludhiana, Punjab, India"
        assert src.source_type == "university"
        assert src.publisher == "The Fertiliser Association of India"
        assert src.publication_year == 2012
        assert src.data_type == "stcr_field_verification"
        assert src.verification_status == VerificationStatus.VERIFIED

    def test_dataset_registry_and_raw_source_status(self):
        registries = load_and_validate_all_registries()
        assert "DS-PAU-RICE-STCR-FIELD-VERIFICATION-2012" in registries.datasets
        ds = registries.get_dataset("DS-PAU-RICE-STCR-FIELD-VERIFICATION-2012")
        assert ds is not None
        assert ds.source_id == "SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012"
        assert ds.raw_source_status == "not_acquired"
        assert ds.checksum is None
        assert ds.local_path is None
        assert ds.verification_status == VerificationStatus.VERIFIED

    def test_all_three_datasets_coexist_in_registries(self):
        registries = load_and_validate_all_registries()
        assert len(registries.sources) >= 3
        assert len(registries.datasets) >= 3
        assert "SRC-ICAR-PAU-WHEAT-STCR-2022" in registries.sources
        assert "SRC-ICAR-PAU-RICE-TYE-INM-2021" in registries.sources
        assert "SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012" in registries.sources
        assert "DS-ICAR-PAU-WHEAT-STCR-2022" in registries.datasets
        assert "DS-ICAR-PAU-RICE-TYE-INM-2021" in registries.datasets
        assert "DS-PAU-RICE-STCR-FIELD-VERIFICATION-2012" in registries.datasets


class TestDataset003SummaryAndRole:
    @pytest.fixture
    def summary_data(self):
        assert PROCESSED_SUMMARY_PATH.is_file()
        with open(PROCESSED_SUMMARY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_role_and_characterization(self, summary_data):
        char = summary_data["study_characterization"]
        assert char["role"] == "field_verification"
        assert char["derives_new_equations"] is False
        assert char["applies_preexisting_equations"] is True

    def test_malwa_direct_evidence_is_false(self, summary_data):
        assert summary_data["study_characterization"]["malwa_direct_evidence"] is False

    def test_provenance_linkage(self, summary_data):
        assert summary_data["provenance"]["source_id"] == "SRC-PAU-RICE-STCR-FIELD-VERIFICATION-2012"
        assert summary_data["provenance"]["raw_source_status"] == "not_acquired"


class TestDataset003TrackBAndProvenanceTrace:
    def test_track_b_classification(self):
        assert TRACK_B_STUDY_PATH.is_file()
        with open(TRACK_B_STUDY_PATH, "r", encoding="utf-8") as f:
            study = yaml.safe_load(f)
        assert study["training_readiness"] == "not_applicable"
        assert study["suitable_for_training"] is False
        assert study["classification"]["training_candidate"] is False
        assert study["classification"]["external_validation_candidate"] is True
        assert study["malwa_direct_evidence"] is False

    def test_provenance_trace_yaml_exists(self):
        assert PROVENANCE_TRACE_PATH.is_file()
        with open(PROVENANCE_TRACE_PATH, "r", encoding="utf-8") as f:
            trace = yaml.safe_load(f)
        candidate_ids = [c["source_id"] for c in trace["candidate_sources"]]
        assert "SRC-PAU-KHOSA-2012" in candidate_ids
        assert trace["equation"]["N"]["calibration_source_status"] == "probable"
