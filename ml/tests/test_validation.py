"""Treino real com dataset controlado, integridade e revisão externa explícita."""

import csv
import io
import json
from datetime import date
from decimal import Decimal

import pytest
from licita_ml.analytical.pipeline import parquet, put_immutable
from licita_ml.analytical.rules import Policy, canonical, prepare_references, reference_row
from licita_ml.experiments import evaluate as engine
from licita_ml.validation.pipeline import ValidationPipeline, load_groups, read_manifest
from licita_ml.validation.review import blind_csv, sample, summarize
from licita_shared.storage.local import LocalObjectStorage

POLICY = Policy(date(2025, 10, 1), date(2026, 6, 30), date(2026, 9, 30))


def fixture_dataset(tmp_path, eligible=True):
    objects = LocalObjectStorage(tmp_path)
    rows = []
    for n in range(135 if eligible else 5):
        evaluation = n >= 100
        row = reference_row(
            {
                "codigoItemCatalogo": "486374",
                "idCompra": str(10000 + n),
                "idItemCompra": str(10000 + n),
                "idCompraItem": str(10000 + n) + "00001",
                "niFornecedor": str(n % 4),
                "forma": "SISRP",
                "codigoOrgao": str(n % 3),
                "precoUnitario": str(Decimal("0.5") + Decimal(n % 9) / 10),
                "quantidade": str(1 + n % 13),
                "siglaUnidadeFornecimento": "UN",
                "capacidadeUnidadeFornecimento": "0",
                "descricaoDetalhadaItem": "Caneta amarela",
                "dataCompra": "2026-08-01" if evaluation else "2026-01-01",
                "dataResultado": "2026-08-02" if evaluation else "2026-01-02",
            }
        )
        row["proveniencias"] = [
            {"arquivo_id": "origem", "membro": "pagina-1.json", "ordinal": n + 1}
        ]
        rows.append(row)
    groups = prepare_references(rows, POLICY, {})
    raw, _ = parquet(rows, "referencias")
    refs = {
        **put_immutable(objects, "input/refs.parquet", raw),
        "entidade": "referencias",
        "linhas": len(rows),
    }
    exclusions = {
        **put_immutable(objects, "input/exclusoes.json", b'{"exclusoes":[]}'),
        "entidade": "politica_exclusoes",
    }
    manifest = {
        "schema": "licita-atributos-v1",
        "fingerprint": "test",
        "configuracao": {"politica": POLICY.manifest()},
        "fontes": [],
        "artefatos": [refs, exclusions],
        "grupos": groups,
    }
    stored = put_immutable(objects, "input/manifesto.json", canonical(manifest).encode())
    return objects, stored, rows


def test_versioned_real_training_replay_reuse_blind_samples_and_tampering(tmp_path, monkeypatch):
    objects, source, rows = fixture_dataset(tmp_path)
    # Mantém os modelos reais e a âncora; reduz só a grade deste teste.
    monkeypatch.setattr(engine, "CONFIGS", ((200, 256),))
    monkeypatch.setattr(engine, "SEEDS", (11, 42))
    pipeline = ValidationPipeline(objects)
    result = pipeline.run(source["chave"], source["sha256"])
    assert result["status"] == "inconclusivo_por_revisao"
    assert result["grupos_avaliados"] == 1
    again = pipeline.run(source["chave"], source["sha256"])
    assert again["reutilizada"] and again["fingerprint"] == result["fingerprint"]
    manifest, contents = read_manifest(
        objects, result["manifesto"], result["sha256_manifesto"], "licita-validacao-if-v1"
    )
    group = manifest["grupos"][0]
    assert all(m["replay_exato"] for m in group["modelos"].values())
    training = next(a for a in manifest["artefatos"] if a["entidade"] == "manifesto_treino")
    train = json.loads(contents[training["chave"]])
    assert set(train["ids_treino"]) == {r["id"] for r in rows if r["particao"] == "treino"}
    assert not train["base_sql_treino_registrada"]
    for kind in ["treino", "avaliacao"]:
        artifact = next(a for a in manifest["artefatos"] if a["entidade"] == "revisao_" + kind)
        csv_raw = contents[artifact["chave"]]
        assert b"score" not in csv_raw and b"ranking" not in csv_raw and b"if_" not in csv_raw
        path = tmp_path / (kind + ".csv")
        path.write_bytes(csv_raw)
    review = pipeline.review(
        result["manifesto"],
        result["sha256_manifesto"],
        group["group_id"],
        tmp_path / "treino.csv",
        tmp_path / "avaliacao.csv",
    )
    assert review["treino"]["contagens"] == {"pendente": 20}
    assert review["avaliacao"]["status"] == "revisao_pendente"
    assert not review["publicacao_autorizada"]
    assert all(v["denominador_original"] == 4 for v in review["avaliacao"]["por_ranking"].values())
    objects.put(training["chave"], io.BytesIO(b"alterado"))
    with pytest.raises(ValueError, match="tamanho diverge|SHA-256"):
        pipeline.run(source["chave"], source["sha256"])


def test_insufficient_data_never_trains_and_pin_is_required(tmp_path, monkeypatch):
    objects, source, _ = fixture_dataset(tmp_path, eligible=False)
    monkeypatch.setattr(engine.IsolationForest, "fit", lambda *_: pytest.fail("Não treinar"))
    pipeline = ValidationPipeline(objects)
    with pytest.raises(ValueError, match="SHA-256"):
        pipeline.run(source["chave"], "0" * 64)
    assert pipeline.run(source["chave"], source["sha256"])["status"] == "inconclusivo_por_dados"


def test_policy_recomputed_before_training(tmp_path):
    objects, source, _ = fixture_dataset(tmp_path)
    manifest, contents = read_manifest(
        objects, source["chave"], source["sha256"], "licita-atributos-v1"
    )
    manifest["grupos"][0]["treino"] += 1
    with pytest.raises(ValueError, match="Grupos"):
        load_groups(manifest, contents)


def test_reviews_keep_inconclusive_and_errors_separate_and_require_complete_evidence(tmp_path):
    _, _, rows = fixture_dataset(tmp_path, eligible=False)
    selected = sample(rows, 3)
    raw = blind_csv(selected)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    records, fields = list(reader), reader.fieldnames

    def encode():
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        return out.getvalue().encode()

    expected = [r["id"] for r in selected]
    with pytest.raises(ValueError, match="IDs"):
        summarize(raw, expected + ["outro"], {})
    for row, verdict in zip(
        records, ["requer_verificacao", "inconclusivo", "erro_dado_ou_unidade"], strict=True
    ):
        row.update(
            parecer_humano=verdict,
            justificativa="Evidência de teste",
            evidencia_url="https://example.test/doc",
            revisor="Revisor de teste",
            data_revisao="2026-11-03",
        )
    result = summarize(encode(), expected, {"metodo": expected})
    assert result["status"] == "pareceres_registrados"
    assert result["contagens"]["inconclusivo"] == 1
    assert result["contagens"]["erro_dado_ou_unidade"] == 1
    assert not result["utilidade_aprovada_automaticamente"]
    records[0]["evidencia_url"] = ""
    with pytest.raises(ValueError, match="evidência"):
        summarize(encode(), expected, {})
    records[0]["preco_unitario"] = "999"
    with pytest.raises(ValueError, match="Contexto"):
        summarize(encode(), expected, {}, raw)
