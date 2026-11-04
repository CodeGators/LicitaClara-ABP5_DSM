"""Coorte congelada, escalas restritas ao treino, recarga e revisão sem aprovação automática."""

import csv
import io
import json
import shutil
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from licita_ml.comparison.autoencoder import score
from licita_ml.diagnostics import checksum
from licita_ml.organized.pipeline import prepare as organize
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.pipeline import prepare as make_temporal
from licita_ml.temporal.rules import TemporalPolicy
from licita_ml.training.dataset import load
from licita_ml.training.pipeline import PROTOCOL, prepare, protocol_config, review, validate
from test_temporal import history as temporal_history


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    root = tmp_path_factory.mktemp("training-source")
    folder, _ = temporal_history.__wrapped__(root)
    organized = organize([folder], root / "organized")
    result = make_temporal(
        Path(organized["diretorio"]),
        root / "temporal",
        TemporalPolicy(),
        RESOURCE_DIR / "exclusoes_v1.json",
    )
    return Path(result["diretorio"])


@pytest.fixture(scope="module")
def completed(dataset, tmp_path_factory):
    root = tmp_path_factory.mktemp("training-execution")
    return prepare(dataset, root / "models", root / "reviews")


def test_real_fit_replay_scaler_and_scores_share_the_same_cohort(completed, dataset):
    folder = Path(completed["diretorio"])
    manifest = validate(folder)
    assert not completed["reutilizada"]
    assert manifest["vencedor_validado"] is None and not manifest["publicacao_autorizada"]
    assert not manifest["aplicacao_pontuada"] and not manifest["scores_combinados"]
    assert manifest["grupos"][0]["total_ajustes"] == 45
    _, groups = load(dataset)
    gid, group = next(iter(groups.items()))
    bundle = joblib.load(folder / gid / "modelos/autoencoder-42.joblib")
    assert bundle["train_end"] == date(2025, 12, 31)
    assert bundle["scaler"].n_samples_seen_ == 140
    assert bundle["ids_treino"] == [r["id"] for r in group["train"]]
    np.testing.assert_allclose(
        bundle["scaler"].mean_, group["matrices"]["treino"].mean(axis=0), rtol=1e-14
    )
    points = pq.ParquetFile(folder / gid / "pontuacoes_avaliacao.parquet").read().to_pylist()
    assert len(points) == 40 * 3
    expected, _ = score(bundle, group["test"])
    ae = [p for p in points if p["metodo"] == "ae"]
    assert np.array_equal(expected, [p["score_bruto"] for p in ae])
    for p in points:
        assert np.isfinite(p["score_bruto"])
        assert p["preco_unitario"] > 0 and p["quantidade"] > 0
        assert p["compra"] and p["item_oficial"] and p["data_resultado"] >= p["data_compra"]
        if p["metodo"] == "ae":
            assert p["parcela_erro_preco_ae"] + p["parcela_erro_quantidade_ae"] == pytest.approx(
                p["score_bruto"]
            )
        else:
            assert p["parcela_erro_preco_ae"] is None
    train = pq.ParquetFile(folder / gid / "pontuacoes_treino.parquet").read().to_pylist()
    assert len(train) == 140 * 3
    assert {p["id_observacao"] for p in train}.isdisjoint(p["id_observacao"] for p in points)
    assert len(list((folder / gid / "modelos").glob("*.joblib"))) == 7


def test_cache_does_not_retrain_or_deserialize_and_preserves_edited_reviews(
    completed, dataset, tmp_path, monkeypatch
):
    from licita_ml.training import pipeline

    folder = Path(completed["diretorio"])
    original = prepare(dataset, folder.parent, tmp_path / "reviews")
    editable = (
        Path(original["revisoes_editaveis"])
        / original["manifesto"]["grupos"][0]["grupo"]
        / "revisao_treino.csv"
    )
    editable.write_text("user work", encoding="utf-8")
    monkeypatch.setattr(
        pipeline.if_engine, "evaluate", lambda *_a, **_kw: pytest.fail("Não retreinar")
    )
    monkeypatch.setattr(
        pipeline.ae_engine, "evaluate_autoencoder", lambda *_a, **_kw: pytest.fail("Não retreinar")
    )
    monkeypatch.setattr(
        joblib, "load", lambda *_: pytest.fail("Cache não deve desserializar modelos")
    )
    result = prepare(dataset, folder.parent, tmp_path / "reviews")
    assert result["reutilizada"] and editable.read_text() == "user work"


