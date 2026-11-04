"""Catálogo integral, médias de referências sem duplicação e treino separado."""

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from licita_ml.catalog import pipeline
from licita_ml.organized.pipeline import prepare as organize
from test_organized import sources as source_files
from test_organized import write


@pytest.fixture
def catalog_base(tmp_path):
    folder, data = source_files.__wrapped__(tmp_path)
    template = data["material"][0]
    template.update(
        descricao_item="CANETA, COR: AZUL, MATERIAL: PLASTICO",
        descricao_detalhada_item="Caneta cor: azul, material: plástico",
    )
    rows = []
    for i, (event, price, detail) in enumerate(
        [
            ("2025-11-01", "1.00000001", "Caneta cor: azul, material: plástico"),
            ("2025-11-02", "3.00000001", "CANETA, MATERIAL: PLASTICO; COR: AZUL"),
            ("2026-07-01", "100", "Caneta cor: azul, material: plástico"),
        ]
    ):
        rows.append(
            dict(
                template,
                id_compra=f"00{i + 1}",
                id_compra_item=f"00{i + 1}01",
                id_item_compra=f"0{i}",
                preco_unitario=price,
                data_compra=event,
                data_resultado=event,
                descricao_detalhada_item=detail,
            )
        )
    data["material"] = rows
    for kind, values in data.items():
        write(folder, kind, values)
    return Path(organize([folder], tmp_path / "organized")["diretorio"]), data


def read(result, name):
    return pq.ParquetFile(Path(result["diretorio"]) / f"{name}.parquet").read().to_pylist()


def test_all_observations_survive_and_native_results_do_not_double_count_prices(
    catalog_base, tmp_path
):
    base, _ = catalog_base
    result = pipeline.prepare(base, tmp_path / "catalog")
    observations = read(result, "observacoes")
    groups = read(result, "grupos")
    assert len(observations) == 3 and len(groups) == 1
    group = groups[0]
    assert group["referencias"] == 3 and group["grupos_anteriores"] == 2
    assert group["preco_medio_descritivo"] == "34.66666667"
    assert group["mediana_descritiva"] == "3.00000001"
    assert group["preco_medio_treino_diagnostico"] == "2.00000001"
    assert group["mediana_treino_diagnostico"] == "2.00000001"
    assert group["treino_validas_datas"] == 2 and group["avaliacao_validas_datas"] == 1
    assert not group["aprovado_treino"]
    assert (
        len(read(result, "itens_catalogados")) == 1
        and len(read(result, "resultados_catalogados")) == 2
    )
    assert all(r["media_global_catalogo"] is None for r in read(result, "produtos"))
    assert all(r["arquivo_sha256"] and r["linha"] >= 2 for r in observations)
    assert not result["manifesto"]["treino_executado"] and not result["manifesto"]["banco_alterado"]


def test_all_catalogs_are_included_instead_of_office_filter(catalog_base, tmp_path):
    _, data = catalog_base
    folder = tmp_path / "all" / "2026-09"
    folder.mkdir(parents=True)
    data["material"][0].update(codigo_item_catalogo="999999", codigo_classe="9999")
    for kind, values in data.items():
        write(folder, kind, values)
    base = Path(organize([folder], tmp_path / "organized-all")["diretorio"])
    result = pipeline.prepare(base, tmp_path / "catalog")
    assert {r["catalogo"] for r in read(result, "observacoes")} == {"999999", "000123"}


def test_future_prices_do_not_change_training_reference(catalog_base, tmp_path):
    base, data = catalog_base
    a = pipeline.prepare(base, tmp_path / "first")
    folder = tmp_path / "second-source" / "2026-09"
    folder.mkdir(parents=True)
    data["material"][-1]["preco_unitario"] = "99999"
    for kind, values in data.items():
        write(folder, kind, values)
    bbase = Path(organize([folder], tmp_path / "organized-b")["diretorio"])
    b = pipeline.prepare(bbase, tmp_path / "second")
    ga, gb = read(a, "grupos")[0], read(b, "grupos")[0]
    assert ga["mediana_treino_diagnostico"] == gb["mediana_treino_diagnostico"]
    assert ga["preco_medio_descritivo"] != gb["preco_medio_descritivo"]


