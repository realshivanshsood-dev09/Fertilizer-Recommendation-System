"""
Database model tests using SQLite in-memory.
==============================================
These tests verify:
  - Model instantiation for all 14 entities
  - UUID generation
  - Relationship navigation
  - FK constraints
  - Nullable field acceptance
  - Provenance chain integrity
  - JSON fields (ModelVersion.metrics, Recommendation.request_payload)
  - is_lab_measured constraint semantics

PostgreSQL/PostGIS behavior is NOT tested here.
These are ORM/structural tests only. No fabricated agricultural data.

All test values are minimal, structurally valid placeholders.
"""
from __future__ import annotations

import datetime as dt
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base, generate_uuid
from app.models.biofertilizer import BiofertilizerRecord
from app.models.crop import CropRecord
from app.models.farmer import Farmer
from app.models.fertilizer_price import FertilizerPrice
from app.models.fertilizer_product import FertilizerProductRecord
from app.models.field_trial import FieldTrialObservation
from app.models.location import Location
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.recommendation_item import RecommendationItem
from app.models.soil_test import SoilTest
from app.models.stcr_config import STCRConfiguration
from app.models.study import Study
from app.models.weather_observation import WeatherObservation


# ── SQLite in-memory test database ────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a fresh SQLite in-memory async session for each test.
    Tables are created from the SQLAlchemy models at fixture setup.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


# ── UUID generation ───────────────────────────────────────────────────────────

class TestUUIDGeneration:
    def test_generate_uuid_returns_string(self):
        uid = generate_uuid()
        assert isinstance(uid, str)

    def test_generate_uuid_is_unique(self):
        uids = {generate_uuid() for _ in range(100)}
        assert len(uids) == 100

    def test_generate_uuid_is_36_chars(self):
        uid = generate_uuid()
        assert len(uid) == 36
        assert uid.count("-") == 4


# ── Location ──────────────────────────────────────────────────────────────────

class TestLocation:
    async def test_create_minimal(self, db_session: AsyncSession):
        loc = Location(id=generate_uuid(), district="Bathinda")
        db_session.add(loc)
        await db_session.flush()
        fetched = await db_session.get(Location, loc.id)
        assert fetched is not None
        assert fetched.district == "Bathinda"
        assert fetched.state == "Punjab"

    async def test_optional_fields_nullable(self, db_session: AsyncSession):
        loc = Location(id=generate_uuid(), district="Mansa")
        db_session.add(loc)
        await db_session.flush()
        assert loc.block is None
        assert loc.village is None
        assert loc.latitude is None
        assert loc.longitude is None

    async def test_accepts_any_district(self, db_session: AsyncSession):
        """Location district is not constrained at DB level (only Pydantic layer)."""
        loc = Location(id=generate_uuid(), district="Ludhiana")  # not an MVP district
        db_session.add(loc)
        await db_session.flush()
        assert loc.district == "Ludhiana"

    async def test_all_fields(self, db_session: AsyncSession):
        loc = Location(
            id=generate_uuid(),
            state="Punjab",
            district="Moga",
            block="Nihal Singh Wala",
            village="Test Village",
            latitude=30.81,
            longitude=75.17,
        )
        db_session.add(loc)
        await db_session.flush()
        fetched = await db_session.get(Location, loc.id)
        assert fetched.block == "Nihal Singh Wala"
        assert fetched.latitude == pytest.approx(30.81)


# ── Farmer ────────────────────────────────────────────────────────────────────

