"""
Agronomic Data Loaders
=======================
Single source of truth: load all agronomic configuration from YAML files.

These loaders are the ONLY path for agronomic data into the pipeline.
Services must NOT maintain duplicate hardcoded dictionaries.

Graceful degradation:
  - Missing YAML file → warning log + empty/None data
  - Null scientific values → accepted as "not yet populated"
  - Malformed YAML → raises at startup
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import structlog
import yaml

log = structlog.get_logger(__name__)

# ── Project root detection ────────────────────────────────────────────────────
# Resolve relative to this file: backend/app/core/data_loader.py → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Default paths (can be overridden for testing)
STCR_COEFFICIENTS_PATH = _PROJECT_ROOT / "agronomy" / "stcr" / "stcr_coefficients.yaml"
DISTRICT_AVERAGES_PATH = _PROJECT_ROOT / "data" / "soil" / "district_averages.yaml"
BIOFERTILIZERS_PATH = _PROJECT_ROOT / "data" / "agronomy" / "biofertilizers.yaml"


def _load_yaml(path: Path, label: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its contents as a dict.

    - Logs a warning and returns empty dict if the file doesn't exist.
    - Raises on malformed YAML (parse errors should not be silently ignored).
    """
    if not path.exists():
        log.warning(
            "yaml_file_not_found",
            label=label,
            path=str(path),
        )
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        log.error(
            "yaml_parse_error",
            label=label,
            path=str(path),
            error=str(exc),
        )
        raise ValueError(
            f"Failed to parse YAML file '{label}' at {path}: {exc}"
        ) from exc

    if data is None:
        log.warning("yaml_file_empty", label=label, path=str(path))
        return {}

    if not isinstance(data, dict):
        raise ValueError(
            f"YAML file '{label}' at {path} must contain a mapping (dict), "
            f"got {type(data).__name__}"
        )

    return data


# ── STCR Coefficients ────────────────────────────────────────────────────────

