"""
Performance & Latency Benchmark Tests (Phase 9)
==============================================
Validates that recommendation pipeline executes with sub-millisecond to low-millisecond
in-memory latency using static YAML loaders and zero network hops.
"""

from __future__ import annotations

import time
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.constants import Crop, District, Season, SoilSource
from app.main import app
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline


@pytest.mark.asyncio
async def test_recommendation_pipeline_latency_benchmark():
    req = RecommendRequest(
        crop=Crop.WHEAT,
        district=District.BATHINDA,
        season=Season.RABI,
        soil_source=SoilSource.SOIL_HEALTH_CARD,
        target_yield_q_ha=50.0,
        soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
    )

    # 1. Cold request
    t0 = time.perf_counter()
    cold_resp = await run_pipeline(req)
    t_cold = (time.perf_counter() - t0) * 1000.0  # ms
    assert cold_resp.final_recommendation.N_kg_per_ha is not None

    # 2. Warm request
    t1 = time.perf_counter()
    warm_resp = await run_pipeline(req)
    t_warm = (time.perf_counter() - t1) * 1000.0  # ms
    assert warm_resp.final_recommendation.N_kg_per_ha is not None

    # 3. 10 Sequential requests
    t2 = time.perf_counter()
    for _ in range(10):
        await run_pipeline(req)
    t_10 = (time.perf_counter() - t2) * 1000.0 / 10.0  # avg ms

    # 4. 50 Sequential requests
    t3 = time.perf_counter()
    for _ in range(50):
        await run_pipeline(req)
    t_50 = (time.perf_counter() - t3) * 1000.0 / 50.0  # avg ms

    print(
        f"\n[PERFORMANCE BENCHMARK] Cold: {t_cold:.2f}ms | Warm: {t_warm:.2f}ms | "
        f"10-run avg: {t_10:.2f}ms | 50-run avg: {t_50:.2f}ms"
    )

    # In-memory target: average per-request processing time must be well under 50ms
    assert t_50 < 50.0
