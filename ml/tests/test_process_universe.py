"""Universo de compra não é a contagem de linhas nem de versões da API."""

import io
import json
from hashlib import sha256

import pytest
from licita_ml.analytical.rules import canonical
from licita_ml.inference.process_sources import envelope, universe_from_rows
from licita_shared.storage.local import LocalObjectStorage


def result(**changes):
    return {
        "idCompra": "0001",
        "idCompraItem": "000101",
        "niFornecedor": "001",
        "sequencialResultado": 1,
        "nomeRazaoSocialFornecedor": "A",
        "dataAtualizacaoPncp": "2026-10-01T10:00:00",
        "dataCancelamentoPncp": None,
        **changes,
    }


def test_item_versions_are_counted_once_and_canceled_winners_are_not_active():
    items = [{"idCompraItem": "000101"}] * 3 + [{"idCompraItem": "000102"}]
    results = [
        result(),
        result(dataAtualizacaoPncp="2026-10-02T10:00:00", dataCancelamentoPncp="2026-10-02"),
        result(niFornecedor="002", sequencialResultado=2),
    ]
    universe = universe_from_rows(items, results, [])
    assert universe["itens"] == ["000101", "000102"]
    assert universe["resultados_ativos"] == {"000101": [["002", 2]], "000102": []}


def test_conflicting_result_versions_prevent_confirming_universe():
    universe = universe_from_rows(
        [{"idCompraItem": "000101"}], [result(), result(quantidadeHomologada="2")], []
    )
    assert (
        universe["status"] == "nao_confirmado"
        and universe["motivo"] == "CONFLITO_RESULTADO_OFICIAL"
    )


def test_envelope_reconciles_original_decimals_and_counts(tmp_path):
    objects = LocalObjectStorage(tmp_path)
    original = (
        '{"resultado":[{"idCompra":"0001","idCompraItem":"000101",'
        '"quantidade":0.00000000}],"totalRegistros":1,"totalPaginas":1}'
    )
    page = {
        "pagina": 1,
        "resultado": [{"idCompra": "0001", "idCompraItem": "000101", "quantidade": "0E-8"}],
        "resposta_original": original,
    }
    body = {
        "schema": "licita-json-v1",
        "kind": "itens_api",
        "query": {"idCompra": "0001"},
        "paginas": [page],
    }
    raw = canonical(body).encode()
    objects.put("raw/a.json", io.BytesIO(raw))
    artifact = {"chave_objeto": "raw/a.json", "sha256": sha256(raw).hexdigest()}
    assert envelope(objects, artifact)[1] == "0001"
    page["resultado"][0]["quantidade"] = "99"
    raw = canonical(body).encode()
    objects.put("raw/b.json", io.BytesIO(raw))
    with pytest.raises(ValueError, match="Paginação/original"):
        envelope(objects, {"chave_objeto": "raw/b.json", "sha256": sha256(raw).hexdigest()})


def test_record_from_other_purchase_cannot_confirm_scope(tmp_path):
    objects = LocalObjectStorage(tmp_path)
    rows = [{"idCompra": "0002", "idCompraItem": "000201"}]
    page = {
        "pagina": 1,
        "resultado": rows,
        "resposta_original": json.dumps(
            {"resultado": rows, "totalRegistros": 1, "totalPaginas": 1}
        ),
    }
    body = {
        "schema": "licita-json-v1",
        "kind": "itens_api",
        "query": {"idCompra": "0001"},
        "paginas": [page],
    }
    raw = canonical(body).encode()
    objects.put("raw/a.json", io.BytesIO(raw))
    with pytest.raises(ValueError, match="outra compra"):
        envelope(objects, {"chave_objeto": "raw/a.json", "sha256": sha256(raw).hexdigest()})
