"""
Tests for YAML data loading and validation.
============================================
Ensures that:
  - YAML files load correctly
  - Malformed YAML is detected and raises
  - Missing required fields are detected
  - Verified scientific values (Wheat 2022, Rice 2021) are correctly loaded
  - Unpopulated crops (Cotton) remain explicitly null (not fabricated)
  - The application does not silently substitute fabricated values
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from app.core.data_loader import (
    BiofertilizerData,
    DistrictAverages,
    STCRCoefficients,
    load_biofertilizer_data,
    load_district_averages,
    load_stcr_coefficients,
    _load_yaml,
    STCR_COEFFICIENTS_PATH,
    DISTRICT_AVERAGES_PATH,
    BIOFERTILIZERS_PATH,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_yaml(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a YAML string to a temporary file and return its path."""
    p = tmp_path / filename
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ── _load_yaml base function ─────────────────────────────────────────────────

class TestLoadYaml:

    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = _load_yaml(tmp_path / "nonexistent.yaml", "test")
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        result = _load_yaml(p, "empty")
        assert result == {}

    def test_valid_yaml_returns_dict(self, tmp_path):
        p = _write_yaml(tmp_path, "valid.yaml", """\
        key: value
        number: 42
        """)
        result = _load_yaml(p, "valid")
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_malformed_yaml_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "bad.yaml", """\
        key: value
          bad_indent: oops
        another: [unclosed
        """)
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            _load_yaml(p, "bad")

    def test_non_dict_yaml_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "list.yaml", """\
        - item1
        - item2
        """)
        with pytest.raises(ValueError, match="must contain a mapping"):
            _load_yaml(p, "list")

    def test_null_values_accepted(self, tmp_path):
        p = _write_yaml(tmp_path, "nulls.yaml", """\
        a: null
        b: null
        c: ~
        """)
        result = _load_yaml(p, "nulls")
        assert result["a"] is None
        assert result["b"] is None
        assert result["c"] is None


# ── STCR Coefficients ────────────────────────────────────────────────────────

class TestSTCRCoefficients:

    def test_load_from_project_file(self):
        """The project's stcr_coefficients.yaml should load without error."""
        coeffs = load_stcr_coefficients(reload=True)
        assert isinstance(coeffs, STCRCoefficients)

    def test_project_file_has_all_crops(self):
        coeffs = load_stcr_coefficients(reload=True)
        for crop in ("wheat", "rice", "cotton"):
            crop_data = coeffs.get_crop_coefficients(crop)
            assert isinstance(crop_data, dict), f"Missing crop: {crop}"

    def test_project_file_has_all_nutrients_per_crop(self):
        coeffs = load_stcr_coefficients(reload=True)
        for crop in ("wheat", "rice", "cotton"):
            for nutrient in ("N", "P", "K"):
                n_data = coeffs.get_nutrient_coefficients(crop, nutrient)
                assert isinstance(n_data, dict), f"Missing {crop}.{nutrient}"
                assert "a" in n_data, f"Missing 'a' in {crop}.{nutrient}"
                assert "b" in n_data, f"Missing 'b' in {crop}.{nutrient}"

    def test_project_file_is_populated_for_wheat_and_rice(self):
        """
        Wheat and Rice coefficients are populated from verified Track A studies.
        Cotton remains unpopulated.
        """
        coeffs = load_stcr_coefficients(reload=True)
        assert coeffs.is_populated is True
        assert coeffs.is_crop_populated("wheat") is True
        assert coeffs.is_crop_populated("rice") is True
        assert coeffs.is_crop_populated("cotton") is False

    def test_wheat_and_rice_coefficients_match_track_a(self):
        coeffs = load_stcr_coefficients(reload=True)
        # Wheat
        w_n = coeffs.get_nutrient_coefficients("wheat", "N")
        w_p = coeffs.get_nutrient_coefficients("wheat", "P")
        w_k = coeffs.get_nutrient_coefficients("wheat", "K")
        assert w_n["a"] == 3.78 and w_n["b"] == 0.96
        assert w_p["a"] == 1.54 and w_p["b"] == 0.23
        assert w_k["a"] == 0.95 and w_k["b"] == 0.09

        # Rice
        r_n = coeffs.get_nutrient_coefficients("rice", "N")
        r_p = coeffs.get_nutrient_coefficients("rice", "P")
        r_k = coeffs.get_nutrient_coefficients("rice", "K")
        assert r_n["a"] == 3.02 and r_n["b"] == 0.63
        assert r_p["a"] == 1.78 and r_p["b"] == 8.37
        assert r_k["a"] == 2.75 and r_k["b"] == 1.39

    def test_cotton_coefficients_are_null(self):
        """Cotton coefficients must remain null until verified data is acquired."""
        coeffs = load_stcr_coefficients(reload=True)
        for nutrient in ("N", "P", "K"):
            n_data = coeffs.get_nutrient_coefficients("cotton", nutrient)
            assert n_data.get("a") is None
            assert n_data.get("b") is None

    def test_metadata_present(self):
        coeffs = load_stcr_coefficients(reload=True)
        meta = coeffs.metadata
        assert isinstance(meta, dict)
        assert "schema_version" in meta

    def test_missing_crop_returns_empty_dict(self):
        coeffs = load_stcr_coefficients(reload=True)
        assert coeffs.get_crop_coefficients("sugarcane") == {}

    def test_missing_nutrient_returns_empty_dict(self):
        coeffs = load_stcr_coefficients(reload=True)
        assert coeffs.get_nutrient_coefficients("wheat", "Zn") == {}

    def test_custom_yaml_with_real_values(self, tmp_path):
        """If real coefficients are provided, is_populated should be True."""
        p = _write_yaml(tmp_path, "stcr.yaml", """\
        _metadata:
          schema_version: "1.0"
          verified: false
        wheat:
          N:
            a: 5.21
            b: 0.50
            target_yield_Mg_per_ha: 5.0
            FUE: 0.40
        """)
        coeffs = load_stcr_coefficients(path=p)
        assert coeffs.is_populated is True
        n = coeffs.get_nutrient_coefficients("wheat", "N")
        assert n["a"] == 5.21

    def test_missing_file_produces_unpopulated(self, tmp_path):
        coeffs = load_stcr_coefficients(path=tmp_path / "no_such_file.yaml")
        assert coeffs.is_populated is False


