"""Recarga congelada, aplicação posterior e persistência atômica com API existente."""

import copy
import json
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from licita_backend.core.config import Settings as ApiSettings
from licita_backend.db.session import get_session
from licita_backend.main import create_app
from licita_backend.models import analysis as a
from licita_backend.repositories.analises import AnalysisRepository
from licita_backend.schemas.analises import AnalysisPage
from licita_ml.analytical.operational import read_base
from licita_ml.diagnostics import checksum
from licita_ml.inference.pipeline import InferencePipeline
from licita_ml.inference.temporal import (
    application,
    compatible_unit,
    frozen_models,
    infer_references,
    infer_sql,
    sql_targets,
)
from licita_ml.pipeline import Pipeline
from licita_shared.storage.local import LocalObjectStorage
from sqlalchemy.orm import Session
from test_training import completed as completed
from test_training import dataset as dataset


@pytest.fixture
def loaded(completed, dataset, tmp_path):
    folder = Path(completed["diretorio"])
    objects = LocalObjectStorage(tmp_path / "objects")
    sha = checksum(folder / "manifesto.json")
    values = frozen_models(folder, dataset, sha, objects)
    return folder, sha, objects, values


def test_inference_reuses_frozen_models_and_training_cdf(loaded, dataset, monkeypatch):
    folder, sha, objects, (_, temporal, models, _) = loaded
    from sklearn.ensemble import IsolationForest
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler

    for cls in (IsolationForest, MLPRegressor, StandardScaler):
        monkeypatch.setattr(cls, "fit", lambda *_a, **_kw: pytest.fail("Inferência não ajusta"))
    rows, scores, coverage = application(dataset, temporal, models)
    assert len(rows) == 1 and len(scores) == len(coverage) == 2
    assert all(r["score_processo"] is None and r["prioridade"] is None for r in scores)
    assert all(0 <= float(r["indice_experimental"]) <= 100 for r in scores)
    assert all(r["id_observacao"] not in m["train_ids"] for m in models for r in scores)
    ae = next(r for r in scores if r["algoritmo"] == "autoencoder")
    assert sum(ae["parcelas_ae"]) == pytest.approx(float(ae["score_bruto"]))
    first = infer_references(folder, dataset, sha, objects)
    second = infer_references(folder, dataset, sha, objects)
    assert first == second
    with objects.open(first["manifesto"]["chave"]) as stream:
        manifest = json.load(stream)
    assert not manifest["persistido_dominio_sql"] and not manifest["utilidade_comprovada"]
    assert len(manifest["artefatos"]) == 2
    for model in models:
        assert len(model["calibration"]) == 140
        assert model["bundle"]["train_end"] == date(2025, 12, 31)


def test_pinned_hash_rejects_before_deserializing(completed, dataset, tmp_path, monkeypatch):
    import joblib

    monkeypatch.setattr(joblib, "load", lambda *_: pytest.fail("Hash deve ser conferido antes"))
    with pytest.raises(ValueError, match="Hash do manifesto"):
        frozen_models(Path(completed["diretorio"]), dataset, "0" * 64, LocalObjectStorage(tmp_path))


def test_dependency_mismatch_rejects_before_deserializing(
    completed, dataset, tmp_path, monkeypatch
):
    import joblib
    from licita_ml.inference import temporal

    monkeypatch.setattr(temporal, "version", lambda _: "incompatível")
    monkeypatch.setattr(joblib, "load", lambda *_: pytest.fail("Não carregar"))
    folder = Path(completed["diretorio"])
    with pytest.raises(ValueError, match="Dependência"):
        frozen_models(
            folder, dataset, checksum(folder / "manifesto.json"), LocalObjectStorage(tmp_path)
        )


