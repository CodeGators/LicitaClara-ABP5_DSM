"""Consultas HTTP reais sob o papel de API em schema isolado no banco *_test."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from licita_backend.db.permissions import apply_permissions, bootstrap_roles, ident
from licita_backend.db.session import build_session_factory, get_session
from licita_backend.main import create_app
from licita_backend.models import Base
from licita_backend.models import collection as c
from licita_backend.models import complementary as k
from licita_backend.models import procurement as p
from sqlalchemy.exc import OperationalError


def add(connection, table, **values):
    return connection.execute(table.insert().values(**values).returning(table.c.id)).scalar_one()


@pytest.fixture
def query_database(integration_engine):
    schema = "test_queries_" + uuid4().hex
    with integration_engine.begin() as connection:
        connection.exec_driver_sql(f"CREATE SCHEMA {ident(schema)}")
    engine = sa.create_engine(
        integration_engine.url, connect_args={"options": f"-c search_path={schema}"}
    )
    reader = None
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as cn:
            bootstrap_roles(cn, schema)
            apply_permissions(cn, schema)
        reader = sa.create_engine(
            integration_engine.url,
            connect_args={
                "options": f"-c search_path={schema} -c role=licita_api",
            },
        )
        yield engine, reader
    finally:
        if reader is not None:
            reader.dispose()
        engine.dispose()
        with integration_engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {ident(schema)} CASCADE")


@pytest.fixture
def populated(query_database):
    engine, reader = query_database
    with engine.begin() as cn:

        def base(version, day, status="validada"):
            return add(
                cn,
                c.versoes_base,
                versao=version,
                versao_transformador="teste",
                versao_codigo="teste",
                chave_manifesto=version,
                sha256_manifesto="a" * 64,
                periodo_inicio=date(2026, 9, 1),
                periodo_fim=date(2026, 9, 30),
                status=status,
                criado_em=datetime(2026, 10, day, tzinfo=timezone.utc),
            )

        old, current, rejected = (
            base("antiga", 1),
            base("atual", 2),
            base("rejeitada", 3, "rejeitada"),
        )
        org = add(cn, p.orgaos, fonte="teste", chave_oficial="001", nome="Nome atual cadastro")
        old_org = add(cn, p.orgaos, fonte="teste", chave_oficial="002", nome="Órgão antigo")
        modality = add(cn, p.modalidades, fonte="teste", codigo="05", nome="Pregão")
        old_modality = add(cn, p.modalidades, fonte="teste", codigo="06", nome="Dispensa")
        supplier = add(
            cn,
            p.fornecedores,
            fonte="teste",
            tipo_identificacao="CNPJ",
            identificacao="00000000000100",
            nome="Cadastro fornecedor",
        )
        other_supplier = add(
            cn,
            p.fornecedores,
            fonte="teste",
            tipo_identificacao="CNPJ",
            identificacao="00000000000200",
            nome="Cadastro outro",
        )
        first = add(cn, p.processos, fonte="teste", chave_oficial="000001")
        second = add(cn, p.processos, fonte="teste", chave_oficial="000002")

        def snapshot(base_id, process_id, title, amount, organization=org, mod=modality, day=1):
            return add(
                cn,
                p.processos_versoes,
                base_id=base_id,
                processo_id=process_id,
                orgao_id=organization,
                orgao_nome="Órgão novo" if day == 2 else "Órgão snapshot",
                modalidade_id=mod,
                codigo_unidade="000001",
                numero_compra="00001",
                numero_processo="PROCESSO-001" if process_id == first else "PROCESSO-002",
                ano=2026,
                objeto=title,
                situacao="homologado",
                valor_homologado=Decimal(amount),
                valor_estimado=Decimal("300"),
                data_publicacao=date(2026, 9, day),
            )

        current_pv = snapshot(current, first, "Material A", "200.00000001")
        snapshot(current, second, "Material B", "100", day=2)
        old_pv = snapshot(old, first, "Objeto antigo", "999", old_org, old_modality)
        item_ids = [
            add(cn, p.itens_processo, processo_id=first, chave_oficial=str(n)) for n in (1, 2)
        ]

        def item(base_id, pv, item_id, number, description, unit):
            return add(
                cn,
                p.itens_versoes,
                base_id=base_id,
                item_id=item_id,
                processo_id=first,
                processo_versao_id=pv,
                numero_item=number,
                descricao=description,
                unidade_medida=unit,
                quantidade=Decimal("3.00000001"),
            )

        i1 = item(current, current_pv, item_ids[0], "1", "Borracha 100% original", "UN")
        i2 = item(current, current_pv, item_ids[1], "2", "Outro material", None)
        old_iv = item(old, old_pv, item_ids[0], "1", "Item antigo", "CX")

        def result(base_id, iv, who, name, sequence, amount, day, cancelled=False):
            return add(
                cn,
                p.resultados_itens,
                base_id=base_id,
                item_versao_id=iv,
                fornecedor_id=who,
                fornecedor_nome=name,
                sequencial_resultado=sequence,
                chave_origem=str(uuid4()),
                situacao="Informado",
                cancelado=cancelled,
                quantidade_homologada=Decimal("1"),
                valor_unitario_homologado=Decimal(amount),
                valor_total_homologado=Decimal(amount),
                data_resultado=date(2026, 9, day),
            )

        result(current, i1, supplier, "Fornecedor Alfa", 1, "0.10000001", 10)
        result(current, i1, supplier, "Fornecedor Alfa", 2, "0.20000000", 12)
        result(current, i1, other_supplier, "Fornecedor Beta", 3, "9999", 20, True)
        result(current, i2, other_supplier, "Fornecedor Beta", 1, "0.30000000", 15)
        result(old, old_iv, supplier, "Nome antigo", 1, "500", 1)
        for n, participant in enumerate((supplier, other_supplier), 1):
            add(
                cn,
                k.participacoes,
                base_id=current,
                processo_versao_id=current_pv,
                item_versao_id=i1,
                fornecedor_id=participant,
                fonte="teste",
                chave_origem=f"participante-{n}",
            )
        for n in (1, 2):
            add(
                cn,
                k.documentos,
                base_id=current,
                processo_versao_id=current_pv,
                fonte="teste",
                chave_origem=f"doc{n}",
                sequencial_documento=n,
                titulo=f"Anexo {n}",
                url_origem=f"https://example.test/{n}",
                ativo=True,
            )
        contract = add(cn, k.contratos, fonte="teste", chave_oficial="contrato-1")
        contract_version = add(
            cn, k.contratos_versoes, base_id=current, contrato_id=contract, numero_contrato="1"
        )
        add(
            cn,
            k.contratos_processos,
            base_id=current,
            contrato_versao_id=contract_version,
            processo_versao_id=current_pv,
            tipo_chave_vinculo="idCompra",
            chave_vinculo="000001",
        )
        add(
            cn,
            k.documentos,
            base_id=current,
            contrato_versao_id=contract_version,
            fonte="teste",
            chave_origem="contrato-doc",
            sequencial_documento=1,
            titulo="Contrato",
            url_origem="https://example.test/contrato",
            ativo=True,
        )
    return {
        "engine": engine,
        "reader": reader,
        "base": str(current),
        "old": str(old),
        "rejected": str(rejected),
        "first": str(first),
        "second": str(second),
        "org": str(org),
        "supplier": str(supplier),
        "other_supplier": str(other_supplier),
        "modality": str(modality),
        "item_first": str(item_ids[0]),
        "item_second": str(item_ids[1]),
        "item_version_first": str(i1),
        "item_version_second": str(i2),
    }


@pytest.fixture
def query_client(populated, settings):
    factory = build_session_factory(populated["reader"])
    app = create_app(settings)

    def session():
        with factory() as value:
            yield value

    app.dependency_overrides[get_session] = session
    with TestClient(app) as client:
        yield client, populated


@pytest.mark.integration
def test_latest_valid_base_snapshots_and_decimal_precision(query_client):
    client, data = query_client
    response = client.get("/api/v1/processos", params={"ordenacao": "valor_desc"})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["base_id"] == data["base"]
    assert body["meta"]["total"] == 2
    process = body["dados"][0]
    assert process["chave_oficial"] == "000001"
    assert process["valor_homologado_processo"] == "200.00000001"
    assert process["valor_homologado_itens_recorte"] == "0.60000001"
    assert process["quantidade_itens_recorte"] == 2
    assert process["data_resultado"] is None
    assert process["ultima_data_resultado_itens_recorte"] == "2026-09-15"
    assert len(process["fornecedores"]) == 2
    assert process["analise"] == {"status": "nao_publicada", "score": None, "prioridade": None}
    old = client.get(f"/api/v1/processos/{data['first']}", params={"base_id": data["old"]}).json()
    assert old["processo"]["objeto"] == "Objeto antigo"
    assert old["processo"]["valor_homologado_itens_recorte"] == "500.00000000"


@pytest.mark.integration
def test_filters_use_same_active_result_for_supplier_and_dates(query_client):
    client, data = query_client
    params = {
        "fornecedor_id": data["supplier"],
        "orgao_id": data["org"],
        "modalidade_id": data["modality"],
        "homologacao_inicio": "2026-09-15",
        "homologacao_fim": "2026-09-15",
    }
    assert client.get("/api/v1/processos", params=params).json()["meta"]["total"] == 0
    params["fornecedor_id"] = data["other_supplier"]
    assert client.get("/api/v1/processos", params=params).json()["meta"]["total"] == 1
    params["homologacao_inicio"] = params["homologacao_fim"] = "2026-09-20"
    assert client.get("/api/v1/processos", params=params).json()["meta"]["total"] == 0


@pytest.mark.integration
def test_value_scope_and_literal_search(query_client):
    client, _ = query_client
    params = {"valor_minimo": "0.60000001", "valor_maximo": "0.60000001"}
    assert client.get("/api/v1/processos", params=params).json()["meta"]["total"] == 0
    params["escopo_valor"] = "itens_recorte"
    assert client.get("/api/v1/processos", params=params).json()["meta"]["total"] == 1
    for search in ("alfa", "borracha", "100%", "PROCESSO-001"):
        assert (
            client.get("/api/v1/processos", params={"busca": search}).json()["meta"]["total"] == 1
        )
    assert client.get("/api/v1/processos", params={"busca": "' OR 1=1 --"}).json()["dados"] == []


@pytest.mark.integration
def test_pagination_and_lookups_are_scoped_and_deduplicated(query_client):
    client, data = query_client
    page1 = client.get("/api/v1/processos?tamanho_pagina=1&pagina=1").json()
    page2 = client.get("/api/v1/processos?tamanho_pagina=1&pagina=2").json()
    assert page1["meta"]["total_paginas"] == 2
    assert page1["dados"][0]["id"] != page2["dados"][0]["id"]
    assert client.get("/api/v1/processos?pagina=99").json()["dados"] == []
    orgs = client.get("/api/v1/orgaos").json()
    assert orgs["meta"]["total"] == 1
    assert orgs["dados"][0]["id"] == data["org"]
    assert orgs["dados"][0]["nome"] == "Órgão novo"
    assert client.get("/api/v1/modalidades").json()["meta"]["total"] == 1
    assert client.get("/api/v1/orgaos?busca=inexistente").json()["dados"] == []


@pytest.mark.integration
def test_items_and_documents_do_not_multiply_rows_or_amounts(query_client):
    client, data = query_client
    items = client.get(f"/api/v1/processos/{data['first']}/itens").json()
    assert items["meta"]["total"] == 2
    assert len(items["dados"][0]["resultados"]) == 3
    assert items["dados"][0]["resultados"][2]["cancelado"] is True
    assert items["dados"][1]["unidade_medida"] is None
    assert items["dados"][0]["quantidade"] == "3.00000001"
    documents = client.get(f"/api/v1/processos/{data['first']}/documentos").json()
    assert documents["meta"]["total"] == 3
    assert all(d["binario_registrado"] is False for d in documents["dados"])
    assert all("chave_objeto" not in d for d in documents["dados"])
    assert any(d["contrato_versao_id"] is not None for d in documents["dados"])
    assert client.get(f"/api/v1/processos/{data['second']}/documentos").json()["dados"] == []
    assert client.get(f"/api/v1/processos/{data['second']}/itens").json()["dados"] == []
    body = client.get(f"/api/v1/processos/{data['first']}").json()["processo"]
    assert body["valor_homologado_itens_recorte"] == "0.60000001"


@pytest.mark.integration
def test_base_status_counts_only_selected_snapshot(query_client):
    client, _ = query_client
    status = client.get("/api/v1/base/status").json()
    coverage = status["cobertura"]
    assert coverage["processos"] == 2 and coverage["itens"] == 2
    assert coverage["resultados_ativos"] == 3 and coverage["resultados_cancelados"] == 1
    assert coverage["fornecedores_resultados_ativos"] == 2
    assert coverage["documentos"] == 3
    assert coverage["itens_sem_unidade"] == 1
    assert status["ultima_importacao_concluida_em"] is None


@pytest.mark.integration
def test_missing_or_unvalidated_base_and_unknown_process(query_client):
    client, data = query_client
    for path in (
        f"/api/v1/processos?base_id={data['rejected']}",
        f"/api/v1/processos?base_id={uuid4()}",
        f"/api/v1/processos/{uuid4()}",
        f"/api/v1/processos/{uuid4()}/itens",
        f"/api/v1/processos/{uuid4()}/documentos",
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["erro"]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.integration
def test_no_base_is_explicit_and_does_not_look_like_database_outage(query_database, settings):
    _, reader = query_database
    app = create_app(settings)
    factory = build_session_factory(reader)

    def session():
        with factory() as value:
            yield value

    app.dependency_overrides[get_session] = session
    with TestClient(app) as client:
        response = client.get("/api/v1/base/status")
        assert response.status_code == 200
        assert response.json()["status"] == "sem_base"
        assert response.json()["cobertura"] is None
        assert client.get("/api/v1/processos").status_code == 404
        assert client.get("/api/v1/itens").status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"pagina": 0},
        {"tamanho_pagina": 101},
        {"base_id": "invalid"},
        {"ordenacao": "score"},
        {"valor_minimo": "NaN"},
        {"valor_minimo": "-1"},
        {"valor_minimo": "0.000000001"},
        {"valor_minimo": "2", "valor_maximo": "1"},
        {"homologacao_inicio": "2026-09-30", "homologacao_fim": "2026-09-01"},
        {"homologacao_inicio": "ontem"},
        {"desconhecido": "x"},
        {"busca": "a" * 201},
    ],
)
def test_invalid_queries_are_rejected_before_database_access(settings, params):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/processos", params=params)
    assert response.status_code == 422
    assert response.json()["erro"]["codigo"] == "parametros_invalidos"
    assert "input" not in response.text


def test_database_outage_is_sanitized(settings, caplog):
    app = create_app(settings)

    def unavailable():
        raise OperationalError("PRIVATE_SQL", {}, Exception("PRIVATE_PASSWORD"))

    app.dependency_overrides[get_session] = unavailable
    with TestClient(app) as client:
        response = client.get("/api/v1/processos")
    assert response.status_code == 503
    assert response.json()["erro"]["codigo"] == "banco_indisponivel"
    assert "PRIVATE_" not in response.text + caplog.text


def test_openapi_documents_decimal_strings_and_uniform_errors(settings):
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()
    model = schema["components"]["schemas"]["ProcessSummary"]["properties"]
    assert {"type": "string"} in model["valor_homologado_processo"]["anyOf"]
    operation = schema["paths"]["/api/v1/processos"]["get"]
    for code in ("404", "422", "500", "503"):
        assert operation["responses"][code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }


def test_unexpected_errors_are_sanitized_and_preserve_request_id(settings, caplog):
    app = create_app(settings)

    def broken():
        raise RuntimeError("PRIVATE_INTERNAL_DETAIL")

    app.dependency_overrides[get_session] = broken
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/processos")
    assert response.status_code == 500
    assert response.json()["erro"]["request_id"] == response.headers["X-Request-ID"]
    assert "PRIVATE_" not in response.text + caplog.text


@pytest.mark.integration
def test_unknown_result_amount_does_not_become_a_partial_total(query_client):
    client, data = query_client
    with data["engine"].begin() as connection:
        connection.execute(
            p.resultados_itens.update()
            .where(
                p.resultados_itens.c.base_id == data["base"],
                p.resultados_itens.c.fornecedor_id == data["supplier"],
                p.resultados_itens.c.sequencial_resultado == 1,
            )
            .values(valor_total_homologado=None)
        )
    process = client.get(f"/api/v1/processos/{data['first']}").json()["processo"]
    assert process["valor_homologado_itens_recorte"] is None
    assert process["resultados_sem_valor_total_recorte"] == 1
    assert process["valor_homologado_processo"] == "200.00000001"


@pytest.mark.integration
def test_item_contract_keeps_process_context_and_all_results(query_client):
    client, data = query_client
    page = client.get("/api/v1/itens?ordenacao=descricao_asc&tamanho_pagina=1").json()
    assert page["meta"]["total"] == 2
    assert page["meta"]["total_paginas"] == 2
    item = page["dados"][0]
    assert item["id"] == data["item_first"]
    assert item["item_versao_id"] == data["item_version_first"]
    assert item["chave_oficial"] == "1"
    assert item["quantidade"] == "3.00000001"
    assert item["valor_unitario_estimado"] is None
    assert item["valor_homologado_item"] == "0.30000001"
    assert item["resultados_ativos"] == 2
    assert item["resultados_sem_valor_total"] == 0
    assert item["ultima_data_resultado"] == "2026-09-12"
    assert len(item["resultados"]) == 3
    assert item["resultados"][2]["cancelado"] is True
    assert item["processo"]["id"] == data["first"]
    assert item["processo"]["chave_oficial"] == "000001"
    assert item["processo"]["orgao_nome"] == "Órgão snapshot"
    assert item["analise"] == {"status": "nao_publicada", "score": None, "prioridade": None}
    detail = client.get(f"/api/v1/itens/{item['id']}", params={"base_id": data["base"]})
    assert detail.status_code == 200
    assert detail.json() == {"base_id": data["base"], "item": item}
    process = client.get(f"/api/v1/processos/{item['processo']['id']}").json()["processo"]
    assert process["processo_versao_id"] == item["processo"]["processo_versao_id"]
    assert process["valor_homologado_processo"] == "200.00000001"
    assert process["valor_homologado_itens_recorte"] == "0.60000001"
    legacy = client.get(f"/api/v1/processos/{data['first']}/itens").json()["dados"][0]
    for field, value in legacy.items():
        assert item[field] == value


@pytest.mark.integration
def test_item_ids_are_stable_but_snapshots_and_results_are_base_specific(query_client):
    client, data = query_client
    current = client.get(f"/api/v1/itens/{data['item_first']}").json()["item"]
    old_response = client.get(
        f"/api/v1/itens/{data['item_first']}", params={"base_id": data["old"]}
    ).json()
    old = old_response["item"]
    assert old_response["base_id"] == data["old"]
    assert old["id"] == current["id"]
    assert old["item_versao_id"] != current["item_versao_id"]
    assert old["processo"]["processo_versao_id"] != current["processo"]["processo_versao_id"]
    assert old["unidade_medida"] == "CX"
    assert old["valor_homologado_item"] == "500.00000000"
    assert [r["fornecedor_nome"] for r in old["resultados"]] == ["Nome antigo"]
    assert client.get("/api/v1/itens", params={"base_id": data["old"]}).json()["meta"]["total"] == 1
    missing = client.get(f"/api/v1/itens/{data['item_second']}", params={"base_id": data["old"]})
    assert missing.status_code == 404
    assert missing.json()["erro"]["codigo"] == "item_nao_encontrado"


@pytest.mark.integration
def test_item_filters_do_not_match_a_supplier_on_another_item_or_result(query_client):
    client, data = query_client
    params = {
        "processo_id": data["first"],
        "orgao_id": data["org"],
        "modalidade_id": data["modality"],
        "fornecedor_id": data["supplier"],
        "homologacao_inicio": "2026-09-15",
        "homologacao_fim": "2026-09-15",
    }
    assert client.get("/api/v1/itens", params=params).json()["dados"] == []
    params["fornecedor_id"] = data["other_supplier"]
    items = client.get("/api/v1/itens", params=params).json()["dados"]
    assert [i["id"] for i in items] == [data["item_second"]]
    params["homologacao_inicio"] = params["homologacao_fim"] = "2026-09-20"
    assert client.get("/api/v1/itens", params=params).json()["dados"] == []
    for field in ["processo_id", "orgao_id", "modalidade_id", "fornecedor_id"]:
        assert client.get("/api/v1/itens", params={field: str(uuid4())}).json()["dados"] == []
    with data["engine"].begin() as cn:
        # Outro vencedor ativo no mesmo item, com data diferente dos resultados Alfa.
        add(
            cn,
            p.resultados_itens,
            base_id=data["base"],
            item_versao_id=data["item_version_first"],
            fornecedor_id=data["other_supplier"],
            fornecedor_nome="Outro vencedor",
            sequencial_resultado=4,
            chave_origem="resultado-adicional",
            situacao="Informado",
            cancelado=False,
            valor_total_homologado=Decimal("1"),
            data_resultado=date(2026, 9, 15),
        )
    no_match = {
        "fornecedor_id": data["supplier"],
        "homologacao_inicio": "2026-09-15",
        "homologacao_fim": "2026-09-15",
    }
    assert client.get("/api/v1/itens", params=no_match).json()["dados"] == []
    selected = client.get("/api/v1/itens", params={"fornecedor_id": data["supplier"]}).json()
    assert selected["dados"][0]["valor_homologado_item"] == "1.30000001"
    assert len(selected["dados"][0]["resultados"]) == 4
    assert selected["dados"][0]["ultima_data_resultado"] == "2026-09-15"


@pytest.mark.integration
def test_item_search_catalog_filters_and_amount_pagination(query_client):
    client, data = query_client
    for search in ["BORRACHA", "100%", "Alfa"]:
        body = client.get("/api/v1/itens", params={"busca": search}).json()
        assert [i["id"] for i in body["dados"]] == [data["item_first"]]
    for search in ["100_", "' OR 1=1 --", "inexistente"]:
        assert client.get("/api/v1/itens", params={"busca": search}).json()["dados"] == []
    assert client.get("/api/v1/itens?busca=%20%20").json()["meta"]["total"] == 2
    params = {"valor_minimo": "0.30000001", "valor_maximo": "0.30000001"}
    assert client.get("/api/v1/itens", params=params).json()["dados"][0]["id"] == data["item_first"]
    assert client.get("/api/v1/itens?valor_minimo=200").json()["dados"] == []
    page1 = client.get("/api/v1/itens?ordenacao=valor_desc&tamanho_pagina=1").json()
    page2 = client.get("/api/v1/itens?ordenacao=valor_desc&tamanho_pagina=1&pagina=2").json()
    assert page1["dados"][0]["id"] == data["item_first"]
    assert page2["dados"][0]["id"] == data["item_second"]
    beyond = client.get("/api/v1/itens?pagina=99").json()
    assert beyond["dados"] == [] and beyond["meta"]["total"] == 2
    with data["engine"].begin() as cn:
        catalog = add(cn, p.itens_catalogo, catalogo="CATMAT", codigo="000123", descricao="Teste")
        cn.execute(
            p.itens_versoes.update()
            .where(p.itens_versoes.c.id == data["item_version_first"])
            .values(catalogo_id=catalog)
        )
    catalog_params = {"catalogo": "CATMAT", "codigo_catalogo": "000123"}
    match = client.get("/api/v1/itens", params=catalog_params).json()["dados"]
    assert len(match) == 1 and match[0]["codigo_catalogo"] == "000123"
    assert client.get("/api/v1/itens?codigo_catalogo=123").json()["dados"] == []
    assert client.get("/api/v1/itens?catalogo=CATSER").json()["dados"] == []


@pytest.mark.integration
def test_item_unknown_amount_empty_results_and_known_zero_are_distinct(query_client):
    client, data = query_client
    with data["engine"].begin() as cn:
        cn.execute(
            p.resultados_itens.update()
            .where(
                p.resultados_itens.c.item_versao_id == data["item_version_first"],
                p.resultados_itens.c.sequencial_resultado == 1,
            )
            .values(valor_total_homologado=None)
        )
        cn.execute(
            p.resultados_itens.update()
            .where(p.resultados_itens.c.item_versao_id == data["item_version_second"])
            .values(valor_total_homologado=Decimal("0"), data_resultado=None)
        )
    item = client.get(f"/api/v1/itens/{data['item_first']}").json()["item"]
    assert item["valor_homologado_item"] is None
    assert item["resultados_sem_valor_total"] == 1
    zero = client.get(f"/api/v1/itens/{data['item_second']}").json()["item"]
    assert zero["valor_homologado_item"] == "0.00000000"
    assert zero["ultima_data_resultado"] is None
    assert [i["id"] for i in client.get("/api/v1/itens?ordenacao=valor_asc").json()["dados"]] == [
        data["item_second"],
        data["item_first"],
    ]
    assert [i["id"] for i in client.get("/api/v1/itens?valor_minimo=0").json()["dados"]] == [
        data["item_second"]
    ]
    assert client.get("/api/v1/itens?homologacao_inicio=2026-09-13").json()["dados"] == []
    with data["engine"].begin() as cn:
        cn.execute(
            p.resultados_itens.update()
            .where(p.resultados_itens.c.item_versao_id == data["item_version_second"])
            .values(cancelado=True)
        )
    empty = client.get(f"/api/v1/itens/{data['item_second']}").json()["item"]
    assert empty["valor_homologado_item"] is None
    assert empty["resultados_ativos"] == 0 and empty["resultados_sem_valor_total"] == 0
    assert len(empty["resultados"]) == 1 and empty["resultados"][0]["cancelado"] is True
    # Ambos os totais ficaram desconhecidos: desempatar por UUID, não por ordem de inserção.
    assert [i["id"] for i in client.get("/api/v1/itens?ordenacao=valor_asc").json()["dados"]] == (
        sorted([data["item_first"], data["item_second"]])
    )


@pytest.mark.integration
def test_item_errors_and_validated_empty_base(query_client):
    client, data = query_client
    for params in [{"base_id": data["rejected"]}, {"base_id": str(uuid4())}]:
        assert client.get("/api/v1/itens", params=params).status_code == 404
    missing = client.get(f"/api/v1/itens/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["erro"]["codigo"] == "item_nao_encontrado"
    assert missing.json()["erro"]["request_id"] == missing.headers["X-Request-ID"]
    with data["engine"].begin() as cn:
        empty = add(
            cn,
            c.versoes_base,
            versao="vazia",
            versao_transformador="teste",
            versao_codigo="teste",
            chave_manifesto="vazia.json",
            sha256_manifesto="a" * 64,
            periodo_inicio=date(2026, 9, 1),
            periodo_fim=date(2026, 9, 30),
            status="validada",
        )
    page = client.get("/api/v1/itens", params={"base_id": str(empty)}).json()
    assert page["dados"] == [] and page["meta"]["total"] == 0


@pytest.mark.integration
def test_item_without_any_results_remains_visible_and_order_is_stable(query_client):
    client, data = query_client
    with data["engine"].begin() as cn:
        identity = add(
            cn,
            p.itens_processo,
            processo_id=data["first"],
            chave_oficial="00003",
        )
        parent = cn.scalar(
            sa.select(p.processos_versoes.c.id).where(
                p.processos_versoes.c.base_id == data["base"],
                p.processos_versoes.c.processo_id == data["first"],
            )
        )
        add(
            cn,
            p.itens_versoes,
            base_id=data["base"],
            item_id=identity,
            processo_id=data["first"],
            processo_versao_id=parent,
            numero_item="00003",
            descricao="Sem resultado",
        )
    item = client.get(f"/api/v1/itens/{identity}").json()["item"]
    assert item["chave_oficial"] == "00003" and item["numero_item"] == "00003"
    assert item["resultados"] == [] and item["valor_homologado_item"] is None
    assert item["resultados_ativos"] == 0 and item["ultima_data_resultado"] is None
    assert item["quantidade"] is None and item["unidade_medida"] is None
    for ordering in ["publicacao_asc", "publicacao_desc"]:
        pages = [
            client.get(
                "/api/v1/itens",
                params={"ordenacao": ordering, "tamanho_pagina": 1, "pagina": n},
            ).json()["dados"][0]["id"]
            for n in [1, 2, 3]
        ]
        assert pages == sorted([data["item_first"], data["item_second"], str(identity)])


@pytest.mark.parametrize(
    "params",
    [
        {"processo_id": "LC-2026-0142"},
        {"escopo_valor": "processo"},
        {"execucao_analise_id": str(uuid4())},
        {"ordenacao": "score_desc"},
        {"valor_minimo": "2", "valor_maximo": "1"},
        {"valor_minimo": "Infinity"},
        {"homologacao_inicio": "2026-09-30", "homologacao_fim": "2026-09-01"},
        {"codigo_catalogo": ""},
        {"pagina": 0},
        {"tamanho_pagina": 101},
    ],
)
def test_invalid_item_filters_are_rejected_before_database_access(settings, params):
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/itens", params=params)
    assert response.status_code == 422
    assert response.json()["erro"]["codigo"] == "parametros_invalidos"


def test_item_openapi_identifies_granularity_and_rejects_fake_path_id(settings):
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()
        assert client.get("/api/v1/itens/LC-2026-0142").status_code == 422
    operation = schema["paths"]["/api/v1/itens"]["get"]
    params = {p["name"] for p in operation["parameters"]}
    assert {"base_id", "processo_id", "fornecedor_id", "codigo_catalogo"} <= params
    assert "escopo_valor" not in params and "execucao_analise_id" not in params
    model = schema["components"]["schemas"]["ItemSummary"]["properties"]
    assert model["processo"] == {"$ref": "#/components/schemas/ItemProcessContext"}
    assert {"type": "string"} in model["valor_homologado_item"]["anyOf"]
    for code in ["404", "422", "500", "503"]:
        assert operation["responses"][code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
