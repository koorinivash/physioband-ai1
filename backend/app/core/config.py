"""Environment-based configuration. Values come from environment variables or backend/.env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PhysioBand AI API"
    environment: str = Field("development", description="development | production | test")
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # MongoDB Atlas. Never hard-code the real connection string: set MONGODB_URI in .env.
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "physioband_ai"
    mongodb_timeout_ms: int = 8000

    # JWT authentication
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # CORS (comma separated); the mobile app does not need CORS, Swagger / web tools might.
    cors_origins: str = "*"

    # ML integration
    ml_src_path: str = "../ml/src"
    ml_model_path: str = "../ml/saved_models/biceps_curl_quality.pkl"

    # Sensor data limits
    max_samples_per_batch: int = 500
    max_samples_per_session: int = 90_000  # 30 minutes at 50 Hz

    @field_validator("ml_src_path", "ml_model_path")
    @classmethod
    def _resolve_relative(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_DIR / path).resolve())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
