from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    processing_database_url: SecretStr
    storage_backend: str = "local"
    storage_root: Path = Path("data/objects")
    processing_work_dir: Path = Path("data/processing")
    processing_batch_size: int = Field(default=500, ge=1, le=2000)
    processing_max_file_bytes: int = 100 * 1024**2
    processing_max_uncompressed_bytes: int = 2 * 1024**3
    object_storage_endpoint: str | None = None
    object_storage_bucket: str | None = None
    object_storage_access_key_id: SecretStr | None = None
    object_storage_secret_access_key: SecretStr | None = None

    @field_validator("processing_database_url")
    @classmethod
    def database(cls, value):
        url = make_url(value.get_secret_value())
        if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
            raise ValueError("PROCESSING_DATABASE_URL deve usar PostgreSQL/psycopg")
        return value
