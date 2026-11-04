"""Conciliação, precisão, linhagem e publicação atômica da base organizada."""

import csv
import io
import json
import shutil
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from licita_ml.organized.pipeline import prepare
from licita_ml.organized.schema import Export


def write(folder, kind, rows):
    stream = io.StringIO()
    columns = sorted(set().union(*(row.keys() for row in rows)))
    writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    with ZipFile(folder / f"{kind}_2026_09.csv.zip", "w") as archive:
        archive.writestr(f"{kind}.csv", stream.getvalue())


@pytest.fixture
def sources(tmp_path):
    folder = tmp_path / "2026-09"
    folder.mkdir()
    data = {
        "compra": [
            {
                "id_compra": "0001",
                "data_atualizacao_pncp": "2026-09-02T12:00:00",
                "objeto_compra": "Material",
                "valor_total_homologado": "11.00000007",
            }
        ],
        "compra_item": [
            {
                "id_compra": "0001",
                "id_compra_item": "00001",
                "numero_item_pncp": "001",
                "unidade_medida": "UNIDADE",
                "quantidade": "7",
                "valor_unitario_estimado": "0",
                "data_atualizacao_pncp": "2026-09-02T12:00:00",
            }
        ],
        "item_resultado": [
            {
                "id_compra": "0001",
                "id_compra_item": "00001",
                "sequencial_resultado": "01",
                "ni_fornecedor": "000001",
                "valor_unitario_homologado": "1.00000001",
                "valor_total_homologado": "3.00000003",
                "quantidade_homologada": "3",
                "data_resultado_pncp": "2026-09-01",
                "data_atualizacao_pncp": "2026-09-02T12:00:00",
            },
            {
                "id_compra": "0001",
                "id_compra_item": "00001",
                "sequencial_resultado": "02",
                "ni_fornecedor": "000002",
                "valor_unitario_homologado": "2.00000001",
                "valor_total_homologado": "8.00000004",
                "quantidade_homologada": "4",
                "data_resultado_pncp": "2026-09-01",
                "data_atualizacao_pncp": "2026-09-02T12:00:00",
            },
        ],
        "material": [
            {
                "id_compra": "0001",
                "id_compra_item": "00001",
                "id_item_compra": "001",
                "ni_fornecedor": "000001",
                "forma": "SISRP",
                "codigo_item_catalogo": "000123",
                "preco_unitario": "1.00000001",
                "quantidade": "3.00000000",
                "data_compra": "2026-09-01",
                "data_resultado": "2026-09-01",
                "descricao_detalhada_item": "Caneta azul",
                "sigla_unidade_fornecimento": "UN",
                "capacidade_unidade_fornecimento": "0",
                "data_hora_atualizacao_item": "2026-09-02T12:00:00",
            },
        ],
    }
    for kind, rows in data.items():
        write(folder, kind, rows)
    return folder, data


def read(result, table):
    return pq.ParquetFile(Path(result["diretorio"]) / f"{table}.parquet").read().to_pylist()


def test_decimal_supplier_results_and_lineage_survive_without_join_multiplication(
    sources, tmp_path
):
    folder, data = sources
    originals = {p: p.read_bytes() for p in folder.iterdir()}
    result = prepare([folder], tmp_path / "out")
    results = read(result, "resultados")
    assert len(results) == 2
    assert {r["fornecedor"] for r in results} == {"000001", "000002"}
    assert sum(r["valor_total"] for r in results) == Decimal("11.00000007")
    assert results[0]["preco_unitario"] == Decimal("1.00000001")
    item = read(result, "itens")[0]
    assert item["id_compra_item"] == "00001" and item["numero_item"] == "001"
    assert item["catalogo_original"] is None
    assert item["preco_unitario_estimado"] == Decimal(0)
    assert read(result, "enriquecimento_itens")[0]["catalogo_referencia_unico"] == "000123"
    links = read(result, "vinculos")
    assert (
        sum(
            link["destino_tabela"] == "resultados" and link["destino_id"] is not None
            for link in links
        )
        == 1
    )
    for kind in ("compras", "itens", "resultados", "referencias"):
        for row in read(result, kind):
            assert row["linha"] >= 2 and len(row["arquivo_sha256"]) == 64
        with (Path(result["diretorio"]) / f"{kind}.csv").open() as stream:
            assert len(list(csv.DictReader(stream, delimiter=";"))) == len(read(result, kind))
    assert all(p.read_bytes() == original for p, original in originals.items())
    schema = pq.ParquetFile(Path(result["diretorio"]) / "resultados.parquet").schema_arrow
    assert schema.field("preco_unitario").type == pa.decimal128(28, 8)
    assert schema.field("data_resultado").type == pa.date32()
    assert not result["manifesto"]["modelos_executados"]


