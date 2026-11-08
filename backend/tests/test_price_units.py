"""Unidade da mediana vem da assinatura treinada, nunca do item atual."""

from licita_backend.repositories.analises import price_unit


def test_median_unit_is_explicit_for_legacy_kg_and_packaging():
    assert (
        price_unit({"assinatura_catalogo": {"unidade": "kg", "capacidade": "0", "medida": "kg"}})[
            "unidade_preco"
        ]
        == "kg"
    )
    assert (
        price_unit({"assinatura_catalogo": {"unidade": "pct", "capacidade": "500", "medida": "g"}})[
            "unidade_preco"
        ]
        == "pct de 500 g"
    )
    assert price_unit({}) is None
    assert (
        price_unit({"assinatura_catalogo": {"unidade": "kg", "capacidade": "0", "medida": "un"}})
        is None
    )


def test_new_validated_measurement_passes_through_without_inference():
    info = {"unidade_preco": "kg", "versao": "unidades-preco-v1"}
    assert price_unit({"assinatura_catalogo": {"unidade_preco": info}}) == info
