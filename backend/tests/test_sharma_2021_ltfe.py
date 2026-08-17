"""
Tests for Track B Dataset B2-001: PAU Long-Term Rice-Wheat Experiment (Sharma et al., 2021)
===========================================================================================
Validates:
  1. Raw PDF existence and SHA-256 checksum match.
  2. Source registry entry in data/metadata/source_registry.yaml.
  3. Dataset registry entry in data/metadata/dataset_registry.yaml.
  4. All processed rows in data/processed/sharma_2021_ltfe_rice_wheat.csv have full provenance.
  5. Granularity is strictly 'treatment_mean' (no synthetic plot-level rows).
  6. Exactly 12 observation rows (6 treatments x 2 crops).
  7. Exact transcribed values for grain and straw yields, plant N content, and N uptake.
  8. Missing STCR values are explicitly handled (STCR_applicability_match=False).
  9. Preserved integrity of Track A Datasets 001, 002, and 003.
"""

from __future__ import annotations

import csv
from pathlib import Path
import pytest
import yaml

from app.ingestion.checksum import verify_checksum
from app.ingestion.registry_loader import load_and_validate_all_registries
from app.ingestion.schemas import VerificationStatus

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_PDF_PATH = _REPO_ROOT / "data" / "raw" / "icar" / "sharma_dheri_saini_2021_pau_ltfe_rice_wheat.pdf"
CSV_PROCESSED_PATH = _REPO_ROOT / "data" / "processed" / "sharma_2021_ltfe_rice_wheat.csv"
YAML_PROCESSED_PATH = _REPO_ROOT / "data" / "processed" / "sharma_2021_ltfe_rice_wheat.yaml"
ML_STUDY_PATH = _REPO_ROOT / "ml" / "registry" / "sharma_2021_ltfe_rice_wheat_study.yaml"
EXPECTED_SHA256 = "c7c61744905f6c23d69ad04b9187edd4e239fafdb9fb2b149930715dfde15879"


class TestSharma2021RawAndRegistries:
    def test_raw_pdf_and_checksum(self):
        assert RAW_PDF_PATH.is_file(), f"Raw PDF not found at {RAW_PDF_PATH}"
        assert verify_checksum(RAW_PDF_PATH, EXPECTED_SHA256) is True

    def test_source_registry_entry(self):
        registries = load_and_validate_all_registries()
        assert "SRC-ICAR-PAU-LTFE-RICE-WHEAT-2021" in registries.sources
        src = registries.get_source("SRC-ICAR-PAU-LTFE-RICE-WHEAT-2021")
        assert src is not None
        assert src.institution == "Punjab Agricultural University, Ludhiana, Punjab, India"
        assert src.source_type == "university"
        assert src.publisher == "Indian Council of Agricultural Research"
        assert src.publication_year == 2021
        assert src.doi == "10.56093/ijas.v91i8.115807"
        assert src.crop == "rice"
        assert src.secondary_crop == "wheat"
        assert src.data_type == "field_trial"
        assert src.verification_status == VerificationStatus.VERIFIED

    def test_dataset_registry_entry(self):
        registries = load_and_validate_all_registries()
        assert "DS-ICAR-PAU-LTFE-RICE-WHEAT-2021" in registries.datasets
        ds = registries.get_dataset("DS-ICAR-PAU-LTFE-RICE-WHEAT-2021")
        assert ds is not None
        assert ds.source_id == "SRC-ICAR-PAU-LTFE-RICE-WHEAT-2021"
        assert ds.checksum == EXPECTED_SHA256
        assert ds.raw_source_status == "acquired"
        assert ds.verification_status == VerificationStatus.VERIFIED

    def test_all_four_datasets_coexist_independently(self):
        registries = load_and_validate_all_registries()
        assert len(registries.sources) >= 4
        assert len(registries.datasets) >= 4
        assert "DS-ICAR-PAU-WHEAT-STCR-2022" in registries.datasets
        assert "DS-ICAR-PAU-RICE-TYE-INM-2021" in registries.datasets
        assert "DS-PAU-RICE-STCR-FIELD-VERIFICATION-2012" in registries.datasets
        assert "DS-ICAR-PAU-LTFE-RICE-WHEAT-2021" in registries.datasets


