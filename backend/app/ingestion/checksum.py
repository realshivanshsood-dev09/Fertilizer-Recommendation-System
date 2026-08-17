"""
SHA-256 Checksum Utilities
===========================
Provides deterministic cryptographic checksum calculation and validation
to guarantee raw data immutability and provenance integrity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union


def compute_sha256(data_or_path: Union[str, Path, bytes]) -> str:
    """
    Computes the SHA-256 hex digest of a file (path) or raw bytes/string.
    Reads files in 64KB chunks to handle large datasets efficiently.
    """
    hasher = hashlib.sha256()

    if isinstance(data_or_path, bytes):
        hasher.update(data_or_path)
        return hasher.hexdigest()

    if isinstance(data_or_path, str) and not Path(data_or_path).exists():
        # Treat as raw string content if it's not an existing file path
        hasher.update(data_or_path.encode("utf-8"))
        return hasher.hexdigest()

    path = Path(data_or_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for checksum computation: {path}")

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_checksum(filepath: Union[str, Path], expected_checksum: str) -> bool:
    """
    Compares the calculated SHA-256 of filepath against expected_checksum.
    Raises ValueError on mismatch, returns True on success.
    """
    calculated = compute_sha256(filepath)
    if calculated.lower() != expected_checksum.lower():
        raise ValueError(
            f"Checksum mismatch for '{filepath}'!\n"
            f"  Expected:   {expected_checksum}\n"
            f"  Calculated: {calculated}"
        )
    return True