def test_shared_purchase_is_not_counted_in_later_partition(catalog_base, tmp_path):
    _, data = catalog_base
    folder = tmp_path / "shared" / "2026-09"
    folder.mkdir(parents=True)
    data["material"][-1]["id_compra"] = data["material"][0]["id_compra"]
    for kind, values in data.items():
        write(folder, kind, values)
    base = Path(organize([folder], tmp_path / "organized-b")["diretorio"])
    result = pipeline.prepare(base, tmp_path / "catalog")
    assert read(result, "grupos")[0]["avaliacao_validas_datas"] == 0
    assert any(
        "COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR" in json.loads(r["motivos_json"])
        for r in read(result, "observacoes")
    )


def test_cache_is_checked_and_corruption_is_not_overwritten(catalog_base, tmp_path, monkeypatch):
    base, _ = catalog_base
    first = pipeline.prepare(base, tmp_path / "catalog")
    monkeypatch.setattr(pipeline, "stage", lambda *_: pytest.fail("Não regenerar"))
    assert pipeline.prepare(base, tmp_path / "catalog")["reutilizada"]
    path = Path(first["diretorio"]) / "grupos.csv"
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="corrompido"):
        pipeline.prepare(base, tmp_path / "catalog")
    assert path.read_bytes() == b"corrupt"


def test_failure_does_not_publish_partial_catalog(catalog_base, tmp_path, monkeypatch):
    base, _ = catalog_base

    def fail(*_):
        raise RuntimeError("test failure")

    monkeypatch.setattr(pipeline, "export_native", fail)
    with pytest.raises(RuntimeError, match="test failure"):
        pipeline.prepare(base, tmp_path / "catalog")
    assert not list((tmp_path / "catalog").glob("catalogo=*"))
    assert not list((tmp_path / "catalog").glob(".catalogo-*"))


def test_mean_uses_decimal_not_binary_float_or_scientific_notation():
    from decimal import Decimal

    assert (
        pipeline.mean([Decimal("9007199254740993.00000001"), Decimal("9007199254740995.00000001")])
        == "9007199254740994.00000001"
    )
    assert pipeline.mean([Decimal("0.00000001")]) == "0.00000001"


def test_refining_verified_catalog_matches_fresh_generation(catalog_base, tmp_path, monkeypatch):
    from licita_ml.catalog import rules

    _, data = catalog_base
    folder = tmp_path / "copy-source" / "2026-09"
    folder.mkdir(parents=True)
    data["material"][1]["descricao_detalhada_item"] = "CANETA MATERIALPLASTICO, CORAZUL"
    for kind, values in data.items():
        write(folder, kind, values)
    base = Path(organize([folder], tmp_path / "copy-organized")["diretorio"])
    with monkeypatch.context() as old:
        old.setattr(rules, "refine_spec", lambda spec: spec)
        parent = pipeline.prepare(base, tmp_path / "prior")
    assert len(read(parent, "grupos")) == 2
    fresh = pipeline.prepare(base, tmp_path / "fresh")
    refined = pipeline.prepare(base, tmp_path / "refined", previous=Path(parent["diretorio"]))
    for table in pipeline.SCHEMAS:
        assert read(refined, table) == read(fresh, table), table
    assert len(read(refined, "grupos")) == 1
    assert pipeline.prepare(base, tmp_path / "refined", previous=Path(parent["diretorio"]))[
        "reutilizada"
    ]


def test_incremental_catalog_rejects_incompatible_period(catalog_base, tmp_path):
    from datetime import date

    from licita_ml.temporal.rules import TemporalPolicy

    base, _ = catalog_base
    parent = pipeline.prepare(base, tmp_path / "prior")
    with pytest.raises(ValueError, match="outra base, período ou exclusões"):
        pipeline.prepare(
            base,
            tmp_path / "refined",
            policy=TemporalPolicy(train_start=date(2025, 8, 1)),
            previous=Path(parent["diretorio"]),
        )
    assert not (tmp_path / "refined").exists()
