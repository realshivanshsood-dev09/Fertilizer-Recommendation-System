"""
Tests for YAML data loading and validation.
============================================
Ensures that:
  - YAML files load correctly
  - Malformed YAML is detected and raises
  - Missing required fields are detected
  - Null scientific values are accepted as "not yet populated"
  - Incorrect schema is rejected
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
        coeffs = load_stcr_coefficients()
        assert isinstance(coeffs, STCRCoefficients)

    def test_project_file_has_all_crops(self):
        coeffs = load_stcr_coefficients()
        for crop in ("wheat", "rice", "cotton"):
            crop_data = coeffs.get_crop_coefficients(crop)
            assert isinstance(crop_data, dict), f"Missing crop: {crop}"

    def test_project_file_has_all_nutrients_per_crop(self):
        coeffs = load_stcr_coefficients()
        for crop in ("wheat", "rice", "cotton"):
            for nutrient in ("N", "P", "K"):
                n_data = coeffs.get_nutrient_coefficients(crop, nutrient)
                assert isinstance(n_data, dict), f"Missing {crop}.{nutrient}"
                # Must have the required keys (even if null)
                assert "a" in n_data, f"Missing 'a' in {crop}.{nutrient}"
                assert "b" in n_data, f"Missing 'b' in {crop}.{nutrient}"
                assert "target_yield_Mg_per_ha" in n_data
                assert "FUE" in n_data

    def test_project_file_is_not_populated(self):
        """
        Current state: all coefficients should be None (placeholder).
        This test ensures we never silently populate with fabricated values.
        """
        coeffs = load_stcr_coefficients()
        assert coeffs.is_populated is False, (
            "STCR coefficients appear populated — was data fabricated? "
            "Only real PAU/ICAR values should be loaded."
        )

    def test_null_coefficients_produce_none_doses(self):
        """With null coefficients, get_nutrient_coefficients returns null fields."""
        coeffs = load_stcr_coefficients()
        for crop in ("wheat", "rice", "cotton"):
            n_data = coeffs.get_nutrient_coefficients(crop, "N")
            assert n_data.get("a") is None
            assert n_data.get("b") is None

    def test_metadata_present(self):
        coeffs = load_stcr_coefficients()
        meta = coeffs.metadata
        assert isinstance(meta, dict)
        assert "schema_version" in meta

    def test_missing_crop_returns_empty_dict(self):
        coeffs = load_stcr_coefficients()
        assert coeffs.get_crop_coefficients("sugarcane") == {}

    def test_missing_nutrient_returns_empty_dict(self):
        coeffs = load_stcr_coefficients()
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

    def test_no_fabricated_values_in_stcr(self):
        """
        CRITICAL: Ensure no one has silently filled in fake STCR coefficients.
        All 'a' values must be null until real data arrives.
        """
        with open(STCR_COEFFICIENTS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for crop in ("wheat", "rice", "cotton"):
            for nutrient in ("N", "P", "K"):
                a_val = data[crop][nutrient].get("a")
                assert a_val is None, (
                    f"{crop}.{nutrient}.a = {a_val} — this appears fabricated. "
                    "Only real PAU/ICAR coefficients should be loaded."
                )
