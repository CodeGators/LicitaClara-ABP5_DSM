"""Cortes, compras disjuntas, referência congelada e insuficiência sem scores fictícios."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from licita_ml.analytical.rules import digest
from licita_ml.organized.pipeline import prepare as organize
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.pipeline import prepare
from licita_ml.temporal.rules import TemporalPolicy
from test_organized import sources as source_files
from test_organized import write


@pytest.fixture
def history(tmp_path):
    folder, data = source_files.__wrapped__(tmp_path)
    data["compra"][0]["contratacao_excluida"] = "False"
    data["compra_item"][0]["descricao_resumida"] = "Caneta azul"
    for result in data["item_resultado"]:
        result.update(
            situacao_compra_item_resultado_id="1", situacao_compra_item_resultado_nome="Informado"
        )
    application = data["material"][0]
    application["codigo_classe"] = "7510"
    application["nome_unidade_fornecimento"] = "UNIDADE"
    records = []
    for partition, count in (("treino", 140), ("avaliacao", 40)):
        for i in range(count):
            row = dict(application)
            event = "2025-11-01" if partition == "treino" else "2026-07-01"
            result = "2025-11-02" if partition == "treino" else "2026-07-02"
            offset = 10000 if partition == "treino" else 20000
            row.update(
                id_compra=str(offset + i),
                id_compra_item=str(offset + i),
                id_item_compra=str(offset + i),
                data_compra=event,
                data_resultado=result,
                data_hora_atualizacao_item=result + "T12:00:00",
                ni_fornecedor=f"{i % 4 + 1:06}",
                codigo_orgao=str(i % 4 + 1),
                preco_unitario=str(Decimal("0.80") + Decimal(i % 11) / 100),
                quantidade=str(i % 7 + 1),
            )
            records.append(row)
    data["material"] = records + [application]
    for kind, values in data.items():
        write(folder, kind, values)
    return folder, data


def run(history, tmp_path, policy=None, exclusion=None, name="output"):
    folder, _ = history
    organized = organize([folder], tmp_path / "organized")
    return prepare(
        Path(organized["diretorio"]),
        tmp_path / name,
        policy or TemporalPolicy(),
        exclusion or RESOURCE_DIR / "exclusoes_v1.json",
    )


def read(result, table):
    return pq.ParquetFile(Path(result["diretorio"]) / f"{table}.parquet").read().to_pylist()


def test_features_are_numeric_and_operational_results_are_separate_from_references(
    history, tmp_path
):
    result = run(history, tmp_path)
    assert result["manifesto"]["grupos_elegiveis"] == 1
    assert len(read(result, "treino")) == 140
    assert len(read(result, "avaliacao")) == 40
    assert len(read(result, "aplicacao_referencias")) == 1
    assert len(read(result, "aplicacao_resultados")) == 1
    assert len(read(result, "alvos_resultados")) == 2
    for row in read(result, "treino"):
        assert isinstance(row["log_preco_mediana"], float)
        assert isinstance(row["log_quantidade"], float)
    assert not result["manifesto"]["modelos_executados"]
    assert (
        read(result, "aplicacao_resultados")[0]["id_observacao"]
        != read(result, "aplicacao_referencias")[0]["id_observacao"]
    )


def test_evaluation_prices_do_not_change_training_reference_or_training_features(history, tmp_path):
    first = run(history, tmp_path, name="first")
    folder, data = history
    for row in data["material"]:
        if row["data_compra"] == "2026-07-01":
            row["preco_unitario"] = "9999"
    write(folder, "material", data["material"])
    second = run(history, tmp_path, name="second")
    assert read(first, "treino") == read(second, "treino")
    assert read(first, "avaliacao") != read(second, "avaliacao")
    assert json.loads(
        (Path(first["diretorio"]) / "medianas_treino.json").read_text()
    ) == json.loads((Path(second["diretorio"]) / "medianas_treino.json").read_text())


def test_future_results_and_shared_purchases_are_excluded(history, tmp_path):
    folder, data = history
    future = data["material"][0]
    future["data_resultado"] = "2026-01-01"
    shared = next(r for r in data["material"] if r["data_compra"] == "2026-07-01")
    shared["id_compra"] = data["material"][1]["id_compra"]
    write(folder, "material", data["material"])
    result = run(history, tmp_path)
    assert len(read(result, "treino")) == 139
    assert len(read(result, "avaliacao")) == 39
    a = {r["compra"] for r in read(result, "treino")}
    b = {r["compra"] for r in read(result, "avaliacao")}
    assert not a & b
    reasons = [
        reason
        for row in read(result, "referencias_temporais")
        for reason in json.loads(row["motivos_json"])
    ]
    assert "RESULTADO_POSTERIOR_AO_CORTE" in reasons
    assert "COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR" in reasons


def test_insufficient_data_keeps_audit_and_exports_no_training_rows(history, tmp_path):
    folder, data = history
    data["material"] = [
        r for i, r in enumerate(data["material"]) if i < 20 or r["data_compra"] != "2025-11-01"
    ]
    write(folder, "material", data["material"])
    result = run(history, tmp_path)
    assert result["manifesto"]["status"] == "insuficiente_para_modelagem"
    assert read(result, "treino") == [] and read(result, "avaliacao") == []
    assert len(read(result, "referencias_temporais")) == 61
    assert result["manifesto"]["motivos_referencias"]["TREINO_INSUFICIENTE"] == 61


def test_documentary_exclusion_and_invalid_units_are_preserved(history, tmp_path):
    folder, data = history
    row = data["material"][0]
    excluded = digest(
        [row["id_compra"], row["id_item_compra"], row["ni_fornecedor"], row["forma"]]
    )[:20]
    path = tmp_path / "exclusions.json"
    path.write_text(
        json.dumps(
            {"versao": "exclusoes-documentais-v1", "exclusoes": [{"id_referencia": excluded}]}
        )
    )
    data["material"][1]["sigla_unidade_fornecimento"] = "CX"
    data["material"][1]["capacidade_unidade_fornecimento"] = "0"
    write(folder, "material", data["material"])
    result = run(history, tmp_path, exclusion=path)
    assert len(read(result, "treino")) == 138
    reasons = result["manifesto"]["motivos_referencias"]
    assert reasons["DIVERGENCIA_DOCUMENTAL_SUSPENSA"] == 1
    assert reasons["CAPACIDADE_EMBALAGEM_AUSENTE"] == 1


def test_operational_specification_mismatch_cannot_inherit_reference_features(history, tmp_path):
    folder, data = history
    data["compra_item"][0]["descricao_resumida"] = "Outro produto"
    write(folder, "compra_item", data["compra_item"])
    result = run(history, tmp_path)
    assert len(read(result, "aplicacao_referencias")) == 1
    assert read(result, "aplicacao_resultados") == []
    assert result["manifesto"]["motivos_alvos"]["ESPECIFICACAO_ITEM_DIVERGENTE"] == 1


def test_replay_and_corruption_are_checked(history, tmp_path):
    first = run(history, tmp_path)
    second = run(history, tmp_path)
    assert second["reutilizada"]
    assert first["manifesto"] == second["manifesto"]
    (Path(first["diretorio"]) / "treino.csv").write_text("broken")
    with pytest.raises(ValueError, match="corrompido"):
        run(history, tmp_path)


def test_windows_cannot_overlap():
    with pytest.raises(ValueError, match="Janelas"):
        TemporalPolicy(evaluation_start=date(2025, 12, 31))


def test_purchase_leakage_is_checked_even_when_earlier_product_is_outside_scope(history, tmp_path):
    folder, data = history
    old = data["material"][0]
    old.update(codigo_classe="9999", codigo_item_catalogo="999999")
    later = next(r for r in data["material"] if r["data_compra"] == "2026-07-01")
    later["id_compra"] = old["id_compra"]
    write(folder, "material", data["material"])
    result = run(history, tmp_path)
    assert len(read(result, "treino")) == 139
    assert len(read(result, "avaliacao")) == 39
    assert result["manifesto"]["referencias_fora_recorte"] == 1


@pytest.mark.parametrize(
    "change,reason",
    [
        (
            {"data_cancelamento_pncp": "2026-09-02"},
            "RESULTADO_CANCELADO_OU_SITUACAO_NAO_CONFIRMADA",
        ),
        ({"moeda_estrangeira_id": "1"}, "MOEDA_ESTRANGEIRA_REQUER_POLITICA"),
    ],
)
def test_ineligible_operational_result_cannot_inherit_reference_vector(
    history, tmp_path, change, reason
):
    folder, data = history
    data["item_resultado"][0].update(change)
    write(folder, "item_resultado", data["item_resultado"])
    result = run(history, tmp_path)
    assert len(read(result, "aplicacao_referencias")) == 1
    assert read(result, "aplicacao_resultados") == []
    assert result["manifesto"]["motivos_alvos"][reason] >= 1


def test_fresh_exports_reproduce_the_same_artifact_hashes(history, tmp_path):
    first = run(history, tmp_path, name="first")
    second = run(history, tmp_path, name="second")
    assert first["manifesto"] == second["manifesto"]
    assert not first["reutilizada"] and not second["reutilizada"]
