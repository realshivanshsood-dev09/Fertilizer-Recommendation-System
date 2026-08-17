"""
Tests for Track A Dataset 001: PAU Wheat STCR (Singh et al., 2022)
==================================================================
Validates:
  - Source registry entry SRC-ICAR-PAU-WHEAT-STCR-2022
  - Dataset registry entry DS-ICAR-PAU-WHEAT-STCR-2022
  - Raw PDF existence and SHA-256 checksum match
  - Exact parameters and equations in pau_wheat_stcr_2022.yaml
  - Table 1 experimental summary data integrity
  - Experimental design metadata
  - Track B ML readiness status
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from app.ingestion.checksum import compute_sha256, verify_checksum
from app.ingestion.registry_loader import load_and_validate_all_registries
from app.ingestion.schemas import VerificationStatus

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_YAML_PATH = _REPO_ROOT / "data" / "processed" / "pau_wheat_stcr_2022.yaml"
TABLE1_CSV_PATH = _REPO_ROOT / "data" / "processed" / "pau_wheat_stcr_2022_table1.csv"
EXPERIMENTAL_META_PATH = _REPO_ROOT / "data" / "processed" / "pau_wheat_stcr_2022_experimental_metadata.yaml"
TRACK_B_STUDY_PATH = _REPO_ROOT / "ml" / "registry" / "pau_wheat_stcr_2022_study.yaml"
RAW_PDF_PATH = _REPO_ROOT / "data" / "raw" / "icar" / "singh_mavi_saini_2022_pau_wheat_stcr.pdf"


class TestDataset001Registries:
    def test_source_and_dataset_registries_load_cleanly(self):
        registries = load_and_validate_all_registries()
        assert "SRC-ICAR-PAU-WHEAT-STCR-2022" in registries.sources
        assert "DS-ICAR-PAU-WHEAT-STCR-2022" in registries.datasets

    def test_source_registry_metadata(self):
        registries = load_and_validate_all_registries()
        src = registries.get_source("SRC-ICAR-PAU-WHEAT-STCR-2022")
        assert src is not None
        assert src.institution == "Punjab Agricultural University, Ludhiana, Punjab, India"
        assert src.source_type == "university"
        assert src.publisher == "Indian Council of Agricultural Research"
        assert src.publication_year == 2022
        assert src.doi == "10.56093/ijas.v92i12.125137"
        assert src.license == "Not explicitly stated"
        assert src.access_status == "Openly accessible via ICAR e-pubs"
        assert src.verification_status == VerificationStatus.VERIFIED
        assert src.crop == "wheat"

    def test_dataset_registry_and_checksum(self):
        registries = load_and_validate_all_registries()
        ds = registries.get_dataset("DS-ICAR-PAU-WHEAT-STCR-2022")
        assert ds is not None
        assert ds.source_id == "SRC-ICAR-PAU-WHEAT-STCR-2022"
        assert ds.local_path == "data/raw/icar/singh_mavi_saini_2022_pau_wheat_stcr.pdf"
        assert ds.extraction_method is not None
        assert ds.license == "Not explicitly stated"
        assert ds.access_status == "Openly accessible via ICAR e-pubs"
        assert ds.verification_status == VerificationStatus.VERIFIED

        # Check that physical PDF file matches registered checksum
        assert RAW_PDF_PATH.is_file(), f"Raw PDF not found at {RAW_PDF_PATH}"
        assert verify_checksum(RAW_PDF_PATH, ds.checksum) is True


class TestDataset001STCREquations:
    @pytest.fixture
    def stcr_data(self):
        assert PROCESSED_YAML_PATH.is_file(), f"Processed YAML not found at {PROCESSED_YAML_PATH}"
        with open(PROCESSED_YAML_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_provenance_and_scope(self, stcr_data):
        assert stcr_data["provenance"]["source_id"] == "SRC-ICAR-PAU-WHEAT-STCR-2022"
        assert stcr_data["provenance"]["table_reference"] == "Table 2: Nutrient requirement, response and fertilizer adjustment equations for wheat"
        assert stcr_data["scope"]["cultivar"] == "HD3086"
        assert "Typic Ustochrepts" in stcr_data["scope"]["soil_type"]

    def test_nutrient_requirements(self, stcr_data):
        nr = stcr_data["parameters"]["nutrient_requirement_kg_per_q"]
        assert nr["N"] == pytest.approx(2.06)
        assert nr["P2O5"] == pytest.approx(0.78)
        assert nr["K2O"] == pytest.approx(1.95)

    def test_soil_contributions(self, stcr_data):
        cs = stcr_data["parameters"]["soil_contribution_pct"]
        assert cs["N"] == pytest.approx(52.3)
        assert cs["P2O5"] == pytest.approx(11.7)
        assert cs["K2O"] == pytest.approx(20.2)

    def test_fertilizer_contributions(self, stcr_data):
        cf = stcr_data["parameters"]["fertilizer_contribution_pct"]
        assert cf["N"] == pytest.approx(54.0)
        assert cf["P2O5"] == pytest.approx(50.0)
        assert cf["K2O"] == pytest.approx(20.6)

    def test_rice_residue_contributions(self, stcr_data):
        crr = stcr_data["parameters"]["rice_residue_contribution_pct"]
        assert crr["N"] == pytest.approx(42.0)
        assert crr["P2O5"] == pytest.approx(15.3)
        assert crr["K2O"] == pytest.approx(26.0)

    def test_npk_alone_equations(self, stcr_data):
        npk = stcr_data["equations"]["npk_alone"]
        assert npk["N"]["equation_string"] == "3.78*T - 0.96*SN"
        assert npk["N"]["a"] == pytest.approx(3.78)
        assert npk["N"]["b"] == pytest.approx(0.96)

        assert npk["P2O5"]["equation_string"] == "1.54*T - 0.23*SP2O5"
        assert npk["P2O5"]["a"] == pytest.approx(1.54)
        assert npk["P2O5"]["b"] == pytest.approx(0.23)

        assert npk["K2O"]["equation_string"] == "0.95*T - 0.09*SK2O"
        assert npk["K2O"]["a"] == pytest.approx(0.95)
        assert npk["K2O"]["b"] == pytest.approx(0.09)

    def test_npk_plus_rice_residue_equations(self, stcr_data):
        npk_rr = stcr_data["equations"]["npk_plus_rice_residue"]
        assert npk_rr["N"]["equation_string"] == "3.78*T - 0.96*SN - 0.77*RRN"
        assert npk_rr["N"]["c_residue"] == pytest.approx(0.77)

        assert npk_rr["P2O5"]["equation_string"] == "1.54*T - 0.23*SP2O5 - 0.30*RRP2O5"
        assert npk_rr["P2O5"]["c_residue"] == pytest.approx(0.30)

        assert npk_rr["K2O"]["equation_string"] == "0.95*T - 0.10*SK2O - 0.12*RRK2O"
        assert npk_rr["K2O"]["c_residue"] == pytest.approx(0.12)

    def test_soil_test_methods_declared(self, stcr_data):
        methods = stcr_data["soil_test_methods"]
        assert "KMnO4" in methods["nitrogen"]["method"]
        assert "NaHCO3" in methods["phosphorus"]["method"]
        assert "ammonium acetate" in methods["potassium"]["method"]


class TestDataset001ExperimentalAndTrackB:
    def test_table1_csv_exists_and_valid(self):
        import csv
        assert TABLE1_CSV_PATH.is_file()
        with open(TABLE1_CSV_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("#")]
            reader = csv.DictReader(lines)
            rows = list(reader)
        assert len(rows) == 3
        strips = {r["strip"] for r in rows}
        assert strips == {"Control", "Strip_1", "Strip_2"}

    def test_experimental_metadata_exists(self):
        assert EXPERIMENTAL_META_PATH.is_file()
        with open(EXPERIMENTAL_META_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["trial_design"]["cultivar"] == "HD3086"
        assert data["trial_design"]["treatment_levels"]["rice_residue_t_per_ha"] == pytest.approx(6.0)

    def test_track_b_readiness_flagged(self):
        assert TRACK_B_STUDY_PATH.is_file()
        with open(TRACK_B_STUDY_PATH, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        assert meta["training_readiness"] == "needs_extraction_review"
        assert meta["ml_assessment"]["suitable_for_training"] is False
