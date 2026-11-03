"""Inferência real em schemas descartáveis, múltiplos resultados e falhas atômicas."""

import json
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from licita_backend.db.session import build_session_factory, get_session
from licita_backend.main import create_app
from licita_backend.models import analysis as a
from licita_backend.repositories.analises import AnalysisRepository
from licita_ml.analytical.pipeline import AnalyticalPipeline
from licita_ml.comparison.pipeline import ComparisonPipeline
from licita_ml.experiments import evaluate as if_engine
from licita_ml.inference.pipeline import InferencePipeline
from licita_ml.inference.registry import percentile
from licita_ml.pipeline import Pipeline
from licita_ml.validation.pipeline import ValidationPipeline
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_analytical import POLICY, raw_row, register_history


@pytest.fixture
def inference_case(database, settings, sources, tmp_path, monkeypatch):
    repo, admin = database
    objects, ids, add, material = sources
    purchase, official = material["id_compra"], material["id_compra_item"]
    material = dict(
        material,
        codigo_item_catalogo="486374",
        descricao_item="Caneta amarela",
        preco_unitario="0.6",
        quantidade="6",
        data_hora_atualizacao_item="2026-09-18 10:00:00",
    )
    add("material", [material])
    add(
        "compra_item",
        [
            dict(
                id_compra=purchase,
                id_compra_item=official,
                numero_item_pncp="1",
                descricao_detalhada="Caneta amarela",
                data_atualizacao_pncp="2026-09-18 10:00:00",
                quantidade="6",
                unidade_medida="UN",
                valor_unitario_estimado="1",
            )
        ],
    )
    results = []
    for n, supplier in enumerate(["00000000000200", "00000000000300"], 1):
        results.append(
            dict(
                id_compra=purchase,
                id_compra_item=official,
                ni_fornecedor=supplier,
                sequencial_resultado=str(n),
                srk_item_resultado="00000" + str(n + 6),
                data_atualizacao_pncp="2026-09-18 10:00:00",
                nome_razao_social_fornecedor="Fornecedor controlado",
                valor_unitario_homologado=str(Decimal("0.5") + Decimal(n) / 10),
                quantidade_homologada=str(n + 5),
                data_resultado_pncp="2026-09-20",
            )
        )
    add("item_resultado", results)
    base = Pipeline(settings, repo, objects).run(
        date(2026, 9, 1), date(2026, 9, 30), "486374", list(ids)
    )
    rows = [
        raw_row(
            n,
            n >= 100,
            precoUnitario=str(Decimal("0.5") + Decimal(n % 9) / 10),
            quantidade=str(1 + n % 13),
        )
        for n in range(135)
    ]
    for n in [100, 101]:
        index = n - 100
        rows[n].update(
            idCompra=purchase,
            idItemCompra=str(123 + index),
            idCompraItem=official,
            niFornecedor=results[index]["ni_fornecedor"],
            precoUnitario=results[index]["valor_unitario_homologado"],
            quantidade=results[index]["quantidade_homologada"],
            dataCompra="2026-09-15",
            dataResultado="2026-09-20",
        )
    history = register_history(admin, objects, rows)
    exclusion = tmp_path / "exclusions.json"
    exclusion.write_text(json.dumps({"versao": "exclusoes-documentais-v1", "exclusoes": []}))
    attributes = AnalyticalPipeline(settings, repo, objects).run(
        UUID(base["base_id"]), [history], POLICY, exclusion
    )
    monkeypatch.setattr(if_engine, "CONFIGS", ((200, 256),))
    # Mesmas cinco sementes e âncora; reduz somente a grade deste teste.
    validated = ValidationPipeline(objects).run(
        attributes["manifesto"], attributes["sha256_manifesto"]
    )
    compared = ComparisonPipeline(objects).run(
        validated["manifesto"], validated["sha256_manifesto"]
    )
    return repo, admin, objects, base, attributes, compared


def run_case(settings, case, fail_after=None):
    repo, _, objects, _, attributes, compared = case
    pipeline = InferencePipeline(settings, repo, objects)
    result = pipeline.run(
        compared["manifesto"],
        compared["sha256_manifesto"],
        attributes["manifesto"],
        attributes["sha256_manifesto"],
        fail_after,
    )
    return pipeline, result


