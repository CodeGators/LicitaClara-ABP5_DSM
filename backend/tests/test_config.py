import pytest
from licita_backend.core.config import Settings
from pydantic import ValidationError


def test_missing_database_configuration_fails_early(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_configuration_does_not_expose_password():
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url="mysql://user:sensitive_password@localhost/db")
    assert "sensitive_password" not in str(error.value)


def test_database_url_is_masked_in_settings(settings):
    assert "test_password_do_not_leak" not in repr(settings)


@pytest.mark.parametrize("origin", ["*", "https://example.com/path", "javascript:alert(1)"])
def test_invalid_cors_origin_is_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:pass@localhost/test",
            cors_allowed_origins=[origin],
        )
