"""
Tests for Track B Data Architecture & Study Registries (B1, B2, B3)
===================================================================
Validates:
  - B1: Soil Health Card (SHC) registry, schema, target districts, and PII exclusion.
  - B1: SHC Track B ML feature registry and non-training classification.
  - B2: Sharma et al. (2021) PAU LTFE study registry and treatment_mean granularity.
  - Track B Unified Dataset Schema (B1/B2/B3 separation, GroupKFold validation policy).
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SHC_REGISTRY_PATH = _REPO_ROOT / "data" / "metadata" / "shc_registry.yaml"
SHC_ML_REGISTRY_PATH = _REPO_ROOT / "ml" / "registry" / "shc_track_b_registry.yaml"
SHARMA_STUDY_PATH = _REPO_ROOT / "ml" / "registry" / "sharma_2021_ltfe_rice_wheat_study.yaml"
TRACK_B_SCHEMA_PATH = _REPO_ROOT / "data" / "metadata" / "track_b_dataset_schema.yaml"
SHARMA_PDF_PATH = _REPO_ROOT / "data" / "raw" / "icar" / "sharma_dheri_saini_2021_pau_ltfe_rice_wheat.pdf"


class TestB1SoilHealthCardRegistry:
    @pytest.fixture
    def shc_data(self):
        assert SHC_REGISTRY_PATH.is_file()
        with open(SHC_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_shc_target_districts(self, shc_data):
        districts = [d["district_name"] for d in shc_data["target_region"]["districts"]]
        assert "Bathinda" in districts
        assert "Mansa" in districts
        assert "Faridkot" in districts
        assert "Moga" in districts
        assert "Sri Muktsar Sahib" in districts

    def test_shc_schema_units_and_properties(self, shc_data):
        schema = shc_data["schema"]
        assert schema["soil_properties"]["pH"]["unit"] == "unitless"
        assert schema["soil_properties"]["EC"]["unit"] == "dS/m"
        assert schema["soil_properties"]["OC"]["unit"] == "%"
        assert schema["macronutrients"]["N"]["unit"] == "kg/ha"
        assert schema["macronutrients"]["P"]["unit"] == "kg/ha"
        assert schema["macronutrients"]["K"]["unit"] == "kg/ha"

    def test_shc_pii_strict_exclusion(self, shc_data):
        pii = shc_data["privacy_and_security_assessment"]["personally_identifiable_information"]
        assert pii["policy"] == "STRICT_EXCLUSION"
        excluded = pii["excluded_fields"]
        assert "farmer_name" in excluded
        assert "mobile_number" in excluded
        assert "aadhaar_number" in excluded

    def test_shc_ml_registry(self):
        assert SHC_ML_REGISTRY_PATH.is_file()
        with open(SHC_ML_REGISTRY_PATH, "r", encoding="utf-8") as f:
            ml_data = yaml.safe_load(f)
        assert ml_data["ml_role"]["training_candidate"] is False
        assert ml_data["ml_role"]["feature_lookup_candidate"] is True
        assert ml_data["suitable_for_training"] is False
        assert ml_data["privacy_compliance"]["pii_status"] == "verified_excluded"


class TestB2Sharma2021StudyRegistry:
    @pytest.fixture
    def study_data(self):
        assert SHARMA_STUDY_PATH.is_file()
        with open(SHARMA_STUDY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_study_metadata_and_granularity(self, study_data):
        assert study_data["study_id"] == "STUDY-PAU-LTFE-RICE-WHEAT-2021"
        assert study_data["reported_data_granularity"]["granularity"] == "treatment_mean"
        assert study_data["reported_data_granularity"]["raw_replicate_plots_published"] is False
        assert study_data["ml_assessment"]["suitable_for_training"] is False
        assert study_data["ml_assessment"]["suitable_for_validation"] is True

    def test_six_ltfe_treatments(self, study_data):
        treatments = study_data["treatments"]
        assert len(treatments) == 6
        treatment_ids = [t["id"] for t in treatments]
        assert set(treatment_ids) == {"T1", "T2", "T3", "T4", "T5", "T6"}

    def test_raw_pdf_exists(self):
        assert SHARMA_PDF_PATH.is_file()


class TestTrackBUnifiedDatasetSchema:
    @pytest.fixture
    def schema_data(self):
        assert TRACK_B_SCHEMA_PATH.is_file()
        with open(TRACK_B_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_data_classes_b1_b2_b3_defined(self, schema_data):
        classes = schema_data["data_classes"]
        assert "B1_soil_state" in classes
        assert "B2_field_trial_response" in classes
        assert "B3_stcr_baseline" in classes
        assert classes["B1_soil_state"]["suitable_for_response_training"] is False

    def test_grouped_validation_policy(self, schema_data):
        val = schema_data["validation_strategy"]
        assert "study_id" in val["grouping_strategy"]
        assert "STRICTLY PROHIBITED" in val["prohibition"]

    def test_ml_target_candidates(self, schema_data):
        targets = schema_data["ml_formulation_policy"]["candidate_targets"]
        assert "target_option_1" in targets  # Delta_D
        assert "target_option_2" in targets  # Delta_Y
