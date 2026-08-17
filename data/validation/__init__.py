"""
Data Validation Module (Track A)
=================================
Exposes schemas and validator functions for standalone ingestion scripts
and CI pipeline data-integrity checks.
"""

import sys
from pathlib import Path

# Ensure backend app is discoverable if running scripts directly from data/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.ingestion.schemas import *
from app.ingestion.validators import *
from app.ingestion.checksum import *
