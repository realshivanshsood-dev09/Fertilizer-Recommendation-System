"""
Conftest for pytest — sets APP_ENV to test so structlog uses console renderer.
"""

import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("ML_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