def test_corruption_and_incomplete_manifest_are_rejected(completed, tmp_path):
    folder = tmp_path / "execution"
    shutil.copytree(completed["diretorio"], folder)
    manifest = json.loads((folder / "manifesto.json").read_text())
    model = next(a for a in manifest["artefatos"] if a["arquivo"].endswith(".joblib"))
    path = folder / model["arquivo"]
    path.write_bytes(b"broken")
    with pytest.raises(ValueError, match="corrompido"):
        validate(folder)
    manifest["artefatos"] = [a for a in manifest["artefatos"] if a != model]
    (folder / "manifesto.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="incompleto"):
        validate(folder)


def test_loader_rejects_matrix_that_disagrees_with_audit_before_fitting(dataset, tmp_path):
    folder = tmp_path / "dataset"
    shutil.copytree(dataset, folder)
    path = folder / "treino.parquet"
    file = pq.ParquetFile(path)
    rows = file.read().to_pylist()
    rows[0]["log_preco_mediana"] += 1
    pq.write_table(pa.Table.from_pylist(rows, schema=file.schema_arrow), path)
    manifest = json.loads((folder / "manifesto.json").read_text())
    for artifact in manifest["artefatos"]:
        if artifact["arquivo"] == "treino.parquet":
            artifact.update(sha256=checksum(path), bytes=path.stat().st_size)
    (folder / "manifesto.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="atributos congelados"):
        load(folder)


def test_loader_never_includes_application_observations(dataset):
    _, groups = load(dataset)
    application = pq.ParquetFile(dataset / "aplicacao_referencias.parquet").read().to_pylist()
    ids = {r["id_observacao"] for r in application}
    for group in groups.values():
        assert not ids & set(group["audit"])


def test_protocol_cannot_silently_change_the_anchor(tmp_path):
    document = json.loads(PROTOCOL.read_text())
    document["isolation_forest"]["ancora"]["seed"] = 11
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="âncoras"):
        protocol_config(path)


def test_failure_leaves_no_published_execution(dataset, tmp_path, monkeypatch):
    from licita_ml.training import pipeline

    monkeypatch.setattr(
        pipeline, "train_group", lambda *_: (_ for _ in ()).throw(RuntimeError("failure"))
    )
    with pytest.raises(RuntimeError, match="failure"):
        prepare(dataset, tmp_path / "models", tmp_path / "reviews")
    assert not list((tmp_path / "models").glob("execucao=*"))
    assert not list((tmp_path / "models").glob(".treino-*"))


def test_review_is_pending_and_never_automatically_approves_utility(completed):
    folder = Path(completed["diretorio"])
    gid = completed["manifesto"]["grupos"][0]["grupo"]
    result = review(
        folder,
        gid,
        folder / gid / "revisao_treino.csv",
        folder / gid / "revisao_avaliacao.csv",
        "interna",
    )
    assert result["natureza_declarada"] == "interna"
    assert result["treino"]["contagens"]["pendente"] == 20
    assert not result["publicacao_autorizada"] and not result["utilidade_aprovada_automaticamente"]
    assert result["vencedor_validado"] is None


def test_review_context_cannot_be_changed(completed, tmp_path):
    folder = Path(completed["diretorio"])
    gid = completed["manifesto"]["grupos"][0]["grupo"]
    rows = list(
        csv.DictReader(
            io.StringIO((folder / gid / "revisao_avaliacao.csv").read_text(encoding="utf-8-sig"))
        )
    )
    rows[0]["preco_unitario"] = "999"
    path = tmp_path / "edited.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Contexto"):
        review(folder, gid, folder / gid / "revisao_treino.csv", path, "interna")


def test_insufficient_dataset_is_rejected_before_training(dataset, tmp_path):
    folder = tmp_path / "insufficient"
    shutil.copytree(dataset, folder)
    path = folder / "manifesto.json"
    document = json.loads(path.read_text())
    document["status"] = "insuficiente_para_modelagem"
    document["grupos_elegiveis"] = 0
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="insuficiente"):
        load(folder)
