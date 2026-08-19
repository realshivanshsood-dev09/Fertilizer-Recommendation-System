"""
DigiLocker Requester Gateway Schemas
====================================
Based on DigiLocker Requester Integration Architecture:
https://www.digilocker.gov.in/web/partners/requesters
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from app.integrations.shc.schemas import NormalizedSoilHealthCard


class DigiLockerSessionResponse(BaseModel):
    session_id: str
    auth_url: str
    state: str
    expires_in_seconds: int = 300
    is_mock: bool = True
    provider: str = "SIH_DEMO_MOCK_DIGILOCKER"


class DigiLockerConsentRequest(BaseModel):
    session_id: str
    farmer_aadhaar_hash: Optional[str] = Field(None, description="SHA-256 hashed virtual ID/Aadhaar for privacy")
    consent_granted: bool = True


class DigiLockerConsentResponse(BaseModel):
    session_id: str
    status: str = Field(description="granted | denied | expired")
    access_token: Optional[str] = None
    is_mock: bool = True
    message: str


class DigiLockerDocumentHeader(BaseModel):
    document_id: str
    doc_type: str = "SHC"
    title: str
    issuer: str = "Department of Agriculture & Farmers Welfare (SHC Portal)"
    issued_date: Optional[str] = None
    is_mock: bool = True


class DigiLockerDocumentsListResponse(BaseModel):
    session_id: Optional[str] = None
    documents: List[DigiLockerDocumentHeader]
    is_mock: bool = True


class DigiLockerDocumentDetailResponse(BaseModel):
    document_id: str
    doc_type: str = "SHC"
    raw_format: str = "JSON"
    normalized_card: Optional[NormalizedSoilHealthCard] = None
    is_mock: bool = True
    status: str = Field(description="found | not_found | access_denied")