# ── District Averages ────────────────────────────────────────────────────────

class TestDistrictAverages:

    def test_load_from_project_file(self):
        avg = load_district_averages()
        assert isinstance(avg, DistrictAverages)

    def test_all_five_districts_present(self):
        avg = load_district_averages()
        for district in ("Bathinda", "Mansa", "Muktsar", "Moga", "Faridkot"):
            d = avg.get_district(district)
            assert isinstance(d, dict), f"Missing district: {district}"

    def test_all_soil_values_are_none(self):
        """
        Current state: all district averages should be None (placeholder).
        """
        avg = load_district_averages()
        for district in ("Bathinda", "Mansa", "Muktsar", "Moga", "Faridkot"):
            vals = avg.get_soil_values(district)
            for key, val in vals.items():
                assert val is None, (
                    f"District {district}.{key} is {val} — was data fabricated?"
                )

    def test_missing_district_returns_empty(self):
        avg = load_district_averages()
        vals = avg.get_soil_values("Ludhiana")
        assert all(v is None for v in vals.values())

    def test_metadata_present(self):
        avg = load_district_averages()
        meta = avg.metadata
        assert isinstance(meta, dict)
        assert "schema_version" in meta

    def test_custom_yaml_with_values(self, tmp_path):
        p = _write_yaml(tmp_path, "districts.yaml", """\
        _metadata:
          schema_version: "1.0"
        districts:
          TestDistrict:
            N_kg_per_ha: 200.0
            P2O5_kg_per_ha: 15.0
            K2O_kg_per_ha: 250.0
            pH: 8.1
            organic_carbon_pct: 0.38
        """)
        avg = load_district_averages(path=p)
        vals = avg.get_soil_values("TestDistrict")
        assert vals["nitrogen"] == 200.0
        assert vals["phosphorus"] == 15.0


# ── Biofertilizer Data ───────────────────────────────────────────────────────

class TestBiofertilizerData:

    def test_load_from_project_file(self):
        bio = load_biofertilizer_data()
        assert isinstance(bio, BiofertilizerData)

    def test_all_crops_present(self):
        bio = load_biofertilizer_data()
        for crop in ("wheat", "rice", "cotton"):
            c = bio.get_crop(crop)
            assert isinstance(c, dict), f"Missing crop: {crop}"

    def test_inoculants_are_empty_lists(self):
        """Current state: all inoculant lists should be empty (placeholder)."""
        bio = load_biofertilizer_data()
        for crop in ("wheat", "rice", "cotton"):
            c = bio.get_crop(crop)
            assert c.get("inoculants") == [], (
                f"Crop {crop} has inoculants — was data fabricated?"
            )

    def test_missing_crop_returns_empty_dict(self):
        bio = load_biofertilizer_data()
        assert bio.get_crop("sugarcane") == {}

    def test_metadata_present(self):
        bio = load_biofertilizer_data()
        meta = bio.metadata
        assert isinstance(meta, dict)
        assert "schema_version" in meta


# ── YAML schema validation ───────────────────────────────────────────────────

class TestYAMLSchemaValidation:

    def test_stcr_yaml_is_valid_yaml(self):
        """The project STCR YAML file must be parseable."""
        with open(STCR_COEFFICIENTS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_district_yaml_is_valid_yaml(self):
        with open(DISTRICT_AVERAGES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_biofertilizer_yaml_is_valid_yaml(self):
        with open(BIOFERTILIZERS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_stcr_yaml_has_required_structure(self):
        with open(STCR_COEFFICIENTS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Must have all three crops
        for crop in ("wheat", "rice", "cotton"):
            assert crop in data, f"Missing crop '{crop}' in STCR YAML"
            for nutrient in ("N", "P", "K"):
                assert nutrient in data[crop], (
                    f"Missing nutrient '{nutrient}' under crop '{crop}'"
                )

    def test_district_yaml_has_required_structure(self):
        with open(DISTRICT_AVERAGES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        districts = data.get("districts", {})
        for name in ("Bathinda", "Mansa", "Muktsar", "Moga", "Faridkot"):
            assert name in districts, f"Missing district '{name}'"

    def test_no_fabricated_values_in_cotton(self):
        """
        CRITICAL: Ensure cotton has not been silently filled with fake coefficients.
        All 'a' values for cotton must be null until verified data arrives.
        """
        with open(STCR_COEFFICIENTS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for nutrient in ("N", "P", "K"):
            a_val = data["cotton"][nutrient].get("a")
            assert a_val is None, (
                f"cotton.{nutrient}.a = {a_val} — this appears fabricated."
            )
