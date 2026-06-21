import json
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# Resolve .env relative to this file so Settings() works regardless of CWD.
# In Docker, env vars arrive via docker-compose env_file so this path need
# not exist there — pydantic-settings silently ignores a missing env_file.
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class _CsvFallbackMixin:
    """Overrides decode_complex_value to accept comma-separated strings as list[str]."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            raise


class _CsvEnvSource(_CsvFallbackMixin, EnvSettingsSource):
    pass


class _CsvDotEnvSource(_CsvFallbackMixin, DotEnvSettingsSource):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

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

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        **kwargs: Any,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # secrets_settings was renamed to file_secret_settings in pydantic-settings 2.14
        file_secret_settings = kwargs.get("file_secret_settings") or kwargs.get("secrets_settings")
        return (
            init_settings,
            _CsvEnvSource(settings_cls),
            _CsvDotEnvSource(settings_cls),
            *(([file_secret_settings]) if file_secret_settings else []),
        )


settings = Settings()  # type: ignore[call-arg]  # fields populated from .env at runtime
