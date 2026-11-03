from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    collector_database_url: SecretStr
    storage_backend: Literal["local", "s3"] = "local"
    storage_root: Path = Path("data/objects")
    collector_temp_dir: Path = Path("data/tmp/collector")
    collector_extract_dir: Path = Path("data/extracted")
    collector_timeout: int = Field(default=30, ge=1, le=60)
    collector_attempts: int = Field(default=3, ge=1, le=5)
    collector_max_download_bytes: int = Field(default=100 * 1024**2, ge=1, le=1024**3)
    collector_max_uncompressed_bytes: int = Field(default=2 * 1024**3, ge=1)
    collector_max_members: int = Field(default=32, ge=1, le=1000)
    collector_max_compression_ratio: int = Field(default=200, ge=1)
    object_storage_endpoint: str | None = None
    object_storage_bucket: str | None = None
    object_storage_access_key_id: SecretStr | None = None
    object_storage_secret_access_key: SecretStr | None = None

    @field_validator("collector_database_url")
    @classmethod
    def database(cls, value):
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and url.host and url.database
        except Exception:
            valid = False
        if not valid:
            raise ValueError("COLLECTOR_DATABASE_URL deve apontar para PostgreSQL via psycopg")
        return value

    @model_validator(mode="after")
    def s3_configuration(self):
        if self.storage_backend == "s3":
            if not all(
                [
                    self.object_storage_bucket,
                    self.object_storage_access_key_id,
                    self.object_storage_secret_access_key,
                ]
            ):
                raise ValueError("S3 requer bucket e credenciais próprias")
            if self.object_storage_endpoint and not self.object_storage_endpoint.startswith(
                "https://"
            ):
                raise ValueError("Endpoint de objetos deve usar HTTPS")
        return self
