"""
Data validators proxy for Track A data ingestion.
"""
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.ingestion.validators import (
    ValidationError,
    detect_duplicates,
    preserve_source_conflict,
    validate_dataset_entry,
    validate_path_separation,
    validate_source_entry,
    validate_unit_declarations,
)

__all__ = [
    "ValidationError",
    "detect_duplicates",
    "preserve_source_conflict",
    "validate_dataset_entry",
    "validate_path_separation",
    "validate_source_entry",
    "validate_unit_declarations",
]
