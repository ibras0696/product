from functools import lru_cache
from pathlib import Path

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_environment: str = "development"
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"
    encryption_key: str | None = None
    auth_session_idle_days: PositiveInt = 7
    auth_session_absolute_days: PositiveInt = 30
    auth_rate_limit_attempts: PositiveInt = 5
    auth_rate_limit_window_seconds: PositiveInt = 900
    media_storage_root: Path = Path("/var/lib/product/media")


@lru_cache
def get_settings() -> Settings:
    return Settings()
