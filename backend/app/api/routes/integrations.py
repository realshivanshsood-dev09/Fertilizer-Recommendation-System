"""
Integration Routes: Soil Health Card & DigiLocker Gateway
=========================================================
Production-shaped demonstration endpoints simulating government integrations.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, status
import structlog

from app.integrations.digilocker.schemas import (
    DigiLockerConsentRequest,
    DigiLockerConsentResponse,
    DigiLockerDocumentDetailResponse,
    DigiLockerDocumentsListResponse,
    DigiLockerSessionResponse,
)
from app.integrations.digilocker.service import DigiLockerIntegrationService
from app.integrations.shc.schemas import SHCLookupResponse
from app.integrations.shc.service import SHCIntegrationService

log = structlog.get_logger(__name__)
router = APIRouter()

_shc_service = SHCIntegrationService()
_digilocker_service = DigiLockerIntegrationService()


# ── Soil Health Card Portal Routes ────────────────────────────────────────────

@router.get(
    "/integrations/shc/{card_number}",
    response_model=SHCLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Soil Health Card API (Mock)",
    description="Simulates the official Department of Agriculture & Farmers Welfare SHC API query.",
)
async def query_soil_health_card(card_number: str) -> SHCLookupResponse:
    log.info("shc_api_query_received", card_number=card_number)
    resp = await _shc_service.lookup_card(card_number)
    if resp.status == "invalid_card_number":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=resp.error_message or "Invalid Soil Health Card number.",
        )
    return resp


# ── DigiLocker Requester Routes ───────────────────────────────────────────────

@router.post(
    "/integrations/digilocker/session",
    response_model=DigiLockerSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize DigiLocker OAuth Requester Session (Mock)",
)
async def init_digilocker_session() -> DigiLockerSessionResponse:
    log.info("digilocker_session_init")
    return await _digilocker_service.initiate_session()


@router.post(
    "/integrations/digilocker/consent",
    response_model=DigiLockerConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Farmer DigiLocker Consent (Mock)",
)
async def process_digilocker_consent(req: DigiLockerConsentRequest) -> DigiLockerConsentResponse:
    log.info("digilocker_consent_received", session_id=req.session_id, consent=req.consent_granted)
    return await _digilocker_service.grant_consent(
        session_id=req.session_id,
        consent_granted=req.consent_granted,
        aadhaar_hash=req.farmer_aadhaar_hash,
    )


@router.get(
    "/integrations/digilocker/documents",
    response_model=DigiLockerDocumentsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List DigiLocker Issued Soil Documents (Mock)",
)
async def list_digilocker_documents(session_id: Optional[str] = None) -> DigiLockerDocumentsListResponse:
    log.info("digilocker_list_documents", session_id=session_id)
    docs = await _digilocker_service.list_available_documents()
    return DigiLockerDocumentsListResponse(
        session_id=session_id,
        documents=docs,
        is_mock=True,
    )


@router.get(
    "/integrations/digilocker/documents/{document_id}",
    response_model=DigiLockerDocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve DigiLocker Soil Health Card Document (Mock)",
)
async def get_digilocker_document(document_id: str) -> DigiLockerDocumentDetailResponse:
    log.info("digilocker_get_document", document_id=document_id)
    resp = await _digilocker_service.fetch_document(document_id)
    if resp.status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DigiLocker document '{document_id}' not found.",
        )
    return resp