class STCRCoefficients:
    """
    Loaded STCR coefficient data from the YAML file.
    Provides safe accessors that return None when data is unavailable.
    """

    def __init__(self, data: Dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path
        self._metadata = data.get("_metadata", {})

    @property
    def is_populated(self) -> bool:
        """True only when at least one crop has a non-null 'a' coefficient."""
        for crop in ("wheat", "rice", "cotton"):
            crop_data = self._data.get(crop, {})
            for nutrient in ("N", "P", "K"):
                n_data = crop_data.get(nutrient, {})
                if n_data.get("a") is not None:
                    return True
        return False

    def is_crop_populated(self, crop_name: str) -> bool:
        """True when the specific crop has populated STCR coefficients."""
        crop_data = self._data.get(crop_name, {})
        for nutrient in ("N", "P", "K"):
            n_data = crop_data.get(nutrient, {})
            if n_data.get("a") is not None:
                return True
        return False

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    def get_crop_coefficients(self, crop_name: str) -> Dict[str, Any]:
        """
        Returns the coefficient dict for a given crop.
        Returns empty dict if crop not found.
        """
        return self._data.get(crop_name, {})

    def get_nutrient_coefficients(
        self, crop_name: str, nutrient: str
    ) -> Dict[str, Any]:
        """
        Returns {a, b, target_yield_Mg_per_ha, FUE, ...} for a crop × nutrient.
        Returns empty dict if not found.
        """
        return self.get_crop_coefficients(crop_name).get(nutrient, {})

    def get_source_note(self, crop_name: str) -> str:
        """Returns the source field for a crop, or a placeholder string."""
        crop_data = self._data.get(crop_name, {})
        # Check per-nutrient sources or crop-level
        for nutrient in ("N", "P", "K"):
            n_data = crop_data.get(nutrient, {})
            src = n_data.get("source")
            if src is not None:
                return src
        dataset_id = crop_data.get("dataset_id")
        if dataset_id:
            return f"{dataset_id} (PAU/ICAR)"
        return f"PLACEHOLDER — STCR coefficients for {crop_name} not yet loaded"


_CACHED_STCR_COEFFICIENTS: Optional[STCRCoefficients] = None


def load_stcr_coefficients(
    path: Optional[Path] = None,
    reload: bool = False,
) -> STCRCoefficients:
    """
    Load STCR coefficients from YAML with caching.
    Returns an STCRCoefficients wrapper with safe accessors.
    """
    global _CACHED_STCR_COEFFICIENTS
    if path is None and _CACHED_STCR_COEFFICIENTS is not None and not reload:
        return _CACHED_STCR_COEFFICIENTS

    p = path or STCR_COEFFICIENTS_PATH
    data = _load_yaml(p, "stcr_coefficients")
    loaded = STCRCoefficients(data, p)
    log.info(
        "stcr_coefficients_loaded",
        path=str(p),
        is_populated=loaded.is_populated,
    )
    if path is None:
        _CACHED_STCR_COEFFICIENTS = loaded
    return loaded


# ── District Soil Averages ────────────────────────────────────────────────────

class DistrictAverages:
    """
    Loaded district soil average data from the YAML file.
    Provides safe accessors that return None when data is unavailable.
    """

    def __init__(self, data: Dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path
        self._metadata = data.get("_metadata", {})
        # Districts may be under a 'districts' key or at top-level
        self._districts = data.get("districts", {})

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    def get_district(self, district_name: str) -> Dict[str, Any]:
        """
        Returns the soil average dict for a given district.
        Returns empty dict if not found.
        """
        return self._districts.get(district_name, {})

    def get_soil_values(
        self, district_name: str
    ) -> Dict[str, Optional[float]]:
        """
        Returns {nitrogen, phosphorus, potassium, ph, organic_carbon}
        mapped from the YAML field names.
        All values may be None if not yet populated.
        """
        d = self.get_district(district_name)
        return {
            "nitrogen": d.get("N_kg_per_ha"),
            "phosphorus": d.get("P2O5_kg_per_ha"),
            "potassium": d.get("K2O_kg_per_ha"),
            "ph": d.get("pH"),
            "organic_carbon": d.get("organic_carbon_pct"),
        }


_CACHED_DISTRICT_AVERAGES: Optional[DistrictAverages] = None


def load_district_averages(
    path: Optional[Path] = None,
    reload: bool = False,
) -> DistrictAverages:
    """
    Load district soil averages from YAML with caching.
    Returns a DistrictAverages wrapper with safe accessors.
    """
    global _CACHED_DISTRICT_AVERAGES
    if path is None and _CACHED_DISTRICT_AVERAGES is not None and not reload:
        return _CACHED_DISTRICT_AVERAGES

    p = path or DISTRICT_AVERAGES_PATH
    data = _load_yaml(p, "district_averages")
    loaded = DistrictAverages(data, p)
    log.info("district_averages_loaded", path=str(p))
    if path is None:
        _CACHED_DISTRICT_AVERAGES = loaded
    return loaded


# ── Biofertilizer Recommendations ────────────────────────────────────────────

class BiofertilizerData:
    """
    Loaded biofertilizer recommendation data from the YAML file.
    """

    def __init__(self, data: Dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path
        self._metadata = data.get("_metadata", {})
        self._crops = data.get("crops", {})

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    def get_crop(self, crop_name: str) -> Dict[str, Any]:
        """
        Returns biofertilizer data for a given crop.
        Returns empty dict if not found.
        """
        return self._crops.get(crop_name, {})


_CACHED_BIOFERTILIZER_DATA: Optional[BiofertilizerData] = None


def load_biofertilizer_data(
    path: Optional[Path] = None,
    reload: bool = False,
) -> BiofertilizerData:
    """
    Load biofertilizer recommendations from YAML with caching.
    Returns a BiofertilizerData wrapper with safe accessors.
    """
    global _CACHED_BIOFERTILIZER_DATA
    if path is None and _CACHED_BIOFERTILIZER_DATA is not None and not reload:
        return _CACHED_BIOFERTILIZER_DATA

    p = path or BIOFERTILIZERS_PATH
    data = _load_yaml(p, "biofertilizers")
    loaded = BiofertilizerData(data, p)
    log.info("biofertilizer_data_loaded", path=str(p))
    if path is None:
        _CACHED_BIOFERTILIZER_DATA = loaded
    return loaded
