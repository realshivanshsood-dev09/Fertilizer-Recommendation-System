"""
Tests for STCRService.
======================
Verifies:
  - Wheat STCR calculation matches PAU 2022 Dataset 001 equations
  - Rice STCR calculation matches PAU 2021 Dataset 002 equations
  - Cotton returns placeholder/None doses (no fabricated coefficients)
  - Negative soil inputs are rejected with ValueError
  - Negative target yield is rejected with ValueError
  - Negative calculated doses are clipped to 0.0
  - Incomplete soil profiles skip STCR gracefully
  - Provenance and metadata are propagated correctly
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


class TestSTCRServiceWheat:

    def test_wheat_stcr_npk_calculation(self, service):
        """
        FN = 3.78*T - 0.96*SN
        FP2O5 = 1.54*T - 0.23*SP2O5
        FK2O = 0.95*T - 0.09*SK2O
        For T = 50 q/ha, SN = 120 kg/ha, SP = 18 kg/ha, SK = 180 kg/ha:
          FN = 3.78*50 - 0.96*120 = 189.0 - 115.2 = 73.8
          FP = 1.54*50 - 0.23*18 = 77.0 - 4.14 = 72.86
          FK = 0.95*50 - 0.09*180 = 47.5 - 16.2 = 31.3
        """
        soil = _make_soil(n=120.0, p=18.0, k=180.0)
        result = service.compute(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil=soil,
            target_yield_q_ha=50.0,
        )
        assert result.N_kg_per_ha == pytest.approx(73.8, rel=1e-2)
        assert result.P2O5_kg_per_ha == pytest.approx(72.86, rel=1e-2)
        assert result.K2O_kg_per_ha == pytest.approx(31.3, rel=1e-2)
        assert result.is_placeholder is False
        assert result.dataset_id == "DS-ICAR-PAU-WHEAT-STCR-2022"
        assert result.provenance_status == "verified"

    def test_wheat_stcr_with_rice_residue(self, service):
        """
        Residue formula:
          FN = 3.78*T - 0.96*SN - 0.77*RRN
          FP2O5 = 1.54*T - 0.23*SP2O5 - 0.30*RRP2O5
          FK2O = 0.95*T - 0.10*SK2O - 0.12*RRK2O
        """
        soil = _make_soil(n=120.0, p=18.0, k=180.0)
        result = service.compute(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil=soil,
            target_yield_q_ha=50.0,
            rice_residue_incorporated=True,
            rice_residue_rrn=20.0,
            rice_residue_rrp2o5=5.0,
            rice_residue_rrk2o=30.0,
        )
        # Expected:
        # FN = 73.8 - 0.77*20 = 73.8 - 15.4 = 58.4
        # FP = 72.86 - 0.30*5 = 72.86 - 1.5 = 71.36
        # FK = (0.95*50 - 0.10*180) - 0.12*30 = (47.5 - 18.0) - 3.6 = 25.9
        assert result.N_kg_per_ha == pytest.approx(58.4, rel=1e-2)
        assert result.P2O5_kg_per_ha == pytest.approx(71.36, rel=1e-2)
        assert result.K2O_kg_per_ha == pytest.approx(25.9, rel=1e-2)
        assert "RESIDUE" in result.equation_version


class TestSTCRServiceRice:

    def test_rice_stcr_calculation(self, service):
        """
        FN = 3.02*T - 0.63*SN
        FP2O5 = 1.78*T - 8.37*SP
        FK2O = 2.75*T - 1.39*SK
        For T = 70 q/ha, SN = 114.7, SP = 10.0, SK = 100.0:
          FN = 3.02*70 - 0.63*114.7 = 211.4 - 72.261 = 139.14
          FP = 1.78*70 - 8.37*10 = 124.6 - 83.7 = 40.9
          FK = 2.75*70 - 1.39*100 = 192.5 - 139.0 = 53.5
        """
        soil = _make_soil(n=114.7, p=10.0, k=100.0)
        result = service.compute(
            crop=Crop.RICE,
            district=District.MANSA,
            season=Season.KHARIF,
            soil=soil,
            target_yield_q_ha=70.0,
        )
        assert result.N_kg_per_ha == pytest.approx(139.14, rel=1e-2)
        assert result.P2O5_kg_per_ha == pytest.approx(40.9, rel=1e-2)
        assert result.K2O_kg_per_ha == pytest.approx(53.5, rel=1e-2)
        assert result.is_placeholder is False
        assert result.dataset_id == "DS-ICAR-PAU-RICE-TYE-INM-2021"
        assert result.provenance_status == "verified_application_probable_calibration"


class TestSTCRServiceEdgeCases:

    def test_cotton_returns_placeholder(self, service):
        """Cotton coefficients are unverified — doses must be None."""
        soil = _make_soil(n=120.0, p=18.0, k=180.0)
        result = service.compute(
            crop=Crop.COTTON,
            district=District.FARIDKOT,
            season=Season.KHARIF,
            soil=soil,
        )
        assert result.N_kg_per_ha is None
        assert result.P2O5_kg_per_ha is None
        assert result.K2O_kg_per_ha is None
        assert result.is_placeholder is True

    def test_negative_dose_clipping(self, service):
        """High initial soil fertility must clip calculated doses to 0.0 (never negative)."""
        # Very high soil P and K
        soil = _make_soil(n=300.0, p=50.0, k=800.0)
        result = service.compute(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil=soil,
            target_yield_q_ha=40.0,
        )
        # FK = 0.95*40 - 0.09*800 = 38 - 72 = -34 -> clipped to 0.0
        assert result.K2O_kg_per_ha == 0.0

    def test_negative_soil_nitrogen_rejected(self, service):
        soil = _make_soil(n=-10.0, p=15.0, k=150.0)
        with pytest.raises(ValueError, match="cannot be negative"):
            service.compute(Crop.WHEAT, District.BATHINDA, Season.RABI, soil)

    def test_negative_soil_phosphorus_rejected(self, service):
        soil = _make_soil(n=100.0, p=-5.0, k=150.0)
        with pytest.raises(ValueError, match="cannot be negative"):
            service.compute(Crop.WHEAT, District.BATHINDA, Season.RABI, soil)

    def test_negative_target_yield_rejected(self, service):
        soil = _make_soil(n=100.0, p=15.0, k=150.0)
        with pytest.raises(ValueError, match="Target yield must be strictly positive"):
            service.compute(
                Crop.WHEAT,
                District.BATHINDA,
                Season.RABI,
                soil,
                target_yield_q_ha=-50.0,
            )

    def test_incomplete_soil_profile_skipped(self, service):
        soil = _make_soil(n=None, p=15.0, k=150.0)
        result = service.compute(Crop.WHEAT, District.BATHINDA, Season.RABI, soil)
        assert result.N_kg_per_ha is None
        assert result.is_placeholder is True
        assert "skipped" in result.data_source.lower()

    def test_all_five_malwa_districts_accepted(self, service):
        soil = _make_soil(n=120.0, p=18.0, k=180.0)
        for district in District:
            result = service.compute(Crop.WHEAT, district, Season.RABI, soil)
            assert result.N_kg_per_ha is not None
