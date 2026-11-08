"""Roteamento real entre grupos, persistência esparsa e consulta automática na API."""

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
from licita_ml.analytical.operational import read_base
from licita_ml.grouped import inference, temporal, training
from licita_ml.inference.pipeline import InferencePipeline
from licita_ml.pipeline import Pipeline
from sqlalchemy.orm import Session
from test_grouped_temporal import grouped_source


@pytest.fixture(scope="module")
def trained_groups(tmp_path_factory):
    root = tmp_path_factory.mktemp("grouped-models")
    base, catalog = grouped_source.__wrapped__(root)
    prep = temporal.prepare(base, catalog, root / "temporal")
    result = training.run(Path(prep["diretorio"]), root / "models", root / "reviews", workers=1)
    return Path(result["diretorio"])


@pytest.fixture
def grouped_case(database, settings, sources, trained_groups):
    repo, admin = database
    objects, ids, add, _ = sources
    origin, models, train_bases, rows = inference.load_models(
        trained_groups, objects, date(2026, 10, 31)
    )
    assert len({r["grupo"] for r in rows}) == 2
    specs = {m["group"]: m for m in models}
    material = []
    items = []
    events = []
    for index, row in enumerate(rows, 1):
        model = specs[row["grupo"]]
        material.append(
            dict(
                id_compra=row["compra"],
                id_compra_item=row["item"],
                id_item_compra=str(index),
                ni_fornecedor=row["fornecedor"],
                nome_fornecedor="Fornecedor teste",
                codigo_item_catalogo=model["canonical_spec"]["catalogo"],
                preco_unitario=str(row["preco_unitario"]),
                quantidade=str(row["quantidade"]),
                data_compra=str(row["data_compra"]),
                data_resultado=str(row["data_resultado"]),
                forma="SISRP",
                descricao_item=model["catalog_description"],
                descricao_detalhada_item="CANETA COR: AZUL, MATERIAL: PLASTICO",
                sigla_unidade_fornecimento="UN",
                nome_unidade_fornecimento="UNIDADE",
                capacidade_unidade_fornecimento="0",
                data_hora_atualizacao_item="2026-09-02T12:00:00",
            )
        )
        items.append(
            dict(
                id_compra=row["compra"],
                id_compra_item=row["item"],
                numero_item_pncp=str(index),
                descricao_detalhada="CANETA MATERIALPLASTICO, CORAZUL",
                unidade_medida="UNIDADE",
                quantidade=str(row["quantidade"]),
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        )
        events.append(
            dict(
                id_compra=row["compra"],
                id_compra_item=row["item"],
                ni_fornecedor=row["fornecedor"],
                nome_fornecedor="Fornecedor teste",
                sequencial_resultado="1",
                srk_item_resultado=str(index),
                nome_razao_social_fornecedor="Teste",
                quantidade_homologada=str(row["quantidade"]),
                valor_unitario_homologado=str(row["preco_unitario"]),
                data_resultado_pncp=str(row["data_resultado"]),
                situacao_compra_item_resultado_id="1",
                situacao_compra_item_resultado_nome="Informado",
                moeda_estrangeira_id="",
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        )
    unknown = dict(
        material[0], id_compra_item="unknown", id_item_compra="99", codigo_item_catalogo="999999"
    )
    material.append(unknown)
    items.append(dict(items[0], id_compra_item="unknown", numero_item_pncp="99"))
    events.append(dict(events[0], id_compra_item="unknown", srk_item_resultado="99"))
    add("material", material)
    add("compra_item", items)
    add("item_resultado", events)
    add(
        "compra",
        [
            dict(
                id_compra="0001",
                codigo_orgao="00001",
                unidade_orgao_codigo_unidade="000001",
                orgao_entidade_razao_social="Orgao",
                ano_compra_pncp="2026",
                numero_compra="1",
                objeto_compra="Materiais",
                contratacao_excluida="False",
                data_atualizacao_pncp="2026-09-02T12:00:00",
            )
        ],
    )
    codes = sorted({r["codigo_item_catalogo"] for r in material})
    base = Pipeline(settings, repo, objects).run(
        date(2026, 9, 1),
        date(2026, 9, 30),
        codes,
        list(ids),
        selected_items=[r["id_compra_item"] for r in material],
    )
    return repo, admin, objects, UUID(base["base_id"]), models, rows, train_bases


@pytest.mark.integration
def test_real_sparse_inference_atomic_replay_and_automatic_api(
    grouped_case, settings, trained_groups, monkeypatch
):
    repo, admin, objects, base_id, models, rows, _ = grouped_case
    from sklearn.ensemble import IsolationForest
    from sklearn.neural_network import MLPRegressor

    monkeypatch.setattr(
        IsolationForest, "fit", lambda *_a, **_kw: pytest.fail("Inferência não treina IF")
    )
    monkeypatch.setattr(
        MLPRegressor, "fit", lambda *_a, **_kw: pytest.fail("Inferência não treina AE")
    )
    pipeline = InferencePipeline(settings, repo, objects)
    with pytest.raises(RuntimeError, match="Falha controlada"):
        inference.infer(pipeline, trained_groups, base_id, fail_after=1)
    with admin.connect() as cn:
        assert cn.scalar(sa.select(sa.func.count()).select_from(a.resultados_modelo)) == 0
    result = inference.infer(pipeline, trained_groups, base_id)
    assert inference.infer(pipeline, trained_groups, base_id)["reutilizada"]
    execution = UUID(result["execucao_id"])
    pipeline.publish(execution)
    with repo.locked() as cn:
        _, data = read_base(repo, cn, base_id)
        scores, coverage, _, routing = inference.route({"id": base_id}, data, rows, models)
    assert len(coverage) == len(scores) + 1
    assert len(routing) == 3
    assert all(
        s["atributos"]["referencia"]["grupo"]
        == next(m["group"] for m in models if m["id"] == s["modelo_id"])
        for s in scores
    )
    unknown = next(c for c in coverage if c["modelo_id"] is None)
    assert unknown["indice_experimental"] is None and unknown["status"] == "nao_analisado"
    api = create_app(
        ApiSettings(_env_file=None, database_url="postgresql+psycopg://api:api@localhost/test")
    )

    def session():
        with Session(admin) as s:
            yield s

    api.dependency_overrides[get_session] = session
    with TestClient(api) as client:
        run = client.get(
            f"/api/v1/analises/execucoes/{execution}", params={"base_id": str(base_id)}
        )
        assert run.status_code == 200 and run.json()["roteamento_automatico"]
        view = client.get(
            "/api/v1/visao/ranking", params={"base_id": str(base_id), "execucao_id": str(execution)}
        )
        assert view.status_code == 200, view.text
        assert view.json()["resumo"]["analisados"] == 2
        assert view.json()["resumo"]["nao_analisados"] == 1
        process = client.get(
            f"/api/v1/analises/execucoes/{execution}/processos", params={"base_id": str(base_id)}
        )
        assert process.status_code == 200
        summary = process.json()["dados"][0]["cobertura_agrupada"]
        assert summary["quantidade_grupos"] == 2 and summary["score_processo"] is None
        assert summary["motivo"] == "MULTIPLOS_GRUPOS_SEM_ESCALA_COMUM"
        assert summary["resultados_com_analise"] == 2 and summary["itens_importados"] == 3


def test_unit_matching_preserves_pack_capacity_and_measure():
    model = {"canonical_spec": {"unidade": "cx", "capacidade": "50", "medida": "un"}}
    assert inference.unit_matches("Caixa 50 UN", model)
    assert not inference.unit_matches("Caixa 100 UN", model)
    assert not inference.unit_matches("Caixa 50 KG", model)
    assert not inference.unit_matches("UN", model)
    simple = {"canonical_spec": {"unidade": "un", "capacidade": "0", "medida": "un"}}
    assert inference.unit_matches("Unidade 1 UN", simple)
    assert not inference.unit_matches("Unidade 100 UN", simple)
    assert inference.unit_matches(
        "Quilograma", {"canonical_spec": {"unidade": "kg", "capacidade": "0", "medida": "kg"}}
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "change,reason",
    [
        ("description", "ESPECIFICACAO_ITEM_DIVERGENTE"),
        ("unit", "UNIDADE_OPERACIONAL_DIVERGENTE"),
        ("date", "DATA_RESULTADO_DIVERGENTE_DA_REFERENCIA"),
        ("canceled", "RESULTADO_CANCELADO"),
    ],
)
def test_group_routing_does_not_relax_matching(grouped_case, change, reason):
    repo, _, _, base_id, models, rows, _ = grouped_case
    with repo.locked() as cn:
        base, data = read_base(repo, cn, base_id)
    data = copy.deepcopy(data)
    item = next(
        i for i in data["itens_versoes"] if i["atributos_origem"]["id_compra_item"] != "unknown"
    )
    event = next(e for e in data["resultados_itens"] if e["item_versao_id"] == item["id"])
    if change == "description":
        item["descricao"] = "CANETA COR: PRETA, MATERIAL: PLASTICO"
    elif change == "unit":
        item["unidade_medida"] = "Caixa 100 UN"
    elif change == "date":
        event["data_resultado"] = date(2026, 9, 2)
    else:
        event["cancelado"] = True
    scores, coverage, _, _ = inference.route(base, data, rows, models)
    assert not any(s["item_versao_id"] == item["id"] for s in scores)
    assert all(c["motivo"] == reason for c in coverage if c["item_versao_id"] == str(item["id"]))


@pytest.mark.parametrize("change", ["wrong_group", "missing_model", "missing_target", "extra_pair"])
def test_reconciliation_rejects_wrong_or_missing_routes(change):
    from licita_ml.analytical.rules import digest
    from licita_ml.catalog.rules import grouping

    model_rows = []
    for code, mid in [("123", "m1"), ("124", "m2")]:
        group, _ = grouping(
            {
                "catalogo": code,
                "descricao": "CANETA, COR: AZUL",
                "descricao_detalhada": "CANETA, COR: AZUL",
                "unidade_fornecimento_sigla": "UN",
                "capacidade": 0,
            }
        )
        params = {
            "contrato": inference.VERSION,
            "catalogo_versao": inference.CATALOG_VERSION,
            "grupo": group["id"],
            "assinatura_catalogo": group["especificacao"],
        }
        model_rows.append({"id": mid, "parametros": params, "versao": digest(params)})
    gid = model_rows[0]["parametros"]["grupo"]
    config = {
        "modelos": ["m1", "m2"],
        "roteamento": {
            "i1:e1": {"grupo": gid, "modelos": ["m1"]},
            "i2:-": {"grupo": None, "modelos": []},
        },
    }
    coverage = [
        {
            "item_versao_id": "i1",
            "resultado_item_id": "e1",
            "modelo_id": "m1",
            "grupo": gid,
            "status": "nao_analisado",
        },
        {
            "item_versao_id": "i2",
            "resultado_item_id": None,
            "modelo_id": None,
            "grupo": None,
            "status": "nao_analisado",
        },
    ]
    inference.validate_routing({"i1": ["e1"], "i2": []}, config, model_rows, coverage, [])
    if change == "wrong_group":
        config["roteamento"]["i1:e1"]["grupo"] = model_rows[1]["parametros"]["grupo"]
    elif change == "missing_model":
        config["roteamento"]["i1:e1"]["modelos"] = []
    elif change == "missing_target":
        coverage.pop()
    else:
        coverage.append({**coverage[0], "modelo_id": "m2"})
    with pytest.raises(ValueError):
        inference.validate_routing({"i1": ["e1"], "i2": []}, config, model_rows, coverage, [])


def test_late_result_extension_cannot_bypass_purchase_concentration():
    rows = [
        {"grupo": "g", "compra": "p", "apto_modelagem": True, "motivos_json": "[]"}
        for _ in range(6)
    ]
    rows.append({"grupo": "other", "compra": "p", "apto_modelagem": True, "motivos_json": "[]"})
    inference.apply_purchase_limit(rows, 5)
    assert all(
        not r["apto_modelagem"]
        and json.loads(r["motivos_json"]) == ["EXCESSO_REFERENCIAS_MESMA_COMPRA"]
        for r in rows[:6]
    )
    assert rows[-1]["apto_modelagem"]


@pytest.mark.parametrize(
    "value,expected",
    [(None, False), ("", False), ("  ", False), (0, True), ("0", True), (1, True), ("BRL", True)],
)
def test_currency_absence_in_csv_and_json_is_not_foreign(value, expected):
    from licita_ml.inference.temporal import has_foreign_currency

    for key in ("moedaEstrangeiraId", "moeda_estrangeira_id"):
        assert has_foreign_currency({key: value}) is expected
    assert has_foreign_currency({"moedaEstrangeiraId": "", "moeda_estrangeira_id": "1"})
