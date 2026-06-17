from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    secret_key: str
    secret_encryption_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    re_valuation_provider: str = "manual"
    re_valuation_api_key: str = ""
    re_valuation_refresh_schedule: str = "0 3 * * 1"
    backup_path: str = "/data/backups"
    backup_retention_days: int = 30
    backup_schedule: str = "0 2 * * *"
    export_path: str = "/data/exports"
    allowed_origins: list[str] = ["http://localhost"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()  # type: ignore[call-arg]  # fields populated from .env at runtime
