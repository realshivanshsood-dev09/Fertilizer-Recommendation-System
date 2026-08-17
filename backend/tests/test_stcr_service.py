"""
Tests for STCRService.
Verifies that the STCR service correctly returns placeholder values
and does not invent coefficients.
"""

from __future__ import annotations

import pytest

from app.core.constants import Crop, District, Season, SoilSource
from app.services.soil_resolution import SoilProfile
from app.services.stcr_service import STCRService


@pytest.fixture
def service() -> STCRService:
    return STCRService()


def _make_soil(
    n=None, p=None, k=None, ph=None, oc=None,
    source=SoilSource.SOIL_HEALTH_CARD
) -> SoilProfile:
    return SoilProfile(
        nitrogen=n, phosphorus=p, potassium=k,
        ph=ph, organic_carbon=oc,
        source=source, reliability_note="test",
    )


class TestSTCRService:

    def test_stcr_returns_none_doses_when_coefficients_are_placeholders(self, service):
        """
        STCR coefficients are not loaded — all doses must be None.
        This test ensures we never invent fertilizer numbers.
        """
        soil = _make_soil(n=120.0, p=18.0, k=180.0)
        result = service.compute(Crop.WHEAT, District.BATHINDA, Season.RABI, soil)
        assert result.N_kg_per_ha is None
        assert result.P2O5_kg_per_ha is None
        assert result.K2O_kg_per_ha is None

    def test_stcr_notes_contains_placeholder_marker(self, service):
        soil = _make_soil(n=100.0, p=15.0, k=200.0)
        result = service.compute(Crop.WHEAT, District.BATHINDA, Season.RABI, soil)
        assert "placeholder" in result.notes.lower() or "PLACEHOLDER" in result.notes

    def test_stcr_skips_when_soil_incomplete(self, service):
        """Incomplete soil profile must produce None doses and appropriate note."""
        soil = _make_soil()  # all None
        result = service.compute(Crop.RICE, District.MANSA, Season.KHARIF, soil)
        assert result.N_kg_per_ha is None
        assert "not available" in result.data_source or "skipped" in result.data_source.lower()

    def test_stcr_all_crops_return_placeholder(self, service):
        """All three crops must return placeholder baselines."""
        soil = _make_soil(n=100.0, p=15.0, k=200.0)
        for crop, season in [
            (Crop.WHEAT, Season.RABI),
            (Crop.RICE, Season.KHARIF),
            (Crop.COTTON, Season.KHARIF),
        ]:
            result = service.compute(crop, District.MOGA, season, soil)
            assert result.N_kg_per_ha is None, f"Expected None for {crop.value}"

    def test_stcr_all_districts_supported(self, service):
        """All five target districts must be accepted without error."""
        soil = _make_soil(n=100.0, p=15.0, k=200.0)
        for district in District:
            result = service.compute(Crop.WHEAT, district, Season.RABI, soil)
            assert result is not None

    def test_stcr_questionnaire_fallback_handled(self, service):
        soil = _make_soil(source=SoilSource.QUESTIONNAIRE_FALLBACK)
        result = service.compute(Crop.WHEAT, District.FARIDKOT, Season.RABI, soil)
        assert result.N_kg_per_ha is None
