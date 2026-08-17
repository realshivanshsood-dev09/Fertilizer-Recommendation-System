"""
Registry Loader & Manager
==========================
Loads, verifies, and interfaces with source_registry.yaml and dataset_registry.yaml.
Provides referential integrity checks between datasets and data sources.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set
import structlog
import yaml

from app.ingestion.schemas import DatasetRegistryEntry, SourceRegistryEntry
from app.ingestion.validators import ValidationError, validate_dataset_entry, validate_source_entry

log = structlog.get_logger(__name__)

# Default locations relative to repository root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_SOURCE_REGISTRY_PATH = _REPO_ROOT / "data" / "metadata" / "source_registry.yaml"
DEFAULT_DATASET_REGISTRY_PATH = _REPO_ROOT / "data" / "metadata" / "dataset_registry.yaml"


def _read_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        log.warning("registry_file_not_found", path=str(path))
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationError(f"Registry file at {path} must contain a mapping (dict), got {type(data).__name__}")
    return data


class MasterRegistries:
    """
    In-memory container holding validated source and dataset registries.
    """
    def __init__(
        self,
        sources: Dict[str, SourceRegistryEntry],
        datasets: Dict[str, DatasetRegistryEntry],
    ) -> None:
        self.sources = sources
        self.datasets = datasets

    def get_source(self, source_id: str) -> Optional[SourceRegistryEntry]:
        return self.sources.get(source_id)

    def get_dataset(self, dataset_id: str) -> Optional[DatasetRegistryEntry]:
        return self.datasets.get(dataset_id)

    def get_datasets_for_source(self, source_id: str) -> list[DatasetRegistryEntry]:
        return [ds for ds in self.datasets.values() if ds.source_id == source_id]


def load_source_registry(
    path: Optional[Path] = None,
) -> Dict[str, SourceRegistryEntry]:
    """
    Loads and validates all entries in source_registry.yaml.
    """
    p = path or DEFAULT_SOURCE_REGISTRY_PATH
    raw_data = _read_yaml_file(p)
    sources_dict = raw_data.get("sources", {})
    
    validated_sources: Dict[str, SourceRegistryEntry] = {}
    for src_id, entry in sources_dict.items():
        if isinstance(entry, dict):
            entry_with_id = {"source_id": src_id, **entry} if "source_id" not in entry else entry
            validated_sources[src_id] = validate_source_entry(entry_with_id)

    log.info("source_registry_loaded", path=str(p), count=len(validated_sources))
    return validated_sources


def load_dataset_registry(
    path: Optional[Path] = None,
    known_source_ids: Optional[Set[str]] = None,
) -> Dict[str, DatasetRegistryEntry]:
    """
    Loads and validates all entries in dataset_registry.yaml.
    Checks referential integrity against known source IDs.
    """
    p = path or DEFAULT_DATASET_REGISTRY_PATH
    raw_data = _read_yaml_file(p)
    datasets_dict = raw_data.get("datasets", {})

    validated_datasets: Dict[str, DatasetRegistryEntry] = {}
    for ds_id, entry in datasets_dict.items():
        if isinstance(entry, dict):
            entry_with_id = {"dataset_id": ds_id, **entry} if "dataset_id" not in entry else entry
            validated_datasets[ds_id] = validate_dataset_entry(entry_with_id, known_source_ids)

    log.info("dataset_registry_loaded", path=str(p), count=len(validated_datasets))
    return validated_datasets


def load_and_validate_all_registries(
    source_registry_path: Optional[Path] = None,
    dataset_registry_path: Optional[Path] = None,
) -> MasterRegistries:
    """
    Loads both source and dataset registries and ensures complete cross-validation.
    """
    sources = load_source_registry(source_registry_path)
    datasets = load_dataset_registry(dataset_registry_path, known_source_ids=set(sources.keys()))
    return MasterRegistries(sources=sources, datasets=datasets)
