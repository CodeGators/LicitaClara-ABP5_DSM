"""Sinalização, contagens e totais pertencem ao fornecedor do resultado."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import test_consultas as shared
from licita_backend.repositories.produtos import price_review_result_ids
from licita_backend.repositories.visao import ViewRepository
from licita_backend.schemas.visao import SupplierFilters
from test_produtos import item as sample_product

query_database = shared.query_database
populated = shared.populated
query_client = shared.query_client


def supplier_sample():
    a, b, organ = uuid4(), uuid4(), uuid4()
    rows = [sample_product(price) for price in ["1", "1", "10"]]
    for row in rows:
        row["processo"].update(
            id=uuid4(),
            processo_versao_id=uuid4(),
            orgao_id=organ,
            orgao_nome="Órgão",
            data_publicacao=date(2026, 9, 1),
        )
        row["scores"] = []
        row["resultados"][0].update(fornecedor_id=a, fornecedor_nome="Fornecedor A")
    shared_item = rows[-1]
    expensive = shared_item["resultados"][0]
    expensive.update(fornecedor_id=b, fornecedor_nome="Fornecedor B")
    cheap = {
        **expensive,
        "id": uuid4(),
        "fornecedor_id": a,
        "fornecedor_nome": "Fornecedor A",
        "valor_unitario_homologado": Decimal(1),
        "valor_total_homologado": Decimal(1),
    }
    shared_item["resultados"].append(cheap)
    shared_item["scores"] = [
        {"resultado_item_id": expensive["id"], "score_bruto": Decimal("0.9")},
        {"resultado_item_id": cheap["id"], "score_bruto": Decimal("0.4")},
    ]
    shared_item["medida_if"] = Decimal("0.9")
    return a, b, rows


def test_supplier_does_not_inherit_score_or_review_from_co_winner():
    a, b, items = supplier_sample()
    reviews = price_review_result_ids(items)
    rows = ViewRepository(None).supplier_rows(
        items, [], [], SupplierFilters(base_id=uuid4()), reviews
    )
    first = next(r for r in rows if r["id"] == a)
    second = next(r for r in rows if r["id"] == b)
    assert first["medida_if"] == Decimal("0.4")
    assert first["requer_validacao"] is False
    assert first["sinalizacao"] == "menor_anomalia"
    assert (first["itens_com_medida_if"], first["itens"]) == (1, 3)
    assert first["valor_homologado"] == 3
    assert second["medida_if"] == Decimal("0.9")
    assert second["requer_validacao"] is True
    assert second["sinalizacao"] == "requer_validacao"
    assert second["valor_homologado"] == 10


def test_name_and_signal_select_full_suppliers_before_pagination(monkeypatch):
    a, b, items = supplier_sample()
    repository = ViewRepository(None)
    monkeypatch.setattr(
        repository,
        "supplier_dataset",
        lambda _: ({"universo": {}}, items, [], [], price_review_result_ids(items)),
    )
    params = SupplierFilters(base_id=uuid4(), busca="Fornecedor A")
    result = repository.suppliers(params)
    assert result["total"] == 1
    assert result["dados"][0]["valor_homologado"] == "3"
    assert result["dados"][0]["compras_com_resultado"] == 3
    params = params.model_copy(
        update={
            "busca": None,
            "sinalizacao": ["menor_anomalia", "requer_validacao"],
            "tamanho_pagina": 1,
        }
    )
    first, second = (
        repository.suppliers(params),
        repository.suppliers(params.model_copy(update={"pagina": 2})),
    )
    assert first["total"] == second["total"] == 2
    assert {first["dados"][0]["id"], second["dados"][0]["id"]} == {str(a), str(b)}
    detail = repository.supplier(params.model_copy(update={"sinalizacao": ["maior_anomalia"]}), a)
    shared = next(r for r in detail["itens"]["dados"] if r["id"] == str(items[-1]["id"]))
    assert shared["medida_if"] == "0.4"
    assert shared["requer_validacao"] is False
    assert len(shared["scores"]) == 1
    assert shared["scores"][0]["resultado_item_id"] == str(items[-1]["resultados"][-1]["id"])


def test_supplier_api_filters_name_and_signals_and_keeps_detail_independent(query_client):
    client, data = query_client
    params = {"base_id": data["base"]}
    response = client.get("/api/v1/visao/fornecedores", params=params)
    assert response.status_code == 200, response.text
    row = response.json()["dados"][0]
    filtered = client.get("/api/v1/visao/fornecedores", params={**params, "busca": row["nome"]})
    assert filtered.status_code == 200, filtered.text
    found = next(r for r in filtered.json()["dados"] if r["id"] == row["id"])
    assert found == row
    detail = client.get(
        "/api/v1/visao/fornecedores/" + row["id"],
        params={**params, "busca": "ausente", "sinalizacao": "maior_anomalia"},
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["fornecedor"] == row
    assert (
        client.get(
            "/api/v1/visao/fornecedores", params={**params, "sinalizacao": "invalido"}
        ).status_code
        == 422
    )
