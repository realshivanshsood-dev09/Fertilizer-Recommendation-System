"""
Tests for pipeline orchestrator.
Verifies end-to-end pipeline execution with live STCR calculation and provenance.
"""

from __future__ import annotations

import pytest

from app.core.constants import Crop, District, IrrigationType, Season, SoilSource
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline


def _make_request(soil_source=SoilSource.SOIL_HEALTH_CARD, **kwargs) -> RecommendRequest:
    defaults = dict(
        crop=Crop.WHEAT,
        district=District.BATHINDA,
        season=Season.RABI,
        soil_source=soil_source,
        soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        irrigation=IrrigationType.TUBE_WELL,
    )
    defaults.update(kwargs)
    return RecommendRequest(**defaults)


class TestPipeline:

    @pytest.mark.asyncio
    async def test_pipeline_returns_response(self):
        req = _make_request()
        resp = await run_pipeline(req)
        assert resp is not None

    @pytest.mark.asyncio
    async def test_pipeline_wheat_stcr_live_calculation(self):
        """Wheat recommendation should now compute real STCR doses and final doses."""
        req = _make_request(
            crop=Crop.WHEAT,
            season=Season.RABI,
            target_yield_q_ha=50.0,
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is False
        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(73.8, rel=1e-2)
        assert resp.stcr_baseline.P2O5_kg_per_ha == pytest.approx(72.86, rel=1e-2)
        assert resp.stcr_baseline.K2O_kg_per_ha == pytest.approx(31.3, rel=1e-2)
        assert resp.final_recommendation.N_kg_per_ha == pytest.approx(73.8, rel=1e-2)

    @pytest.mark.asyncio
    async def test_pipeline_rice_stcr_live_calculation(self):
        """Rice recommendation computes real STCR doses."""
        req = _make_request(
            crop=Crop.RICE,
            season=Season.KHARIF,
            target_yield_q_ha=70.0,
            soil=SoilInput(nitrogen=114.7, phosphorus=10.0, potassium=100.0),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is False
        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(139.14, rel=1e-2)
        assert resp.final_recommendation.N_kg_per_ha == pytest.approx(139.14, rel=1e-2)

    @pytest.mark.asyncio
    async def test_pipeline_cotton_remains_placeholder(self):
        """Cotton STCR is not populated in Track A and remains placeholder."""
        req = _make_request(
            crop=Crop.COTTON,
            season=Season.KHARIF,
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.stcr_baseline.N_kg_per_ha is None
        assert resp.final_recommendation.N_kg_per_ha is None

    @pytest.mark.asyncio
    async def test_pipeline_soil_source_preserved(self):
        req = _make_request(soil_source=SoilSource.SOIL_HEALTH_CARD)
        resp = await run_pipeline(req)
        assert resp.soil_source == SoilSource.SOIL_HEALTH_CARD

    @pytest.mark.asyncio
    async def test_pipeline_ml_disabled(self):
        req = _make_request()
        resp = await run_pipeline(req)
        assert resp.ml_adjustment.model_enabled is False

    @pytest.mark.asyncio
    async def test_pipeline_questionnaire_fallback_completes(self):
        req = _make_request(
            soil_source=SoilSource.QUESTIONNAIRE_FALLBACK,
            soil=SoilInput(),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.soil_source == SoilSource.QUESTIONNAIRE_FALLBACK
        assert resp.stcr_baseline.N_kg_per_ha is None

    @pytest.mark.asyncio
    async def test_pipeline_explanation_caveats_present(self):
        req = _make_request()
        resp = await run_pipeline(req)
        assert len(resp.explanation.caveats) > 0

    @pytest.mark.asyncio
    async def test_pipeline_all_crops(self):
        for crop, season in [(Crop.WHEAT, Season.RABI),
                             (Crop.RICE, Season.KHARIF),
                             (Crop.COTTON, Season.KHARIF)]:
            req = _make_request(crop=crop, season=season)
            resp = await run_pipeline(req)
            assert resp.crop == crop
