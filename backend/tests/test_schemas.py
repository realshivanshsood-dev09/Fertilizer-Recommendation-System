"""
Tests for Pydantic request/response schemas.
Validates field constraints, crop-season validation, and soil-source consistency.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.constants import Crop, District, IrrigationType, Season, SoilSource
from app.schemas.request import RecommendRequest, SoilInput


def _valid_shc_request(**overrides) -> dict:
    base = {
        "crop": "wheat",
        "district": "Bathinda",
        "season": "rabi",
        "soil_source": "soil_health_card",
        "soil": {"nitrogen": 120.0, "phosphorus": 18.0, "potassium": 180.0},
        "irrigation": "tube_well",
    }
    base.update(overrides)
    return base


class TestRecommendRequest:

    def test_valid_wheat_rabi(self):
        req = RecommendRequest(**_valid_shc_request())
        assert req.crop == Crop.WHEAT
        assert req.district == District.BATHINDA

    def test_valid_rice_kharif(self):
        req = RecommendRequest(**_valid_shc_request(crop="rice", season="kharif"))
        assert req.crop == Crop.RICE

    def test_valid_cotton_kharif(self):
        req = RecommendRequest(**_valid_shc_request(crop="cotton", season="kharif"))
        assert req.crop == Crop.COTTON

    def test_invalid_crop_season_wheat_kharif(self):
        """Wheat is a rabi crop — kharif should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendRequest(**_valid_shc_request(season="kharif"))
        assert "rabi" in str(exc_info.value).lower() or "season" in str(exc_info.value).lower()

    def test_invalid_crop_season_rice_rabi(self):
        """Rice is a kharif crop — rabi should raise ValidationError."""
        with pytest.raises(ValidationError):
            RecommendRequest(**_valid_shc_request(crop="rice", season="rabi"))

    def test_invalid_district_rejected(self):
        with pytest.raises(ValidationError):
            RecommendRequest(**_valid_shc_request(district="Ludhiana"))

    def test_invalid_crop_rejected(self):
        with pytest.raises(ValidationError):
            RecommendRequest(**_valid_shc_request(crop="sugarcane"))

    def test_questionnaire_fallback_with_npk_raises(self):
        """Questionnaire fallback must not carry N/P/K values."""
        with pytest.raises(ValidationError) as exc_info:
            RecommendRequest(**_valid_shc_request(
                soil_source="questionnaire_fallback",
                soil={"nitrogen": 100.0, "phosphorus": None, "potassium": None},
            ))
        assert "questionnaire" in str(exc_info.value).lower()

    def test_questionnaire_fallback_with_null_npk_valid(self):
        """Questionnaire fallback with all-null N/P/K is valid."""
        req = RecommendRequest(**_valid_shc_request(
            soil_source="questionnaire_fallback",
            soil={},
        ))
        assert req.soil_source == SoilSource.QUESTIONNAIRE_FALLBACK
        assert req.soil.nitrogen is None

    def test_soil_ph_bounds_enforced(self):
        with pytest.raises(ValidationError):
            RecommendRequest(**_valid_shc_request(soil={"ph": 15.0}))

    def test_soil_nitrogen_negative_rejected(self):
        with pytest.raises(ValidationError):
            RecommendRequest(**_valid_shc_request(soil={"nitrogen": -10.0}))

    def test_all_five_districts_accepted(self):
        for district in ["Bathinda", "Mansa", "Muktsar", "Moga", "Faridkot"]:
            req = RecommendRequest(**_valid_shc_request(district=district))
            assert req.district.value == district

    def test_block_is_optional(self):
        req = RecommendRequest(**_valid_shc_request(block="Talwandi Sabo"))
        assert req.block == "Talwandi Sabo"

    def test_soil_source_is_recorded(self):
        req = RecommendRequest(**_valid_shc_request())
        assert req.soil_source == SoilSource.SOIL_HEALTH_CARD
