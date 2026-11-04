"""Diagnóstico deve preservar granularidade e rejeitar entradas malformadas."""

import csv
import io
import json
from zipfile import ZipFile

import pytest
from licita_ml.diagnostics import diagnose, number_status, records


def archive(folder, kind, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    with ZipFile(folder / f"{kind}_2026_09.csv.zip", "w") as output:
        output.writestr(f"{kind}.csv", buffer.getvalue())


def sources(tmp_path):
    folder = tmp_path / "2026-09"
    folder.mkdir()
    archive(
        folder,
        "compra",
        [
            {"id_compra": "001", "objeto_compra": "versão A"},
            {"id_compra": "001", "objeto_compra": "versão B"},
        ],
    )
    archive(
        folder,
        "compra_item",
        [
            {"id_compra": "001", "id_compra_item": "item1", "quantidade": "10"},
            {"id_compra": "999", "id_compra_item": "item2", "quantidade": ""},
        ],
    )
    archive(
        folder,
        "item_resultado",
        [
            {
                "id_compra": "001",
                "id_compra_item": "item1",
                "sequencial_resultado": "1",
                "ni_fornecedor": "0001",
                "valor_unitario_homologado": "2.00",
                "quantidade_homologada": "10",
                "data_resultado_pncp": "2026-09-10",
            },
            {
                "id_compra": "001",
                "id_compra_item": "item1",
                "sequencial_resultado": "2",
                "ni_fornecedor": "0002",
                "valor_unitario_homologado": "3.00",
                "quantidade_homologada": "5",
                "data_resultado_pncp": "2026-09-10",
            },
            {
                "id_compra": "other",
                "id_compra_item": "item1",
                "sequencial_resultado": "1",
                "ni_fornecedor": "0001",
                "valor_unitario_homologado": "NaN",
                "quantidade_homologada": "0",
                "data_resultado_pncp": "2026-02-30",
            },
        ],
    )
    row = {
        "id_compra": "001",
        "id_compra_item": "item1",
        "id_item_compra": "00001",
        "codigo_item_catalogo": "000123",
        "preco_unitario": "2.00",
        "quantidade": "10",
        "data_compra": "2026-09-01",
        "data_resultado": "2026-09-10",
        "ni_fornecedor": "0001",
        "forma": "SISRP",
        "descricao_item": "CANETA AZUL",
        "sigla_unidade_fornecimento": "UN",
        "capacidade_unidade_fornecimento": "0",
    }
    archive(folder, "material", [row, row])
    return folder


def test_profile_does_not_multiply_versions_or_merge_supplier_results(tmp_path):
    result = diagnose(sources(tmp_path))
    profiles = result["perfis"]
    assert profiles["compra"]["linhas_excedentes_por_identidade"] == 1
    assert profiles["compra"]["duplicatas_exatas"] == 0
    assert profiles["item_resultado"]["identidades_distintas"] == 3
    assert profiles["material"]["duplicatas_exatas"] == 1
    assert profiles["item_resultado"]["numericos"]["valor_unitario_homologado"]["invalido"] == 1
    assert profiles["item_resultado"]["datas_invalidas"]["data_resultado_pncp"] == 1
    links = result["vinculos_por_chaves"]
    assert links["compra_item_compra_sem_vinculo"] == 1
    assert links["item_resultado_compra_item_sem_vinculo"] == 1
    assert links["resultado_item_fornecedor_preco_quantidade_data_exatos"] == 1
    assert result["categorias_por_compras_distintas"][0]["catalogo"] == "000123"
    assert (
        result["categorias_por_compras_distintas"][0]["resultados_com_campos_textuais_coincidentes"]
        == 1
    )
    # Only report data: JSON serializable; no generated dataset or model.
    json.dumps(result)


def test_rerun_preserves_input_bytes_and_reproduces_profile(tmp_path):
    folder = sources(tmp_path)
    originals = {p: p.read_bytes() for p in folder.iterdir()}
    first = diagnose(folder)
    assert diagnose(folder) == first
    assert all(p.read_bytes() == content for p, content in originals.items())


def test_malformed_csv_is_rejected(tmp_path):
    path = tmp_path / "invalid.zip"
    with ZipFile(path, "w") as output:
        output.writestr("rows.csv", "a;b\n1;2;3\n")
    with pytest.raises(ValueError, match="largura"):
        list(records(path))
    with ZipFile(path, "w") as output:
        output.writestr("rows.csv", "a;a\n1;2\n")
    with pytest.raises(ValueError, match="Cabeçalho"):
        list(records(path))


def test_nonfinite_and_localized_numbers_are_not_silently_coerced():
    assert number_status("Infinity") == "invalido"
    assert number_status("1,23") == "invalido"
    assert number_status("-1") == "negativo"
    assert number_status("0.000") == "zero"
