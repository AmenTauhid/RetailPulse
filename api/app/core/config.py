"""API configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://retailpulse:retailpulse@localhost:5432/retailpulse"
    )
    database_url_sync: str = (
        "postgresql://retailpulse:retailpulse@localhost:5432/retailpulse"
    )
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    api_base_url: str = "http://localhost:8000"

    # ML model paths
    xgboost_model_path: str = "ml/outputs/xgboost_latest.joblib"
    xgboost_metrics_path: str = "ml/outputs/xgboost_latest_metrics.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
