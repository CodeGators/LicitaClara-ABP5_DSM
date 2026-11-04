"""Dicionário e conversões da base organizada v1; nenhuma imputação."""

import csv
import json
from datetime import date
from decimal import Decimal, localcontext

import pyarrow as pa
import pyarrow.parquet as pq

from licita_ml.normalize import RowError, boolean, day, instant, money, text

# Output name -> (source column, logical type). IDs always remain text.
FIELDS = {
    "compras": {
        "id_compra": ("id_compra", "texto"),
        "numero_compra": ("numero_compra", "texto"),
        "numero_processo": ("processo", "texto"),
        "numero_controle_pncp": ("numero_controle_PNCP", "texto"),
        "objeto": ("objeto_compra", "texto"),
        "orgao_codigo": ("codigo_orgao", "texto"),
        "orgao_cnpj": ("orgao_entidade_cnpj", "texto"),
        "orgao_nome": ("orgao_entidade_razao_social", "texto"),
        "unidade_orgao": ("unidade_orgao_codigo_unidade", "texto"),
        "uf": ("unidade_orgao_uf_sigla", "texto"),
        "municipio": ("unidade_orgao_municipio_nome", "texto"),
        "modalidade_codigo": ("codigo_modalidade", "texto"),
        "modalidade_nome": ("modalidade_nome", "texto"),
        "modo_disputa_codigo": ("codigo_modo_disputa", "texto"),
        "data_publicacao": ("data_publicacao_pncp", "data"),
        "abertura_propostas": ("data_abertura_proposta_pncp", "instante"),
        "encerramento_propostas": ("data_encerramento_proposta_pncp", "instante"),
        "valor_estimado": ("valor_total_estimado", "decimal"),
        "valor_homologado": ("valor_total_homologado", "decimal"),
        "situacao": ("situacao_compra_nome_pncp", "texto"),
        "excluida": ("contratacao_excluida", "booleano"),
    },
    "itens": {
        "id_compra": ("id_compra", "texto"),
        "id_compra_item": ("id_compra_item", "texto"),
        "numero_item": ("numero_item_pncp", "texto"),
        "descricao_detalhada": ("descricao_detalhada", "texto"),
        "descricao_resumida": ("descricao_resumida", "texto"),
        "catalogo_original": ("cod_item_catalogo", "texto"),
        "classe": ("codigo_classe", "texto"),
        "grupo": ("codigo_grupo", "texto"),
        "material_ou_servico": ("material_ou_servico", "texto"),
        "unidade": ("unidade_medida", "texto"),
        "quantidade": ("quantidade", "decimal"),
        "preco_unitario_estimado": ("valor_unitario_estimado", "decimal"),
        "valor_total_estimado": ("valor_total", "decimal"),
        "orcamento_sigiloso": ("orcamento_sigiloso", "booleano"),
        "situacao": ("situacao_compra_item_nome", "texto"),
        "criterio_julgamento": ("criterio_julgamento_id_pncp", "texto"),
    },
    "resultados": {
        "id_compra": ("id_compra", "texto"),
        "id_compra_item": ("id_compra_item", "texto"),
        "sequencial": ("sequencial_resultado", "texto"),
        "chave_origem": ("srk_item_resultado", "texto"),
        "fornecedor": ("ni_fornecedor", "texto"),
        "fornecedor_nome": ("nome_razao_social_fornecedor", "texto"),
        "tipo_pessoa": ("tipo_pessoa", "texto"),
        "quantidade": ("quantidade_homologada", "decimal"),
        "preco_unitario": ("valor_unitario_homologado", "decimal"),
        "valor_total": ("valor_total_homologado", "decimal"),
        "data_resultado": ("data_resultado_pncp", "data"),
        "data_cancelamento": ("data_cancelamento_pncp", "data"),
        "situacao_codigo": ("situacao_compra_item_resultado_id", "texto"),
        "situacao": ("situacao_compra_item_resultado_nome", "texto"),
        "orgao_cnpj": ("orgao_entidade_cnpj", "texto"),
        "uf": ("unidade_orgao_uf_sigla", "texto"),
        "moeda_estrangeira_id": ("moeda_estrangeira_id", "texto"),
        "valor_nominal_moeda_estrangeira": ("valor_nominal_moeda_estrangeira", "decimal"),
        "data_cotacao_moeda_estrangeira": ("data_cotacao_moeda_estrangeira", "instante"),
    },
    "referencias": {
        "id_compra": ("id_compra", "texto"),
        "id_compra_item": ("id_compra_item", "texto"),
        "id_item_fonte": ("id_item_compra", "texto"),
        "forma": ("forma", "texto"),
        "catalogo": ("codigo_item_catalogo", "texto"),
        "classe": ("codigo_classe", "texto"),
        "grupo": ("codigo_grupo", "texto"),
        "descricao": ("descricao_item", "texto"),
        "descricao_detalhada": ("descricao_detalhada_item", "texto"),
        "unidade_fornecimento_sigla": ("sigla_unidade_fornecimento", "texto"),
        "unidade_fornecimento_nome": ("nome_unidade_fornecimento", "texto"),
        "capacidade": ("capacidade_unidade_fornecimento", "decimal"),
        "unidade_medida_sigla": ("sigla_unidade_medida", "texto"),
        "unidade_medida_nome": ("nome_unidade_medida", "texto"),
        "quantidade": ("quantidade", "decimal"),
        "preco_unitario": ("preco_unitario", "decimal"),
        "data_compra": ("data_compra", "data"),
        "data_resultado": ("data_resultado", "data"),
        "fornecedor": ("ni_fornecedor", "texto"),
        "fornecedor_nome": ("nome_fornecedor", "texto"),
        "marca": ("marca", "texto"),
        "orgao_codigo": ("codigo_orgao", "texto"),
        "orgao_nome": ("nome_orgao", "texto"),
        "uasg": ("codigo_uasg", "texto"),
        "uf": ("estado", "texto"),
        "municipio_codigo": ("codigo_municipio", "texto"),
        "modalidade": ("modalidade", "texto"),
    },
}
IDENTITY = {
    "compras": ("id_compra",),
    "itens": ("id_compra", "id_compra_item"),
    "resultados": ("id_compra", "id_compra_item", "sequencial_resultado"),
    "referencias": ("id_compra", "id_item_compra", "ni_fornecedor", "forma"),
}
COMMON = {
    "id_registro": "texto",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
    "competencia_arquivo": "texto",
    "atualizacao_primaria": "texto",
    "atualizacao_secundaria": "texto",
    "avisos_json": "texto",
}
TYPES = {
    "texto": pa.string(),
    "instante": pa.string(),
    "data": pa.date32(),
    "decimal": pa.decimal128(28, 8),
    "inteiro": pa.int64(),
    "booleano": pa.bool_(),
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def convert(value, kind):
    if kind == "texto":
        return text(value)
    if kind == "decimal":
        value = money(value)
        if value is None:
            return None
        with localcontext() as context:
            context.prec = 38
            return format(value.quantize(Decimal("0.00000001")), "f")
    if kind == "data":
        value = day(value)
        return value.isoformat() if value else None
    if kind == "instante":
        value = instant(value)
        return value.isoformat() if value else None
    return boolean(value)


def transform(table, raw):
    values, warnings = {}, []
    for field, (source, kind) in FIELDS[table].items():
        try:
            values[field] = convert(raw.get(source), kind)
        except RowError as exc:
            values[field] = None
            warnings.append({"campo": field, "motivo": exc.code})
    for field in ("preco_unitario", "quantidade", "preco_unitario_estimado"):
        if values.get(field) == "0.00000000":
            warnings.append({"campo": field, "motivo": "ZERO_CONHECIDO_NAO_E_AUSENCIA"})
    if table == "resultados":
        # Invalid cancellation date remains a warning; never assert active from an invalid value.
        values["cancelamento_informado"] = bool(text(raw.get("data_cancelamento_pncp")))
    return values, warnings


def dictionary():
    result = {}
    for table, fields in FIELDS.items():
        result[table] = {
            **{name: {"tipo": kind, "origem": source} for name, (source, kind) in fields.items()},
            **{name: {"tipo": kind, "origem": "proveniencia"} for name, kind in COMMON.items()},
        }
    result["resultados"]["cancelamento_informado"] = {
        "tipo": "booleano",
        "origem": "data_cancelamento_pncp preenchida na fonte",
    }
    return result


class Export:
    """Escrita em lotes; CSV usa ponto decimal, ;, UTF-8 e vazio para null."""

    def __init__(self, folder, name, fields):
        self.name, self.fields, self.count = name, fields, 0
        self.buffer = []
        self.schema = pa.schema([(field, TYPES[kind]) for field, kind in fields.items()])
        self.parquet = pq.ParquetWriter(folder / f"{name}.parquet", self.schema, compression="zstd")
        self.stream = (folder / f"{name}.csv").open("w", encoding="utf-8", newline="")
        self.csv = csv.DictWriter(self.stream, fieldnames=list(fields), delimiter=";")
        self.csv.writeheader()

    def add(self, row):
        row = {key: row.get(key) for key in self.fields}
        self.csv.writerow(row)
        typed = dict(row)
        for field, kind in self.fields.items():
            if typed[field] is not None:
                if kind == "decimal":
                    typed[field] = Decimal(typed[field])
                elif kind == "data":
                    typed[field] = date.fromisoformat(typed[field])
        self.buffer.append(typed)
        self.count += 1
        if len(self.buffer) >= 2000:
            self.flush()

    def flush(self):
        if self.buffer:
            self.parquet.write_table(pa.Table.from_pylist(self.buffer, schema=self.schema))
            self.buffer.clear()

    def close(self):
        self.flush()
        self.parquet.close()
        self.stream.close()
