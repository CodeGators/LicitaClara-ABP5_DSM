"""Reconciliação do recorte, concentração com denominador completo e versão explícita."""

from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
import test_consultas as shared
from licita_backend.models import analysis as a
from licita_backend.models import procurement as p
from licita_backend.repositories.visao import concentration

query_database = shared.query_database
populated = shared.populated
query_client = shared.query_client


def test_known_hhi_and_missing_totals_are_not_partial_or_zero():
    x, y = uuid4(), uuid4()
    rows = [
        {"fornecedor_id": x, "valor_total_homologado": Decimal(75)},
        {"fornecedor_id": y, "valor_total_homologado": Decimal(25)},
    ]
    assert concentration(rows, x)["hhi"] == Decimal("0.625")
    assert concentration(rows, x)["participacao"] == Decimal("0.75")
    rows[1]["valor_total_homologado"] = None
    assert concentration(rows, x)["hhi"] is None
    assert concentration(rows, x)["participacao"] is None
    assert concentration(rows, x)["soma_valores_conhecidos"] == 75
    rows[0]["valor_total_homologado"] = Decimal(0)
    rows[1]["valor_total_homologado"] = Decimal(0)
    assert concentration(rows, x)["hhi"] is None


def test_dashboard_ranking_suppliers_same_universe_no_join_multiplication(query_client):
    client, data = query_client
    params = {"base_id": data["base"]}
    dashboard = client.get("/api/v1/visao/painel", params=params)
    assert dashboard.status_code == 200, dashboard.text
    summary = dashboard.json()["resumo"]
    assert (
        summary["itens"],
        summary["processos"],
        summary["fornecedores"],
        summary["resultados"],
        summary["contratos_vinculados"],
    ) == (2, 1, 2, 3, 1)
    assert summary["valor_homologado"] == "0.60000001"
    assert summary["nao_analisados"] == 2 and summary["analisados"] == 0
    assert sum(r["itens"] for r in dashboard.json()["evolucao"]) == 2
    assert sum(r["itens"] for r in dashboard.json()["distribuicao"]) == 0
    ranking = client.get("/api/v1/visao/ranking", params=params).json()
    suppliers = client.get("/api/v1/visao/fornecedores", params=params).json()
    assert ranking["resumo"] == summary == suppliers["resumo"]
    assert sum(Decimal(s["valor_homologado"]) for s in suppliers["dados"]) == Decimal(
        summary["valor_homologado"]
    )
    detail = client.get("/api/v1/visao/fornecedores/" + data["supplier"], params=params).json()
    assert detail["fornecedor"]["compras_com_resultado"] == 1
    assert detail["fornecedor"]["contratos_vinculados"] == 0
    assert detail["itens"]["total"] == 1
    assert abs(Decimal(detail["relacoes"][0]["hhi"]) - Decimal("0.5")) < Decimal("0.00000001")
    assert (
        client.get(
            "/api/v1/visao/ranking", params={**params, "pagina": 2, "tamanho_pagina": 1}
        ).json()["dados"][0]["id"]
        != client.get(
            "/api/v1/visao/ranking", params={**params, "pagina": 1, "tamanho_pagina": 1}
        ).json()["dados"][0]["id"]
    )
    assert client.get("/api/v1/visao/painel").status_code == 422
    assert (
        client.get("/api/v1/visao/painel", params={**params, "prioridade": "alta"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/visao/painel",
            params={**params, "homologacao_inicio": "2026-09-30", "homologacao_fim": "2026-09-01"},
        ).status_code
        == 422
    )


def test_unknown_values_and_date_filters_reconcile(query_client):
    client, data = query_client
    params = {"base_id": data["base"]}
    with data["engine"].begin() as cn:
        cn.execute(
            p.resultados_itens.update()
            .where(
                p.resultados_itens.c.base_id == UUID(data["base"]),
                p.resultados_itens.c.fornecedor_id == UUID(data["other_supplier"]),
                p.resultados_itens.c.cancelado.is_(False),
            )
            .values(valor_total_homologado=None)
        )
    summary = client.get("/api/v1/visao/painel", params=params).json()["resumo"]
    assert (
        summary["valor_homologado"] is None and summary["soma_valores_conhecidos"] == "0.30000001"
    )
    detail = client.get("/api/v1/visao/fornecedores/" + data["supplier"], params=params).json()
    assert detail["relacoes"][0]["hhi"] is None
    filtered = {**params, "homologacao_fim": "2026-09-12"}
    assert (
        client.get("/api/v1/visao/painel", params=filtered).json()["resumo"]["valor_homologado"]
        == "0.30000001"
    )
    assert (
        client.get("/api/v1/visao/ranking", params={**params, "busca": "100%"}).json()["total"] == 1
    )
    assert (
        client.get("/api/v1/visao/ranking", params={**params, "busca": "ausente"}).json()["total"]
        == 0
    )


def test_model_selection_published_execution_and_partial_coverage(query_client):
    client, data = query_client
    uid, model = uuid4(), uuid4()
    base = UUID(data["base"])
    with data["engine"].begin() as cn:
        cn.execute(
            a.versoes_modelo.insert().values(
                id=model,
                base_treino_id=base,
                algoritmo="controle",
                versao="teste",
                versao_codigo="fixture",
                chave_artefato="teste",
                sha256_artefato="a" * 64,
            )
        )
        cn.execute(
            a.execucoes_analise.insert().values(
                id=uid,
                base_id=base,
                versao_politica_score="experimental-v1",
                status="concluida",
                concluido_em=sa.func.now(),
                configuracao={"experimental": True, "cobertura": []},
            )
        )
        cn.execute(a.execucoes_modelos.insert().values(execucao_id=uid, modelo_id=model))
        cn.execute(
            a.publicacoes_analise.insert().values(
                nome="experimental:" + str(base), base_id=base, execucao_id=uid
            )
        )
        event = (
            cn.execute(
                sa.select(p.resultados_itens).where(
                    p.resultados_itens.c.item_versao_id == UUID(data["item_version_first"]),
                    p.resultados_itens.c.cancelado.is_(False),
                )
            )
            .mappings()
            .first()
        )
        process = cn.scalar(
            sa.select(p.itens_versoes.c.processo_versao_id).where(
                p.itens_versoes.c.id == event["item_versao_id"]
            )
        )
        cn.execute(
            a.resultados_modelo.insert().values(
                base_id=base,
                execucao_id=uid,
                modelo_id=model,
                processo_versao_id=process,
                item_versao_id=event["item_versao_id"],
                resultado_item_id=event["id"],
                tipo_alvo="resultado",
                score_bruto=Decimal("0.2"),
                score_normalizado=Decimal("88.125"),
                versao_normalizacao="cdf-treino-v1",
            )
        )
    params = {"base_id": str(base), "execucao_id": str(uid), "modelo_id": str(model)}

    tenders = client.get("/api/v1/visao/licitacoes", params=params)
    assert tenders.status_code == 200, tenders.text
    purchase = tenders.json()["dados"][0]
    assert purchase["score_medio"] == "88.125"
    assert purchase["maior_score"] == "88.125"
    assert purchase["itens_com_score"] == 1 and purchase["itens_importados"] == 2
    assert purchase["status_analise"] == "parcial"
    detail = client.get(
        "/api/v1/visao/licitacoes/" + purchase["id"],
        params={**params, "pagina": 2, "tamanho_pagina": 1},
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["licitacao"] == purchase
    assert detail.json()["itens"]["total"] == 2
    assert len(detail.json()["itens"]["dados"]) == 1
    assert client.get("/api/v1/visao/licitacoes/" + str(uuid4()), params=params).status_code == 404
    assert (
        client.get(
            "/api/v1/visao/licitacoes", params={**params, "modelo_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/visao/licitacoes", params={**params, "base_id": data["old"]}
        ).status_code
        == 404
    )

    body = client.get("/api/v1/visao/painel", params=params)
    assert body.status_code == 200, body.text
    assert body.json()["resumo"]["parcial"] == 1
    assert sum(r["itens"] for r in body.json()["distribuicao"]) == 1
    row = client.get("/api/v1/visao/ranking", params={**params, "analise": "parcial"}).json()[
        "dados"
    ][0]
    assert (
        row["indice_experimental"] == "88.125"
        and row["resultados_analisados"] == 1
        and row["resultados_ativos"] == 2
    )
    assert (
        client.get(
            "/api/v1/visao/ranking", params={**params, "modelo_id": str(uuid4())}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/visao/ranking", params={**params, "execucao_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert (
        client.get("/api/v1/visao/ranking", params={**params, "base_id": data["old"]}).status_code
        == 404
    )


def test_supplier_filter_retains_cowinners_in_denominator(query_client):
    client, data = query_client
    with data["engine"].begin() as cn:
        cn.execute(
            p.resultados_itens.update()
            .where(
                p.resultados_itens.c.base_id == UUID(data["base"]),
                p.resultados_itens.c.cancelado.is_(True),
            )
            .values(cancelado=False, valor_total_homologado=Decimal("0.1"))
        )
    params = {"base_id": data["base"], "fornecedor_id": data["supplier"]}
    detail = client.get("/api/v1/visao/fornecedores/" + data["supplier"], params=params).json()
    assert (
        detail["resumo"]["fornecedores"] == 1
        and detail["resumo"]["fornecedores_no_denominador"] == 2
    )
    assert detail["itens"]["total"] == 1
    assert abs(Decimal(detail["relacoes"][0]["hhi"]) - Decimal("0.625")) < Decimal("0.000001")
    assert client.get("/api/v1/visao/fornecedores", params=params).json()["total"] == 1


def test_same_organ_id_with_different_snapshot_names_is_one_universe(query_client):
    client, data = query_client
    with data["engine"].begin() as cn:
        process = (
            cn.execute(
                sa.select(p.processos_versoes).where(
                    p.processos_versoes.c.base_id == UUID(data["base"]),
                    p.processos_versoes.c.processo_id == UUID(data["second"]),
                )
            )
            .mappings()
            .one()
        )
        identity = cn.execute(
            p.itens_processo.insert()
            .values(processo_id=UUID(data["second"]), chave_oficial="outro-processo")
            .returning(p.itens_processo.c.id)
        ).scalar_one()
        item = dict(
            cn.execute(
                sa.select(p.itens_versoes).where(
                    p.itens_versoes.c.id == UUID(data["item_version_first"])
                )
            )
            .mappings()
            .one()
        )
        item.update(
            id=uuid4(),
            item_id=identity,
            processo_id=UUID(data["second"]),
            processo_versao_id=process["id"],
        )
        cn.execute(p.itens_versoes.insert().values(**item))
        event = dict(
            cn.execute(
                sa.select(p.resultados_itens).where(
                    p.resultados_itens.c.item_versao_id == UUID(data["item_version_first"]),
                    p.resultados_itens.c.cancelado.is_(False),
                )
            )
            .mappings()
            .first()
        )
        event.update(id=uuid4(), item_versao_id=item["id"], chave_origem="novo-controlado")
        cn.execute(p.resultados_itens.insert().values(**event))
    detail = client.get(
        "/api/v1/visao/fornecedores/" + data["supplier"], params={"base_id": data["base"]}
    ).json()
    assert len(detail["relacoes"]) == 1
    assert detail["relacoes"][0]["compras_com_resultado"] == 2
    assert detail["relacoes"][0]["orgao_nome"] == "Órgão novo"


def test_resource_limit_is_explicit_instead_of_silent_partial_data(query_client, monkeypatch):
    client, data = query_client
    monkeypatch.setattr("licita_backend.repositories.visao.LIMIT", 1)
    response = client.get("/api/v1/visao/painel", params={"base_id": data["base"]})
    assert response.status_code == 503
    assert response.json()["erro"]["codigo"] == "recorte_excede_limite"
