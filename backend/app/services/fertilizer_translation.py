"""
Fertilizer Translation Service
================================
Translates abstract N / P2O5 / K2O nutrient requirements (kg/ha) into specific
commercial fertilizer products standard in Punjab (Urea, DAP, MOP, SSP).

Standard Specifications (Fertiliser Control Order 1985 / PAU Recommended Practices):
  - Urea: 46% N (45 kg standard bag)
  - DAP (Di-Ammonium Phosphate): 18% N, 46% P2O5 (50 kg bag)
  - MOP (Muriate of Potash): 60% K2O (50 kg bag)
  - SSP (Single Super Phosphate): 16% P2O5, 11% S (50 kg bag)

Pricing:
  Prices loaded from verified Government of India / IFFCO statutory benchmarks
  (data/agronomy/fertilizer_prices.yaml).
"""

from __future__ import annotations

import structlog
from typing import Dict, List, Optional, Tuple

from app.core.constants import Crop
from app.core.data_loader import FertilizerPriceData, load_fertilizer_prices
from app.schemas.response import ApplicationTiming, FertilizerProduct

log = structlog.get_logger(__name__)

_price_data: FertilizerPriceData = load_fertilizer_prices()

PRODUCT_CATALOGUE: Dict[str, dict] = {
    "DAP": {
        "full_name": "Di-Ammonium Phosphate (DAP 18-46-0)",
        "nutrient_type": "complex",
        "n_pct": 18.0,
        "p2o5_pct": 46.0,
        "k2o_pct": 0.0,
        "bag_size_kg": 50.0,
        "source_standard": "Fertiliser (Control) Order 1985, Schedule I",
        "verified": True,
    },
    "Urea": {
        "full_name": "Neem Coated Urea (46% N)",
        "nutrient_type": "N",
        "n_pct": 46.0,
        "p2o5_pct": 0.0,
        "k2o_pct": 0.0,
        "bag_size_kg": 45.0,
        "source_standard": "Fertiliser (Control) Order 1985, Schedule I",
        "verified": True,
    },
    "MOP": {
        "full_name": "Muriate of Potash (MOP 60% K2O)",
        "nutrient_type": "K",
        "n_pct": 0.0,
        "p2o5_pct": 0.0,
        "k2o_pct": 60.0,
        "bag_size_kg": 50.0,
        "source_standard": "Fertiliser (Control) Order 1985, Schedule I",
        "verified": True,
    },
    "SSP": {
        "full_name": "Single Superphosphate (SSP 16% P2O5, 11% S)",
        "nutrient_type": "P",
        "n_pct": 0.0,
        "p2o5_pct": 16.0,
        "k2o_pct": 0.0,
        "bag_size_kg": 50.0,
        "source_standard": "Fertiliser (Control) Order 1985, Schedule I",
        "verified": True,
    },
}