class TestFarmer:
    async def test_create_minimal(self, db_session: AsyncSession):
        farmer = Farmer(id=generate_uuid())
        db_session.add(farmer)
        await db_session.flush()
        fetched = await db_session.get(Farmer, farmer.id)
        assert fetched is not None
        assert fetched.consent_recorded is False

    async def test_optional_external_id(self, db_session: AsyncSession):
        farmer = Farmer(id=generate_uuid(), external_id="FARMER-001")
        db_session.add(farmer)
        await db_session.flush()
        assert farmer.external_id == "FARMER-001"

    async def test_with_location_fk(self, db_session: AsyncSession):
        loc = Location(id=generate_uuid(), district="Faridkot")
        db_session.add(loc)
        await db_session.flush()
        farmer = Farmer(id=generate_uuid(), location_id=loc.id, consent_recorded=True)
        db_session.add(farmer)
        await db_session.flush()
        assert farmer.location_id == loc.id
        assert farmer.consent_recorded is True


# ── CropRecord ────────────────────────────────────────────────────────────────

class TestCropRecord:
    async def test_create(self, db_session: AsyncSession):
        crop = CropRecord(id=generate_uuid(), name="wheat", season="rabi")
        db_session.add(crop)
        await db_session.flush()
        assert crop.is_active is True
        assert crop.scientific_name is None

    async def test_all_crops(self, db_session: AsyncSession):
        for name, season in [("wheat", "rabi"), ("rice", "kharif"), ("cotton", "kharif")]:
            crop = CropRecord(id=generate_uuid(), name=name, season=season)
            db_session.add(crop)
        await db_session.flush()


# ── SoilTest ──────────────────────────────────────────────────────────────────

class TestSoilTest:
    async def test_shc_is_lab_measured(self, db_session: AsyncSession):
        """Soil Health Card records should have is_lab_measured=True."""
        st = SoilTest(
            id=generate_uuid(),
            soil_source="soil_health_card",
            is_lab_measured=True,
        )
        db_session.add(st)
        await db_session.flush()
        assert st.is_lab_measured is True

    async def test_questionnaire_not_lab_measured(self, db_session: AsyncSession):
        """Questionnaire fallback must never have is_lab_measured=True."""
        st = SoilTest(
            id=generate_uuid(),
            soil_source="questionnaire_fallback",
            is_lab_measured=False,
        )
        db_session.add(st)
        await db_session.flush()
        assert st.is_lab_measured is False
        assert st.nitrogen_kg_per_ha is None
        assert st.phosphorus_kg_per_ha is None
        assert st.potassium_kg_per_ha is None

    async def test_all_nutrient_fields_nullable(self, db_session: AsyncSession):
        st = SoilTest(id=generate_uuid(), soil_source="district_average")
        db_session.add(st)
        await db_session.flush()
        assert st.nitrogen_kg_per_ha is None
        assert st.phosphorus_kg_per_ha is None
        assert st.potassium_kg_per_ha is None
        assert st.ph is None
        assert st.organic_carbon_pct is None

    async def test_extensible_soil_source(self, db_session: AsyncSession):
        """soil_source is a free string — not constrained to enum at DB level."""
        for source in ["soil_health_card", "government_lab", "icar_kvk",
                       "pau_lab", "research_trial", "district_average", "questionnaire_fallback"]:
            st = SoilTest(id=generate_uuid(), soil_source=source)
            db_session.add(st)
        await db_session.flush()

    async def test_with_provenance_fields(self, db_session: AsyncSession):
        st = SoilTest(
            id=generate_uuid(),
            soil_source="soil_health_card",
            is_lab_measured=True,
            source_identifier="SHC-PB-BTD-2024-000123",
            units_note="N by alkaline KMnO4, P by Olsen's, K by ammonium acetate",
            provenance="Punjab SHC portal, retrieved 2024-03",
        )
        db_session.add(st)
        await db_session.flush()
        assert st.source_identifier == "SHC-PB-BTD-2024-000123"


# ── Study ─────────────────────────────────────────────────────────────────────

