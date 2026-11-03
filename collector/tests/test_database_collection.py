"""Ciclo de coleta usando permissões reais e schema descartável em banco *_test."""

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from licita_backend.db.permissions import apply_permissions, bootstrap_roles, ident
from licita_collector.errors import Busy, InvalidArchive
from licita_collector.http import HttpClient
from licita_collector.repository import Repository
from licita_collector.service import Collector
from licita_collector.source import Scope
from licita_shared.storage.local import LocalObjectStorage

pytestmark = pytest.mark.integration


def test_operational_offline_history_repeat_and_resume(database, settings, tmp_path):
    from licita_collector.api import JsonScope
    from licita_collector.history import CachedHistory

    repository, admin = database
    scope = JsonScope(
        "material_historico_api",
        date(2026, 9, 1),
        {"catalogo": "486374", "inicio": "2025-10-01", "fim": "2026-09-30"},
    )
    raw = json.dumps(
        {"resultado": [{"codigoItemCatalogo": 486374}], "totalRegistros": 1, "totalPaginas": 1}
    ).encode()
    path = tmp_path / "historico_486374_pagina_1.json"
    path.write_bytes(raw)
    path.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "url": scope.url(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "status": 200,
            }
        )
    )
    service = Collector(
        settings,
        repository,
        LocalObjectStorage(settings.storage_root),
        CachedHistory(settings, scope, tmp_path),
    )
    first = service.collect(scope)
    second = service.collect(scope)
    assert second["arquivo_id"] == first["arquivo_id"] and second["reutilizado"]
    assert repository.execution(first["execucao_id"]) == scope
    assert service.collect(scope, first["execucao_id"])["reutilizado"]
    with admin.connect() as cn:
        assert cn.scalar(sa.text("SELECT count(*) FROM arquivos_coletados")) == 1
        assert cn.scalar(sa.text("SELECT count(*) FROM processos_versoes")) == 0


@pytest.fixture
def database():
    url = os.getenv("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada")
    assert sa.engine.make_url(url).database.endswith("_test")
    admin = sa.create_engine(url)
    schema = "test_collector_" + uuid4().hex
    with admin.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {ident(schema)}")
    engine = sa.create_engine(url, connect_args={"options": f"-c search_path={schema}"})
    try:
        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.connect() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        with engine.begin() as connection:
            bootstrap_roles(connection, schema)
            apply_permissions(connection, schema)
        restricted = sa.create_engine(
            url,
            pool_size=2,
            max_overflow=0,
            connect_args={"options": f"-c search_path={schema} -c role=licita_collector"},
        )
        try:
            yield Repository(restricted), engine
        finally:
            restricted.dispose()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {ident(schema)} CASCADE")
        admin.dispose()


def test_repeat_version_resume_and_lock(database, source, settings):
    repository, admin = database
    base, state = source
    objects = LocalObjectStorage(settings.storage_root)
    service = Collector(
        settings, repository, objects, HttpClient(settings, sleep=lambda _: None), base
    )
    scope = Scope("compra", date(2026, 9, 1))
    with repository.locked(scope):
        with pytest.raises(Busy):
            with repository.locked(scope):
                pass
    first = service.collect(scope)
    repeat = service.collect(scope)
    assert repeat["reutilizado"]
    assert repeat["arquivo_id"] == first["arquivo_id"]
    resumed = service.collect(scope, first["execucao_id"])
    assert resumed["reutilizado"]
    state["etag"] = '"v2"'
    state["body"] = state["body"].replace(b"Teste", b"Outro")
    # Esta substituição invalida CRC; nenhum objeto ou metadado pode ser publicado.
    with pytest.raises(InvalidArchive):
        service.collect(scope)
    import io
    from zipfile import ZipFile

    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("dados.csv", "id;nome\n1;Corrigido\n")
    state["body"] = buffer.getvalue()
    with admin.connect() as connection:
        failed = connection.scalar(sa.text("SELECT id FROM execucoes_coleta WHERE status='falhou'"))
    changed = service.collect(scope, failed)
    assert changed["arquivo_id"] != first["arquivo_id"]
    service.reprocess(first["arquivo_id"], unpack=True)
    with admin.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM arquivos_coletados")) == 2
        assert connection.scalar(sa.text("SELECT count(*) FROM execucoes_coleta")) == 3
        assert connection.scalar(sa.text("SELECT count(*) FROM execucoes_arquivos")) == 3
        assert connection.scalar(sa.text("SELECT count(*) FROM processos")) == 0
    assert len(list(settings.storage_root.rglob("*.zip"))) == 2
