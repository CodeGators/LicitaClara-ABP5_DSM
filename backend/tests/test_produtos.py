"""Estatísticas operacionais: grupos completos, unidades separadas e extremos visíveis."""

from decimal import Decimal
from uuid import uuid4

import test_consultas as shared
from licita_backend.repositories.produtos import group_products

query_database = shared.query_database
populated = shared.populated
query_client = shared.query_client


def item(price, *, description="Água mineral", unit="Copo 200 ML", code="445484", identifier=None):
    uid = identifier or uuid4()
    return {
        "id": uid,
        "descricao": description,
        "catalogo": "CATMAT",
        "codigo_catalogo": code,
        "unidade_medida": unit,
        "numero_item": "1",
        "processo": {"numero_compra": str(uid)},
        "status_analise": "nao_analisados",
        "medida_if": None,
        "resultados": [
            {
                "id": uuid4(),
                "cancelado": False,
                "valor_unitario_homologado": Decimal(price) if price is not None else None,
                "valor_total_homologado": Decimal(price) if price is not None else None,
                "quantidade_homologada": Decimal("9999"),
            }
        ],
    }


def test_operational_prices_group_across_purchases_and_do_not_use_training_median():
    rows = [item(p) for p in ["0.6", "0.8", "0.8", "30185.2"]]
    for row in rows:
        row["scores"] = [{"atributos": {"comparacao": {"mediana": "12345"}}}]
    result = group_products(rows)
    assert len(result) == 1
    group = result[0]
    assert group["preco_minimo"] == Decimal("0.6")
    assert group["preco_maximo"] == Decimal("30185.2")
    assert group["mediana"] == Decimal("0.8")
    assert group["quantidade_registros"] == 4
    assert len(group["itens"]) == 4
    assert group["requer_validacao"] is True
    assert group["medida_if"] is None  # prices work without any ML analysis
    assert group_products(list(reversed(rows))) == result


def test_different_units_capacities_specifications_and_codes_do_not_merge():
    rows = [
        item("1"),
        item("2", unit="Garrafa 500 ML"),
        item("3", unit="Copo 300 ML"),
        item("4", description="Água com gás"),
        item("5", code="445485"),
    ]
    assert len(group_products(rows)) == 5
    assert len(group_products([item("1", unit=None), item("2", unit=None)])) == 2


def test_missing_prices_cancelled_results_and_duplicate_events_are_not_imputed():
    a, b = item("2"), item(None)
    a["resultados"].append(
        {
            **a["resultados"][0],
            "id": uuid4(),
            "cancelado": True,
            "valor_unitario_homologado": Decimal("99999"),
        }
    )
    a["resultados"].append(a["resultados"][0])
    result = group_products([a, b])[0]
    assert result["mediana"] == result["preco_maximo"] == Decimal(2)
    assert result["quantidade_registros"] == 1
    assert result["registros_sem_preco"] == 1
    assert result["requer_validacao"] is False
    empty = group_products([b])[0]
    assert empty["preco_minimo"] is empty["preco_maximo"] is empty["mediana"] is None


def test_validation_threshold_and_even_median_are_exact():
    assert group_products([item("100"), item("100"), item("600")])[0]["requer_validacao"] is False
    assert (
        group_products([item("100"), item("100"), item("600.00000001")])[0]["requer_validacao"]
        is True
    )
    assert group_products([item("0.00000001"), item("0.00000002")])[0]["mediana"] == Decimal(
        "0.000000015"
    )


def test_products_api_is_paginated_and_exposes_current_base_origin(query_client):
    client, data = query_client
    response = client.get(
        "/api/v1/visao/produtos", params={"base_id": data["base"], "tamanho_pagina": 1}
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["dados"]) == 1
    assert payload["universo"]["estatisticas"] == "precos_unitarios_da_base_atual"
    all_rows = client.get("/api/v1/visao/produtos", params={"base_id": data["base"]}).json()[
        "dados"
    ]
    assert sum(r["quantidade_registros"] for r in all_rows) == 3
    for row in all_rows:
        assert "orgao_nome" not in row
        assert "preco_minimo" in row and "mediana" in row


def test_attribute_order_is_ignored_but_all_specifications_are_preserved():
    a = item("0.7", description="Água mineral tipo: sem gás, material embalagem: plástico")
    b = item("0.8", description="Água mineral material embalagem: plástico, tipo: sem gás")
    c = item("1.6", description="Água mineral material embalagem: plástico, tipo: com gás")
    for row in (a, b, c):
        row["descricao_catalogo"] = "Água mineral, tipo: sem gás"
    groups = group_products([a, b, c])
    assert len(groups) == 2
    assert sorted(r["quantidade_registros"] for r in groups) == [1, 2]
    assert next(r for r in groups if r["quantidade_registros"] == 2)["mediana"] == Decimal("0.75")
