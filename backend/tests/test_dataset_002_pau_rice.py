"""
Tests for Track A Dataset 002: PAU Rice Target-Yield / INM Validation (Singh et al., 2021)
==========================================================================================
Validates:
  - Source registry entry SRC-ICAR-PAU-RICE-TYE-INM-2021
  - Dataset registry entry DS-ICAR-PAU-RICE-TYE-INM-2021
  - Raw PDF existence and SHA-256 checksum verification
  - Exact applied target-yield equations in pau_rice_tye_inm_2021_equations.yaml
  - Initial soil status, treatments, and design in pau_rice_tye_inm_2021_experimental_metadata.yaml
  - Table 1 treatment mean yields and productivity in pau_rice_tye_inm_2021_table1.csv
  - Track B validation suitability classification
  - Strict separation from Dataset 001 (wheat calibration)
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
PROCESSED_EQUATIONS_PATH = _REPO_ROOT / "data" / "processed" / "pau_rice_tye_inm_2021_equations.yaml"
EXPERIMENTAL_META_PATH = _REPO_ROOT / "data" / "processed" / "pau_rice_tye_inm_2021_experimental_metadata.yaml"
TABLE1_CSV_PATH = _REPO_ROOT / "data" / "processed" / "pau_rice_tye_inm_2021_table1.csv"
TRACK_B_STUDY_PATH = _REPO_ROOT / "ml" / "registry" / "pau_rice_tye_inm_2021_study.yaml"
RAW_PDF_PATH = _REPO_ROOT / "data" / "raw" / "icar" / "singh_mavi_saini_2021_pau_rice_wheat_tye_inm.pdf"


class TestDataset002Registries:
    def test_source_registry_metadata(self):
        registries = load_and_validate_all_registries()
        assert "SRC-ICAR-PAU-RICE-TYE-INM-2021" in registries.sources
        src = registries.get_source("SRC-ICAR-PAU-RICE-TYE-INM-2021")
        assert src is not None
        assert src.institution == "Punjab Agricultural University, Ludhiana, Punjab, India"
        assert src.source_type == "university"
        assert src.publisher == "Indian Council of Agricultural Research"
        assert src.publication_year == 2021
        assert src.doi == "10.56093/ijas.v91i10.117521"
        assert src.license == "CC BY-NC-SA 4.0"
        assert src.crop == "rice"
        assert src.secondary_crop == "wheat"
        assert src.data_type == "stcr_target_yield_application_validation"
        assert src.verification_status == VerificationStatus.VERIFIED

    def test_dataset_registry_and_checksum(self):
        registries = load_and_validate_all_registries()
        assert "DS-ICAR-PAU-RICE-TYE-INM-2021" in registries.datasets
        ds = registries.get_dataset("DS-ICAR-PAU-RICE-TYE-INM-2021")
        assert ds is not None
        assert ds.source_id == "SRC-ICAR-PAU-RICE-TYE-INM-2021"
        assert ds.local_path == "data/raw/icar/singh_mavi_saini_2021_pau_rice_wheat_tye_inm.pdf"
        assert ds.crop == "rice"
        assert ds.secondary_crop == "wheat"
        assert ds.license == "CC BY-NC-SA 4.0"
        assert ds.verification_status == VerificationStatus.VERIFIED

        # Check that physical PDF file matches registered checksum
        assert RAW_PDF_PATH.is_file(), f"Raw PDF not found at {RAW_PDF_PATH}"
        assert verify_checksum(RAW_PDF_PATH, ds.checksum) is True

    def test_dataset_001_and_002_coexist_independently(self):
        registries = load_and_validate_all_registries()
        assert len(registries.sources) >= 2
        assert len(registries.datasets) >= 2
        assert "SRC-ICAR-PAU-WHEAT-STCR-2022" in registries.sources
        assert "SRC-ICAR-PAU-RICE-TYE-INM-2021" in registries.sources


class TestDataset002Equations:
    @pytest.fixture
    def eq_data(self):
        assert PROCESSED_EQUATIONS_PATH.is_file()
        with open(PROCESSED_EQUATIONS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_provenance_and_scope(self, eq_data):
        assert eq_data["provenance"]["source_id"] == "SRC-ICAR-PAU-RICE-TYE-INM-2021"
        assert eq_data["provenance"]["classification"] == "stcr_target_yield_application_validation"
        assert eq_data["scope"]["cultivar"] == "PR121"
        assert "Typic Ustipsamment" in eq_data["scope"]["soil_type"]
        assert "Gurdaspur" in eq_data["scope"]["geographic_scope"]

    def test_exact_rice_target_yield_equations(self, eq_data):
        eqs = eq_data["equations"]["rice_stcr_target_yield"]
        
        # N: FN = 3.02T - 0.63SN
        assert eqs["N"]["equation_string"] == "3.02*T - 0.63*SN"
        assert eqs["N"]["a"] == pytest.approx(3.02)
        assert eqs["N"]["b"] == pytest.approx(0.63)

        # P2O5: FP2O5 = 1.78T - 8.37SP
        assert eqs["P2O5"]["equation_string"] == "1.78*T - 8.37*SP"
        assert eqs["P2O5"]["a"] == pytest.approx(1.78)
        assert eqs["P2O5"]["b"] == pytest.approx(8.37)

        # K2O: FK2O = 2.75T - 1.39SK
        assert eqs["K2O"]["equation_string"] == "2.75*T - 1.39*SK"
        assert eqs["K2O"]["a"] == pytest.approx(2.75)
        assert eqs["K2O"]["b"] == pytest.approx(1.39)

    def test_soil_analytical_methods(self, eq_data):
        methods = eq_data["soil_test_methods"]
        assert "KMnO4" in methods["nitrogen"]["method"]
        assert "Olsen" in methods["phosphorus"]["method"]
        assert "ammonium acetate" in methods["potassium"]["method"]


class TestDataset002ExperimentalMetadata:
    @pytest.fixture
    def exp_data(self):
        assert EXPERIMENTAL_META_PATH.is_file()
        with open(EXPERIMENTAL_META_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_initial_soil_test_values(self, exp_data):
        soil = exp_data["site_and_soil_characteristics"]["initial_soil_test"]
        assert soil["pH"] == pytest.approx(7.5)
        assert soil["electrical_conductivity_dS_per_m"] == pytest.approx(0.16)
        assert soil["organic_carbon_g_per_kg"] == pytest.approx(4.65)
        assert soil["available_n_kmno4_kg_per_ha"] == pytest.approx(112.0)
        assert soil["available_p_olsen_kg_per_ha"] == pytest.approx(21.0)
        assert soil["available_k_nh4oac_kg_per_ha"] == pytest.approx(108.0)

    def test_fym_composition_at_50pct_moisture(self, exp_data):
        fym = exp_data["organic_manure_fym"]["nutrient_composition_at_50pct_moisture"]
        assert fym["nitrogen_n_pct"] == pytest.approx(0.85)
        assert fym["phosphorus_p2o5_pct"] == pytest.approx(0.23)
        assert fym["potassium_k2o_pct"] == pytest.approx(0.77)

    def test_five_treatments_recorded(self, exp_data):
        treatments = exp_data["treatments"]
        assert len(treatments) == 5
        assert "T1" in treatments and "T2" in treatments and "T5" in treatments


class TestDataset002TreatmentResultsAndTrackB:
    def test_table1_csv_treatment_means(self):
        assert TABLE1_CSV_PATH.is_file()
        with open(TABLE1_CSV_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("#")]
            reader = csv.DictReader(lines)
            rows = {r["treatment_id"]: r for r in reader}

        assert len(rows) == 5

        # T1 (100% NPK)
        assert float(rows["T1"]["rice_grain_yield_t_per_ha"]) == pytest.approx(6.74)
        assert float(rows["T1"]["rice_target_achievement_pct"]) == pytest.approx(89.9)
        assert float(rows["T1"]["wheat_grain_yield_t_per_ha"]) == pytest.approx(4.35)
        assert float(rows["T1"]["system_productivity_t_per_ha"]) == pytest.approx(11.4)

        # T2 (75% NPK + 25% FYM)
        assert float(rows["T2"]["rice_grain_yield_t_per_ha"]) == pytest.approx(7.29)
        assert float(rows["T2"]["rice_target_achievement_pct"]) == pytest.approx(97.2)

        # T5 (Control)
        assert float(rows["T5"]["rice_grain_yield_t_per_ha"]) == pytest.approx(3.69)
        assert rows["T5"]["rice_target_achievement_pct"] == ""  # Not inferred

    def test_track_b_validation_classification(self):
        assert TRACK_B_STUDY_PATH.is_file()
        with open(TRACK_B_STUDY_PATH, "r", encoding="utf-8") as f:
            study = yaml.safe_load(f)

        assert study["training_readiness"] == "needs_extraction_review"
        assert study["suitable_for_training"] is False
        assert study["classification"]["potential_validation_source"] is True
        assert study["classification"]["potential_stcr_validation_source"] is True
