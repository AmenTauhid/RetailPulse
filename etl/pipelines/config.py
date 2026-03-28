from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://retailpulse:retailpulse@localhost:5432/retailpulse"
    database_url_sync: str = "postgresql://retailpulse:retailpulse@localhost:5432/retailpulse"
    postgres_user: str = "retailpulse"
    postgres_password: str = "retailpulse"
    postgres_db: str = "retailpulse"

    # External APIs
    openweathermap_api_key: str = ""
    anthropic_api_key: str = ""

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    api_base_url: str = "http://localhost:8000"

    # Data generation
    data_start_date: str = "2024-01-01"
    data_end_date: str = "2025-12-31"


@lru_cache
def get_settings() -> Settings:
    return Settings()
