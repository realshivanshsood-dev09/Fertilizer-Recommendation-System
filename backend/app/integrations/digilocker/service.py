"""
DigiLocker Integration Service
==============================
"""

from __future__ import annotations

from typing import List, Optional
import structlog

from app.integrations.digilocker.client import DigiLockerClientBase
from app.integrations.digilocker.mock_client import MockDigiLockerClient
from app.integrations.digilocker.schemas import (
    DigiLockerConsentResponse,
    DigiLockerDocumentDetailResponse,
    DigiLockerDocumentHeader,
    DigiLockerSessionResponse,
)

log = structlog.get_logger(__name__)


class DigiLockerIntegrationService:
    """High-level service managing DigiLocker requester operations."""

    def __init__(self, client: Optional[DigiLockerClientBase] = None) -> None:
        self.client = client or MockDigiLockerClient()

    async def initiate_session(self) -> DigiLockerSessionResponse:
        return await self.client.create_session()

    async def grant_consent(
        self, session_id: str, consent_granted: bool = True, aadhaar_hash: Optional[str] = None
    ) -> DigiLockerConsentResponse:
        return await self.client.process_consent(session_id, consent_granted, aadhaar_hash)

    async def list_available_documents(self, token: Optional[str] = None) -> List[DigiLockerDocumentHeader]:
        return await self.client.list_documents(token)

    async def fetch_document(self, document_id: str) -> DigiLockerDocumentDetailResponse:
        return await self.client.get_document(document_id)
