import io
import json
from datetime import date
from types import SimpleNamespace

import pytest
from licita_collector.api import JsonScope, acquire
from licita_collector.errors import CollectionError


class HTTP:
    settings = SimpleNamespace(collector_max_download_bytes=100000, collector_attempts=2)

    def __init__(self, pages):
        self.pages = iter(pages)
        self.urls = []

    def request(self, url):
        self.urls.append(url)
        return io.BytesIO(json.dumps(next(self.pages)).encode())


def test_json_pagination_reconciles_and_stores_envelope(tmp_path):
    scope = JsonScope("contratos_api", date(2026, 9, 1), {"idCompra": "000123"})
    http = HTTP(
        [
            {"resultado": [{"id": 1}], "totalPaginas": 2, "totalRegistros": 2},
            {"resultado": [{"id": 2}], "totalPaginas": 2, "totalRegistros": 2},
        ]
    )
    download, info, _ = acquire(scope, tmp_path, http)
    data = json.loads(download.path.read_text())
    assert len(data["paginas"]) == 2 and info["membros"] == 2
    assert "pagina=2" in http.urls[1]
    assert scope.source == "comprasgov"


@pytest.mark.parametrize(
    "pages",
    [
        [{"resultado": [{"id": 1}], "totalPaginas": 2, "totalRegistros": 2}] * 2,
        [{"resultado": [{"id": 1}], "totalPaginas": 1, "totalRegistros": 2}],
    ],
)
def test_json_rejects_repeated_or_incomplete_pages(tmp_path, pages):
    scope = JsonScope("itens_api", date(2026, 9, 1), {"idCompra": "000123"})
    with pytest.raises(CollectionError):
        acquire(scope, tmp_path, HTTP(pages))
    assert not (tmp_path / scope.filename).exists()


def test_pncp_query_is_validated_and_scoped():
    with pytest.raises(ValueError):
        JsonScope(
            "documentos_compra", date(2026, 9, 1), {"cnpj": "../etc", "ano": 2026, "sequencial": 1}
        )
    scope = JsonScope(
        "documentos_contrato",
        date(2026, 9, 1),
        {"cnpj": "00000000000100", "ano": 2026, "sequencial": 1},
    )
    assert scope.url().endswith("/orgaos/00000000000100/contratos/2026/1/arquivos")


def test_json_money_preserves_original_decimal_text(tmp_path):
    scope = JsonScope("contratos_api", date(2026, 9, 1), {"idCompra": "000123"})
    payload = (
        b'{"resultado":[{"valorGlobal":123456789012.12345678}],"totalPaginas":1,"totalRegistros":1}'
    )
    http = HTTP([])
    http.request = lambda _: io.BytesIO(payload)
    download, _, _ = acquire(scope, tmp_path, http)
    page = json.loads(download.path.read_text())["paginas"][0]
    assert page["resultado"][0]["valorGlobal"] == "123456789012.12345678"
    assert page["resposta_original"] == payload.decode()


def test_historical_scope_uses_catalog_and_dates_instead_of_purchase():
    scope = JsonScope(
        "material_historico_api",
        date(2026, 9, 1),
        {"catalogo": "486374", "inicio": "2025-10-01", "fim": "2026-09-30"},
    )
    assert "codigo=486374" in scope.url()
    assert "dataCompraInicio=2025-10-01" in scope.url()
    assert "pagina=2" in scope.url(2)
    assert scope.module.startswith("historico/material/")
    with pytest.raises(ValueError):
        JsonScope(
            "material_historico_api",
            date(2026, 9, 1),
            {"catalogo": "../bad", "inicio": "2025-10-01", "fim": "2026-09-30"},
        )


def test_offline_history_requires_matching_hash_url_size_and_preserves_original(tmp_path, settings):
    import hashlib

    from licita_collector.history import CachedHistory

    scope = JsonScope(
        "material_historico_api",
        date(2026, 9, 1),
        {"catalogo": "486374", "inicio": "2025-10-01", "fim": "2026-09-30"},
    )
    raw = b'{"resultado":[{"precoUnitario":0.12345678}],"totalPaginas":1,"totalRegistros":1}'
    path = tmp_path / "historico_486374_pagina_1.json"
    path.write_bytes(raw)
    meta = {
        "url": scope.url(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "status": 200,
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta))
    http = CachedHistory(settings, scope, tmp_path)
    download, _, _ = acquire(scope, tmp_path / "output", http)
    page = json.loads(download.path.read_text())["paginas"][0]
    assert page["resposta_original"].encode() == raw
    assert page["origem_cache"]["coletado_em_utc_original"] is None
    assert page["resultado"][0]["precoUnitario"] == "0.12345678"
    path.write_bytes(raw + b" ")
    with pytest.raises(CollectionError, match="Cache histórico diverge"):
        http.request(scope.url())
