"""Configuração validada; executar comandos a partir da raiz do repositório."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_env: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr
    db_connect_timeout: int = Field(default=3, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=3000, ge=100, le=30000)
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=0, ge=0, le=10)
    cors_allowed_origins: list[str] = Field(default_factory=list)
    storage_root: Path = Path("data/objects")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and url.host and url.database
        except Exception:
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL deve apontar para PostgreSQL via postgresql+psycopg")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        from urllib.parse import urlsplit

        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS_ALLOWED_ORIGINS exige origens HTTP(S) sem caminho")
        return values
