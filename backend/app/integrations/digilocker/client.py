"""
Abstract DigiLocker Requester Client Interface
==============================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.integrations.digilocker.schemas import (
    DigiLockerConsentResponse,
    DigiLockerDocumentDetailResponse,
    DigiLockerDocumentHeader,
    DigiLockerSessionResponse,
)


class DigiLockerClientBase(ABC):

    @abstractmethod
    async def create_session(self) -> DigiLockerSessionResponse:
        pass

    @abstractmethod
    async def process_consent(
        self, session_id: str, consent_granted: bool, aadhaar_hash: Optional[str] = None
    ) -> DigiLockerConsentResponse:
        pass

    @abstractmethod
    async def list_documents(self, token_or_session: Optional[str] = None) -> List[DigiLockerDocumentHeader]:
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> DigiLockerDocumentDetailResponse:
        pass
