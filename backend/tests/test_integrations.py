"""
Tests for Soil Health Card & DigiLocker Integration Adapters (Phase 8A)
======================================================================
Verifies:
  - SHC Mock Client & API endpoint (lookup, not found, invalid, incomplete)
  - DigiLocker Requester OAuth Flow (session, consent granted/denied, document list/detail)
  - Seamless convergence into /recommend pipeline
  - Explicit is_mock and integration_source provenance
  - Clean fallback handling for incomplete cards
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.constants import Crop, District, Season, SoilSource
from app.integrations.digilocker.service import DigiLockerIntegrationService
from app.integrations.shc.service import SHCIntegrationService
from app.main import app
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestSHCIntegration:

    @pytest.mark.asyncio
    async def test_valid_shc_lookup_via_api(self, client):
        resp = await client.get("/api/v1/integrations/shc/SHC-PB-BAT-2024-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "found"
        assert data["is_mock"] is True
        assert data["card"]["location"]["district"] == "Bathinda"
        assert data["card"]["soil"]["N_kg_ha"] == 120.0
        assert data["card"]["soil"]["P_kg_ha"] == 18.0
        assert data["card"]["soil"]["K_kg_ha"] == 180.0

    @pytest.mark.asyncio
    async def test_shc_not_found(self, client):
        resp = await client.get("/api/v1/integrations/shc/SHC-PB-NONEXISTENT-999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"
        assert data["card"] is None

    @pytest.mark.asyncio
    async def test_shc_invalid_number_422(self, client):
        resp = await client.get("/api/v1/integrations/shc/X")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_incomplete_shc_status(self, client):
        resp = await client.get("/api/v1/integrations/shc/SHC-PB-BAT-2024-INCOMPLETE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "incomplete"
        assert data["card"]["soil"]["N_kg_ha"] is None


class TestDigiLockerIntegration:

    @pytest.mark.asyncio
    async def test_digilocker_session_initiation(self, client):
        resp = await client.post("/api/v1/integrations/digilocker/session")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"].startswith("DL-SESS-")
        assert data["is_mock"] is True
        assert "authorize" in data["auth_url"]

    @pytest.mark.asyncio
    async def test_digilocker_consent_granted(self, client):
        # 1. Init session
        sess_resp = await client.post("/api/v1/integrations/digilocker/session")
        sess_id = sess_resp.json()["session_id"]

        # 2. Grant consent
        consent_payload = {"session_id": sess_id, "consent_granted": True}
        consent_resp = await client.post("/api/v1/integrations/digilocker/consent", json=consent_payload)
        assert consent_resp.status_code == 200
        c_data = consent_resp.json()
        assert c_data["status"] == "granted"
        assert c_data["access_token"] is not None

    @pytest.mark.asyncio
    async def test_digilocker_consent_denied(self, client):
        sess_resp = await client.post("/api/v1/integrations/digilocker/session")
        sess_id = sess_resp.json()["session_id"]

        consent_payload = {"session_id": sess_id, "consent_granted": False}
        consent_resp = await client.post("/api/v1/integrations/digilocker/consent", json=consent_payload)
        assert consent_resp.status_code == 200
        assert consent_resp.json()["status"] == "denied"
        assert consent_resp.json()["access_token"] is None

    @pytest.mark.asyncio
    async def test_digilocker_document_list_and_get(self, client):
        list_resp = await client.get("/api/v1/integrations/digilocker/documents")
        assert list_resp.status_code == 200
        docs = list_resp.json()["documents"]
        assert len(docs) >= 5

        doc_id = docs[0]["document_id"]
        detail_resp = await client.get(f"/api/v1/integrations/digilocker/documents/{doc_id}")
        assert detail_resp.status_code == 200
        d_data = detail_resp.json()
        assert d_data["status"] == "found"
        assert d_data["normalized_card"] is not None

    @pytest.mark.asyncio
    async def test_digilocker_document_not_found(self, client):
        resp = await client.get("/api/v1/integrations/digilocker/documents/DOC-NONEXISTENT")
        assert resp.status_code == 404


class TestRecommendWithIntegrations:

    @pytest.mark.asyncio
    async def test_recommend_via_shc_api_mode(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=50.0,
            soil_input_mode="shc_api",
            soil_health_card_number="SHC-PB-BAT-2024-001",
        )
        resp = await run_pipeline(req)

        assert resp.is_mock is True
        assert resp.integration_source == "shc_mock_api"
        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(73.8, rel=1e-2)
        assert resp.stcr_baseline.P2O5_kg_per_ha == pytest.approx(72.86, rel=1e-2)
        assert resp.stcr_baseline.K2O_kg_per_ha == pytest.approx(31.3, rel=1e-2)
        assert len(resp.fertilizers) == 3

    @pytest.mark.asyncio
    async def test_recommend_via_digilocker_mode(self):
        req = RecommendRequest(
            crop=Crop.RICE,
            district=District.FARIDKOT,
            season=Season.KHARIF,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=70.0,
            soil_input_mode="digilocker",
            digilocker_document_id="DOC-DL-SHC-FAR-003",
        )
        resp = await run_pipeline(req)

        assert resp.is_mock is True
        assert resp.integration_source == "digilocker_mock"
        assert resp.stcr_baseline.N_kg_per_ha == pytest.approx(139.14, rel=1e-2)
        assert resp.stcr_baseline.P2O5_kg_per_ha == pytest.approx(40.9, rel=1e-2)
        assert resp.stcr_baseline.K2O_kg_per_ha == pytest.approx(53.5, rel=1e-2)

    @pytest.mark.asyncio
    async def test_incomplete_shc_triggers_fallback_hierarchy(self):
        req = RecommendRequest(
            crop=Crop.WHEAT,
            district=District.BATHINDA,
            season=Season.RABI,
            soil_source=SoilSource.SOIL_HEALTH_CARD,
            target_yield_q_ha=50.0,
            soil_input_mode="shc_api",
            soil_health_card_number="SHC-PB-BAT-2024-INCOMPLETE",
        )
        resp = await run_pipeline(req)
        # Missing NPK from card means STCR cannot be computed
        assert resp.is_placeholder is True
        assert resp.explanation.soil_status == "insufficient_data"

    @pytest.mark.asyncio
    async def test_invalid_soil_input_mode_rejected_via_api(self, client):
        payload = {
            "crop": "wheat",
            "district": "Bathinda",
            "season": "rabi",
            "soil_source": "soil_health_card",
            "soil_input_mode": "invalid_telepathic_mode",
            "soil": {"nitrogen": 120.0, "phosphorus": 18.0, "potassium": 180.0},
        }
        resp = await client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422