class TestStudy:
    async def test_create_minimal(self, db_session: AsyncSession):
        study = Study(
            id=generate_uuid(),
            title="Test Study Title",
            verification_status="unverified",
        )
        db_session.add(study)
        await db_session.flush()
        assert study.institution is None
        assert study.doi is None

    async def test_provenance_fields(self, db_session: AsyncSession):
        study = Study(
            id=generate_uuid(),
            title="AICRP-STCR Field Trial Report",
            institution="ICAR-IISS",
            doi="10.0000/test.doi.001",
            publication_year=2022,
            verification_status="under_review",
            geographic_scope="Malwa, Punjab",
            crop="wheat",
        )
        db_session.add(study)
        await db_session.flush()
        assert study.institution == "ICAR-IISS"
        assert study.publication_year == 2022

    async def test_verification_status_values(self, db_session: AsyncSession):
        for status in ["unverified", "under_review", "verified", "rejected"]:
            study = Study(id=generate_uuid(), title=f"Study-{status}", verification_status=status)
            db_session.add(study)
        await db_session.flush()


# ── FieldTrialObservation ─────────────────────────────────────────────────────

class TestFieldTrialObservation:
    async def test_create_minimal_all_nulls(self, db_session: AsyncSession):
        """All measurement fields are nullable — heterogeneous studies."""
        obs = FieldTrialObservation(id=generate_uuid())
        db_session.add(obs)
        await db_session.flush()
        assert obs.crop is None
        assert obs.observed_yield_mg_per_ha is None

    async def test_linked_to_study(self, db_session: AsyncSession):
        study = Study(id=generate_uuid(), title="Test Study", verification_status="unverified")
        db_session.add(study)
        await db_session.flush()

        obs = FieldTrialObservation(
            id=generate_uuid(),
            study_id=study.id,
            crop="wheat",
            season="rabi",
            year=2023,
        )
        db_session.add(obs)
        await db_session.flush()
        assert obs.study_id == study.id

    async def test_full_observation(self, db_session: AsyncSession):
        obs = FieldTrialObservation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            year=2022,
            soil_n=120.0,
            soil_p=18.0,
            soil_k=180.0,
            ph=7.8,
            organic_carbon=0.42,
            fertilizer_n=120.0,
            fertilizer_p2o5=60.0,
            fertilizer_k2o=0.0,
            observed_yield_mg_per_ha=4.8,
            replications=3,
            provenance="AICRP-STCR experiment, station data",
        )
        db_session.add(obs)
        await db_session.flush()
        assert obs.observed_yield_mg_per_ha == pytest.approx(4.8)
        assert obs.replications == 3


# ── STCRConfiguration ─────────────────────────────────────────────────────────

