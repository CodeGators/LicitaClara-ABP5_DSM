"""Controles do ensaio: agrupamento, corte temporal e pré-processamento sem futuro."""

from datetime import date
from decimal import Decimal

import pytest
from licita_ml.experiments.data import clean, normalized, split_groups


def row(purchase="000001", item="000001", when="2026-01-01", **changes):
    result = dict(
        idCompra=purchase,
        idItemCompra=item,
        niFornecedor="00000000000100",
        forma="SISRP",
        codigoItemCatalogo="486054",
        dataCompra=when,
        precoUnitario="2.00",
        quantidade="10",
        siglaUnidadeFornecimento="UN",
        capacidadeUnidadeFornecimento="0",
        siglaUnidadeMedida="",
        descricaoDetalhadaItem="Borracha 53 mm",
        codigoOrgao="1",
    )
    result.update(changes)
    return result


def test_comparable_groups_do_not_merge_different_units_or_specs():
    rows = [
        row(item="1"),
        row(item="2", siglaUnidadeFornecimento="CX"),
        row(item="3", descricaoDetalhadaItem="Borracha 50 mm"),
    ]
    # kwargs acima devem substituir campos, não serem atributos ignorados.
    cleaned, _ = clean(rows, "486054")
    assert len({r["group"] for r in cleaned}) == 3
    assert normalized("LÁPIS, 53 MM") == "lapis 53 mm"


def test_missing_unit_is_excluded_and_ids_keep_leading_zeroes():
    cleaned, reasons = clean([row(), row(item="2", siglaUnidadeFornecimento=None)], "486054")
    assert len(cleaned) == 1 and reasons["UNIDADE_AUSENTE"] == 1
    assert cleaned[0]["purchase"] == "000001"
    assert cleaned[0]["price"] == Decimal("2.00")


def test_cross_period_purchase_never_appears_in_test_and_bulk_is_segregated():
    records = [
        row(purchase="1", item="1"),
        row(purchase="1", item="2", when="2026-08-01"),
        row(purchase="2", item="3", when="2026-08-01"),
    ]
    records += [row(purchase="3", item=str(i + 10)) for i in range(6)]
    cleaned, _ = clean(records, "486054")
    groups = split_groups(cleaned)
    assert len(groups) == 1
    group = groups[0]
    assert group["excluded_bulk_train"] == 6
    assert group["excluded_cross_purchase"] == 1
    assert {r["purchase"] for r in group["test"]} == {"2"}
    assert not group["eligible"]


def test_conflicting_version_is_not_resolved_by_highest_or_lowest_price():
    first = row()
    second = dict(first, precoUnitario="100")
    cleaned, reasons = clean([first, second], "486054")
    assert not cleaned and reasons["CONFLITO_DE_VERSAO"] == 1


def test_reference_rejects_future_and_saved_model_replays(tmp_path):
    pytest.importorskip("sklearn")
    import joblib
    import numpy as np
    from licita_ml.experiments.evaluate import features, train_reference
    from sklearn.ensemble import IsolationForest

    records, _ = clean([row(item="1"), row(item="2", precoUnitario="4")], "486054")
    median = train_reference(records)
    assert median == Decimal("3.00")
    with pytest.raises(ValueError, match="futura"):
        train_reference([dict(records[0], date=date(2026, 8, 1))])
    # Referência congelada não depende da distribuição do holdout.
    test = [dict(records[0], price=Decimal("100"))]
    transformed = features(test, median, ["log_preco_mediana"])
    assert transformed[0, 0] == pytest.approx(np.log(100 / 3))
    model = IsolationForest(n_estimators=20, random_state=42).fit(
        features(records, median, ["log_preco_mediana"])
    )
    path = tmp_path / "model.joblib"
    joblib.dump({"model": model, "median": median}, path)
    loaded = joblib.load(path)
    assert np.array_equal(
        model.score_samples(transformed), loaded["model"].score_samples(transformed)
    )


def test_purchase_overlap_is_removed_even_across_different_specifications():
    records = [
        row(purchase="1", item="1"),
        row(purchase="1", item="2", when="2026-08-01", descricaoDetalhadaItem="Outra medida"),
        row(purchase="2", item="3", when="2026-08-01", descricaoDetalhadaItem="Outra medida"),
    ]
    cleaned, _ = clean(records, "486054")
    groups = split_groups(cleaned)
    assert sum(g["excluded_cross_purchase"] for g in groups) == 1
    assert {r["purchase"] for g in groups for r in g["test"]} == {"2"}


def test_review_with_human_evidence_cannot_be_overwritten(tmp_path):
    from licita_ml.experiments.core import review_files

    rows, _ = clean([row()], "486054")
    group = {"id": "grupo", "test": rows}
    folder = tmp_path / "revisao"
    folder.mkdir()
    sheet = folder / "grupo-revisao-cega.csv"
    content = "parecer,justificativa,evidencia_url\nrequer_verificacao,Conferir embalagem,https://exemplo.test\n"
    sheet.write_text(content)
    result = {"baseline_sobrepreco": [], "baseline_bilateral": []}
    with pytest.raises(ValueError, match="Revisão já preenchida"):
        review_files(group, result, {}, [], [], tmp_path)
    assert sheet.read_text() == content
