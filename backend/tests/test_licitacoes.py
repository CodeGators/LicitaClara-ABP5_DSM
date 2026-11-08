"""Médias por item, sem zeros imputados e sem encolher compras pelos filtros."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from licita_backend.repositories.licitacoes import group_purchases
from licita_backend.repositories.visao import ViewRepository
from licita_backend.schemas.visao import ViewFilters


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
    for n, score in enumerate([Decimal(0), Decimal(100), None]):
        items.append(
            {
                "id": uuid4(),
                "processo": process,
                "descricao": f"Item {n}",
                "indice_experimental": score,
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
    assert row["score_medio"] == Decimal(50)
    assert row["maior_score"] == 100
    assert (row["itens_com_score"], row["itens_importados"], row["itens_sem_score"]) == (2, 3, 1)
    assert row["status_analise"] == "parcial"
    assert row["valor_homologado"] == Decimal("999.00000001")
    assert row["valores_itens_importados"]["valor_homologado"] == Decimal("0.30000003")
    assert row["itens_oficiais"] is None
    # Amount and number of winners do not weight the already-computed item index.
    items[0]["resultados"] *= 4
    assert group_purchases([process], items, filters)[0]["score_medio"] == 50


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
    assert row["itens_importados"] == 3 and row["score_medio"] == 50
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
    assert row["score_medio"] is None and row["maior_score"] is None
    assert row["itens_importados"] == 0 and row["status_analise"] == "nao_analisados"
    items[0]["status_analise"] = "parcial"
    row = group_purchases([process], items[:1], filters)[0]
    assert row["score_medio"] == 0 and row["itens_com_score"] == 1
    assert row["status_analise"] == "parcial" and row["itens_analise_parcial"] == 1
    items[0]["status_analise"] = "analisados"
    assert group_purchases([process], items[:1], filters)[0]["status_analise"] == "analisados"


def test_mean_rounding_and_nulls_last_sort_before_pagination():
    process, items, filters = sample()
    for i, value in zip(items, [1, 2, 2], strict=True):
        i["indice_experimental"] = Decimal(value)
    row = group_purchases([process], items, filters)[0]
    assert row["score_medio"] == Decimal("1.667")
    rows = [
        {**row, "id": uuid4(), "score_medio": value} for value in [None, Decimal(0), Decimal(99)]
    ]
    result = ViewRepository(None).page(
        rows, filters.model_copy(update={"tamanho_pagina": 2}), score_key="score_medio"
    )
    assert [r["score_medio"] for r in result["dados"]] == [99, 0]
    assert result["total"] == 3