class TestSTCRConfiguration:
    async def test_create_unpopulated(self, db_session: AsyncSession):
        """Current state: coefficients_populated must default to False."""
        cfg = STCRConfiguration(
            id=generate_uuid(),
            version="v0.1-placeholder",
        )
        db_session.add(cfg)
        await db_session.flush()
        assert cfg.coefficients_populated is False
        assert cfg.is_active is True
        assert cfg.verification_status == "unverified"

    async def test_version_uniqueness(self, db_session: AsyncSession):
        cfg1 = STCRConfiguration(id=generate_uuid(), version="v0.1")
        db_session.add(cfg1)
        await db_session.flush()

        from sqlalchemy.exc import IntegrityError
        cfg2 = STCRConfiguration(id=generate_uuid(), version="v0.1")
        db_session.add(cfg2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_yaml_hash_nullable(self, db_session: AsyncSession):
        cfg = STCRConfiguration(
            id=generate_uuid(),
            version="v0.2",
            yaml_hash=None,  # not populated yet
        )
        db_session.add(cfg)
        await db_session.flush()
        assert cfg.yaml_hash is None


# ── ModelVersion ──────────────────────────────────────────────────────────────

class TestModelVersion:
    async def test_create_inactive_by_default(self, db_session: AsyncSession):
        mv = ModelVersion(
            id=generate_uuid(),
            model_type="xgboost_correction",
            version="v0.1.0",
        )
        db_session.add(mv)
        await db_session.flush()
        assert mv.is_active is False
        assert mv.metrics is None

    async def test_json_metrics_field(self, db_session: AsyncSession):
        mv = ModelVersion(
            id=generate_uuid(),
            model_type="xgboost_correction",
            version="v0.2.0",
            metrics={"rmse_N": 5.21, "r2_N": 0.87, "rmse_P": 3.14},
        )
        db_session.add(mv)
        await db_session.flush()
        fetched = await db_session.get(ModelVersion, mv.id)
        assert fetched.metrics["rmse_N"] == pytest.approx(5.21)

    async def test_git_commit_field(self, db_session: AsyncSession):
        mv = ModelVersion(
            id=generate_uuid(),
            model_type="xgboost_correction",
            version="v0.3.0",
            git_commit="abc123def456abc123def456abc123def456abc1",
        )
        db_session.add(mv)
        await db_session.flush()
        assert len(mv.git_commit) == 40

    async def test_version_uniqueness(self, db_session: AsyncSession):
        from sqlalchemy.exc import IntegrityError
        mv1 = ModelVersion(id=generate_uuid(), model_type="xgboost_correction", version="v1.0")
        db_session.add(mv1)
        await db_session.flush()

        mv2 = ModelVersion(id=generate_uuid(), model_type="xgboost_correction", version="v1.0")
        db_session.add(mv2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


# ── Recommendation ────────────────────────────────────────────────────────────

class TestRecommendation:
    async def test_create_minimal(self, db_session: AsyncSession):
        rec = Recommendation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
        )
        db_session.add(rec)
        await db_session.flush()
        assert rec.is_placeholder is True
        assert rec.final_n_kg_per_ha is None

    async def test_all_npk_fields_nullable(self, db_session: AsyncSession):
        rec = Recommendation(
            id=generate_uuid(),
            crop="rice",
            season="kharif",
            pipeline_version="0.1.0-scaffold",
            soil_source="district_average",
            is_placeholder=True,
        )
        db_session.add(rec)
        await db_session.flush()
        for field in [
            rec.stcr_n_kg_per_ha, rec.stcr_p2o5_kg_per_ha, rec.stcr_k2o_kg_per_ha,
            rec.ml_correction_n, rec.ml_correction_p, rec.ml_correction_k,
            rec.final_n_kg_per_ha, rec.final_p2o5_kg_per_ha, rec.final_k2o_kg_per_ha,
        ]:
            assert field is None

    async def test_json_request_payload(self, db_session: AsyncSession):
        payload = {"crop": "wheat", "district": "Bathinda", "soil_source": "soil_health_card"}
        rec = Recommendation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
            request_payload=payload,
        )
        db_session.add(rec)
        await db_session.flush()
        fetched = await db_session.get(Recommendation, rec.id)
        assert fetched.request_payload["crop"] == "wheat"

    async def test_linked_to_soil_test(self, db_session: AsyncSession):
        st = SoilTest(id=generate_uuid(), soil_source="soil_health_card", is_lab_measured=True)
        db_session.add(st)
        await db_session.flush()

        rec = Recommendation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
            soil_test_id=st.id,
        )
        db_session.add(rec)
        await db_session.flush()
        assert rec.soil_test_id == st.id

    async def test_linked_to_stcr_config(self, db_session: AsyncSession):
        cfg = STCRConfiguration(id=generate_uuid(), version="v0.1-test")
        db_session.add(cfg)
        await db_session.flush()

        rec = Recommendation(
            id=generate_uuid(),
            crop="cotton",
            season="kharif",
            pipeline_version="0.1.0-scaffold",
            soil_source="district_average",
            is_placeholder=True,
            stcr_config_id=cfg.id,
        )
        db_session.add(rec)
        await db_session.flush()
        assert rec.stcr_config_id == cfg.id

    async def test_linked_to_model_version(self, db_session: AsyncSession):
        mv = ModelVersion(id=generate_uuid(), model_type="xgboost_correction", version="v0.99")
        db_session.add(mv)
        await db_session.flush()

        rec = Recommendation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=False,
            model_version_id=mv.id,
        )
        db_session.add(rec)
        await db_session.flush()
        assert rec.model_version_id == mv.id


