"""
API Hardening & Edge-Case Failure Suite (Phase 9)
=================================================
Verifies that all abnormal inputs, edge cases, and external failures result in
clean, structured HTTP responses rather than stack traces or system crashes.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.constants import Crop, District, Season, SoilSource
from app.main import app
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestAPIInputValidationHardening:

    @pytest.mark.asyncio
    async def test_invalid_crop_rejected_422(self, client):
        payload = {
            "crop": "sugarcane",
            "district": "Bathinda",
            "season": "rabi",
            "soil_source": "soil_health_card",
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422
        assert "crop" in resp.text

    @pytest.mark.asyncio
    async def test_invalid_district_rejected_422(self, client):
        payload = {
            "crop": "wheat",
            "district": "Patiala",
            "season": "rabi",
            "soil_source": "soil_health_card",
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422
        assert "district" in resp.text

    @pytest.mark.asyncio
    async def test_mismatched_crop_season_rejected_422(self, client):
        payload = {
            "crop": "wheat",
            "district": "Bathinda",
            "season": "kharif",  # Wheat is rabi
            "soil_source": "soil_health_card",
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_soil_nutrients_rejected_422(self, client):
        for nutrient in ["nitrogen", "phosphorus", "potassium", "organic_carbon"]:
            payload = {
                "crop": "wheat",
                "district": "Bathinda",
                "season": "rabi",
                "soil_source": "soil_health_card",
                "soil": {nutrient: -10.0},
            }
            resp = await client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_soil_ph_bounds_rejected_422(self, client):
        for invalid_ph in [1.5, 12.0]:
            payload = {
                "crop": "wheat",
                "district": "Bathinda",
                "season": "rabi",
                "soil_source": "soil_health_card",
                "soil": {"ph": invalid_ph},
            }
            resp = await client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_impossible_target_yield_rejected_422(self, client):
        for invalid_yield in [-5.0, 0.0, 250.0]:
            payload = {
                "crop": "wheat",
                "district": "Bathinda",
                "season": "rabi",
                "soil_source": "soil_health_card",
                "target_yield_q_ha": invalid_yield,
            }
            resp = await client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_malformed_json_body_422(self, client):
        resp = await client.post(
            "/api/v1/recommend",
            content="NOT_VALID_JSON_STRING",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


class TestAgronomicEdgeCaseHandling:

    @pytest.mark.asyncio
    async def test_unsupported_cotton_returns_clean_placeholder_200(self, client):
        payload = {
            "crop": "cotton",
            "district": "Mansa",
            "season": "kharif",
            "soil_source": "soil_health_card",
            "soil": {"nitrogen": 120.0, "phosphorus": 18.0, "potassium": 180.0},
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_placeholder"] is True
        assert data["final_recommendation"]["N_kg_per_ha"] is None
        assert data["fertilizers"] == []
        assert "unpopulated" in data["explanation"]["caveats"][0]

    @pytest.mark.asyncio
    async def test_completely_missing_nutrients_fallback_200(self, client):
        payload = {
            "crop": "wheat",
            "district": "Bathinda",
            "season": "rabi",
            "soil_source": "questionnaire_fallback",
            "soil": {},
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_placeholder"] is True
        assert data["explanation"]["soil_status"] == "qualitative_only"


class TestIntegrationFailureResilience:

    @pytest.mark.asyncio
    async def test_nonexistent_shc_returns_not_found(self, client):
        resp = await client.get("/api/v1/integrations/shc/SHC-DOES-NOT-EXIST")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"
        assert data["card"] is None

    @pytest.mark.asyncio
    async def test_unknown_digilocker_document_404(self, client):
        resp = await client.get("/api/v1/integrations/digilocker/documents/DOC-UNKNOWN-999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_digilocker_consent_denial(self, client):
        sess_resp = await client.post("/api/v1/integrations/digilocker/session")
        sess_id = sess_resp.json()["session_id"]

        resp = await client.post(
            "/api/v1/integrations/digilocker/consent",
            json={"session_id": sess_id, "consent_granted": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "denied"
        assert data["access_token"] is None