@pytest.fixture
def sql_case(database, settings, sources, loaded):
    repo, admin = database
    objects, ids, add, _ = sources
    _, _, _, (_, temporal, models, _) = loaded
    spec = models[0]["spec"]
    add(
        "material",
        [
            dict(
                id_compra="0001",
                id_compra_item="00001",
                id_item_compra="001",
                ni_fornecedor="000001",
                codigo_item_catalogo=spec[0],
                preco_unitario="1.00000001",
                quantidade="3",
                data_compra="2026-09-01",
                data_resultado="2026-09-01",
                forma="SISRP",
                descricao_item="Caneta azul",
                descricao_detalhada_item="Caneta azul",
                nome_fornecedor="Teste",
                sigla_unidade_fornecimento="UN",
                nome_unidade_fornecimento="UNIDADE",
                capacidade_unidade_fornecimento="0",
                data_hora_atualizacao_item="2026-09-02T12:00:00",
            )
        ],
    )
    add(
        "compra",
        [
            dict(
                id_compra="0001",
                codigo_orgao="00001",
                unidade_orgao_codigo_unidade="000001",
                orgao_entidade_razao_social="Órgão",
                ano_compra_pncp="2026",
                numero_compra="1",
                objeto_compra="Material",
                contratacao_excluida="False",
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        ],
    )
    add(
        "compra_item",
        [
            dict(
                id_compra="0001",
                id_compra_item="00001",
                numero_item_pncp="1",
                descricao_detalhada="Caneta azul",
                unidade_medida="UNIDADE",
                quantidade="3",
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        ],
    )
    add(
        "item_resultado",
        [
            dict(
                id_compra="0001",
                id_compra_item="00001",
                ni_fornecedor="000001",
                sequencial_resultado="1",
                srk_item_resultado="1",
                nome_razao_social_fornecedor="Teste",
                quantidade_homologada="3",
                valor_unitario_homologado="1.00000001",
                data_resultado_pncp="2026-09-01",
                situacao_compra_item_resultado_id="1",
                situacao_compra_item_resultado_nome="Informado",
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        ],
    )
    base = Pipeline(settings, repo, objects).run(
        date(2026, 9, 1), date(2026, 9, 30), spec[0], list(ids)
    )
    return repo, admin, objects, UUID(base["base_id"]), temporal, models


@pytest.mark.integration
def test_sql_atomic_replay_and_published_api(settings, sql_case, loaded, dataset):
    repo, admin, objects, base_id, _, _ = sql_case
    folder, sha, _, _ = loaded
    pipeline = InferencePipeline(settings, repo, objects)
    with pytest.raises(RuntimeError, match="Falha controlada"):
        infer_sql(pipeline, folder, dataset, sha, base_id, fail_after=1)
    with admin.connect() as cn:
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.resultados_modelo)) == 0
        assert cn.scalar(sa.select(a.execucoes_analise.c.status)) == "falhou"
    result = infer_sql(pipeline, folder, dataset, sha, base_id)
    assert result["contagens"]["scores"] == 2
    again = infer_sql(pipeline, folder, dataset, sha, base_id)
    assert again["reutilizada"] and again["execucao_id"] == result["execucao_id"]
    uid = UUID(result["execucao_id"])
    with Session(admin) as session:
        with pytest.raises(Exception, match="não publicada"):
            AnalysisRepository(session).execution(base_id, uid)
    pipeline.publish(uid)
    app = create_app(
        ApiSettings(
            _env_file=None,
            app_env="test",
            database_url="postgresql+psycopg://test:test@localhost/test_test",
        )
    )

    def session_override():
        with Session(admin) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/analises/execucoes/{uid}/itens", params={"base_id": str(base_id)}
        )
        assert response.status_code == 200, response.text
        item = response.json()["dados"][0]
        assert item["status"] == "analisado_experimental" and item["score_processo"] is None
        assert len(item["resultados"]) == 2
    with Session(admin) as session:
        repository = AnalysisRepository(session)
        execution = repository.execution(base_id, uid)
        result = repository.items(execution, AnalysisPage(base_id=base_id))
        assert result["dados"][0]["status"] == "analisado_experimental"
        scores = result["dados"][0]["resultados"]
        assert {r["algoritmo"] for r in scores} == {"isolation_forest", "autoencoder"}
        ae = next(r for r in scores if r["algoritmo"] == "autoencoder")
        parts = ae["explicacao"]["parcelas"]
        assert sum(float(p["parcela_score_bruto"]) for p in parts) == pytest.approx(
            float(ae["score_bruto"])
        )
        assert (
            next(r for r in scores if r["algoritmo"] == "isolation_forest")["explicacao"]["status"]
            == "indisponivel"
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "change,reason",
    [
        ("preco", "SEM_REFERENCIA_OPERACIONAL_EXATA"),
        ("data", "DATA_RESULTADO_DIVERGENTE_DA_REFERENCIA"),
        ("cancelado", "RESULTADO_CANCELADO"),
        ("situacao", "SITUACAO_RESULTADO_NAO_CONFIRMADA"),
        ("unidade", "UNIDADE_OPERACIONAL_DIVERGENTE"),
        ("descricao", "ESPECIFICACAO_ITEM_DIVERGENTE"),
        ("moeda", "MOEDA_ESTRANGEIRA_REQUER_POLITICA"),
        ("excluida", "COMPRA_EXCLUIDA_OU_SITUACAO_NAO_CONFIRMADA"),
        ("sem_resultado", "SEM_RESULTADO_CONHECIDO"),
    ],
)
def test_sql_ineligible_targets_never_receive_zero_score(sql_case, loaded, dataset, change, reason):
    repo, _, _, base_id, temporal, models = sql_case
    with repo.locked() as cn:
        base, data = read_base(repo, cn, base_id)
    data = copy.deepcopy(data)
    event, item, parent = (
        data["resultados_itens"][0],
        data["itens_versoes"][0],
        data["processos_versoes"][0],
    )
    if change == "preco":
        event["valor_unitario_homologado"] += 1
    elif change == "data":
        event["data_resultado"] = date(2026, 9, 2)
    elif change == "cancelado":
        event["cancelado"] = True
    elif change == "situacao":
        event["situacao"] = "desconhecida"
    elif change == "unidade":
        item["unidade_medida"] = "CX"
    elif change == "descricao":
        item["descricao"] = "Outro produto"
    elif change == "moeda":
        event["atributos_origem"]["moeda_estrangeira_id"] = "2"
    elif change == "excluida":
        parent["atributos_origem"]["contratacao_excluida"] = "True"
    else:
        data["resultados_itens"] = []
    rows, _, _ = application(dataset, temporal, models)
    scores, coverage, factors = sql_targets(base, data, rows, models)
    assert not scores and not factors
    assert len(coverage) == 2 and {r["motivo"] for r in coverage} == {reason}
    assert all(r["score_bruto"] is None and r["indice_experimental"] is None for r in coverage)


