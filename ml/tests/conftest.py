import csv
import hashlib
import io
import json
import os
from datetime import date
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from licita_backend.db.permissions import apply_permissions, bootstrap_roles, ident
from licita_ml.config import Settings
from licita_ml.repository import Repository
from licita_shared.storage.local import LocalObjectStorage


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        processing_database_url="postgresql+psycopg://test:test@localhost/test_test",
        storage_root=tmp_path / "objects",
        processing_work_dir=tmp_path / "work",
        processing_batch_size=2,
    )


@pytest.fixture
def database():
    url = os.getenv("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL ausente")
    assert sa.engine.make_url(url).database.endswith("_test")
    admin = sa.create_engine(url)
    schema = "test_processing_" + uuid4().hex
    with admin.begin() as c:
        c.exec_driver_sql(f"CREATE SCHEMA {ident(schema)}")
    engine = sa.create_engine(url, connect_args={"options": f"-c search_path={schema}"})
    try:
        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.connect() as c:
            cfg.attributes["connection"] = c
            command.upgrade(cfg, "head")
        with engine.begin() as c:
            bootstrap_roles(c, schema)
            apply_permissions(c, schema)
        restricted = sa.create_engine(
            url,
            pool_size=1,
            max_overflow=0,
            connect_args={"options": f"-c search_path={schema} -c role=licita_processing"},
        )
        try:
            yield Repository(restricted), engine
        finally:
            restricted.dispose()
    finally:
        engine.dispose()
        with admin.begin() as c:
            c.exec_driver_sql(f"DROP SCHEMA {ident(schema)} CASCADE")
        admin.dispose()


@pytest.fixture
def sources(database, settings):
    _, engine = database
    objects = LocalObjectStorage(settings.storage_root)
    ids = []

    def add(kind, rows, source="comprasgov", query=None):
        if kind.endswith("_api") or kind.startswith("documentos_") or kind == "contrato_pncp":
            body = json.dumps(
                {
                    "schema": "licita-json-v1",
                    "kind": kind,
                    "query": query or {},
                    "paginas": [{"pagina": 1, "url": "https://example.test", "resultado": rows}],
                }
            ).encode()
            key = f"raw/{uuid4()}.json"
            module = f"api/{kind}/{uuid4().hex[:20]}"
        else:
            content = io.StringIO()
            writer = csv.DictWriter(content, fieldnames=list(rows[0]), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
            buffer = io.BytesIO()
            with ZipFile(buffer, "w") as z:
                z.writestr("dados.csv", content.getvalue())
            body = buffer.getvalue()
            key = f"raw/{uuid4()}.zip"
            prefix = (
                "pesquisa_precos"
                if kind == "material"
                else "propostas"
                if kind == "propostas"
                else "pncp"
            )
            module = f"{prefix}/{kind}"
        objects.put(key, io.BytesIO(body))
        uid = uuid4()
        with engine.begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO arquivos_coletados "
                    "(id,fonte,modulo,competencia,url_origem,url_final,"
                    "sha256,tamanho_bytes,chave_objeto) "
                    "VALUES (:id,:fonte,:modulo,:competencia,:url,:url,:sha,:size,:key)"
                ),
                {
                    "id": uid,
                    "fonte": source,
                    "modulo": module,
                    "competencia": date(2026, 9, 1),
                    "url": "https://example.test",
                    "sha": hashlib.sha256(body).hexdigest(),
                    "size": len(body),
                    "key": key,
                },
            )
        ids.append(uid)
        return uid

    purchase = "00000105000012026"
    item = purchase + "00001"
    control = "00000000000100-1-000001/2026"
    material = dict(
        id_compra=purchase,
        id_compra_item=item,
        id_item_compra="000123",
        ni_fornecedor="00000000000200",
        codigo_item_catalogo="486054",
        preco_unitario="0.12345678",
        data_compra="2026-09-15",
        forma="SISRP",
        descricao_item="Borracha",
        nome_fornecedor="Fornecedor teste",
        nome_unidade_fornecimento="UNIDADE",
        sigla_unidade_fornecimento="UN",
        quantidade="5",
        capacidade_unidade_fornecimento="0",
        data_hora_atualizacao_item="2026-09-16 10:00:00",
    )
    add("material", [material])
    add(
        "compra",
        [
            dict(
                id_compra=purchase,
                codigo_orgao="00001",
                orgao_entidade_razao_social="Órgão teste",
                ano_compra_pncp="2026",
                numero_compra="00001",
                objeto_compra="Material escritório",
                data_atualizacao_pncp="2026-09-16 10:00:00",
                unidade_orgao_codigo_unidade="000001",
                numero_controle_PNCP=control,
                valor_total_estimado="1",
                valor_total_homologado="0",
            )
        ],
    )
    add(
        "compra_item",
        [
            dict(
                id_compra=purchase,
                id_compra_item=item,
                numero_item_pncp="1",
                descricao_detalhada="Borracha",
                data_atualizacao_pncp="2026-09-16 10:00:00",
                quantidade="5",
                unidade_medida="UN",
                valor_unitario_estimado="1",
            )
        ],
    )
    add(
        "item_resultado",
        [
            dict(
                id_compra=purchase,
                id_compra_item=item,
                ni_fornecedor="00000000000200",
                sequencial_resultado="1",
                srk_item_resultado="000007",
                data_atualizacao_pncp="2026-09-16 10:00:00",
                nome_razao_social_fornecedor="Fornecedor teste",
                valor_unitario_homologado="0.12345678",
            )
        ],
    )
    proposals = [
        dict(
            id="00001",
            id_compra=purchase,
            id_compra_item=item,
            identificacao_participante="00000000000200",
            valor_proposta_calculado="1",
            classificacao="1",
            data_hora_alteracao="2026-09-16 10:00:00",
            nome_participante="Fornecedor teste",
        )
    ]
    proposals.append(dict(proposals[0], id="00002", classificacao="2"))
    add("propostas", proposals)
    contract_control = "00000000000100-2-000001/2026"
    add(
        "contratos_api",
        [
            dict(
                numeroContrato="00001/2026",
                numeroControlePncpContrato=contract_control,
                idCompra=purchase,
                numeroControlePncpCompra=control,
                valorGlobal="10",
                nomeRazaoSocialFornecedor="Fornecedor teste",
                niFornecedor="00000000000200",
            )
        ],
    )
    add(
        "contrato_pncp",
        [
            dict(
                numeroControlePNCP=contract_control,
                numeroContratoEmpenho="00001",
                numeroControlePncpCompra=control,
                dataAssinatura="2026-09-17",
            )
        ],
        source="pncp",
    )
    add(
        "documentos_compra",
        [dict(sequencialDocumento=1, url="https://pncp.gov.br/example", titulo="Edital")],
        source="pncp",
        query={"cnpj": "00000000000100", "ano": 2026, "sequencial": 1},
    )
    return objects, ids, add, material
