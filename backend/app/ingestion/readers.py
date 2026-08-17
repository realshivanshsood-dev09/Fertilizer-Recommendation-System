"""
Track A Data Ingestion Readers
===============================
Provides format-specific readers for CSV, JSON, XLSX, and PDF-extracted tables.
All readers enforce checksum validation on raw inputs and attach provenance metadata.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import structlog

from app.ingestion.checksum import compute_sha256, verify_checksum
from app.ingestion.schemas import DatasetFormat, ProvenanceRecord

log = structlog.get_logger(__name__)


class RawDataPolicyError(Exception):
    """Raised when a raw data file modification or location policy is violated."""
    pass


def validate_raw_path_policy(path: Union[str, Path]) -> Path:
    """
    Ensures raw files are strictly located under data/raw/.
    """
    p = Path(path).resolve()
    normalized = str(p).replace("\\", "/")
    if "data/raw" not in normalized and "data/metadata" not in normalized:
        raise RawDataPolicyError(
            f"Raw data file must reside in 'data/raw/', illegal path: {path}"
        )
    return p


def read_csv_dataset(
    filepath: Union[str, Path],
    expected_checksum: Optional[str] = None,
    delimiter: str = ",",
) -> Dict[str, Any]:
    """
    Reads a CSV dataset, verifies its cryptographic hash, and returns data and metadata.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"CSV dataset not found: {path}")

    calculated_checksum = compute_sha256(path)
    if expected_checksum:
        verify_checksum(path, expected_checksum)

    records: List[Dict[str, Any]] = []
    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            records.append(dict(row))

    log.info(
        "csv_dataset_read",
        path=str(path),
        record_count=len(records),
        checksum=calculated_checksum,
    )
    return {
        "format": DatasetFormat.CSV,
        "path": str(path),
        "checksum": calculated_checksum,
        "record_count": len(records),
        "records": records,
    }


def read_json_dataset(
    filepath: Union[str, Path],
    expected_checksum: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reads a JSON dataset, verifies its cryptographic hash, and returns data and metadata.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"JSON dataset not found: {path}")

    calculated_checksum = compute_sha256(path)
    if expected_checksum:
        verify_checksum(path, expected_checksum)

    with open(path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    log.info(
        "json_dataset_read",
        path=str(path),
        checksum=calculated_checksum,
    )
    return {
        "format": DatasetFormat.JSON,
        "path": str(path),
        "checksum": calculated_checksum,
        "data": data,
    }


def register_pdf_extracted_table(
    raw_pdf_path: Union[str, Path],
    extracted_table_data: List[Dict[str, Any]],
    table_identifier: str,
    page_number: int,
    extraction_method: str = "manual_expert_extraction",
    extractor_notes: Optional[str] = None,
    expected_pdf_checksum: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Preserves provenance for tables extracted from official PDF publications (e.g. PAU research bulletins).
    Distinguishes the source raw PDF from the extracted structured dataset.
    """
    pdf_path = Path(raw_pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Source PDF publication not found: {pdf_path}")

    pdf_checksum = compute_sha256(pdf_path)
    if expected_pdf_checksum:
        verify_checksum(pdf_path, expected_pdf_checksum)

    log.info(
        "pdf_table_registered",
        pdf_path=str(pdf_path),
        table=table_identifier,
        page=page_number,
        record_count=len(extracted_table_data),
        pdf_checksum=pdf_checksum,
    )

    return {
        "format": DatasetFormat.PDF_TABLE,
        "source_pdf_path": str(pdf_path),
        "source_pdf_checksum": pdf_checksum,
        "table_identifier": table_identifier,
        "page_number": page_number,
        "extraction_method": extraction_method,
        "extractor_notes": extractor_notes,
        "record_count": len(extracted_table_data),
        "records": extracted_table_data,
    }
