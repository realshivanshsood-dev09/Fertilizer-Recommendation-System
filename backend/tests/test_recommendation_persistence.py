"""
Tests for recommendation persistence with database models.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import Crop, District, IrrigationType, Season, SoilSource
from app.db.base import Base
from app.models.recommendation import Recommendation
from app.models.recommendation_item import RecommendationItem
from app.models.soil_test import SoilTest
from app.schemas.request import RecommendRequest, SoilInput
from app.services.pipeline import run_pipeline
from app.services.recommendation_repository import persist_recommendation


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_persist_skipped_when_no_session():
    req = RecommendRequest(
        crop=Crop.WHEAT,
        district=District.BATHINDA,
        season=Season.RABI,
        soil_source=SoilSource.SOIL_HEALTH_CARD,
        soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
    )
    resp = await run_pipeline(req, session=None)
    assert resp is not None
    rec_id = await persist_recommendation(req, resp, session=None)
    assert rec_id is None


@pytest.mark.asyncio
async def test_persist_creates_records_with_session(db_session: AsyncSession):
    req = RecommendRequest(
        crop=Crop.WHEAT,
        district=District.BATHINDA,
        season=Season.RABI,
        soil_source=SoilSource.SOIL_HEALTH_CARD,
        target_yield_q_ha=50.0,
        soil=SoilInput(nitrogen=120.0, phosphorus=18.0, potassium=180.0),
    )
    resp = await run_pipeline(req, session=db_session)
    await db_session.commit()

    # Query Recommendation
    stmt = select(Recommendation).where(Recommendation.crop == "wheat")
    result = await db_session.execute(stmt)
    recs = result.scalars().all()
    assert len(recs) == 1
    rec = recs[0]
    assert rec.final_n_kg_per_ha == pytest.approx(73.8, rel=1e-2)
    assert rec.confidence == 0.95

    # Query SoilTest
    assert rec.soil_test_id is not None
    soil_stmt = select(SoilTest).where(SoilTest.id == rec.soil_test_id)
    soil_res = await db_session.execute(soil_stmt)
    soil_record = soil_res.scalar_one()
    assert soil_record.nitrogen_kg_per_ha == 120.0
    assert soil_record.is_lab_measured is True

    # Query RecommendationItems
    items_stmt = select(RecommendationItem).where(RecommendationItem.recommendation_id == rec.id)
    items_res = await db_session.execute(items_stmt)
    items = items_res.scalars().all()
    assert len(items) >= 2  # DAP, MOP, Urea
    for item in items:
        assert item.quantity_kg_per_ha > 0
        assert item.unit == "kg/ha"
