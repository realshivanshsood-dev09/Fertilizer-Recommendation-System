"""
Mock DigiLocker Requester Client
=================================
Simulates the consent-based OAuth flow and document retrieval without live network calls.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional
import structlog

from app.integrations.digilocker.client import DigiLockerClientBase
from app.integrations.digilocker.schemas import (
    DigiLockerConsentResponse,
    DigiLockerDocumentDetailResponse,
    DigiLockerDocumentHeader,
    DigiLockerSessionResponse,
)
from app.integrations.shc.mock_client import MockSHCClient

log = structlog.get_logger(__name__)


class MockDigiLockerClient(DigiLockerClientBase):
    """
    Mock implementation simulating the DigiLocker Requester sandbox.
    """

    def __init__(self, shc_client: Optional[MockSHCClient] = None) -> None:
        self._shc_client = shc_client or MockSHCClient()
        self._sessions: Dict[str, Dict[str, Any]] = {}

    async def create_session(self) -> DigiLockerSessionResponse:
        session_id = f"DL-SESS-{uuid.uuid4().hex[:12].upper()}"
        state_token = uuid.uuid4().hex[:16]
        auth_url = f"https://mock.digilocker.gov.in/oauth/authorize?response_type=code&client_id=SIH_DEMO&session_id={session_id}&state={state_token}"

        self._sessions[session_id] = {
            "state": state_token,
            "status": "pending_consent",
            "token": None,
        }
        log.info("mock_digilocker_session_created", session_id=session_id)
        return DigiLockerSessionResponse(
            session_id=session_id,
            auth_url=auth_url,
            state=state_token,
            expires_in_seconds=300,
            is_mock=True,
            provider="SIH_DEMO_MOCK_DIGILOCKER",
        )

    async def process_consent(
        self, session_id: str, consent_granted: bool, aadhaar_hash: Optional[str] = None
    ) -> DigiLockerConsentResponse:
        sess = self._sessions.get(session_id)
        if not sess:
            return DigiLockerConsentResponse(
                session_id=session_id,
                status="expired",
                access_token=None,
                is_mock=True,
                message="Session not found or expired.",
            )

        if not consent_granted:
            sess["status"] = "denied"
            return DigiLockerConsentResponse(
                session_id=session_id,
                status="denied",
                access_token=None,
                is_mock=True,
                message="User explicitly denied consent.",
            )

        token = f"DL-TOKEN-{uuid.uuid4().hex.upper()}"
        sess["status"] = "granted"
        sess["token"] = token
        log.info("mock_digilocker_consent_granted", session_id=session_id)
        return DigiLockerConsentResponse(
            session_id=session_id,
            status="granted",
            access_token=token,
            is_mock=True,
            message="Consent successfully recorded. DigiLocker authorization token generated.",
        )

    async def list_documents(self, token_or_session: Optional[str] = None) -> List[DigiLockerDocumentHeader]:
        # Return registered mock cards as available documents in DigiLocker vault
        return [
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-BAT-001",
                doc_type="SHC",
                title="Soil Health Card — Bathinda (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-03-15",
                is_mock=True,
            ),
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-MAN-002",
                doc_type="SHC",
                title="Soil Health Card — Mansa (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-04-10",
                is_mock=True,
            ),
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-FAR-003",
                doc_type="SHC",
                title="Soil Health Card — Faridkot (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-05-02",
                is_mock=True,
            ),
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-MOG-004",
                doc_type="SHC",
                title="Soil Health Card — Moga (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-02-20",
                is_mock=True,
            ),
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-MUK-005",
                doc_type="SHC",
                title="Soil Health Card — Sri Muktsar Sahib (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-03-28",
                is_mock=True,
            ),
            DigiLockerDocumentHeader(
                document_id="DOC-DL-SHC-INCOMPLETE",
                doc_type="SHC",
                title="Soil Health Card — Incomplete Test (2024)",
                issuer="Department of Agriculture & Farmers Welfare",
                issued_date="2024-01-10",
                is_mock=True,
            ),
        ]

    async def get_document(self, document_id: str) -> DigiLockerDocumentDetailResponse:
        mapping = {
            "DOC-DL-SHC-BAT-001": "SHC-PB-BAT-2024-001",
            "DOC-DL-SHC-MAN-002": "SHC-PB-MAN-2024-002",
            "DOC-DL-SHC-FAR-003": "SHC-PB-FAR-2024-003",
            "DOC-DL-SHC-MOG-004": "SHC-PB-MOG-2024-004",
            "DOC-DL-SHC-MUK-005": "SHC-PB-MUK-2024-005",
            "DOC-DL-SHC-INCOMPLETE": "SHC-PB-BAT-2024-INCOMPLETE",
        }
        card_num = mapping.get(document_id.strip().upper())
        if not card_num:
            return DigiLockerDocumentDetailResponse(
                document_id=document_id,
                doc_type="SHC",
                status="not_found",
                is_mock=True,
            )

        card = await self._shc_client.get_soil_health_card(card_num)
        if not card:
            return DigiLockerDocumentDetailResponse(
                document_id=document_id,
                doc_type="SHC",
                status="not_found",
                is_mock=True,
            )

        return DigiLockerDocumentDetailResponse(
            document_id=document_id,
            doc_type="SHC",
            raw_format="JSON",
            normalized_card=card,
            is_mock=True,
            status="found",
        )
