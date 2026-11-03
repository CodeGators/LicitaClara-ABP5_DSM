import os
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from licita_backend.core.config import Settings
from licita_backend.db.session import build_engine
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.engine import make_url


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://test:test_password_do_not_leak@127.0.0.1:1/missing",
        db_connect_timeout=1,
        storage_root=tmp_path / "objects",
        cors_allowed_origins=["http://localhost:5173"],
    )


@pytest.fixture
def integration_engine():
    url = os.getenv("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para executar integração PostgreSQL")
    if not make_url(url).database.endswith("_test"):
        pytest.fail("Use banco descartável com nome terminado em _test")
    engine = build_engine(Settings(_env_file=None, app_env="test", database_url=url))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def transaction_table(integration_engine):
    metadata = MetaData()
    table = Table(
        f"test_transaction_{uuid4().hex}", metadata, Column("id", Integer, primary_key=True)
    )
    metadata.create_all(integration_engine)
    try:
        yield table
    finally:
        metadata.drop_all(integration_engine)
