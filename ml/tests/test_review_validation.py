"""Controles de identidade, versões, período independente e limites dos anexos."""

import io
from datetime import date
from decimal import Decimal
from zipfile import ZipFile

import pytest
from licita_ml.experiments.data import clean, split_groups
from licita_ml.review_validation.documentary import latest, reconcile, textual_purchase
from licita_ml.review_validation.documents import candidates, pdf_sources
from test_core_validation import row


def test_new_window_does_not_change_original_default_window():
    raw = row(when="2026-10-02")
    assert not clean([raw], "486054")[0]
    accepted, reasons = clean([raw], "486054", start=date(2026, 10, 1), end=date(2026, 10, 19))
    assert len(accepted) == 1 and not reasons


def test_historical_replication_uses_its_own_cutoff():
    records = [row(purchase="1", when="2025-01-01"), row(purchase="2", when="2025-07-01")]
    accepted, _ = clean(records, "486054", start=date(2024, 10, 1), end=date(2025, 9, 30))
    group = split_groups(accepted, train_end=date(2025, 6, 30))[0]
    assert len(group["train"]) == len(group["test"]) == 1


def test_lost_zero_can_only_be_resolved_from_consistent_official_text_key():
    raw = {
        "idCompra": 8000805900232025,
        "idCompraItem": "0800080590023202500006",
        "numeroItemCompra": 6,
        "codigoUasg": "080008",
    }
    assert textual_purchase(raw) == "08000805900232025"
    assert textual_purchase(raw | {"numeroItemCompra": 7}) == "8000805900232025"
    assert textual_purchase(raw | {"codigoUasg": "999999"}) == "8000805900232025"
    assert textual_purchase(raw | {"idCompraItem": None}) == "8000805900232025"


def test_latest_version_is_not_chosen_by_price_and_tied_conflicts_remain():
    older = {"dataAtualizacaoPncp": "2026-01-01", "valor": 100}
    newer = {"dataAtualizacaoPncp": "2026-02-01", "valor": 1}
    assert latest([older, newer]) == [newer]
    assert len(latest([newer, newer | {"valor": 200}])) == 2
    assert latest([newer, newer]) == [newer]


def documents_for(raw):
    item = {
        "idCompra": raw["idCompra"],
        "idCompraItem": raw["idCompraItem"],
        "unidadeMedida": "Unidade",
    }
    result = {
        "idCompra": raw["idCompra"],
        "idCompraItem": raw["idCompraItem"],
        "niFornecedor": raw["niFornecedor"],
        "valorUnitarioHomologado": Decimal("2"),
        "quantidadeHomologada": Decimal("10"),
    }
    return item, result


def test_documentary_corroboration_requires_values_supplier_and_unit():
    raw = row(idCompraItem="00000100001")
    item, result = documents_for(raw)
    assert reconcile(raw, [item], [result])["estado"] == "corroborado_estruturalmente"
    assert (
        reconcile(raw, [item], [result | {"quantidadeHomologada": 9}])["estado"]
        == "divergencia_entre_snapshots"
    )
    assert (
        reconcile(raw, [item | {"unidadeMedida": "Caixa 12"}], [result])["estado"]
        == "nao_comparavel_documentado"
    )
    assert (
        reconcile(raw, [item], [result | {"niFornecedor": "outro"}])["estado"]
        == "inconclusivo_sem_vinculo"
    )
    assert (
        reconcile(raw, [item], [result | {"dataCancelamentoPncp": "2026-01-01"}])["estado"]
        == "inconclusivo_sem_vinculo"
    )


def test_independent_window_excludes_old_purchases_and_bulk_rows():
    pytest.importorskip("sklearn")
    from licita_ml.review_validation.confirmation import eligible_new

    base = {"group": ("x",), "quantity": Decimal(1)}
    rows = [base | {"purchase": "antiga"}, base | {"purchase": "nova"}]
    rows += [base | {"purchase": "concentrada"} for _ in range(6)]
    rows += [base | {"purchase": "sem_quantidade", "quantity": None}]
    rows += [base | {"purchase": "outro_grupo", "group": ("y",)}]
    selected, reasons = eligible_new(rows, [{"purchase": "antiga"}], ["x"])
    assert [r["purchase"] for r in selected] == ["nova"]
    assert reasons == {
        "compra_presente_historico": 1,
        "compra_com_mais_de_cinco_referencias": 6,
        "quantidade_ausente": 1,
    }


def test_pdf_zip_is_read_in_memory_and_expansion_is_bounded(tmp_path):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("../../outside.pdf", b"%PDF-test")
    assert pdf_sources(stream.getvalue()) == [("../../outside.pdf", b"%PDF-test")]
    assert not (tmp_path / "outside.pdf").exists()
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for i in range(101):
            archive.writestr(f"{i}.txt", "small")
    with pytest.raises(ValueError, match="limites"):
        pdf_sources(stream.getvalue())


def test_document_selection_is_bounded_and_ignores_inactive_files():
    docs = [
        {
            "url": str(i),
            "tipoDocumentoNome": "Edital",
            "statusAtivo": i != 0,
            "sequencialDocumento": i,
        }
        for i in range(5)
    ]
    assert [d["url"] for d in candidates(docs)] == ["1", "2"]


def test_result_publication_must_be_known_by_the_relevant_cutoff():
    pytest.importorskip("sklearn")
    from licita_ml.review_validation.result_dates import result_known

    cut = date(2026, 6, 30)
    assert result_known({"dataResultado": "2026-06-30"}, cut)
    assert not result_known({"dataResultado": "2026-07-01"}, cut)
    assert not result_known({"dataResultado": None}, cut)
    assert not result_known({"dataResultado": "invalid"}, cut)


def test_independent_dossier_does_not_reveal_ranking_or_assisted_findings(tmp_path, monkeypatch):
    import csv

    from licita_ml.review_validation import report

    monkeypatch.setattr(report, "ROOT", tmp_path)
    case = {
        "id": "caso",
        "id_compra": "1",
        "numero_item": 1,
        "preco_unitario": "2.00",
        "quantidade": "10",
        "pncp_url": "https://pncp.gov.br/app/editais/exemplo",
        "documentos_urls": [],
        "indice_paginas": [],
        "top5_if_preco_quantidade": True,
        "top5_regra_preco": False,
        "achados_assistidos": [{"tipo": "divergencia"}],
    }
    path = report.dossier([case])
    with path.open() as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        assert "top5_if_preco_quantidade" not in reader.fieldnames
        assert "achados_assistidos" not in reader.fieldnames
    assert len(rows) == 1 and rows[0]["parecer_humano"] == "pendente"
