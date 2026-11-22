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


def test_signal_boundaries_and_review_precedence():
    from licita_backend.repositories.produtos import product_signal

    cases = [
        ("0", "menor_anomalia"),
        ("0.499999999999", "menor_anomalia"),
        ("0.50", "anomalia_intermediaria"),
        ("0.699999999999", "anomalia_intermediaria"),
        ("0.70", "maior_anomalia"),
        ("1", "maior_anomalia"),
    ]
    for measure, expected in cases:
        row = {"requer_validacao": False, "medida_if": Decimal(measure)}
        assert product_signal(row) == expected
        assert product_signal({**row, "requer_validacao": True}) == "requer_validacao"
    assert product_signal({"requer_validacao": False, "medida_if": None}) == "sem_analise"
    assert product_signal({"requer_validacao": True, "medida_if": None}) == "requer_validacao"


def test_multi_signal_filter_is_union_before_pagination_and_keeps_full_group_prices(monkeypatch):
    from licita_backend.repositories.produtos import ProductRepository
    from licita_backend.schemas.visao import ProductFilters

    items = []
    for code, score in [("1", "0.49"), ("2", "0.50"), ("3", "0.70"), ("4", None)]:
        row = item("1", code=code)
        row["medida_if"] = Decimal(score) if score else None
        items.append(row)
    for price in ["1", "1", "10"]:
        row = item(price, code="5")
        row["medida_if"] = Decimal("0.9")
        items.append(row)
    repository = ProductRepository(None)
    monkeypatch.setattr(repository, "dataset", lambda _: ({"universo": {}}, items, [], []))
    filters = ProductFilters(
        base_id=uuid4(), sinalizacao=["menor_anomalia", "maior_anomalia"], tamanho_pagina=1
    )
    first = repository.listing(filters)
    second = repository.listing(filters.model_copy(update={"pagina": 2}))
    assert first["total"] == second["total"] == 2
    assert first["total_paginas"] == 2
    assert {first["dados"][0]["sinalizacao"], second["dados"][0]["sinalizacao"]} == {
        "menor_anomalia",
        "maior_anomalia",
    }
    review = repository.listing(filters.model_copy(update={"sinalizacao": ["requer_validacao"]}))
    assert review["total"] == 1
    assert review["dados"][0]["mediana"] == "1"
    assert review["dados"][0]["quantidade_registros"] == 3
    assert repository.listing(filters.model_copy(update={"sinalizacao": []}))["total"] == 5


def test_api_accepts_repeated_signals_and_rejects_unknown_categories(query_client):
    client, data = query_client
    params = [
        ("base_id", data["base"]),
        ("sinalizacao", "sem_analise"),
        ("sinalizacao", "maior_anomalia"),
    ]
    response = client.get("/api/v1/visao/produtos", params=params)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert {r["sinalizacao"] for r in response.json()["dados"]} == {"sem_analise"}
    assert (
        client.get(
            "/api/v1/visao/produtos", params={"base_id": data["base"], "sinalizacao": "invalido"}
        ).status_code
        == 422
    )


def test_review_marks_only_the_occurrence_with_extreme_price():
    from licita_backend.repositories.produtos import price_review_item_ids

    regular_a, regular_b, extreme = item("1"), item("1"), item("10")
    assert price_review_item_ids([regular_a, regular_b, extreme]) == {extreme["id"]}
