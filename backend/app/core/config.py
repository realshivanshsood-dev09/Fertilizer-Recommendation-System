"""
Application configuration via environment variables.
All secrets and environment-specific values are read from .env — never hardcoded.
"""

from __future__ import annotations

import json
from typing import List, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_KEYS = {
    "INSECURE_DEFAULT_KEY_CHANGE_IN_PRODUCTION",
    "CHANGE_ME_IN_PRODUCTION_USE_STRONG_RANDOM_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_ENV: str = "development"
    APP_VERSION: str = "0.2.0"
    SECRET_KEY: str = "INSECURE_DEFAULT_KEY_CHANGE_IN_PRODUCTION"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fertilizer_rec_dev.db"
    DB_ECHO: bool = False           # SQLAlchemy query logging — enable only for debugging
    DB_POOL_SIZE: int = 5           # Ignored for SQLite; effective only for PostgreSQL

    # CORS — JSON list or comma-separated origins via CORS_ORIGINS env var.
    # Typed as Union so pydantic-settings does not JSON-decode comma-separated strings.
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:5173"]

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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        if isinstance(v, str):
            text = v.strip()
            if not text:
                return []
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must be a list of origin strings")
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        raise ValueError("CORS_ORIGINS must be a list, JSON list, or comma-separated string")

    @model_validator(mode="after")
    def reject_insecure_secret_in_production(self) -> Settings:
        if self.APP_ENV == "production" and self.SECRET_KEY in _INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value when APP_ENV=production"
            )
        return self


settings = Settings()
