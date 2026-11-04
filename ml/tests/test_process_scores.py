"""Agregação por processo com cobertura real e limites sem imputação."""

from decimal import Decimal
from uuid import uuid4

import pytest
from licita_ml.inference.processes import summarize


@pytest.fixture
def case():
    process = {"id": uuid4(), "base_id": uuid4(), "atributos_origem": {"idCompra": "0001"}}
    model = uuid4()
    items, events, scores = [], [], []
    universe = {
        "status": "confirmado_no_snapshot",
        "itens": [],
        "resultados_ativos": {},
        "fontes": [],
    }

    def add(values):
        uid = f"0001{len(items) + 1:04}"
        item = {"id": uuid4(), "item_id": uuid4(), "atributos_origem": {"idCompraItem": uid}}
        items.append(item)
        universe["itens"].append(uid)
        universe["resultados_ativos"][uid] = []
        for n, value in enumerate(values):
            raw = {"niFornecedor": f"00{n}", "sequencialResultado": n + 1}
            event = {
                "id": uuid4(),
                "item_versao_id": item["id"],
                "cancelado": False,
                "atributos_origem": raw,
            }
            events.append(event)
            universe["resultados_ativos"][uid].append([f"00{n}", n + 1])
            if value is not None:
                scores.append(
                    {
                        "id": uuid4(),
                        "modelo_id": model,
                        "processo_versao_id": process["id"],
                        "resultado_item_id": event["id"],
                        "score_normalizado": Decimal(str(value)),
                        "versao_normalizacao": "cdf-treino-v1",
                    }
                )
        return item

    def run(official=True):
        return summarize(process, items, events, scores, model, universe if official else None)

    return add, run, process, items, events, scores, model, universe


def test_full_score_balances_items_instead_of_number_of_winners(case):
    add, run, *_ = case
    add([90, 10])
    add([10])
    result = run()
    assert result["score"] == 30 and result["indice_observado"] == 30
    assert result["status"] == "analisado_experimental"
    assert result["limite_inferior"] == result["limite_superior"] == 30
    assert result["contexto"]["prioridade_auditoria"] is None
    assert [i["peso_no_indice_observado"] for i in result["sinais"]["itens"]] == ["1/2", "1/2"]
    assert sum(Decimal(i["contribuicao_observada"]) for i in result["sinais"]["itens"]) == 30


def test_missing_items_prevent_whole_process_score_and_bound_possible_mean(case):
    add, run, *_ = case
    add([90])
    add([None])
    result = run()
    assert result["score"] is None and result["indice_observado"] == 90
    assert (result["limite_inferior"], result["limite_superior"]) == (45, 95)
    assert result["cobertura"]["itens_integralmente_analisados"] == 1
    assert result["cobertura"]["itens_oficiais"] == 2
    assert result["status"] == "parcial"


def test_partial_winners_also_contribute_only_bounds(case):
    add, run, *_ = case
    add([80, None])
    add([20])
    result = run()
    assert result["score"] is None and result["indice_observado"] == 50
    assert (result["limite_inferior"], result["limite_superior"]) == (30, 55)


def test_imported_subset_is_not_assumed_to_be_entire_purchase(case):
    add, run, *_ = case
    add([90])
    add([10])
    result = run(official=False)
    assert result["score"] is None and result["indice_observado"] == 50
    assert result["limite_inferior"] is result["limite_superior"] is None
    assert result["cobertura"]["itens_oficiais"] is None
    assert result["motivo"] == "UNIVERSO_OFICIAL_NAO_CONFIRMADO"


def test_true_zero_is_analyzed_and_not_absence(case):
    add, run, *_ = case
    add([0])
    result = run()
    assert result["score"] == 0 and result["status"] == "analisado_experimental"


def test_no_scores_do_not_imply_normal_purchase(case):
    add, run, *_ = case
    add([None])
    add([])
    result = run()
    assert result["score"] is result["indice_observado"] is None
    assert (result["limite_inferior"], result["limite_superior"]) == (0, 100)
    assert result["status"] == "nao_analisado"


def test_models_are_kept_separate(case):
    add, run, process, items, events, scores, _, universe = case
    add([90])
    other = uuid4()
    scores.append(dict(scores[0], id=uuid4(), modelo_id=other, score_normalizado=Decimal(10)))
    assert run()["score"] == 90
    assert summarize(process, items, events, scores, other, universe)["score"] == 10


def test_duplicate_or_orphan_scores_are_rejected(case):
    add, run, _, _, events, scores, *_ = case
    add([90])
    scores.append(dict(scores[0]))
    with pytest.raises(ValueError, match="mais de uma"):
        run()
    scores.pop()
    events[0]["cancelado"] = True
    with pytest.raises(ValueError, match="órfão"):
        run()


def test_official_items_missing_from_import_reduce_coverage(case):
    add, run, _, _, _, _, _, universe = case
    add([90])
    universe["itens"].append("not-imported")
    universe["resultados_ativos"]["not-imported"] = [["other", 1]]
    result = run()
    assert result["score"] is None and result["cobertura"]["itens_importados"] == 1
    assert result["limite_inferior"] == 45 and result["limite_superior"] == 95


def test_directed_rounding_does_not_narrow_identification_bounds(case):
    add, run, *_ = case
    add([1])
    add([None])
    add([None])
    result = run()
    assert result["limite_inferior"] == Decimal("0.333")
    assert result["limite_superior"] == 67


def test_max_and_mean_have_different_and_explicit_interpretations(case):
    add, run, *_ = case
    add([90])
    add([10])
    first = run()["score"]
    for _ in range(8):
        add([10])
    assert first == 50 and run()["score"] == 18
    assert max(Decimal(i["media_observada"]) for i in run()["sinais"]["itens"]) == 90
