"""Aquisição de respostas JSON oficiais com paginação e escopo explícito."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from licita_collector.errors import CollectionError, InvalidArchive
from licita_collector.http import Download

API = "https://dadosabertos.compras.gov.br"
PNCP = "https://pncp.gov.br/api/pncp/v1"
ENDPOINTS = {
    "compra_api": "/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id",
    "itens_api": "/modulo-contratacoes/2.1_consultarItensContratacoes_PNCP_14133_Id",
    "resultados_api": "/modulo-contratacoes/3.1_consultarResultadoItensContratacoes_PNCP_14133_Id",
    "contratos_api": "/modulo-contratos/1.1_consultarContratos_Id",
    "contrato_pncp": "contratos",
    "documentos_compra": "compras",
    "documentos_contrato": "contratos",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class JsonScope:
    kind: str
    competence: date
    query: dict
    is_json = True

    def __post_init__(self):
        if self.kind not in ENDPOINTS or self.competence.day != 1:
            raise ValueError("Escopo JSON inválido")
        if self.kind.endswith("_api"):
            value = self.query.get("idCompra", "")
            if not value.isdigit():
                raise ValueError("idCompra deve conter somente dígitos")
        else:
            if (
                not str(self.query.get("cnpj", "")).isdigit()
                or len(str(self.query["cnpj"])) != 14
                or int(self.query["ano"]) < 2000
                or int(self.query["sequencial"]) < 1
            ):
                raise ValueError("Controle PNCP inválido")

    @property
    def source(self):
        return "comprasgov" if self.kind.endswith("_api") else "pncp"

    @property
    def module(self):
        digest = hashlib.sha256(canonical(self.query).encode()).hexdigest()[:20]
        return f"api/{self.kind}/{digest}"

    @property
    def filename(self):
        return self.kind + ".json"

    @property
    def parameters(self):
        return {
            "connector": "json-v1",
            "kind": self.kind,
            "query": self.query,
            "competencia_semantica": "janela_referencia_da_coleta",
        }

    def url(self, page=1):
        if self.source == "comprasgov":
            return (
                API
                + ENDPOINTS[self.kind]
                + "?"
                + urlencode(
                    {
                        "tipo": "idCompra",
                        "codigo": self.query["idCompra"],
                        "pagina": page,
                        "tamanhoPagina": 500,
                    }
                )
            )
        url = (
            f"{PNCP}/orgaos/{self.query['cnpj']}/{ENDPOINTS[self.kind]}/"
            f"{int(self.query['ano'])}/{int(self.query['sequencial'])}"
        )
        return url + ("/arquivos" if self.kind.startswith("documentos_") else "")


def acquire(scope, folder, http):
    folder.mkdir(parents=True, exist_ok=True)
    pages, seen, total_bytes = [], set(), 0
    expected_total = None
    for number in range(1, 101):
        url = scope.url(number)
        with http.request(url) as response:
            raw = response.read(http.settings.collector_max_download_bytes + 1)
            total_bytes += len(raw)
            if total_bytes > http.settings.collector_max_download_bytes:
                raise InvalidArchive("JSON excede o limite de aquisição")
            try:
                payload = json.loads(raw, parse_float=Decimal)
            except (ValueError, UnicodeError):
                raise InvalidArchive("Resposta não é JSON válido") from None
        if scope.source == "comprasgov":
            if not isinstance(payload, dict) or not isinstance(payload.get("resultado"), list):
                raise InvalidArchive("Formato inesperado da API Compras.gov.br")
            rows = payload["resultado"]
            total = int(payload["totalRegistros"])
            count = int(payload["totalPaginas"])
            if total < 0 or count < 0 or (expected_total is not None and expected_total != total):
                raise CollectionError("Total da consulta mudou durante a paginação")
            expected_total = total
            digest = hashlib.sha256(canonical(rows).encode()).hexdigest()
            if rows and digest in seen:
                raise CollectionError("API repetiu página; lote incompleto não será publicado")
            seen.add(digest)
        else:
            rows = payload if isinstance(payload, list) else [payload]
            if not all(isinstance(row, dict) for row in rows):
                raise InvalidArchive("Formato inesperado do PNCP")
            count = 1
        pages.append(
            {
                "url": url,
                "pagina": number,
                "resultado": rows,
                "resposta_original": raw.decode("utf-8"),
            }
        )
        if number >= count:
            break
    else:
        raise CollectionError("Paginação ultrapassou limite de 100 páginas")
    if expected_total is not None and sum(len(p["resultado"]) for p in pages) != expected_total:
        raise CollectionError("Total de linhas não reconcilia com a API")
    envelope = {
        "schema": "licita-json-v1",
        "kind": scope.kind,
        "query": scope.query,
        "paginas": pages,
    }
    path = folder / scope.filename
    content = canonical(envelope).encode("utf-8")
    if len(content) > http.settings.collector_max_download_bytes:
        raise InvalidArchive("Envelope JSON excede limite de aquisição")
    path.write_bytes(content)
    return Download(path, scope.url(), None), validate_json(path), scope.url()


def validate_json(path):
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
        assert data["schema"] == "licita-json-v1" and data["kind"] in ENDPOINTS
        assert isinstance(data["paginas"], list)
        assert all(isinstance(p["resultado"], list) for p in data["paginas"])
    except (ValueError, KeyError, TypeError, AssertionError):
        raise InvalidArchive("Envelope JSON inválido") from None
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "membros": len(data["paginas"]),
    }
