"""
Tests for SoilResolutionService.
Verifies that the correct SoilProfile is produced for each soil_source
and that the provenance is correctly recorded.
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
from app.schemas.request import RecommendRequest, SoilInput
from app.services.soil_resolution import SoilProfile, SoilResolutionService


@pytest.fixture
def service() -> SoilResolutionService:
    return SoilResolutionService()


def _make_request(
    soil_source: SoilSource,
    soil: SoilInput | None = None,
) -> RecommendRequest:
    return RecommendRequest(
        crop=Crop.WHEAT,
        district=District.BATHINDA,
        season=Season.RABI,
        soil_source=soil_source,
        soil=soil or SoilInput(),
        irrigation=IrrigationType.TUBE_WELL,
    )


class TestSoilResolutionService:

    def test_soil_health_card_returns_correct_source(self, service):
        soil_input = SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.source == SoilSource.SOIL_HEALTH_CARD

    def test_soil_health_card_values_propagated(self, service):
        soil_input = SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0, ph=7.5)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.nitrogen == 120.0
        assert profile.phosphorus == 18.0
        assert profile.potassium == 180.0
        assert profile.ph == 7.5

    def test_shc_profile_is_complete_for_stcr(self, service):
        soil_input = SoilInput(nitrogen=100.0, phosphorus=15.0, potassium=200.0)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.is_complete_for_stcr() is True

    def test_shc_profile_with_missing_npk_is_not_complete(self, service):
        soil_input = SoilInput(nitrogen=None, phosphorus=None, potassium=None)
        req = _make_request(SoilSource.SOIL_HEALTH_CARD, soil_input)
        profile = service.resolve(req)
        assert profile.is_complete_for_stcr() is False

    def test_district_average_returns_correct_source(self, service):
        req = _make_request(SoilSource.DISTRICT_AVERAGE)
        profile = service.resolve(req)
        assert profile.source == SoilSource.DISTRICT_AVERAGE

    def test_district_average_all_none_until_data_loaded(self, service):
        """District averages are all None until PAU survey data is loaded."""
        req = _make_request(SoilSource.DISTRICT_AVERAGE)
        profile = service.resolve(req)
        # Verify placeholder — no invented values
        assert profile.nitrogen is None
        assert profile.phosphorus is None
        assert profile.potassium is None

    def test_questionnaire_fallback_returns_correct_source(self, service):
        req = _make_request(SoilSource.QUESTIONNAIRE_FALLBACK)
        profile = service.resolve(req)
        assert profile.source == SoilSource.QUESTIONNAIRE_FALLBACK

    def test_questionnaire_fallback_has_no_npk(self, service):
        """Questionnaire cannot provide N/P/K — must remain None."""
        req = _make_request(SoilSource.QUESTIONNAIRE_FALLBACK)
        profile = service.resolve(req)
        assert profile.nitrogen is None
        assert profile.phosphorus is None
        assert profile.potassium is None
        assert profile.is_complete_for_stcr() is False

    def test_soil_profile_repr(self, service):
        req = _make_request(SoilSource.DISTRICT_AVERAGE)
        profile = service.resolve(req)
        rep = repr(profile)
        assert "district_average" in rep