class FertilizerTranslationService:
    """
    Translates required N/P/K doses into commercial product bags, quantities, and costs.
    """

    def __init__(self, price_data: Optional[FertilizerPriceData] = None) -> None:
        self._prices = price_data or _price_data

    def translate(
        self,
        crop: Crop,
        N_kg_per_ha: Optional[float],
        P2O5_kg_per_ha: Optional[float],
        K2O_kg_per_ha: Optional[float],
    ) -> Tuple[List[FertilizerProduct], Optional[float]]:
        """
        Translates N, P2O5, K2O requirements into commercial fertilizers.
        Returns: (list_of_products, total_cost_inr_per_ha)
        """
        log.info(
            "fertilizer_translation_start",
            crop=crop.value,
            N=N_kg_per_ha,
            P=P2O5_kg_per_ha,
            K=K2O_kg_per_ha,
        )

        if N_kg_per_ha is None and P2O5_kg_per_ha is None and K2O_kg_per_ha is None:
            return [], None

        n_req = max(0.0, float(N_kg_per_ha or 0.0))
        p_req = max(0.0, float(P2O5_kg_per_ha or 0.0))
        k_req = max(0.0, float(K2O_kg_per_ha or 0.0))

        if n_req == 0.0 and p_req == 0.0 and k_req == 0.0:
            return [], None

        products: List[FertilizerProduct] = []

        # 1. Satisfy P2O5 using DAP (18-46-0)
        n_from_dap = 0.0
        if p_req > 0:
            dap_spec = PRODUCT_CATALOGUE["DAP"]
            dap_kg = round(p_req / (dap_spec["p2o5_pct"] / 100.0), 2)
            dap_bags = round(dap_kg / dap_spec["bag_size_kg"], 2)
            n_from_dap = round(dap_kg * (dap_spec["n_pct"] / 100.0), 2)
            p_from_dap = round(dap_kg * (dap_spec["p2o5_pct"] / 100.0), 2)

            dap_unit_price = self._prices.get_unit_price("DAP")
            dap_total_cost = (
                round(dap_kg * dap_unit_price, 2) if dap_unit_price is not None else None
            )

            products.append(
                FertilizerProduct(
                    product_name=dap_spec["full_name"],
                    nutrient_type=dap_spec["nutrient_type"],
                    quantity_kg_per_ha=dap_kg,
                    bags_per_ha=dap_bags,
                    bag_size_kg=dap_spec["bag_size_kg"],
                    n_contribution_kg_ha=n_from_dap,
                    p2o5_contribution_kg_ha=p_from_dap,
                    k2o_contribution_kg_ha=0.0,
                    unit_cost_inr_per_kg=dap_unit_price,
                    total_cost_inr=dap_total_cost,
                    source_standards=dap_spec["source_standard"],
                    notes=f"Supplies full P2O5 ({p_from_dap} kg/ha) and {n_from_dap} kg N/ha.",
                )
            )

        # 2. Satisfy remaining Nitrogen using Urea (46% N)
        remaining_n = max(0.0, round(n_req - n_from_dap, 2))
        if remaining_n > 0:
            urea_spec = PRODUCT_CATALOGUE["Urea"]
            urea_kg = round(remaining_n / (urea_spec["n_pct"] / 100.0), 2)
            urea_bags = round(urea_kg / urea_spec["bag_size_kg"], 2)
            n_from_urea = round(urea_kg * (urea_spec["n_pct"] / 100.0), 2)

            urea_unit_price = self._prices.get_unit_price("Urea")
            urea_total_cost = (
                round(urea_kg * urea_unit_price, 2) if urea_unit_price is not None else None
            )

            products.append(
                FertilizerProduct(
                    product_name=urea_spec["full_name"],
                    nutrient_type=urea_spec["nutrient_type"],
                    quantity_kg_per_ha=urea_kg,
                    bags_per_ha=urea_bags,
                    bag_size_kg=urea_spec["bag_size_kg"],
                    n_contribution_kg_ha=n_from_urea,
                    p2o5_contribution_kg_ha=0.0,
                    k2o_contribution_kg_ha=0.0,
                    unit_cost_inr_per_kg=urea_unit_price,
                    total_cost_inr=urea_total_cost,
                    source_standards=urea_spec["source_standard"],
                    notes=f"Supplies remaining N ({n_from_urea} kg N/ha) after DAP contribution.",
                )
            )

        # 3. Satisfy Potassium using MOP (60% K2O)
        if k_req > 0:
            mop_spec = PRODUCT_CATALOGUE["MOP"]
            mop_kg = round(k_req / (mop_spec["k2o_pct"] / 100.0), 2)
            mop_bags = round(mop_kg / mop_spec["bag_size_kg"], 2)
            k_from_mop = round(mop_kg * (mop_spec["k2o_pct"] / 100.0), 2)

            mop_unit_price = self._prices.get_unit_price("MOP")
            mop_total_cost = (
                round(mop_kg * mop_unit_price, 2) if mop_unit_price is not None else None
            )

            products.append(
                FertilizerProduct(
                    product_name=mop_spec["full_name"],
                    nutrient_type=mop_spec["nutrient_type"],
                    quantity_kg_per_ha=mop_kg,
                    bags_per_ha=mop_bags,
                    bag_size_kg=mop_spec["bag_size_kg"],
                    n_contribution_kg_ha=0.0,
                    p2o5_contribution_kg_ha=0.0,
                    k2o_contribution_kg_ha=k_from_mop,
                    unit_cost_inr_per_kg=mop_unit_price,
                    total_cost_inr=mop_total_cost,
                    source_standards=mop_spec["source_standard"],
                    notes=f"Supplies full K2O ({k_from_mop} kg/ha).",
                )
            )

        # Calculate total cost if all products have valid pricing
        if products and all(p.total_cost_inr is not None for p in products):
            total_cost = round(sum(p.total_cost_inr for p in products), 2)  # type: ignore[arg-type]
        else:
            total_cost = None

        log.info(
            "fertilizer_translation_complete",
            product_count=len(products),
            total_cost=total_cost,
        )
        return products, total_cost

    def get_application_timing(self, crop: Crop) -> ApplicationTiming:
        """
        Returns crop-specific split application schedule according to PAU Package of Practices.
        """
        if crop == Crop.WHEAT:
            splits = [
                {
                    "stage": "Basal at Sowing",
                    "timing": "At the time of sowing (drilled below seed)",
                    "fertilizers": "Full DAP + Full MOP + 1/2 Neem Coated Urea",
                    "purpose": "Early root establishment and initial vegetative surge",
                },
                {
                    "stage": "First Irrigation (CRI stage)",
                    "timing": "21–25 days after sowing (crown root initiation)",
                    "fertilizers": "1/4 Neem Coated Urea",
                    "purpose": "Tillering promotion",
                },
                {
                    "stage": "Second Irrigation",
                    "timing": "40–45 days after sowing (late tillering)",
                    "fertilizers": "1/4 Neem Coated Urea",
                    "purpose": "Spikelet development and grain number",
                },
            ]
            return ApplicationTiming(
                splits=splits,
                apply_before="At sowing for phosphatic/potassic fertilizers",
                notes="PAU Ludhiana Package of Practices for Rabi Crops (Wheat).",
            )

        if crop == Crop.RICE:
            splits = [
                {
                    "stage": "Basal at Transplanting",
                    "timing": "Last puddling before transplanting",
                    "fertilizers": "Full DAP + Full MOP + 1/3 Neem Coated Urea",
                    "purpose": "Seedling establishment and tillering base",
                },
                {
                    "stage": "Active Tillering",
                    "timing": "21 days after transplanting (DAT)",
                    "fertilizers": "1/3 Neem Coated Urea",
                    "purpose": "Effective tiller multiplication",
                },
                {
                    "stage": "Panicle Initiation",
                    "timing": "42 days after transplanting (DAT)",
                    "fertilizers": "1/3 Neem Coated Urea",
                    "purpose": "Panicle size and grain filling",
                },
            ]
            return ApplicationTiming(
                splits=splits,
                apply_before="At puddling for phosphatic/potassic fertilizers",
                notes="PAU Ludhiana Package of Practices for Kharif Crops (Rice).",
            )

        return ApplicationTiming(
            splits=None,
            apply_before=None,
            notes=f"PAU split-application guidelines for {crop.value}.",
        )
