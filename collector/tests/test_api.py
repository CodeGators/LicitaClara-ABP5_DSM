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