def test_percentile_uses_training_cdf_and_does_not_impute():
    assert percentile([1, 2, 2, 4], 2) == Decimal("75.000")
    assert percentile([1, 2, 2, 4], 0) == 0
    assert percentile([1, 2, 2, 4], 5) == 100
    with pytest.raises(ValueError):
        percentile([], 1)
    with pytest.raises(ValueError):
        percentile([1], float("nan"))


@pytest.mark.integration
def test_inference_multiple_winners_replay_registry_publication_and_api(
    settings, inference_case, monkeypatch
):
    repo, admin, objects, base, attributes, compared = inference_case
    pipeline, result = run_case(settings, inference_case)
    uid, base_id = UUID(result["execucao_id"]), UUID(base["base_id"])
    assert result["contagens"]["scores"] >= 2, result
    again = run_case(settings, inference_case)[1]
    assert again["reutilizada"] and again["execucao_id"] == result["execucao_id"]
    from licita_ml.inference.pipeline import operational_features as original_features

    monkeypatch.setattr(
        "licita_ml.inference.pipeline.operational_features",
        lambda *args: list(reversed(original_features(*args))),
    )
    assert run_case(settings, inference_case)[1]["reutilizada"]
    with admin.connect() as cn:
        models = cn.execute(sa.select(a.versoes_modelo)).mappings().all()
        assert all(m["base_treino_id"] != base_id for m in models)
        scores = cn.execute(sa.select(a.resultados_modelo)).mappings().all()
        assert len({r["resultado_item_id"] for r in scores}) == 2
        assert len({r["item_versao_id"] for r in scores}) == 1
        ae_scores = [
            r
            for r in scores
            if next(m for m in models if m["id"] == r["modelo_id"])["algoritmo"] == "autoencoder"
        ]
        assert len(ae_scores) == 2
        for row in ae_scores:
            pieces = cn.scalar(
                sa.select(sa.func.sum(a.fatores_sinalizacao.c.contribuicao)).where(
                    a.fatores_sinalizacao.c.resultado_modelo_id == row["id"]
                )
            )
            assert abs(pieces - row["score_bruto"]) <= Decimal("0.000000000002")
    # API sob a identidade restrita, sem ler artefatos/modelos.
    url = admin.url
    with repo.engine.connect() as cn:
        schema_name = cn.scalar(sa.text("SELECT current_schema()"))
    reader = sa.create_engine(
        url, connect_args={"options": f"-c search_path={schema_name} -c role=licita_api"}
    )
    from licita_backend.core.config import Settings as ApiSettings

    app = create_app(
        ApiSettings(
            _env_file=None, app_env="test", database_url=url.render_as_string(hide_password=False)
        )
    )
    factory = build_session_factory(reader)

    def session():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            params = {"base_id": str(base_id)}
            assert client.get(f"/api/v1/analises/execucoes/{uid}", params=params).status_code == 404
            publication = pipeline.publish(uid)
            assert publication["status"] == "publicada_experimental"
            assert pipeline.publish(uid)["reutilizada"]
            active = client.get("/api/v1/analises/publicacao", params=params).json()
            assert active["execucao_id"] == str(uid)
            details = client.get(f"/api/v1/analises/execucoes/{uid}", params=params)
            assert details.status_code == 200, details.text
            listing = client.get("/api/v1/analises/execucoes", params=params)
            assert listing.status_code == 200 and listing.json()["total"] == 1
            page = client.get(f"/api/v1/analises/execucoes/{uid}/itens", params=params)
            assert page.status_code == 200, page.text
            item = page.json()["dados"][0]
            assert len(item["resultados"]) == len(scores) and item["prioridade"] is None
            assert (
                client.get(
                    f"/api/v1/analises/execucoes/{uid}/itens/{item['id']}", params=params
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/analises/execucoes/{uid}/itens/{uuid4()}", params=params
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/analises/execucoes/{uid}", params={"base_id": str(uuid4())}
                ).status_code
                == 404
            )
            assert client.get("/api/v1/analises/publicacao").status_code == 422
            assert client.get("/api/v1/base/status").json()["base"]["id"] == str(base_id)
            train_id = str(models[0]["base_treino_id"])
            assert (
                client.get("/api/v1/base/status", params={"base_id": train_id}).status_code == 404
            )
            # A falha na ativação de outra execução preserva a anterior.
            with admin.begin() as cn:
                other = uuid4()
                old = (
                    cn.execute(
                        sa.select(a.execucoes_analise).where(a.execucoes_analise.c.id == uid)
                    )
                    .mappings()
                    .one()
                )
                cn.execute(
                    a.execucoes_analise.insert().values(
                        id=other,
                        base_id=base_id,
                        versao_politica_score="experimental-v1",
                        configuracao=old["configuracao"],
                        status="falhou",
                    )
                )
            with pytest.raises(ValueError):
                pipeline.publish(other)
            assert client.get("/api/v1/analises/publicacao", params=params).json()[
                "execucao_id"
            ] == str(uid)
    finally:
        reader.dispose()
    # FK composta não admite associar o score a resultado/item/base incompatíveis.
    with admin.begin() as cn:
        bad = dict(scores[0], id=uuid4(), resultado_item_id=uuid4())
        with pytest.raises(IntegrityError), cn.begin_nested():
            cn.execute(a.resultados_modelo.insert().values(**bad))
    with admin.begin() as cn:
        identities, versions = repo.tables["itens_processo"], repo.tables["itens_versoes"]
        identity = dict(cn.execute(sa.select(identities)).mappings().first())
        identity.update(id=uuid4(), chave_oficial=identity["chave_oficial"] + "-outro")
        cn.execute(identities.insert().values(**identity))
        version = dict(cn.execute(sa.select(versions)).mappings().first())
        version.update(
            id=uuid4(), item_id=identity["id"], numero_item=str(int(version["numero_item"]) + 100)
        )
        cn.execute(versions.insert().values(**version))
        bad = dict(scores[0], id=uuid4(), item_versao_id=version["id"])
        with pytest.raises(IntegrityError), cn.begin_nested():
            cn.execute(a.resultados_modelo.insert().values(**bad))


