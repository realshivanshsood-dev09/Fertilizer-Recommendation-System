"""Initial schema - creates all 14 tables.

Revision ID: 001
Revises: (none)
Create Date: 2026-08-17

This migration creates the complete initial schema for the
SIH 2026 Fertilizer Recommendation System.

Tables created:
  locations, farmers, crops, soil_tests,
  studies, field_trial_observations,
  stcr_configurations, model_versions,
  recommendations, recommendation_items,
  fertilizer_products, fertilizer_prices,
  biofertilizer_records, weather_observations

PostGIS geometry:
  The Location.geom column (PostGIS Geometry Point, SRID 4326) is created
  ONLY when running against PostgreSQL with PostGIS installed.
  SQLite testing: the PostGIS branch is not executed.

No agricultural data is seeded. Schema only.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgresql() -> bool:
    """Return True when running against PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    # ── Enable PostGIS (PostgreSQL only) ──────────────────────────────────────
    if _is_postgresql():
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── locations ─────────────────────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", sa.String(100), nullable=False, server_default="Punjab"),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("block", sa.String(100), nullable=True),
        sa.Column("village", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_locations_district", "locations", ["district"])
    op.create_index("ix_locations_district_block", "locations", ["district", "block"])

    # Add PostGIS geometry column for PostgreSQL deployments
    if _is_postgresql():
        op.execute(
            "ALTER TABLE locations ADD COLUMN geom geometry(Point,4326)"
        )
        op.execute(
            "CREATE INDEX ix_locations_geom ON locations USING GIST (geom)"
        )

    # ── farmers ───────────────────────────────────────────────────────────────
    op.create_table(
        "farmers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=True, unique=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("consent_recorded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_farmers_external_id", "farmers", ["external_id"])

    # ── crops ─────────────────────────────────────────────────────────────────
    op.create_table(
        "crops",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("scientific_name", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_crops_name", "crops", ["name"])

    # ── soil_tests ────────────────────────────────────────────────────────────
    op.create_table(
        "soil_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("soil_source", sa.String(50), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("nitrogen_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("phosphorus_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("potassium_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("ph", sa.Float(), nullable=True),
        sa.Column("organic_carbon_pct", sa.Float(), nullable=True),
        sa.Column("source_identifier", sa.String(255), nullable=True),
        sa.Column("units_note", sa.String(500), nullable=True),
        sa.Column("is_lab_measured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_soil_tests_soil_source", "soil_tests", ["soil_source"])

    # ── studies ───────────────────────────────────────────────────────────────
    op.create_table(
        "studies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("institution", sa.String(300), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("publication", sa.String(500), nullable=True),
        sa.Column("doi", sa.String(200), nullable=True, unique=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("geographic_scope", sa.String(300), nullable=True),
        sa.Column("crop", sa.String(50), nullable=True),
        sa.Column("dataset_license", sa.String(200), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("verification_status", sa.String(50), nullable=False, server_default="unverified"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── field_trial_observations ──────────────────────────────────────────────
    op.create_table(
        "field_trial_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("study_id", sa.String(36), sa.ForeignKey("studies.id"), nullable=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("crop", sa.String(50), nullable=True),
        sa.Column("season", sa.String(20), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("soil_n", sa.Float(), nullable=True),
        sa.Column("soil_p", sa.Float(), nullable=True),
        sa.Column("soil_k", sa.Float(), nullable=True),
        sa.Column("ph", sa.Float(), nullable=True),
        sa.Column("organic_carbon", sa.Float(), nullable=True),
        sa.Column("fertilizer_n", sa.Float(), nullable=True),
        sa.Column("fertilizer_p2o5", sa.Float(), nullable=True),
        sa.Column("fertilizer_k2o", sa.Float(), nullable=True),
        sa.Column("organic_input_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("residue_input_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("irrigation", sa.String(50), nullable=True),
        sa.Column("target_yield_mg_per_ha", sa.Float(), nullable=True),
        sa.Column("observed_yield_mg_per_ha", sa.Float(), nullable=True),
        sa.Column("nutrient_uptake_n", sa.Float(), nullable=True),
        sa.Column("nutrient_uptake_p", sa.Float(), nullable=True),
        sa.Column("nutrient_uptake_k", sa.Float(), nullable=True),
        sa.Column("treatment_description", sa.Text(), nullable=True),
        sa.Column("replications", sa.Integer(), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_field_trial_observations_crop", "field_trial_observations", ["crop"])

    # ── stcr_configurations ───────────────────────────────────────────────────
    op.create_table(
        "stcr_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("yaml_hash", sa.String(64), nullable=True),
        sa.Column("crop", sa.String(50), nullable=True),
        sa.Column("geographic_scope", sa.String(300), nullable=True),
        sa.Column("soil_type", sa.String(200), nullable=True),
        sa.Column("source_document", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("units", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("coefficients_populated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_status", sa.String(50), nullable=False, server_default="unverified"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_stcr_configurations_version", "stcr_configurations", ["version"])

    # ── model_versions ────────────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("training_dataset_id", sa.String(255), nullable=True),
        sa.Column("training_date", sa.DateTime(), nullable=True),
        sa.Column("feature_schema_version", sa.String(50), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("artifact_path", sa.String(1000), nullable=True),
        sa.Column("git_commit", sa.String(40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_model_versions_model_type", "model_versions", ["model_type"])
    op.create_index("ix_model_versions_version", "model_versions", ["version"])

    # ── recommendations ───────────────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("soil_test_id", sa.String(36), sa.ForeignKey("soil_tests.id"), nullable=True),
        sa.Column("stcr_config_id", sa.String(36), sa.ForeignKey("stcr_configurations.id"), nullable=True),
        sa.Column("model_version_id", sa.String(36), sa.ForeignKey("model_versions.id"), nullable=True),
        sa.Column("crop", sa.String(50), nullable=False),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("pipeline_version", sa.String(50), nullable=False),
        sa.Column("soil_source", sa.String(50), nullable=False),
        sa.Column("stcr_n_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("stcr_p2o5_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("stcr_k2o_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("ml_correction_n", sa.Float(), nullable=True),
        sa.Column("ml_correction_p", sa.Float(), nullable=True),
        sa.Column("ml_correction_k", sa.Float(), nullable=True),
        sa.Column("final_n_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("final_p2o5_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("final_k2o_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("estimated_cost_inr", sa.Float(), nullable=True),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        sa.Column("explanation_summary", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_recommendations_crop", "recommendations", ["crop"])

    # ── recommendation_items ──────────────────────────────────────────────────
    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recommendation_id", sa.String(36),
                  sa.ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("nutrient_type", sa.String(20), nullable=True),
        sa.Column("quantity_kg_per_ha", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_cost_inr", sa.Float(), nullable=True),
        sa.Column("total_cost_inr", sa.Float(), nullable=True),
        sa.Column("application_timing", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── fertilizer_products ───────────────────────────────────────────────────
    op.create_table(
        "fertilizer_products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_name", sa.String(200), nullable=False, unique=True),
        sa.Column("manufacturer", sa.String(200), nullable=True),
        sa.Column("n_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p2o5_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("k2o_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("bag_size_kg", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fertilizer_products_product_name", "fertilizer_products", ["product_name"])

    # ── fertilizer_prices ─────────────────────────────────────────────────────
    op.create_table(
        "fertilizer_prices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("fertilizer_products.id"), nullable=False),
        sa.Column("price_inr", sa.Float(), nullable=False),
        sa.Column("bag_size_kg", sa.Float(), nullable=False),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── biofertilizer_records ─────────────────────────────────────────────────
    op.create_table(
        "biofertilizer_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("organism", sa.String(200), nullable=True),
        sa.Column("crop_applicability", sa.String(200), nullable=True),
        sa.Column("application_method", sa.String(200), nullable=True),
        sa.Column("dose", sa.String(200), nullable=True),
        sa.Column("timing", sa.String(200), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_biofertilizer_records_name", "biofertilizer_records", ["name"])

    # ── weather_observations ──────────────────────────────────────────────────
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("temp_max_c", sa.Float(), nullable=True),
        sa.Column("temp_min_c", sa.Float(), nullable=True),
        sa.Column("rainfall_mm", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("provenance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_weather_observations_district", "weather_observations", ["district"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("weather_observations")
    op.drop_table("biofertilizer_records")
    op.drop_table("fertilizer_prices")
    op.drop_table("fertilizer_products")
    op.drop_table("recommendation_items")
    op.drop_table("recommendations")
    op.drop_table("model_versions")
    op.drop_table("stcr_configurations")
    op.drop_table("field_trial_observations")
    op.drop_table("studies")
    op.drop_table("soil_tests")
    op.drop_table("crops")
    op.drop_table("farmers")
    op.drop_table("locations")
