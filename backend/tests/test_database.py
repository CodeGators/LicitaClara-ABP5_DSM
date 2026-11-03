import pytest
from fastapi.testclient import TestClient
from licita_backend.core.config import Settings
from licita_backend.db.session import build_session_factory, transaction
from licita_backend.main import create_app
from sqlalchemy import func, insert, select

pytestmark = pytest.mark.integration


def test_transaction_commits_success_and_rolls_back_failure(integration_engine, transaction_table):
    factory = build_session_factory(integration_engine)
    with transaction(factory) as session:
        session.execute(insert(transaction_table).values(id=1))
    with pytest.raises(RuntimeError):
        with transaction(factory) as session:
            session.execute(insert(transaction_table).values(id=2))
            raise RuntimeError("force rollback")
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(transaction_table)) == 1


def test_closing_uncommitted_session_rolls_back(integration_engine, transaction_table):
    factory = build_session_factory(integration_engine)
    with factory() as session:
        session.execute(insert(transaction_table).values(id=3))
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(transaction_table)) == 0


def test_readiness_with_real_postgres(integration_engine, tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=integration_engine.url.render_as_string(hide_password=False),
        storage_root=tmp_path,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/ready").json() == {
            "status": "ok",
            "service": "licita-backend",
            "database": "ok",
        }
