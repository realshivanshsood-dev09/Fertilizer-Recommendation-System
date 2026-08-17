"""
API integration tests — tests the FastAPI routes using httpx AsyncClient.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def valid_shc_payload():
    return {
        "crop": "wheat",
        "district": "Bathinda",
        "season": "rabi",
        "soil_source": "soil_health_card",
        "soil": {
            "nitrogen": 120.0,
            "phosphorus": 18.0,
            "potassium": 180.0,
            "ph": 7.5,
            "organic_carbon": 0.45,
        },
        "irrigation": "tube_well",
    }


@pytest.fixture
def questionnaire_payload():
    return {
        "crop": "cotton",
        "district": "Mansa",
        "season": "kharif",
        "soil_source": "questionnaire_fallback",
        "soil": {},
        "irrigation": "canal",
    }


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_fields(self, client):
        resp = await client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "ml_enabled" in data
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_health_no_credentials_in_database_field(self, client):
        resp = await client.get("/api/v1/health")
        data = resp.json()
        # Must not leak connection string with credentials
        assert "@" not in data.get("database", "")


class TestRecommendEndpoint:

    @pytest.mark.asyncio
    async def test_recommend_returns_200(self, client, valid_shc_payload):
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_recommend_is_placeholder_true(self, client, valid_shc_payload):
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        data = resp.json()
        assert data["is_placeholder"] is True

    @pytest.mark.asyncio
    async def test_recommend_soil_source_preserved(self, client, valid_shc_payload):
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        data = resp.json()
        assert data["soil_source"] == "soil_health_card"

    @pytest.mark.asyncio
    async def test_recommend_stcr_doses_are_none(self, client, valid_shc_payload):
        """STCR coefficients are placeholders — doses must be None."""
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        data = resp.json()
        assert data["stcr_baseline"]["N_kg_per_ha"] is None
        assert data["stcr_baseline"]["P2O5_kg_per_ha"] is None
        assert data["stcr_baseline"]["K2O_kg_per_ha"] is None

    @pytest.mark.asyncio
    async def test_recommend_ml_disabled(self, client, valid_shc_payload):
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        data = resp.json()
        assert data["ml_adjustment"]["model_enabled"] is False

    @pytest.mark.asyncio
    async def test_recommend_questionnaire_fallback(self, client, questionnaire_payload):
        resp = await client.post("/api/v1/recommend", json=questionnaire_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["soil_source"] == "questionnaire_fallback"

    @pytest.mark.asyncio
    async def test_recommend_invalid_crop_season_returns_422(self, client, valid_shc_payload):
        payload = dict(valid_shc_payload, season="kharif")  # wheat is rabi only
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_recommend_invalid_district_returns_422(self, client, valid_shc_payload):
        payload = dict(valid_shc_payload, district="Ludhiana")
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_recommend_response_has_explanation(self, client, valid_shc_payload):
        resp = await client.post("/api/v1/recommend", json=valid_shc_payload)
        data = resp.json()
        assert "explanation" in data
        assert data["explanation"]["ml_used"] is False

    @pytest.mark.asyncio
    async def test_recommend_all_five_districts(self, client, valid_shc_payload):
        for district in ["Bathinda", "Mansa", "Muktsar", "Moga", "Faridkot"]:
            payload = dict(valid_shc_payload, district=district)
            resp = await client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 200, f"Failed for district: {district}"

    @pytest.mark.asyncio
    async def test_recommend_rice_cotton_kharif(self, client, valid_shc_payload):
        for crop in ["rice", "cotton"]:
            payload = dict(valid_shc_payload, crop=crop, season="kharif")
            resp = await client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 200