@pytest.mark.parametrize(
    "unit,expected",
    [
        ("Caixa 5000,00 UN", True),
        ("Caixa 5000.00 UN", True),
        ("CX", True),
        ("Caixa 1000,00 UN", False),
        ("Caixa 5,000 UN", False),
        ("Caixa 5000 KG", False),
        ("Pacote 5000 UN", False),
        ("UN", False),
        (None, False),
    ],
)
def test_packaging_requires_same_explicit_capacity_and_measure(unit, expected):
    assert compatible_unit(unit, ["425226", "grampo", "cx", "5E+3", "un"]) is expected


def test_later_result_cut_only_releases_isolated_late_result(loaded, dataset, tmp_path):
    import shutil

    import pyarrow as pa
    import pyarrow.parquet as pq

    _, _, _, (_, temporal, models, _) = loaded
    folder = tmp_path / "late-results"
    shutil.copytree(dataset, folder)
    path = folder / "referencias_temporais.parquet"
    file = pq.ParquetFile(path)
    rows = file.read().to_pylist()
    row = next(r for r in rows if r["particao"] == "aplicacao")
    row.update(
        data_resultado=date(2026, 10, 5),
        apto_modelagem=False,
        motivos_json='["RESULTADO_POSTERIOR_AO_CORTE"]',
        log_preco_mediana=None,
        log_quantidade=None,
    )
    pq.write_table(pa.Table.from_pylist(rows, schema=file.schema_arrow), path)
    matrix = pq.ParquetFile(folder / "aplicacao_referencias.parquet")
    pq.write_table(
        pa.Table.from_pylist([], schema=matrix.schema_arrow),
        folder / "aplicacao_referencias.parquet",
    )
    assert not application(folder, temporal, models)[1]
    _, scores, _ = application(folder, temporal, models, date(2026, 10, 31))
    assert len(scores) == 2
    assert all(r["motivos_temporais_originais"] == ["RESULTADO_POSTERIOR_AO_CORTE"] for r in scores)
    row["motivos_json"] = '["RESULTADO_POSTERIOR_AO_CORTE","COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR"]'
    pq.write_table(pa.Table.from_pylist(rows, schema=file.schema_arrow), path)
    assert not application(folder, temporal, models, date(2026, 10, 31))[1]
    with pytest.raises(ValueError, match="antecipar"):
        application(folder, temporal, models, date(2026, 8, 31))


def test_training_registry_identity_is_independent_of_inference_code(loaded, dataset, monkeypatch):
    from licita_ml.inference import temporal

    folder, sha, objects, (_, _, models, bases) = loaded
    monkeypatch.setattr(temporal, "code_hash", lambda: "1" * 64)
    _, _, upgraded_models, same_bases = frozen_models(folder, dataset, sha, objects)
    assert same_bases == bases
    assert {m["id"] for m in upgraded_models}.isdisjoint(m["id"] for m in models)
