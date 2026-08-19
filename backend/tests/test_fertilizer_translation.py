"""
Tests for FertilizerTranslationService.
Verifies:
  - N-only translation (Urea only)
  - N + P translation (DAP + Urea)
  - N + P + K translation (DAP + Urea + MOP)
  - No negative quantities
  - Total nutrient coverage >= required nutrients
  - Standards provenance (FCO 1985)
  - Price is nullable / unverified
  - Application timing splits for Wheat and Rice
"""

from __future__ import annotations

import pytest

from app.core.constants import Crop
from app.services.fertilizer_translation import FertilizerTranslationService


@pytest.fixture
def service() -> FertilizerTranslationService:
    return FertilizerTranslationService()


class TestFertilizerTranslationService:

    def test_n_only_translation(self, service):
        """
        Required: 92 kg N/ha, 0 kg P2O5, 0 kg K2O
        Expected: Urea only = 92 / 0.46 = 200.0 kg/ha = 200 / 45 = 4.44 bags/ha
        """
        products, cost = service.translate(Crop.WHEAT, N_kg_per_ha=92.0, P2O5_kg_per_ha=0.0, K2O_kg_per_ha=0.0)
        assert len(products) == 1
        urea = products[0]
        assert "Urea" in urea.product_name
        assert urea.quantity_kg_per_ha == pytest.approx(200.0, rel=1e-2)
        assert urea.bags_per_ha == pytest.approx(4.44, rel=1e-2)
        assert urea.n_contribution_kg_ha == pytest.approx(92.0, rel=1e-2)
        assert urea.p2o5_contribution_kg_ha == 0.0
        assert urea.k2o_contribution_kg_ha == 0.0
        assert cost is None  # price nullable

    def test_np_translation_with_dap_and_urea(self, service):
        """
        Required: 100 kg N/ha, 46 kg P2O5/ha, 0 kg K2O
        1. DAP: 46 / 0.46 = 100 kg DAP/ha (2.0 bags/ha).
           N from DAP = 100 * 0.18 = 18.0 kg N.
           Remaining N = 100 - 18 = 82 kg N.
        2. Urea: 82 / 0.46 = 178.26 kg Urea/ha (3.96 bags/ha).
           N from Urea = 178.26 * 0.46 = 82.0 kg N.
        """
        products, cost = service.translate(Crop.WHEAT, N_kg_per_ha=100.0, P2O5_kg_per_ha=46.0, K2O_kg_per_ha=0.0)
        assert len(products) == 2
        dap = next(p for p in products if "DAP" in p.product_name)
        urea = next(p for p in products if "Urea" in p.product_name)

        assert dap.quantity_kg_per_ha == pytest.approx(100.0, rel=1e-2)
        assert dap.p2o5_contribution_kg_ha == pytest.approx(46.0, rel=1e-2)
        assert dap.n_contribution_kg_ha == pytest.approx(18.0, rel=1e-2)

        assert urea.quantity_kg_per_ha == pytest.approx(178.26, rel=1e-2)
        assert urea.n_contribution_kg_ha == pytest.approx(82.0, rel=1e-2)

        # Check total nutrient coverage
        total_n = dap.n_contribution_kg_ha + urea.n_contribution_kg_ha
        assert total_n >= 100.0 - 0.1
        assert dap.p2o5_contribution_kg_ha >= 46.0 - 0.1

    def test_npk_full_translation(self, service):
        """
        Required: 120 kg N, 60 kg P2O5, 30 kg K2O
        """
        products, cost = service.translate(Crop.RICE, N_kg_per_ha=120.0, P2O5_kg_per_ha=60.0, K2O_kg_per_ha=30.0)
        assert len(products) == 3
        dap = next(p for p in products if "DAP" in p.product_name)
        urea = next(p for p in products if "Urea" in p.product_name)
        mop = next(p for p in products if "MOP" in p.product_name)

        # MOP check: 30 / 0.60 = 50.0 kg MOP = 1.0 bag
        assert mop.quantity_kg_per_ha == pytest.approx(50.0, rel=1e-2)
        assert mop.bags_per_ha == pytest.approx(1.0, rel=1e-2)
        assert mop.k2o_contribution_kg_ha == pytest.approx(30.0, rel=1e-2)

        # Non-negative check
        for p in products:
            assert p.quantity_kg_per_ha >= 0.0
            assert p.bags_per_ha >= 0.0

    def test_empty_when_all_nutrients_none_or_zero(self, service):
        products, cost = service.translate(Crop.COTTON, N_kg_per_ha=None, P2O5_kg_per_ha=None, K2O_kg_per_ha=None)
        assert products == []
        assert cost is None

        products_zero, cost_zero = service.translate(Crop.WHEAT, N_kg_per_ha=0.0, P2O5_kg_per_ha=0.0, K2O_kg_per_ha=0.0)
        assert products_zero == []
        assert cost_zero is None

    def test_product_provenance_and_standards(self, service):
        products, _ = service.translate(Crop.WHEAT, N_kg_per_ha=50.0, P2O5_kg_per_ha=20.0, K2O_kg_per_ha=10.0)
        for p in products:
            assert p.source_standards is not None
            assert "Fertiliser (Control) Order" in p.source_standards

    def test_application_timing_splits_wheat_and_rice(self, service):
        wheat_timing = service.get_application_timing(Crop.WHEAT)
        assert wheat_timing.splits is not None
        assert len(wheat_timing.splits) == 3
        assert "PAU" in wheat_timing.notes

        rice_timing = service.get_application_timing(Crop.RICE)
        assert rice_timing.splits is not None
        assert len(rice_timing.splits) == 3
        assert "Transplanting" in rice_timing.splits[0]["stage"]
