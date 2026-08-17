"""
Cost Calculation Service
=========================
Estimates total fertilizer input cost per hectare from product quantities
and current market prices.

⚠️  PLACEHOLDER — No product prices are available yet.
    See docs/science_status.md §4.
"""

from __future__ import annotations

import structlog
from typing import List, Optional

from app.schemas.response import FertilizerProduct

log = structlog.get_logger(__name__)


class CostCalculationService:
    """
    Computes total estimated fertilizer cost from a list of FertilizerProducts.
    Returns None when any product price is unavailable.
    """

    def calculate(self, products: List[FertilizerProduct]) -> Optional[float]:
        log.info("cost_calculation", product_count=len(products))

        if not products:
            log.warning(
                "cost_calculation_no_products",
                reason="No products to cost — fertilizer translation produced empty list.",
            )
            return None

        total = 0.0
        for product in products:
            if product.total_cost_inr is None:
                log.warning(
                    "cost_calculation_missing_price",
                    product=product.product_name,
                )
                return None  # cannot compute total if any price is missing
            total += product.total_cost_inr

        return total
