"""Síntese derivada imutável: FK, rollback, publicação e leitura HTTP."""

import io
import json
from datetime import date
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from licita_backend.core.config import Settings as ApiSettings
from licita_backend.db.session import get_session
from licita_backend.main import create_app
from licita_backend.models import analysis as a
from licita_ml.inference.pipeline import InferencePipeline
from licita_ml.inference.processes import run
from licita_ml.inference.temporal import infer_sql
from licita_ml.pipeline import Pipeline
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_temporal_inference import completed as completed
from test_temporal_inference import dataset as dataset
from test_temporal_inference import loaded as loaded
from test_temporal_inference import sql_case as sql_case


@pytest.fixture
def complete_case(settings, sql_case, sources, loaded, dataset):
    repo, admin, objects, _, _, _ = sql_case
    _, ids, add, _ = sources
    item = {
        "idCompra": "0001",
        "idCompraItem": "00001",
        "numeroItemPncp": 1,
        "descricaodetalhada": "Caneta azul",
        "unidadeMedida": "UNIDADE",
        "quantidade": "3",
        "dataAtualizacaoPncp": "2026-09-02T12:00:00",
    }
    result = {
        "idCompra": "0001",
        "idCompraItem": "00001",
        "niFornecedor": "000001",
        "sequencialResultado": 1,
        "nomeRazaoSocialFornecedor": "Teste",
        "quantidadeHomologada": "3",
        "valorUnitarioHomologado": "1.00000001",
        "dataResultadoPncp": "2026-09-01",
        "situacaoCompraItemResultadoId": 1,
        "situacaoCompraItemResultadoNome": "Informado",
        "dataAtualizacaoPncp": "2026-09-02T12:00:00",
    }
    for kind, record in (("itens_api", item), ("resultados_api", result)):
        uid = add(kind, [record], query={"idCompra": "0001"})
        with admin.connect() as cn:
            artifact = (
                cn.execute(
                    sa.select(repo.tables["arquivos_coletados"]).where(
                        repo.tables["arquivos_coletados"].c.id == uid
                    )
                )
                .mappings()
                .one()
            )
        with objects.open(artifact["chave_objeto"]) as stream:
            body = json.load(stream)
        body["paginas"][0]["resposta_original"] = json.dumps(
            {"resultado": [record], "totalRegistros": 1, "totalPaginas": 1}
        )
        raw = json.dumps(body).encode()
        key = f"raw/complete-{uid}.json"
        objects.put(key, io.BytesIO(raw))
        with admin.begin() as cn:
            cn.execute(
                repo.tables["arquivos_coletados"]
                .update()
                .where(repo.tables["arquivos_coletados"].c.id == uid)
                .values(chave_objeto=key, sha256=sha256(raw).hexdigest(), tamanho_bytes=len(raw))
            )
    base = Pipeline(settings, repo, objects).run(
        date(2026, 9, 1), date(2026, 9, 30), "000123", list(ids)
    )
    folder, sha, _, _ = loaded
    pipeline = InferencePipeline(settings, repo, objects)
    inferred = infer_sql(pipeline, folder, dataset, sha, UUID(base["base_id"]))
    pipeline.publish(UUID(inferred["execucao_id"]))
    return pipeline, admin, inferred


@pytest.mark.integration
def test_derived_process_score_is_atomic_replayable_and_published(
    settings, complete_case, monkeypatch
):
    pipeline, admin, source = complete_case
    source_id = UUID(source["execucao_id"])
    base_id = source["base_id"]
    import joblib

    monkeypatch.setattr(joblib, "load", lambda *_: pytest.fail("Síntese não carrega modelos"))
    with pytest.raises(RuntimeError, match="Falha controlada"):
        run(pipeline, source_id, fail_after=1)
    with admin.connect() as cn:
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.sinteses_processo_modelo)) == 0
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.resultados_modelo)) == 2
    derived = run(pipeline, source_id)
    uid = UUID(derived["execucao_id"])
    assert derived["contagens"]["sinteses_processo"] == 2
    assert derived["contagens"]["processos_modelos_com_score_integral"] == 2
    assert run(pipeline, source_id)["reutilizada"]
    with pytest.raises(ValueError, match="não outra síntese"):
        run(pipeline, uid)
    app = create_app(
        ApiSettings(
            _env_file=None,
            app_env="test",
            database_url="postgresql+psycopg://test:test@localhost/test_test",
        )
    )

    def override():
        with Session(admin) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        params = {"base_id": base_id}
        url = f"/api/v1/analises/execucoes/{uid}/processos"
        assert client.get(url, params=params).status_code == 404
        pipeline.publish(uid)
        response = client.get(url, params=params)
        assert response.status_code == 200, response.text
        row = response.json()["dados"][0]
        assert len(row["resultados"]) == 2
        for summary in row["resultados"]:
            assert summary["status"] == "analisado_experimental"
            assert summary["score_processo"] == summary["indice_observado"]
            assert summary["cobertura"]["itens_oficiais"] == 1
            with admin.connect() as cn:
                referenced = UUID(
                    summary["sinais"]["itens"][0]["resultados"][0]["resultado_modelo_id"]
                )
                assert (
                    cn.scalar(
                        sa.select(a.resultados_modelo.c.execucao_id).where(
                            a.resultados_modelo.c.id == referenced
                        )
                    )
                    == uid
                )
        assert client.get(url + f"/{row['id']}", params=params).status_code == 200
        assert client.get(url, params={**params, "modelo_id": str(uuid4())}).status_code == 422
        assert client.get(url + f"/{uuid4()}", params=params).status_code == 404
        # Publicação anterior continua consultável e distingue falta de síntese.
        previous = client.get(
            f"/api/v1/analises/execucoes/{source_id}/processos", params=params
        ).json()
        assert previous["dados"][0]["status"] == "sem_sintese"
    with admin.connect() as cn:
        summary = dict(cn.execute(sa.select(a.sinteses_processo_modelo).limit(1)).mappings().one())
    # A identidade de processamento pode inserir, mas não reescrever análises.
    with pytest.raises(sa.exc.ProgrammingError):
        with pipeline.repo.engine.begin() as cn:
            cn.execute(a.sinteses_processo_modelo.update().values(score=0))
    # Não é permitido fabricar prioridade para transformar score técnico em fraude.
    with pytest.raises(IntegrityError):
        with admin.begin() as cn:
            summary.update(id=uuid4(), modelo_id=uuid4())
            cn.execute(a.sinteses_processo_modelo.insert().values(**summary))
