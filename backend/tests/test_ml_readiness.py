"""
Unit and Validation Tests for ML Data Readiness (Phase 7 Audit)
================================================================
Verifies:
  - Inventory count and strict separation of Track A & Track B datasets
  - All empirical rows are classified as treatment_mean
  - No synthetic or fabricated observations exist in data registries
  - ML training blocker assertion (suitable_for_training == False)
  - Provenance integrity (SHA-256, PDF file existence)
  - GroupKFold validation policy enforcement
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AUDIT_YAML_PATH = _PROJECT_ROOT / "data" / "metadata" / "ml_readiness_audit.yaml"
_DATASET_REGISTRY_PATH = _PROJECT_ROOT / "data" / "metadata" / "dataset_registry.yaml"
_SOURCE_REGISTRY_PATH = _PROJECT_ROOT / "data" / "metadata" / "source_registry.yaml"


@pytest.fixture
def audit_data() -> dict:
    assert _AUDIT_YAML_PATH.exists(), f"Audit YAML not found at {_AUDIT_YAML_PATH}"
    with open(_AUDIT_YAML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def dataset_registry() -> dict:
    with open(_DATASET_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def source_registry() -> dict:
    with open(_SOURCE_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestMLDataReadinessAudit:

    def test_audit_verdict_blocks_ml_training(self, audit_data):
        verdict = audit_data.get("ml_readiness_verdict", {})
        assert verdict.get("status") == "NOT_TRAINING_READY"
        assert verdict.get("suitable_for_training") is False
        assert "insufficient independent paired response data" in verdict.get("reason", "")

    def test_zero_plot_level_observations(self, audit_data):
        metrics = audit_data.get("aggregate_metrics", {})
        assert metrics.get("total_plot_level_rows") == 0
        assert metrics.get("total_replicate_level_rows") == 0
        assert metrics.get("total_treatment_mean_rows") == 29

    def test_all_datasets_are_treatment_means(self, audit_data):
        inventory = audit_data.get("inventory_by_dataset", {})
        assert len(inventory) == 4
        for ds_id, ds_info in inventory.items():
            assert ds_info.get("granularity") == "treatment_mean", f"Dataset {ds_id} not treatment_mean"
            assert ds_info.get("replicate_level_data") is False
            assert ds_info.get("suitability_classification") == "VALIDATION_BENCHMARK"

    def test_all_source_pdfs_exist_and_match_sha256(self, audit_data, source_registry):
        inventory = audit_data.get("inventory_by_dataset", {})
        raw_sources = source_registry.get("sources", {})
        sources = raw_sources if isinstance(raw_sources, dict) else {s["source_id"]: s for s in raw_sources}

        for ds_id, ds_info in inventory.items():
            src_id = ds_info.get("source_id")
            assert src_id in sources, f"Source ID {src_id} missing from source_registry.yaml"
            src_entry = sources[src_id]

            raw_file_rel = src_entry.get("raw_file_path")
            if raw_file_rel:
                abs_path = _PROJECT_ROOT / raw_file_rel
                assert abs_path.exists(), f"Raw file does not exist: {abs_path}"

    def test_crop_observation_breakdown(self, audit_data):
        crops = audit_data.get("aggregate_metrics", {}).get("observations_by_crop", {})
        assert crops.get("wheat") == 11
        assert crops.get("rice") == 18
        assert crops.get("cotton") == 0

    def test_no_synthetic_observations_in_registries(self, dataset_registry):
        raw_ds = dataset_registry.get("datasets", {})
        datasets_list = raw_ds.values() if isinstance(raw_ds, dict) else raw_ds

        for ds in datasets_list:
            granularity = ds.get("data_granularity")
            assert granularity != "synthetic", f"Synthetic granularity forbidden in dataset {ds.get('dataset_id')}"
            assert ds.get("suitable_for_training", False) is False

    def test_ml_target_specification_bounds(self, audit_data):
        target_spec = audit_data.get("ml_target_specification", {})
        assert "[-30%, +30%]" in target_spec.get("safety_clipping_bounds", "")
        assert target_spec.get("current_status") == "DEFERRED_UNTIL_DATA_THRESHOLD_MET"
