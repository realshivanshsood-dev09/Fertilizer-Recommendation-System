"""
Application configuration via environment variables.
All secrets and environment-specific values are read from .env — never hardcoded.
"""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "INSECURE_DEFAULT_KEY_CHANGE_IN_PRODUCTION"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fertilizer_rec_dev.db"
    DB_ECHO: bool = False           # SQLAlchemy query logging — enable only for debugging
    DB_POOL_SIZE: int = 5           # Ignored for SQLite; effective only for PostgreSQL

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ML layer toggle — set False until a validated model exists
    ML_ENABLED: bool = False
    ML_MODEL_DIR: str = "../ml/models"

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v


settings = Settings()