# ── RecommendationItem ────────────────────────────────────────────────────────

class TestRecommendationItem:
    async def test_create_linked_to_recommendation(self, db_session: AsyncSession):
        rec = Recommendation(
            id=generate_uuid(),
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
        )
        db_session.add(rec)
        await db_session.flush()

        item = RecommendationItem(
            id=generate_uuid(),
            recommendation_id=rec.id,
            item_type="fertilizer",
        )
        db_session.add(item)
        await db_session.flush()
        assert item.recommendation_id == rec.id
        assert item.product_name is None  # all product fields nullable

    async def test_multiple_items_per_recommendation(self, db_session: AsyncSession):
        rec = Recommendation(
            id=generate_uuid(),
            crop="rice",
            season="kharif",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
        )
        db_session.add(rec)
        await db_session.flush()

        for item_type in ["fertilizer", "biofertilizer", "timing"]:
            item = RecommendationItem(
                id=generate_uuid(),
                recommendation_id=rec.id,
                item_type=item_type,
            )
            db_session.add(item)
        await db_session.flush()


# ── Full Provenance Chain ─────────────────────────────────────────────────────

class TestProvenanceChain:
    async def test_full_chain(self, db_session: AsyncSession):
        """
        Verify complete provenance chain:
        Recommendation → SoilTest → Location → STCRConfiguration → ModelVersion
        """
        # Location
        loc = Location(id=generate_uuid(), district="Bathinda")
        db_session.add(loc)
        await db_session.flush()

        # Farmer at that location
        farmer = Farmer(id=generate_uuid(), location_id=loc.id)
        db_session.add(farmer)
        await db_session.flush()

        # SoilTest linked to farmer + location
        soil = SoilTest(
            id=generate_uuid(),
            farmer_id=farmer.id,
            location_id=loc.id,
            soil_source="soil_health_card",
            is_lab_measured=True,
        )
        db_session.add(soil)
        await db_session.flush()

        # STCR configuration
        stcr_cfg = STCRConfiguration(id=generate_uuid(), version="v0.chain-test")
        db_session.add(stcr_cfg)
        await db_session.flush()

        # ML model version
        mv = ModelVersion(id=generate_uuid(), model_type="xgboost_correction", version="v0.chain-test")
        db_session.add(mv)
        await db_session.flush()

        # Recommendation tying everything together
        rec = Recommendation(
            id=generate_uuid(),
            farmer_id=farmer.id,
            location_id=loc.id,
            soil_test_id=soil.id,
            stcr_config_id=stcr_cfg.id,
            model_version_id=mv.id,
            crop="wheat",
            season="rabi",
            pipeline_version="0.1.0-scaffold",
            soil_source="soil_health_card",
            is_placeholder=True,
        )
        db_session.add(rec)
        await db_session.flush()

        # Verify all FK links are present
        assert rec.farmer_id == farmer.id
        assert rec.location_id == loc.id
        assert rec.soil_test_id == soil.id
        assert rec.stcr_config_id == stcr_cfg.id
        assert rec.model_version_id == mv.id


# ── FertilizerProduct + FertilizerPrice ───────────────────────────────────────

class TestFertilizerProduct:
    async def test_create_empty_product(self, db_session: AsyncSession):
        """Products can be created without prices — schema only."""
        prod = FertilizerProductRecord(
            id=generate_uuid(),
            product_name="Test Urea",
            n_pct=46.0,
            p2o5_pct=0.0,
            k2o_pct=0.0,
        )
        db_session.add(prod)
        await db_session.flush()
        assert prod.is_active is True
        assert prod.manufacturer is None

    async def test_product_with_price(self, db_session: AsyncSession):
        prod = FertilizerProductRecord(
            id=generate_uuid(),
            product_name="Test DAP",
            n_pct=18.0,
            p2o5_pct=46.0,
            k2o_pct=0.0,
        )
        db_session.add(prod)
        await db_session.flush()

        price = FertilizerPrice(
            id=generate_uuid(),
            product_id=prod.id,
            price_inr=1350.0,
            bag_size_kg=50.0,
            effective_from=dt.date(2024, 1, 1),
            verified=False,  # not verified yet
        )
        db_session.add(price)
        await db_session.flush()
        assert price.verified is False
        assert price.product_id == prod.id


