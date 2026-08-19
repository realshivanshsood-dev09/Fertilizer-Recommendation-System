"""
Tests for SoilResolutionService.
Verifies the 4-level soil resolution hierarchy:
  Level A: Farmer Soil Health Card (measured)
  Level B: Verified SHC district prior (prior_estimate)
  Level C: Questionnaire fallback (qualitative_only)
  Level D: Insufficient data
"""

from __future__ import annotations

import pytest

from app.core.constants import (
    Crop,
    District,
    IrrigationType,
    Season,
    SoilSource,
)
from app.core.data_loader import DistrictAverages
from app.schemas.request import RecommendRequest, SoilInput
from app.services.soil_resolution import SoilProfile, SoilResolutionService


@pytest.fixture
def service() -> SoilResolutionService:
    return SoilResolutionService()


def _make_request(
    soil_source: SoilSource,
    soil: SoilInput | None = None,
    district: District = District.BATHINDA,
) -> RecommendRequest:
    return RecommendRequest(
        crop=Crop.WHEAT,
        district=district,
        season=Season.RABI,
        soil_source=soil_source,
        soil=soil or SoilInput(),
        irrigation=IrrigationType.TUBE_WELL,
    )


class TestSoilResolutionService:

    def test_soil_health_card_measured_status_and_confidence(self, service):
        soil_input = SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0, ph=7.5, organic_carbon=0.45)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.source == SoilSource.SOIL_HEALTH_CARD
        assert profile.is_lab_measured is True
        assert profile.status == "measured"
        assert profile.confidence == 0.95
        assert profile.nitrogen == 120.0
        assert profile.phosphorus == 18.0
        assert profile.potassium == 180.0
        assert profile.is_complete_for_stcr() is True

    def test_shc_profile_with_missing_npk_falls_back_or_flags_insufficient(self, service):
        soil_input = SoilInput(nitrogen=None, phosphorus=None, potassium=None)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.is_lab_measured is False
        assert profile.status in ["insufficient_data", "prior_estimate"]
        assert profile.is_complete_for_stcr() is False

    def test_district_average_returns_correct_source_and_status(self, service):
        req = _make_request(SoilSource.DISTRICT_AVERAGE)
        profile = service.resolve(req)
        assert profile.source == SoilSource.DISTRICT_AVERAGE
        assert profile.is_lab_measured is False
        assert profile.status == "insufficient_data"  # currently unpopulated in YAML
        assert profile.confidence == 0.0

    def test_district_prior_fallback_when_populated(self):
        # Create a mock DistrictAverages with populated Bathinda prior
        mock_data = {
            "districts": {
                "Bathinda": {
                    "N_kg_per_ha": 115.0,
                    "P2O5_kg_per_ha": 20.0,
                    "K2O_kg_per_ha": 160.0,
                    "pH": 7.8,
                    "organic_carbon_pct": 0.42,
                }
            }
        }
        mock_avg = DistrictAverages(mock_data, path=None)
        custom_service = SoilResolutionService(district_averages=mock_avg)

        req = _make_request(SoilSource.DISTRICT_AVERAGE, district=District.BATHINDA)
        profile = custom_service.resolve(req)
        assert profile.source == SoilSource.DISTRICT_AVERAGE
        assert profile.is_lab_measured is False
        assert profile.status == "prior_estimate"
        assert profile.confidence == 0.60
        assert profile.nitrogen == 115.0
        assert profile.phosphorus == 20.0
        assert profile.potassium == 160.0
        assert profile.is_complete_for_stcr() is True

    def test_questionnaire_fallback_returns_correct_source_and_status(self, service):
        req = _make_request(SoilSource.QUESTIONNAIRE_FALLBACK)
        profile = service.resolve(req)
        assert profile.source == SoilSource.QUESTIONNAIRE_FALLBACK
        assert profile.is_lab_measured is False
        assert profile.status == "qualitative_only"
        assert profile.confidence == 0.20
        assert profile.nitrogen is None
        assert profile.phosphorus is None
        assert profile.potassium is None
        assert profile.is_complete_for_stcr() is False

    def test_soil_profile_repr(self, service):
        soil_input = SoilInput(nitrogen=100.0, phosphorus=15.0, potassium=200.0)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        rep = repr(profile)
        assert "soil_health_card" in rep
        assert "lab_measured=True" in rep
