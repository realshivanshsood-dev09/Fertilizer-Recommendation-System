"""
Agronomic Validation & Evidence Service
=======================================
Provides access to empirical validation metrics, study provenance, and Malwa
regional verification evidence across registered Track A & B datasets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog
import yaml

log = structlog.get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_VALIDATION_SUMMARY_PATH = _PROJECT_ROOT / "data" / "processed" / "validation_summary.yaml"


class ValidationSummaryService:
    """
    Loads and provides validation metadata and evidence levels.
    """

    def __init__(self, summary_path: Optional[Path] = None) -> None:
        self._path = summary_path or _VALIDATION_SUMMARY_PATH
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            log.warning("validation_summary_not_found", path=str(self._path))
            return
        with open(self._path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def get_summary(self) -> Dict[str, Any]:
        stats = self._data.get("summary_statistics", {})
        evidence_crops = self._data.get("evidence_by_crop", {})

        sources_list: List[Dict[str, Any]] = []
        for crop_name, crop_info in evidence_crops.items():
            for study in crop_info.get("calibration_studies", []):
                sources_list.append({
                    "study_id": study.get("study_id"),
                    "citation": study.get("citation"),
                    "crop": crop_name,
                    "role": study.get("role"),
                    "location": study.get("location"),
                })
            for study in crop_info.get("validation_studies", []):
                sources_list.append({
                    "study_id": study.get("study_id"),
                    "citation": study.get("citation"),
                    "crop": crop_name,
                    "role": study.get("role"),
                    "location": study.get("location"),
                })

        return {
            "total_studies": stats.get("total_studies", 4),
            "total_observations": stats.get("total_observations", 29),
            "malwa_observations": stats.get("malwa_observations", 7),
            "crops": ["wheat", "rice"],
            "validation_sources": sources_list,
            "evidence_status": {
                "wheat": evidence_crops.get("wheat", {}).get("status", "calibration_verified"),
                "rice": evidence_crops.get("rice", {}).get("status", "calibration_and_malwa_validated"),
                "cotton": evidence_crops.get("cotton", {}).get("status", "unsupported_awaiting_calibration"),
            },
            "ml_status": self._data.get("_metadata", {}).get("ml_status", "disabled_insufficient_plot_data"),
        }

    def get_evidence_metadata_for_crop(self, crop_name: str, district_name: str) -> Dict[str, Any]:
        crop_data = self._data.get("evidence_by_crop", {}).get(crop_name.lower(), {})
        status = crop_data.get("status", "unsupported")

        is_malwa_district = district_name.title() in ["Bathinda", "Mansa", "Muktsar", "Faridkot", "Moga"]
        malwa_val_available = crop_data.get("malwa_direct_validation", False) and is_malwa_district

        calib_studies = [s.get("citation") for s in crop_data.get("calibration_studies", [])]
        val_studies = [s.get("citation") for s in crop_data.get("validation_studies", [])]

        if crop_name.lower() == "rice" and malwa_val_available:
            strength = "high_with_regional_malwa_verification"
        elif crop_name.lower() in ["wheat", "rice"]:
            strength = "moderate_alluvial_calibration"
        else:
            strength = "insufficient_calibration"

        return {
            "evidence_status": status,
            "calibration_source": calib_studies[0] if calib_studies else None,
            "validation_sources": val_studies,
            "malwa_validation_available": malwa_val_available,
            "evidence_strength": strength,
            "notes": crop_data.get("malwa_status_note"),
        }
