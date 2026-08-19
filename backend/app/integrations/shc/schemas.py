"""
Soil Health Card (SHC) API Schemas
==================================
Based on Ministry of Agriculture & Farmers Welfare SHC API Integration Guidelines:
https://soilhealth.dac.gov.in/files/SHC_API_Integration_Guidelines.pdf
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class SHCLocation(BaseModel):
    state: str = "Punjab"
    district: str
    block: Optional[str] = None
    village: Optional[str] = None


class SHCSoilNutrients(BaseModel):
    N_kg_ha: Optional[float] = Field(None, description="Available Nitrogen (kg/ha, Alkaline KMnO4)")
    P_kg_ha: Optional[float] = Field(None, description="Available Phosphorus as P2O5 (kg/ha, Olsen)")
    K_kg_ha: Optional[float] = Field(None, description="Available Potassium as K2O (kg/ha, NH4OAc)")
    pH: Optional[float] = Field(None, description="Soil pH (1:2 suspension)")
    organic_carbon: Optional[float] = Field(None, description="Organic Carbon (% Walkley-Black)")
    electrical_conductivity: Optional[float] = Field(None, description="EC (dS/m)")


class NormalizedSoilHealthCard(BaseModel):
    """
    Standardized, normalized Soil Health Card entity consumed across the pipeline.
    """

    card_number: str
    farmer_identifier: Optional[str] = None
    farmer_name: Optional[str] = None
    sample_id: Optional[str] = None
    sample_date: Optional[str] = None
    location: SHCLocation
    soil: SHCSoilNutrients
    source: str = "SIH_DEMO_MOCK_SHC"
    verification_status: str = "verified_mock_record"
    is_mock: bool = True
    is_complete: bool = True


class SHCLookupResponse(BaseModel):
    """API response for GET /api/v1/integrations/shc/{card_number}."""

    card_number: str
    status: str = Field(description="found | not_found | incomplete | invalid_card_number")
    is_mock: bool = True
    source: str = "SIH_DEMO_MOCK_SHC"
    card: Optional[NormalizedSoilHealthCard] = None
    error_message: Optional[str] = None