def test_latest_version_and_exact_duplicates_are_reconciled(sources, tmp_path):
    folder, data = sources
    old = data["compra"][0]
    new = dict(old, data_atualizacao_pncp="2026-09-03T12:00:00", valor_total_homologado="20")
    write(folder, "compra", [old, new, new])
    result = prepare([folder], tmp_path / "out")
    assert read(result, "compras")[0]["valor_homologado"] == Decimal(20)
    assert result["manifesto"]["destinos_linhas"]["compras"] == {
        "aceito": 1,
        "duplicata_exata": 1,
        "versao_superada": 1,
    }


def test_tied_conflicting_versions_are_quarantined_without_using_older_record(sources, tmp_path):
    folder, data = sources
    old = data["compra"][0]
    new = dict(old, data_atualizacao_pncp="2026-09-03T12:00:00", valor_total_homologado="20")
    write(folder, "compra", [old, new, dict(new, valor_total_homologado="30")])
    result = prepare([folder], tmp_path / "out")
    assert read(result, "compras") == []
    rejects = read(result, "rejeicoes")
    assert len(rejects) == 3
    assert {r["motivo"] for r in rejects} == {"EMPATE_DE_VERSAO_DIVERGENTE"}
    assert any(link["status"] == "pai_nao_resolvido" for link in read(result, "vinculos"))


@pytest.mark.parametrize(
    "timestamp,reason",
    [
        ("2026-09-03T12:00:00Z", "VERSOES_COM_FUSOS_INCOMPATIVEIS"),
        ("", "VERSOES_DIVERGENTES_SEM_DATA"),
        ("invalid", "DATA_VERSAO_INVALIDA"),
    ],
)
def test_ambiguous_or_invalid_version_dates_do_not_choose_a_winner(
    sources, tmp_path, timestamp, reason
):
    folder, data = sources
    old = data["compra"][0]
    write(
        folder, "compra", [old, dict(old, data_atualizacao_pncp=timestamp, objeto_compra="outro")]
    )
    result = prepare([folder], tmp_path / "out")
    assert read(result, "compras") == []
    assert {r["motivo"] for r in read(result, "rejeicoes")} == {reason}


def test_invalid_values_are_null_with_warning_not_zero_and_cancellation_is_preserved(
    sources, tmp_path
):
    folder, data = sources
    data["item_resultado"][0].update(
        valor_unitario_homologado="NaN", data_cancelamento_pncp="invalid"
    )
    write(folder, "item_resultado", data["item_resultado"])
    result = prepare([folder], tmp_path / "out")
    row = next(r for r in read(result, "resultados") if r["fornecedor"] == "000001")
    assert row["preco_unitario"] is None
    assert row["cancelamento_informado"] is True and row["data_cancelamento"] is None
    assert {w["campo"] for w in json.loads(row["avisos_json"])} == {
        "preco_unitario",
        "data_cancelamento",
    }


def test_same_item_in_different_purchase_does_not_get_linked(sources, tmp_path):
    folder, data = sources
    data["material"][0]["id_compra"] = "999"
    write(folder, "material", data["material"])
    result = prepare([folder], tmp_path / "out")
    reference_links = [r for r in read(result, "vinculos") if r["origem_tabela"] == "referencias"]
    assert all(r["destino_id"] is None for r in reference_links)
    assert any(r["status"] == "id_item_com_compra_divergente" for r in reference_links)
    assert read(result, "enriquecimento_itens")[0]["status"] == "sem_referencia"


def test_repeated_source_content_reuse_and_artifact_corruption(sources, tmp_path):
    folder, _ = sources
    copy = tmp_path / "copy" / "2026-09"
    shutil.copytree(folder, copy)
    result = prepare([folder, copy], tmp_path / "out")
    assert all(len(s["copias"]) == 2 for s in result["manifesto"]["fontes"])
    assert result["manifesto"]["tabelas"]["linhas"] == 5
    assert prepare([folder], tmp_path / "out")["reutilizada"]
    artifact = Path(result["diretorio"]) / "itens.csv"
    artifact.write_bytes(b"broken")
    with pytest.raises(ValueError, match="corrompido"):
        prepare([folder], tmp_path / "out")
    assert artifact.read_bytes() == b"broken"