@pytest.mark.integration
def test_failed_batch_rolls_back_models_scores_and_can_resume(
    settings, inference_case, monkeypatch
):
    _, admin, _, _, _, _ = inference_case
    with pytest.raises(RuntimeError, match="controlada"):
        run_case(settings, inference_case, fail_after=1)
    with admin.connect() as cn:
        assert cn.scalar(sa.select(a.execucoes_analise.c.status)) == "falhou"
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.resultados_modelo)) == 0
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.versoes_modelo)) == 0
    pipeline, result = run_case(settings, inference_case)
    assert result["status"] == "concluida" and result["contagens"]["scores"] >= 2
    uid = UUID(result["execucao_id"])
    pipeline.publish(uid)
    monkeypatch.setattr("licita_ml.inference.pipeline.code_hash", lambda: "test-version-2")
    second = run_case(settings, inference_case)[1]
    second_uid = UUID(second["execucao_id"])
    assert second_uid != uid
    with pytest.raises(RuntimeError, match="troca"):
        pipeline.publish(second_uid, fail=True)
    with admin.connect() as cn:
        assert (
            cn.scalar(
                sa.select(a.publicacoes_analise.c.execucao_id).where(
                    a.publicacoes_analise.c.ativa.is_(True)
                )
            )
            == uid
        )
    pipeline.publish(second_uid)
    with admin.connect() as cn:
        assert (
            cn.scalar(
                sa.select(a.publicacoes_analise.c.execucao_id).where(
                    a.publicacoes_analise.c.ativa.is_(True)
                )
            )
            == second_uid
        )
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.publicacoes_analise)) == 2
    with Session(admin) as session:
        assert AnalysisRepository(session).execution(UUID(result["base_id"]), uid)["id"] == uid
    # Retirada de dados completos por administrador é detectada antes da reutilização.
    with admin.begin() as cn:
        cn.execute(a.avaliacoes_processo.delete().where(a.avaliacoes_processo.c.execucao_id == uid))
    with pytest.raises(ValueError, match="processos"):
        pipeline.publish(uid)