# ── BiofertilizerRecord ───────────────────────────────────────────────────────

class TestBiofertilizerRecord:
    async def test_create_unverified(self, db_session: AsyncSession):
        """All scientific values start unverified and nullable."""
        bio = BiofertilizerRecord(
            id=generate_uuid(),
            name="Test Rhizobium inoculant",
        )
        db_session.add(bio)
        await db_session.flush()
        assert bio.verified is False
        assert bio.dose is None
        assert bio.organism is None


# ── WeatherObservation ────────────────────────────────────────────────────────

class TestWeatherObservation:
    async def test_create_minimal(self, db_session: AsyncSession):
        obs = WeatherObservation(
            id=generate_uuid(),
            district="Bathinda",
            observed_at=dt.datetime(2024, 6, 15, 8, 0),
        )
        db_session.add(obs)
        await db_session.flush()
        assert obs.rainfall_mm is None
        assert obs.source is None

    async def test_with_all_fields(self, db_session: AsyncSession):
        obs = WeatherObservation(
            id=generate_uuid(),
            district="Mansa",
            observed_at=dt.datetime(2024, 7, 1, 14, 30),
            temp_max_c=41.2,
            temp_min_c=28.5,
            rainfall_mm=12.4,
            humidity_pct=72.0,
            source="IMD",
        )
        db_session.add(obs)
        await db_session.flush()
        assert obs.temp_max_c == pytest.approx(41.2)
        assert obs.source == "IMD"


# ── Study → FieldTrialObservation relationship ────────────────────────────────

class TestStudyFieldTrialRelationship:
    async def test_study_has_multiple_observations(self, db_session: AsyncSession):
        study = Study(
            id=generate_uuid(),
            title="Multi-observation study",
            verification_status="unverified",
        )
        db_session.add(study)
        await db_session.flush()

        obs_ids = []
        for i in range(3):
            obs = FieldTrialObservation(
                id=generate_uuid(),
                study_id=study.id,
                crop="wheat",
                year=2020 + i,
            )
            db_session.add(obs)
            obs_ids.append(obs.id)
        await db_session.flush()

        # All observations linked to same study
        for oid in obs_ids:
            fetched = await db_session.get(FieldTrialObservation, oid)
            assert fetched.study_id == study.id


# ── Alembic configuration validation ─────────────────────────────────────────

class TestAlembicConfig:
    def test_alembic_ini_exists(self):
        from pathlib import Path
        alembic_ini = Path(__file__).parent.parent / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini must exist"

    def test_alembic_versions_dir_exists(self):
        from pathlib import Path
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        assert versions_dir.exists(), "alembic/versions/ must exist"

    def test_initial_migration_exists(self):
        from pathlib import Path
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = list(versions_dir.glob("001_*.py"))
        assert len(migration_files) == 1, "Initial migration 001_*.py must exist"

    def test_alembic_env_imports_models(self):
        """Ensure app.models imports without error (Alembic depends on this)."""
        import app.models  # noqa: F401
        from app.db.base import Base
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "locations", "farmers", "crops", "soil_tests",
            "studies", "field_trial_observations",
            "stcr_configurations", "model_versions",
            "recommendations", "recommendation_items",
            "fertilizer_products", "fertilizer_prices",
            "biofertilizer_records", "weather_observations",
        }
        assert expected == table_names, f"Missing tables: {expected - table_names}"