def test_failure_does_not_publish_partial_base_and_retry_is_possible(
    sources, tmp_path, monkeypatch
):
    folder, _ = sources
    output = tmp_path / "out"
    original = Export.add
    monkeypatch.setattr(Export, "add", lambda *_: (_ for _ in ()).throw(RuntimeError("failure")))
    with pytest.raises(RuntimeError, match="failure"):
        prepare([folder], output)
    assert not list(output.glob("base=*"))
    monkeypatch.setattr(Export, "add", original)
    assert prepare([folder], output)["manifesto"]["tabelas"]["compras"] == 1


def test_fresh_build_reproduces_all_artifact_hashes(sources, tmp_path):
    folder, _ = sources
    first = prepare([folder], tmp_path / "first")
    second = prepare([folder], tmp_path / "second")
    assert first["manifesto"] == second["manifesto"]
    assert not first["reutilizada"] and not second["reutilizada"]


def test_reference_secondary_timestamp_missing_does_not_establish_precedence(sources, tmp_path):
    folder, data = sources
    original = data["material"][0]
    write(
        folder,
        "material",
        [
            original,
            dict(original, preco_unitario="9", data_hora_atualizacao_compra="2026-09-03T00:00:00"),
        ],
    )
    result = prepare([folder], tmp_path / "out")
    assert read(result, "referencias") == []
    assert {row["motivo"] for row in read(result, "rejeicoes")} == {
        "VERSOES_DIVERGENTES_SEM_DATA_SECUNDARIA",
    }


def test_denormalized_item_rows_do_not_turn_suppliers_into_item_version_conflicts(
    sources, tmp_path
):
    folder, data = sources
    item = data["compra_item"][0]
    write(
        folder,
        "compra_item",
        [
            dict(item, cod_fornecedor="000001", valor_total_resultado="3"),
            dict(item, cod_fornecedor="000002", valor_total_resultado="8"),
        ],
    )
    result = prepare([folder], tmp_path / "out")
    assert len(read(result, "itens")) == 1
    assert len(read(result, "resultados")) == 2
    assert result["manifesto"]["destinos_linhas"]["itens"] == {
        "aceito": 1,
        "projecao_equivalente": 1,
    }
    assert read(result, "rejeicoes") == []


def test_point_lookups_do_not_scan_the_entire_history(tmp_path):
    """Budget SQLite instructions to catch quadratic joins without a flaky time limit."""
    import sqlite3
    from contextlib import ExitStack

    from licita_ml.organized.pipeline import (
        export_enrichment,
        reference_result_links,
        resolve,
        setup,
    )

    with sqlite3.connect(":memory:") as connection:
        setup(connection)
        for kind in ("referencias", "resultados"):
            connection.executemany(
                "INSERT INTO selected VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        kind,
                        str(i),
                        f"{kind}-{i}",
                        "other",
                        str(i),
                        "supplier",
                        None,
                        "1.00000000",
                        "1.00000000",
                        "2026-09-01",
                        0,
                        "{}",
                    )
                    for i in range(10000)
                ],
            )
        connection.execute(
            "INSERT INTO selected VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "itens",
                "wanted",
                "item",
                "wanted",
                "wanted",
                None,
                None,
                None,
                None,
                None,
                0,
                "{}",
            ),
        )
        resolve(connection)
        calls = 0

        def budget():
            nonlocal calls
            calls += 1
            return int(calls > 20)

        connection.set_progress_handler(budget, 1000)
        row = {
            "purchase": "wanted",
            "item": "wanted",
            "supplier": "supplier",
            "price": "1.00000000",
            "qty": "1.00000000",
            "result": "2026-09-01",
        }
        assert reference_result_links(connection, row) == [
            (None, "sem_resultado_com_campos_coincidentes")
        ]
        calls = 0
        with ExitStack() as stack:
            writer, stats = export_enrichment(connection, tmp_path, stack)
            assert writer.count == 1 and stats == {"sem_referencia": 1}
