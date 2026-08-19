"""DigiLocker integration package."""
from app.integrations.digilocker.client import DigiLockerClientBase
from app.integrations.digilocker.mock_client import MockDigiLockerClient
from app.integrations.digilocker.schemas import (
    DigiLockerConsentRequest,
    DigiLockerConsentResponse,
    DigiLockerDocumentDetailResponse,
    DigiLockerDocumentHeader,
    DigiLockerDocumentsListResponse,
    DigiLockerSessionResponse,
)
from app.integrations.digilocker.service import DigiLockerIntegrationService

__all__ = [
    "DigiLockerClientBase",
    "MockDigiLockerClient",
    "DigiLockerSessionResponse",
    "DigiLockerConsentRequest",
    "DigiLockerConsentResponse",
    "DigiLockerDocumentHeader",
    "DigiLockerDocumentsListResponse",
    "DigiLockerDocumentDetailResponse",
    "DigiLockerIntegrationService",
]
