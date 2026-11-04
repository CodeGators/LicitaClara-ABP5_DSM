"""Equivalência de formato não pode apagar cor, especificação ou embalagem."""

from decimal import Decimal

import pytest
from licita_ml.catalog.rules import description, grouping


def row(**changes):
    return {
        "catalogo": "000123",
        "descricao": "CANETA ESFEROGRÁFICA, MATERIAL: PLÁSTICO, COR: AZUL",
        "descricao_detalhada": "Caneta Esferográfica material: plástico, cor: azul",
        "unidade_fornecimento_sigla": "UN",
        "capacidade": Decimal(0),
        "unidade_medida_sigla": None,
        **changes,
    }


def test_attribute_order_spacing_accents_and_case_are_grouped():
    a = grouping(row())[0]
    b = grouping(row(descricao_detalhada="CANETA ESFEROGRAFICA, COR: AZUL; MATERIAL: PLASTICO"))[0]
    assert a == b
    assert (
        grouping(row(descricao_detalhada="Caneta Esferográfica cor: preta, material: plástico"))[0]
        != a
    )


def test_measurement_spacing_does_not_create_another_product():
    a = description("Fita, largura: 48mm, comprimento: 50m", "FITA, LARGURA: 48 MM")
    b = description("fita comprimento: 50 m; largura: 48 mm", "FITA, LARGURA: 48 MM")
    assert a == b
    assert description("fita comprimento: 50 m; largura: 24 mm", "FITA, LARGURA: 48 MM") != a


@pytest.mark.parametrize(
    "changes",
    [
        {"catalogo": "000124"},
        {"descricao_detalhada": "Caneta material: metal, cor: azul"},
        {
            "descricao_detalhada": (
                "Caneta Esferográfica material: plástico, cor: azul, exigência: ponta 0,7 mm"
            )
        },
        {
            "unidade_fornecimento_sigla": "CX",
            "capacidade": Decimal(50),
            "unidade_medida_sigla": "UN",
        },
    ],
)
def test_commercial_differences_are_not_merged(changes):
    assert grouping(row(**changes))[0] != grouping(row())[0]


def test_unit_alias_and_single_unit_sentinels_are_compatible_without_conversion():
    a = grouping(row())[0]
    assert (
        grouping(
            row(unidade_fornecimento_sigla="UNIDADE", capacidade=None, unidade_medida_sigla="UN")
        )[0]
        == a
    )
    assert grouping(row(capacidade=Decimal(1), unidade_medida_sigla="UN"))[0] == a
    box = grouping(
        row(unidade_fornecimento_sigla="CX", capacidade=Decimal(50), unidade_medida_sigla="UN")
    )[0]
    assert (
        box
        == grouping(
            row(
                unidade_fornecimento_sigla="CAIXA",
                capacidade=Decimal("50.00"),
                unidade_medida_sigla="UNIDADE",
            )
        )[0]
    )
    assert (
        box
        != grouping(
            row(unidade_fornecimento_sigla="CX", capacidade=Decimal(100), unidade_medida_sigla="UN")
        )[0]
    )


def test_free_text_and_numeric_qualifiers_are_preserved():
    assert description("Computador 16GB RAM SSD512GB") != description("Computador 8GB RAM SSD512GB")
    assert description("Papel 1,5 metros") != description("Papel 15 metros")
    assert description("caneta cor: azul, cor: preta") != description("caneta cor: azul")


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"catalogo": None}, "CATALOGO_AUSENTE_OU_INVALIDO"),
        ({"descricao_detalhada": None}, "ESPECIFICACAO_DETALHADA_AUSENTE"),
        ({"unidade_fornecimento_sigla": None}, "UNIDADE_FORNECIMENTO_AUSENTE"),
        ({"unidade_fornecimento_sigla": "CX", "capacidade": None}, "CAPACIDADE_EMBALAGEM_AUSENTE"),
    ],
)
def test_missing_comparability_remains_explicit(changes, reason):
    assert grouping(row(**changes)) == (None, reason)


def test_catalog_attributes_are_not_erased_by_short_detailed_description():
    blue = row(descricao_detalhada="Caneta")
    red = row(
        descricao_detalhada="Caneta",
        descricao="CANETA ESFEROGRAFICA, MATERIAL: PLASTICO, COR: VERMELHA",
    )
    assert grouping(blue)[0] != grouping(red)[0]


def test_micro_units_and_mathematical_qualifiers_are_not_dropped():
    assert description("Filtro 5 µm") != description("Filtro 5 m")
    assert description("Capacidade ≥ 5 kg") != description("Capacidade 5 kg")


@pytest.mark.parametrize("unit", ["KG", "G", "L", "ML", "M", "M2", "M3"])
def test_basic_measured_units_are_not_rejected_as_boxes_without_capacity(unit):
    plain = row(unidade_fornecimento_sigla=unit, capacidade=None, unidade_medida_sigla=None)
    a = grouping(plain)[0]
    assert a is not None
    assert grouping(dict(plain, capacidade=Decimal(1), unidade_medida_sigla=unit))[0] == a
    assert grouping(row(unidade_fornecimento_sigla="CX", capacidade=None))[0] is None


def test_kg_and_g_are_not_converted_or_merged():
    kg = grouping(row(unidade_fornecimento_sigla="KG", capacidade=Decimal(0)))[0]
    grams = grouping(row(unidade_fornecimento_sigla="G", capacidade=Decimal(0)))[0]
    assert kg is not None and grams is not None and kg != grams


def test_bounded_text_cache_does_not_change_grouping_or_depend_on_prices(monkeypatch):
    from licita_ml.catalog import rules

    original = grouping(row())[0]
    assert grouping(row(preco_unitario=999, quantidade=10))[0] == original
    assert rules._text.cache_info().maxsize == 32768
    monkeypatch.setattr(rules, "_text", rules._text.__wrapped__)
    assert grouping(row())[0] == original


@pytest.mark.parametrize(
    "detail",
    [
        "CANETA ESFEROGRAFICA MATERIAL PLASTICO, COR AZUL",
        "CANETA ESFEROGRAFICA, CORAZUL; MATERIALPLASTICO",
    ],
)
def test_exact_catalog_copy_without_colons_is_grouped(detail):
    assert grouping(row(descricao_detalhada=detail))[0] == grouping(row())[0]


@pytest.mark.parametrize(
    "detail",
    [
        "CANETA ESFEROGRAFICA MATERIAL PLASTICO, COR PRETA",
        "CANETA ESFEROGRAFICA MATERIAL PLASTICO, COR AZUL, GARANTIA 5 ANOS",
        "CANETA ESFEROGRAFICA COR AZUL",
    ],
)
def test_incomplete_or_different_catalog_copy_remains_separate(detail):
    assert grouping(row(descricao_detalhada=detail))[0] != grouping(row())[0]


def test_catalog_copy_keeps_numeric_values_and_spaces_in_values():
    catalog = "FITA, LARGURA: 1,5 MM, MATERIAL: POLI PROPILENO"
    original = grouping(row(descricao=catalog, descricao_detalhada=catalog))[0]
    assert (
        grouping(
            row(descricao=catalog, descricao_detalhada="FITA LARGURA1,5 MM, MATERIALPOLI PROPILENO")
        )[0]
        == original
    )
    for detail in (
        "FITA LARGURA15 MM, MATERIALPOLI PROPILENO",
        "FITA LARGURA1,5 MM, MATERIALPOLIPROPILENO",
    ):
        assert grouping(row(descricao=catalog, descricao_detalhada=detail))[0] != original
