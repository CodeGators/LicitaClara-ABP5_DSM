"""Médias por item, sem zeros imputados e sem encolher compras pelos filtros."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import test_consultas as shared
from licita_backend.repositories.licitacoes import group_purchases
from licita_backend.repositories.visao import ViewRepository
from licita_backend.schemas.visao import ViewFilters

query_database = shared.query_database
populated = shared.populated
query_client = shared.query_client


def sample():
    process = {
        "id": uuid4(),
        "objeto": "Material escolar",
        "numero_compra": "42",
        "orgao_id": uuid4(),
        "orgao_nome": "Escola municipal",
        "modalidade_id": uuid4(),
        "valor_homologado_processo": Decimal("999.00000001"),
        "valor_estimado_processo": None,
    }
    supplier = uuid4()
    items = []
    for n, score in enumerate([Decimal(0), Decimal(1), None]):
        items.append(
            {
                "id": uuid4(),
                "processo": process,
                "descricao": f"Item {n}",
                "medida_if": score,
                "status_analise": "nao_analisados" if score is None else "analisados",
                "resultados": [
                    {
                        "data_resultado": date(2026, 9, n + 1),
                        "fornecedor_id": supplier,
                        "fornecedor_nome": "Fornecedor",
                        "valor_total_homologado": Decimal("0.10000001"),
                    }
                ],
            }
        )
    return process, items, ViewFilters(base_id=uuid4())


def test_mean_equal_weight_includes_real_zero_and_excludes_missing():
    process, items, filters = sample()
    row = group_purchases([process], items, filters)[0]
    assert row["medida_if_media"] == Decimal("0.5")
    assert row["maior_medida_if"] == 1
    assert (row["itens_com_medida_if"], row["itens_importados"], row["itens_sem_medida_if"]) == (
        2,
        3,
        1,
    )
    assert row["status_analise"] == "parcial"
    assert row["valor_homologado"] == Decimal("999.00000001")
    assert row["valores_itens_importados"]["valor_homologado"] == Decimal("0.30000003")
    assert row["itens_oficiais"] is None
    # Amount and number of winners do not weight the already-computed item index.
    items[0]["resultados"] *= 4
    assert group_purchases([process], items, filters)[0]["medida_if_media"] == Decimal("0.5")


def test_search_supplier_date_and_value_select_whole_purchase():
    process, items, filters = sample()
    selection = filters.model_copy(
        update={
            "busca": "Item 1",
            "homologacao_fim": date(2026, 9, 1),
            "fornecedor_id": items[0]["resultados"][0]["fornecedor_id"],
            "valor_minimo": Decimal(999),
        }
    )
    row = group_purchases([process], items, selection)[0]
    assert row["itens_importados"] == 3 and row["medida_if_media"] == Decimal("0.5")
    assert not group_purchases(
        [process], items, selection.model_copy(update={"valor_minimo": Decimal(1000)})
    )
    assert not group_purchases([process], items, selection.model_copy(update={"busca": "ausente"}))
    assert not group_purchases(
        [process], items, selection.model_copy(update={"analise": "analisados"})
    )


def test_empty_purchase_missing_score_and_partially_scored_results():
    process, items, filters = sample()
    row = group_purchases([process], [], filters)[0]
    assert row["medida_if_media"] is None and row["maior_medida_if"] is None
    assert row["itens_importados"] == 0 and row["status_analise"] == "nao_analisados"
    items[0]["status_analise"] = "parcial"
    row = group_purchases([process], items[:1], filters)[0]
    assert row["medida_if_media"] == 0 and row["itens_com_medida_if"] == 1
    assert row["status_analise"] == "parcial" and row["itens_analise_parcial"] == 1
    items[0]["status_analise"] = "analisados"
    assert group_purchases([process], items[:1], filters)[0]["status_analise"] == "analisados"


def test_mean_rounding_and_nulls_last_sort_before_pagination():
    process, items, filters = sample()
    for i, value in zip(items, ["0.1", "0.2", "0.2"], strict=True):
        i["medida_if"] = Decimal(value)
    row = group_purchases([process], items, filters)[0]
    assert row["medida_if_media"] == Decimal("0.166666666667")
    rows = [
        {**row, "id": uuid4(), "medida_if_media": value}
        for value in [None, Decimal(0), Decimal("0.99")]
    ]
    result = ViewRepository(None).page(
        rows, filters.model_copy(update={"tamanho_pagina": 2}), score_key="medida_if_media"
    )
    assert [r["medida_if_media"] for r in result["dados"]] == [Decimal("0.99"), 0]
    assert result["total"] == 3


def test_tender_signal_uses_mean_not_maximum_and_review_overrides_it():
    process, items, filters = sample()
    items[0]["medida_if"], items[1]["medida_if"] = Decimal("0.4"), Decimal("0.8")
    row = group_purchases([process], items, filters)[0]
    assert row["medida_if_media"] == Decimal("0.6")
    assert row["maior_medida_if"] == Decimal("0.8")
    assert row["sinalizacao"] == "anomalia_intermediaria"
    assert row["requer_validacao"] is False
    flagged = group_purchases([process], items, filters, {items[0]["id"]})[0]
    assert flagged["sinalizacao"] == "requer_validacao"
    assert flagged["medida_if_media"] == row["medida_if_media"]
    unrelated = group_purchases([process], items, filters, {uuid4()})[0]
    assert unrelated["requer_validacao"] is False


def test_signal_filter_selects_whole_tender_with_or_semantics():
    from licita_backend.schemas.visao import TenderFilters

    process, items, _ = sample()
    filters = TenderFilters(base_id=uuid4(), sinalizacao=["menor_anomalia", "maior_anomalia"])
    assert not group_purchases([process], items, filters)
    filters = filters.model_copy(
        update={"sinalizacao": ["menor_anomalia", "anomalia_intermediaria"]}
    )
    row = group_purchases([process], items, filters)[0]
    assert row["itens_importados"] == 3
    assert row["medida_if_media"] == Decimal("0.5")
    assert row["sinalizacao"] == "anomalia_intermediaria"


def test_api_signal_filters_do_not_hide_detail_or_shrink_its_items(query_client):
    client, data = query_client
    response = client.get(
        "/api/v1/visao/licitacoes",
        params=[
            ("base_id", data["base"]),
            ("sinalizacao", "sem_analise"),
            ("sinalizacao", "maior_anomalia"),
        ],
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] >= 1
    assert all(r["sinalizacao"] == "sem_analise" for r in payload["dados"])
    row = payload["dados"][0]
    assert row["medida_if_media"] is None
    detail = client.get(
        "/api/v1/visao/licitacoes/" + row["id"],
        params={
            "base_id": data["base"],
            "sinalizacao": "menor_anomalia",
            "tamanho_pagina": 1,
        },
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["licitacao"]["itens_importados"] == row["itens_importados"]
    assert detail.json()["itens"]["total"] == row["itens_importados"]
    assert (
        client.get(
            "/api/v1/visao/licitacoes",
            params={
                "base_id": data["base"],
                "sinalizacao": "invalido",
            },
        ).status_code
        == 422
    )
