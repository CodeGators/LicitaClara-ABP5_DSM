"""Contrato de leitura v1: CSV UTF-8 com ponto e vírgula e envelopes JSON versionados."""

import csv
import hashlib
import io
import json
from contextlib import contextmanager
from decimal import Decimal
from tempfile import TemporaryFile
from zipfile import ZipFile

REQUIRED = {
    "material": {
        "id_compra",
        "id_compra_item",
        "id_item_compra",
        "ni_fornecedor",
        "codigo_item_catalogo",
        "preco_unitario",
        "data_compra",
        "forma",
        "descricao_item",
        "nome_fornecedor",
    },
    "compra": {
        "id_compra",
        "codigo_orgao",
        "orgao_entidade_razao_social",
        "ano_compra_pncp",
        "numero_compra",
        "objeto_compra",
        "data_atualizacao_pncp",
    },
    "compra_item": {
        "id_compra",
        "id_compra_item",
        "numero_item_pncp",
        "descricao_detalhada",
        "data_atualizacao_pncp",
    },
    "item_resultado": {
        "nome_razao_social_fornecedor",
        "id_compra",
        "id_compra_item",
        "ni_fornecedor",
        "sequencial_resultado",
        "srk_item_resultado",
        "data_atualizacao_pncp",
    },
    "propostas": {
        "id",
        "id_compra",
        "id_compra_item",
        "identificacao_participante",
        "valor_proposta_calculado",
        "classificacao",
        "data_hora_alteracao",
    },
    "compra_api": {"idCompra", "codigoOrgao", "anoCompraPncp", "numeroCompra", "objetoCompra"},
    "itens_api": {"idCompra", "idCompraItem", "numeroItemPncp"},
    "resultados_api": {
        "nomeRazaoSocialFornecedor",
        "idCompra",
        "idCompraItem",
        "niFornecedor",
        "sequencialResultado",
    },
    "contratos_api": {"numeroContrato", "numeroControlePncpContrato", "idCompra"},
    "contrato_pncp": {"numeroControlePNCP", "numeroContratoEmpenho", "numeroControlePncpCompra"},
    "documentos_compra": {"sequencialDocumento", "url"},
    "documentos_contrato": {"sequencialDocumento", "url"},
}


class SchemaError(ValueError):
    code = "ESQUEMA_INCOMPATIVEL"

    def __init__(self, message, missing=()):
        self.diagnostic = {"motivo": message, "colunas_ausentes": sorted(missing)}
        super().__init__(message)


def kind_of(file):
    parts = file["modulo"].split("/")
    kind = parts[1] if parts[0] == "api" else parts[-1]
    if kind not in REQUIRED:
        raise SchemaError("Módulo não suportado pelo leitor v1")
    return kind


@contextmanager
def staged(objects, file, settings):
    with TemporaryFile() as temp:
        digest, size = hashlib.sha256(), 0
        with objects.open(file["chave_objeto"]) as source:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > settings.processing_max_file_bytes:
                    raise SchemaError("Arquivo excede o limite de leitura")
                digest.update(chunk)
                temp.write(chunk)
        if size != file["tamanho_bytes"] or digest.hexdigest() != file["sha256"]:
            raise SchemaError("Arquivo diverge do hash/tamanho registrado")
        temp.seek(0)
        yield temp


def records(objects, file, settings):
    kind = kind_of(file)
    required = REQUIRED[kind]
    with staged(objects, file, settings) as stream:
        if file["chave_objeto"].endswith(".json"):
            data = json.load(stream, parse_float=Decimal)
            if data.get("schema") != "licita-json-v1" or data.get("kind") != kind:
                raise SchemaError("Versão de envelope incompatível")
            for page in data["paginas"]:
                for index, row in enumerate(page["resultado"], 1):
                    if not isinstance(row, dict) or not required.issubset(row):
                        raise SchemaError(
                            "Campos obrigatórios ausentes no JSON",
                            required - set(row) if isinstance(row, dict) else required,
                        )
                    yield f"pagina-{page['pagina']}.json", index, row, data["query"]
            return
        with ZipFile(stream) as archive:
            entries = archive.infolist()
            if (
                not entries
                or len(entries) > 32
                or sum(e.file_size for e in entries) > settings.processing_max_uncompressed_bytes
            ):
                raise SchemaError("Limites do ZIP excedidos")
            for entry in entries:
                if not entry.filename.lower().endswith(".csv"):
                    raise SchemaError("Membro não CSV")
                with archive.open(entry) as member:
                    reader = csv.DictReader(
                        io.TextIOWrapper(member, encoding="utf-8-sig", newline=""), delimiter=";"
                    )
                    if (
                        reader.fieldnames is None
                        or not required.issubset(reader.fieldnames)
                        or len(reader.fieldnames) != len(set(reader.fieldnames))
                    ):
                        raise SchemaError(
                            "Cabeçalho CSV incompatível com o leitor v1",
                            required - set(reader.fieldnames or []),
                        )
                    for line, row in enumerate(reader, 2):
                        if None in row or any(v is None for v in row.values()):
                            raise SchemaError("Número de colunas incompatível")
                        yield entry.filename, line, row, {}
