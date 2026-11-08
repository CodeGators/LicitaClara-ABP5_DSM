"""Equivalências exatas não autorizam inferir peso nem tamanho de embalagem."""

from decimal import Decimal

import pytest
from licita_ml.catalog.rules import grouping
from licita_ml.units import exact_values, measurement, operational_matches


@pytest.mark.parametrize(
    "supply,capacity,measure,base,factor",
    [
        ("KG", 0, None, "kg", "1"),
        ("GRAMAS", 0, None, "kg", "0.001"),
        ("ML", 0, None, "l", "0.001"),
        ("LITRO", 0, None, "l", "1"),
        ("PACOTE", 500, "G", "kg", "0.500"),
        ("Caixa", 12, "UN", "un", "12"),
        ("FR", 100, "ML", "l", "0.100"),
        ("UN", 1, "KG", "kg", "1"),
        ("m²", 0, None, "m2", "1"),
        ("Tonelada", 0, None, "kg", "1000"),
    ],
)
def test_explicit_dimensions_and_capacities(supply, capacity, measure, base, factor):
    info, reason = measurement(supply, capacity, measure)
    assert reason is None
    assert info["unidade_base"] == base and Decimal(info["fator_base"]) == Decimal(factor)
    values = exact_values("12.50", "4", info)
    assert Decimal(values["preco_por_unidade_base"]) * Decimal(values["quantidade_base"]) == 50


@pytest.mark.parametrize(
    "supply,capacity,measure",
    [
        ("KG", 0, "UN"),
        ("L", 1, "KG"),
        ("KG", 5, "UN"),
        ("CX", None, None),
        ("PCT", 0, "G"),
        ("CX", 12, None),
        ("DESCONHECIDA", 12, "UN"),
        ("UN", Decimal("NaN"), None),
        ("FR", -1, "ML"),
    ],
)
def test_missing_or_contradictory_metadata_are_not_comparable(supply, capacity, measure):
    assert measurement(supply, capacity, measure)[0] is None


def test_pack_size_must_be_proved_by_operational_label():
    info, _ = measurement("PCT", 500, "G")
    assert operational_matches("Pacote 500 g", info)
    assert operational_matches("Pacote com 500 gramas", info)
    assert not operational_matches("Pacote", info)
    assert not operational_matches("Pacote 1 kg", info)
    assert operational_matches("Pacote 0,5 kg", info)
    assert not operational_matches("Quilograma", info)
    assert operational_matches("Ampola 2ML", measurement("AM", 2, "ML")[0])
    assert operational_matches("Quilograma 1 KG", measurement("KG", 0, None)[0])
    assert not operational_matches("Unidade", measurement("KG", 0, None)[0])


def test_count_is_never_converted_to_weight_and_commercial_groups_stay_distinct():
    base = {
        "catalogo": "464400",
        "descricao": "Fruta, tipo: maçã",
        "descricao_detalhada": "Fruta tipo: maçã",
        "capacidade": 0,
    }
    kg = grouping({**base, "unidade_fornecimento_sigla": "KG"})[0]
    un = grouping({**base, "unidade_fornecimento_sigla": "UN"})[0]
    g = grouping({**base, "unidade_fornecimento_sigla": "G"})[0]
    assert len({kg["id"], un["id"], g["id"]}) == 3
    assert kg["especificacao"]["unidade_preco"]["unidade_preco"] == "kg"


def test_audit_keeps_all_rows_and_does_not_invent_conversion(tmp_path, monkeypatch):
    from licita_ml import units_audit

    (tmp_path / "manifesto.json").write_text("{}")
    rows = []
    for unit_name in ["KG", "UN", "CX"]:
        rows.append(
            {
                "id_registro": unit_name,
                "catalogo": "464400",
                "descricao": "Fruta, tipo: maçã",
                "descricao_detalhada": "Fruta tipo: maçã",
                "unidade_fornecimento_sigla": unit_name,
                "unidade_fornecimento_nome": None,
                "capacidade": 0,
                "unidade_medida_sigla": None,
                "preco_unitario": Decimal(2),
                "quantidade": Decimal(3),
                "membro": "a.csv",
                "linha": 1,
            }
        )
    monkeypatch.setattr(units_audit, "records", lambda *args: iter(rows))
    report = units_audit.audit(tmp_path, tmp_path / "out")
    assert report["referencias"] == 3
    assert report["motivos"]["CAPACIDADE_EMBALAGEM_AUSENTE"] == 1
    assert report["catalogos_com_unidades_distintas"]["464400"] == ["kg", "un"]
    assert not report["dados_originais_alterados"]


def test_generic_unit_with_packaging_description_needs_structured_content():
    from licita_ml.grouped.temporal import structural_blockers

    source = {
        "catalogo": "445484",
        "descricao": "Agua mineral, tipo: sem gas, embalagem: plastico",
        "descricao_detalhada": "Agua mineral tipo: sem gas, embalagem: plastico",
        "unidade_fornecimento_sigla": "UN",
        "capacidade": 0,
    }
    value = grouping(source)[0]["especificacao"]
    assert "CONTEUDO_EMBALAGEM_NAO_CONFIRMADO" in structural_blockers(value)
    source.update(unidade_fornecimento_sigla="GRF", capacidade=500, unidade_medida_sigla="ML")
    value = grouping(source)[0]["especificacao"]
    assert "CONTEUDO_EMBALAGEM_NAO_CONFIRMADO" not in structural_blockers(value)