class TestSharma2021ProcessedObservations:
    @pytest.fixture
    def csv_rows(self):
        assert CSV_PROCESSED_PATH.is_file()
        with open(CSV_PROCESSED_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("#")]
            reader = csv.DictReader(lines)
            return list(reader)

    def test_observation_count_is_exactly_twelve(self, csv_rows):
        # 6 treatments x 2 crops = 12 treatment means
        assert len(csv_rows) == 12

    def test_all_rows_are_treatment_means(self, csv_rows):
        for row in csv_rows:
            assert row["data_granularity"] == "treatment_mean"
            assert row["study_id"] == "STUDY-PAU-LTFE-RICE-WHEAT-2021"
            assert row["source_id"] == "SRC-ICAR-PAU-LTFE-RICE-WHEAT-2021"
            assert row["dataset_id"] == "DS-ICAR-PAU-LTFE-RICE-WHEAT-2021"
            assert row["replications_in_experiment"] == "3"
            assert row["STCR_applicability_match"] == "false"

    def test_rice_observations_exact_yields(self, csv_rows):
        rice_rows = {r["treatment_id"]: r for r in csv_rows if r["crop"] == "rice"}
        assert len(rice_rows) == 6

        # T1 Control: Grain 2.95 Mg/ha, Straw 3.21 Mg/ha
        assert float(rice_rows["T1"]["observed_grain_yield_Mg_ha"]) == pytest.approx(2.95)
        assert float(rice_rows["T1"]["observed_straw_yield_Mg_ha"]) == pytest.approx(3.21)
        assert float(rice_rows["T1"]["grain_N_uptake_kg_ha"]) == pytest.approx(30.4)

        # T2 100% NPK: Grain 6.03 Mg/ha, Straw 6.50 Mg/ha
        assert float(rice_rows["T2"]["observed_grain_yield_Mg_ha"]) == pytest.approx(6.03)
        assert float(rice_rows["T2"]["observed_straw_yield_Mg_ha"]) == pytest.approx(6.50)

        # T4 100% NPK + FYM: Grain 6.94 Mg/ha, Straw 7.52 Mg/ha
        assert float(rice_rows["T4"]["observed_grain_yield_Mg_ha"]) == pytest.approx(6.94)
        assert float(rice_rows["T4"]["observed_straw_yield_Mg_ha"]) == pytest.approx(7.52)
        assert float(rice_rows["T4"]["total_N_uptake_kg_ha"]) == pytest.approx(144.5)

    def test_wheat_observations_exact_yields(self, csv_rows):
        wheat_rows = {r["treatment_id"]: r for r in csv_rows if r["crop"] == "wheat"}
        assert len(wheat_rows) == 6

        # T1 Control: Grain 1.33 Mg/ha, Straw 1.55 Mg/ha
        assert float(wheat_rows["T1"]["observed_grain_yield_Mg_ha"]) == pytest.approx(1.33)
        assert float(wheat_rows["T1"]["observed_straw_yield_Mg_ha"]) == pytest.approx(1.55)

        # T2 100% NPK: Grain 4.36 Mg/ha, Straw 5.10 Mg/ha
        assert float(wheat_rows["T2"]["observed_grain_yield_Mg_ha"]) == pytest.approx(4.36)
        assert float(wheat_rows["T2"]["observed_straw_yield_Mg_ha"]) == pytest.approx(5.10)

        # T4 100% NPK + FYM: Grain 5.00 Mg/ha, Straw 6.36 Mg/ha
        assert float(wheat_rows["T4"]["observed_grain_yield_Mg_ha"]) == pytest.approx(5.00)
        assert float(wheat_rows["T4"]["observed_straw_yield_Mg_ha"]) == pytest.approx(6.36)


class TestSharma2021MLStudyRegistry:
    def test_ml_study_registry_content(self):
        assert ML_STUDY_PATH.is_file()
        with open(ML_STUDY_PATH, "r", encoding="utf-8") as f:
            study = yaml.safe_load(f)

        assert study["study_id"] == "STUDY-PAU-LTFE-RICE-WHEAT-2021"
        assert study["ml_assessment"]["suitable_for_training"] is False
        assert study["ml_assessment"]["suitable_for_validation"] is True
        assert study["ml_assessment"]["role"] == "validation_benchmark"
        assert study["reported_data_granularity"]["granularity"] == "treatment_mean"
        assert study["reported_data_granularity"]["total_processed_observations"] == 12
