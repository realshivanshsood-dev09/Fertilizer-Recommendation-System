"""
End-to-End Comprehensive Pipeline Tests (Phase 6 SIH Demo Hardening)
===================================================================
Covers all required scenarios:
  A. Wheat + complete measured soil
  B. Rice + complete measured soil
  C. Missing N
  D. Missing P
  E. Missing K
  F. Completely missing soil
  G. Unsupported Cotton
  H. Invalid target yield
  I. Negative soil values
  J. Mathematical exactness of fertilizer translation
  K. Summary card validation for UI
  L. Split application timing verification
  M. Biofertilizer graceful handling
  N. In-memory data loader caching verification
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import Crop, District, IrrigationType, Season, SoilSource
from app.core.data_loader import load_stcr_coefficients, load_fertilizer_prices
from app.db.base import Base
from app.main import app
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestScenarioAWheatMeasuredSoil:
    """Scenario A: Wheat + complete measured soil."""

    @pytest.mark.asyncio
    async def test_wheat_pipeline_math_and_summary(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=50.0,
            soil=SoilInput(
                nitrogen=120.0,
                phosphorus=18.0,
                potassium=180.0,
                ph=7.5,
                organic_carbon=0.45,
            ),
        )
        resp = await run_pipeline(req)

        # 1. Agronomic STCR verification
        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(73.8, rel=1e-2)
        assert resp.stcr_baseline.P2O5_kg_per_ha == pytest.approx(72.86, rel=1e-2)
        assert resp.stcr_baseline.K2O_kg_per_ha == pytest.approx(31.3, rel=1e-2)

        # 2. Arithmetic proofs in STCRBaseline
        assert len(resp.stcr_baseline.calculation_steps) == 3
        n_step = resp.stcr_baseline.calculation_steps[0]
        assert n_step.nutrient == "N"
        assert "3.78" in n_step.equation_formula
        assert n_step.final_clipped_dose == pytest.approx(73.8, rel=1e-2)

        # 3. Product translation and bags
        assert len(resp.fertilizers) == 3
        dap = next(f for f in resp.fertilizers if "DAP" in f.product_name)
        urea = next(f for f in resp.fertilizers if "Urea" in f.product_name)
        mop = next(f for f in resp.fertilizers if "MOP" in f.product_name)

        assert dap.quantity_kg_per_ha == pytest.approx(158.39, rel=1e-2)
        assert dap.bags_per_ha == pytest.approx(3.17, rel=1e-2)
        assert urea.quantity_kg_per_ha == pytest.approx(98.46, rel=1e-2)
        assert urea.bags_per_ha == pytest.approx(2.19, rel=1e-2)
        assert mop.quantity_kg_per_ha == pytest.approx(52.17, rel=1e-2)
        assert mop.bags_per_ha == pytest.approx(1.04, rel=1e-2)

        # 4. Total Cost Calculation
        assert resp.estimated_cost_inr == pytest.approx(6581.02, rel=1e-2)

        # 5. Machine-readable UI Summary
        assert resp.summary.crop == Crop.WHEAT
        assert resp.summary.district == District.BATHINDA
        assert resp.summary.total_cost_inr_per_ha == pytest.approx(6581.02, rel=1e-2)
        assert len(resp.summary.recommended_products) == 3
        assert resp.summary.soil_confidence == 0.95
        assert resp.summary.recommendation_confidence == 0.95
        assert resp.summary.data_provenance["source_id"] == "SRC-ICAR-PAU-WHEAT-STCR-2022"


class TestScenarioBRiceMeasuredSoil:
    """Scenario B: Rice + complete measured soil."""

    @pytest.mark.asyncio
    async def test_rice_pipeline_math_and_summary(self):
        req = RecommendRequest(
            crop=Crop.RICE,
            district=District.FARIDKOT,
            season=Season.KHARIF,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=70.0,
            soil=SoilInput(
                nitrogen=114.7,
                phosphorus=10.0,
                potassium=100.0,
            ),
        )
        resp = await run_pipeline(req)

        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(139.14, rel=1e-2)
        assert resp.stcr_baseline.P2O5_kg_per_ha == pytest.approx(40.9, rel=1e-2)
        assert resp.stcr_baseline.K2O_kg_per_ha == pytest.approx(53.5, rel=1e-2)
        assert len(resp.fertilizers) == 3
        assert resp.estimated_cost_inr is not None
        assert resp.estimated_cost_inr > 0


class TestScenarioCMissingNutrients:
    """Scenarios C, D, E, F: Missing or incomplete soil data."""

    @pytest.mark.asyncio
    async def test_missing_nitrogen_skips_stcr(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=None, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.stcr_baseline.N_kg_per_ha is None
        assert resp.fertilizers == []
        assert resp.estimated_cost_inr is None

    @pytest.mark.asyncio
    async def test_missing_phosphorus_skips_stcr(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=None, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.stcr_baseline.P2O5_kg_per_ha is None

    @pytest.mark.asyncio
    async def test_missing_potassium_skips_stcr(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=None),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.stcr_baseline.K2O_kg_per_ha is None

    @pytest.mark.asyncio
    async def test_completely_missing_soil(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.QUESTIONNAIRE_FALLBACK,
            soil=SoilInput(),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.explanation.soil_status == "qualitative_only"
        assert resp.fertilizers == []


class TestScenarioGUnsupportedCotton:
    """Scenario G: Unsupported cotton returns clean unpopulated response."""

    @pytest.mark.asyncio
    async def test_cotton_unpopulated(self):
        req = RecommendRequest(
            crop=Crop.COTTON,
            district=District.MANSA,
            season=Season.KHARIF,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert resp.is_placeholder is True
        assert resp.stcr_baseline.N_kg_per_ha is None
        assert resp.final_recommendation.N_kg_per_ha is None
        assert resp.fertilizers == []


class TestScenarioHValidationAndErrors:
    """Scenarios H, I: Invalid target yield and negative soil values."""

    @pytest.mark.asyncio
    async def test_invalid_target_yield_via_api(self, client):
        payload = {
            "crop": "wheat",
            "district": "Bathinda",
            "season": "rabi",
            "soil_source": "soil_health_card",
            "target_yield_q_ha": -10.0,
            "soil": {"nitrogen": 120.0, "phosphorus": 18.0, "potassium": 180.0},
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_soil_nitrogen_via_api(self, client):
        payload = {
            "crop": "wheat",
            "district": "Bathinda",
            "season": "rabi",
            "soil_source": "soil_health_card",
            "soil": {"nitrogen": -50.0, "phosphorus": 18.0, "potassium": 180.0},
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422


class TestScenarioJNutrientAccountingExactness:
    """Scenario J: Mathematical exactness of fertilizer translation."""

    @pytest.mark.asyncio
    async def test_nutrient_coverage_guarantee(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=50.0,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)

        req_n = resp.final_recommendation.N_kg_per_ha or 0.0
        req_p = resp.final_recommendation.P2O5_kg_per_ha or 0.0
        req_k = resp.final_recommendation.K2O_kg_per_ha or 0.0

        supplied_n = sum(f.n_contribution_kg_ha or 0.0 for f in resp.fertilizers)
        supplied_p = sum(f.p2o5_contribution_kg_ha or 0.0 for f in resp.fertilizers)
        supplied_k = sum(f.k2o_contribution_kg_ha or 0.0 for f in resp.fertilizers)

        # Verification with 0.1 kg/ha tolerance
        assert supplied_n >= req_n - 0.1
        assert supplied_p >= req_p - 0.1
        assert supplied_k >= req_k - 0.1


class TestScenarioLApplicationTimingSplits:
    """Scenario L: Application stage schedules for wheat and rice."""

    @pytest.mark.asyncio
    async def test_wheat_timing_structure(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert resp.application_timing.splits is not None
        assert len(resp.application_timing.splits) == 3
        stages = [s["stage"] for s in resp.application_timing.splits]
        assert "Basal at Sowing" in stages[0]
        assert "First Irrigation (CRI stage)" in stages[1]
        assert "Second Irrigation" in stages[2]

    @pytest.mark.asyncio
    async def test_rice_timing_structure(self):
        req = RecommendRequest(
            crop=Crop.RICE,
            district=District.FARIDKOT,
            season=Season.KHARIF,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert resp.application_timing.splits is not None
        assert len(resp.application_timing.splits) == 3
        stages = [s["stage"] for s in resp.application_timing.splits]
        assert "Basal at Transplanting" in stages[0]
        assert "Active Tillering" in stages[1]
        assert "Panicle Initiation" in stages[2]


class TestScenarioMBiofertilizerProvenance:
    """Scenario M: Biofertilizer unverified placeholder response."""

    @pytest.mark.asyncio
    async def test_biofertilizer_structure(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
        )
        resp = await run_pipeline(req)
        assert isinstance(resp.biofertilizer.recommended, list)
        assert resp.biofertilizer.data_source is not None


class TestScenarioNDataLoaderCaching:
    """Scenario N: In-memory static YAML loader caching."""

    def test_stcr_loader_caching(self):
        c1 = load_stcr_coefficients()
        c2 = load_stcr_coefficients()
        assert c1 is c2  # Identical cached reference in memory

    def test_fertilizer_prices_caching(self):
        p1 = load_fertilizer_prices()
        p2 = load_fertilizer_prices()
        assert p1 is p2  # Identical cached reference in memory
