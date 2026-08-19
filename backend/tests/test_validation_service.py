"""
Tests for ValidationService and /validation/summary endpoint (Phase 8).
========================================================================
Verifies:
  - GET /api/v1/validation/summary returns HTTP 200 with accurate counts
  - Total studies (4), observations (29), Malwa observations (7)
  - Crop-specific evidence classifications (Wheat, Rice, Cotton)
  - Malwa regional verification availability
  - Evidence metadata propagation into /recommend responses
"""

from __future__ import annotations

from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
import pandas as pd

from app.core.constants import Crop, District, Season, SoilSource
from app.main import app
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline
from app.services.validation_service import ValidationSummaryService

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_VALIDATION_CSV_PATH = _PROJECT_ROOT / "data" / "processed" / "validation_results.csv"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def validation_service() -> ValidationSummaryService:
    return ValidationSummaryService()


class TestValidationSummaryEndpoint:

    @pytest.mark.asyncio
    async def test_get_validation_summary_200(self, client):
        resp = await client.get("/api/v1/validation/summary")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_studies"] == 4
        assert data["total_observations"] == 29
        assert data["malwa_observations"] == 7
        assert "wheat" in data["crops"]
        assert "rice" in data["crops"]
        assert data["ml_status"] == "disabled_insufficient_plot_data"
        assert len(data["validation_sources"]) >= 4

    @pytest.mark.asyncio
    async def test_evidence_status_by_crop(self, client):
        resp = await client.get("/api/v1/validation/summary")
        data = resp.json()
        ev_status = data["evidence_status"]
        assert ev_status["wheat"] == "calibration_verified"
        assert ev_status["rice"] == "calibration_and_malwa_validated"
        assert ev_status["cotton"] == "unsupported_awaiting_calibration"


class TestValidationServiceLogic:

    def test_rice_in_bathinda_has_malwa_validation(self, validation_service):
        ev = validation_service.get_evidence_metadata_for_crop("rice", "Bathinda")
        assert ev["malwa_validation_available"] is True
        assert ev["evidence_strength"] == "high_with_regional_malwa_verification"
        assert "Khosa et al. (2012)" in ev["validation_sources"][0]

    def test_wheat_in_bathinda_calibration_only(self, validation_service):
        ev = validation_service.get_evidence_metadata_for_crop("wheat", "Bathinda")
        assert ev["malwa_validation_available"] is False
        assert ev["evidence_strength"] == "moderate_alluvial_calibration"
        assert "Singh, Mavi & Saini (2022)" in ev["calibration_source"]

    def test_cotton_unsupported_evidence(self, validation_service):
        ev = validation_service.get_evidence_metadata_for_crop("cotton", "Mansa")
        assert ev["evidence_status"] == "unsupported_awaiting_calibration"
        assert ev["evidence_strength"] == "insufficient_calibration"
        assert ev["calibration_source"] is None


class TestValidationResultsCSVIntegrity:

    def test_validation_csv_exists_and_row_count(self):
        assert _VALIDATION_CSV_PATH.exists()
        df = pd.read_csv(_VALIDATION_CSV_PATH, comment="#")
        assert len(df) == 29
        assert "study_id" in df.columns
        assert "yield_achievement_pct" in df.columns

    def test_malwa_rows_in_csv(self):
        df = pd.read_csv(_VALIDATION_CSV_PATH, comment="#")
        malwa_rows = df[df["malwa_region"] == True]
        assert len(malwa_rows) == 7
        assert all(malwa_rows["crop"] == "rice")


class TestRecommendEvidenceIntegration:

    @pytest.mark.asyncio
    async def test_recommend_includes_evidence_metadata(self):
        req = RecommendRequest(
            crop=Crop.RICE,
            district=District.BATHINDA,
            season=Season.KHARIF,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=70.0,
            soil=SoilInput(nitrogen=114.7, phosphorus=10.0, potassium=100.0),
        )
        resp = await run_pipeline(req)
        assert resp.evidence is not None
        assert resp.evidence.malwa_validation_available is True
        assert resp.evidence.evidence_strength == "high_with_regional_malwa_verification"
        assert resp.summary.data_provenance["malwa_validation_available"] is True
