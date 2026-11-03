"""Domínios diagnosticados: propostas Compras.gov.br, contratos e anexos PNCP."""

import sqlalchemy as sa

from licita_backend.models.helpers import (
    MONEY,
    base_fk,
    check,
    json,
    pk,
    ref,
    table,
    text,
    timestamp,
    uid,
    unique,
)

participacoes = table(
    "participacoes",
    "dados",
    pk(),
    ref("base_id", "versoes_base"),
    uid("processo_versao_id"),
    uid("item_versao_id"),
    ref("fornecedor_id", "fornecedores", nullable=True),
    text("fonte"),
    text("chave_origem"),
    text("identificacao_participante", nullable=True),
    text("nome_participante", nullable=True),
    sa.Column("valor_proposta", MONEY, nullable=True),
    sa.Column("valor_lance", MONEY, nullable=True),
    sa.Column("valor_negociado", MONEY, nullable=True),
    sa.Column("classificacao", sa.Integer(), nullable=True),
    text("situacao_proposta", nullable=True),
    text("situacao_item", nullable=True),
    sa.Column("homologado", sa.Boolean(), nullable=True),
    # Timestamps CSV não contêm offset; preservar a hora civil, sem inventar UTC.
    sa.Column("incluido_na_origem_em", sa.DateTime(timezone=False), nullable=True),
    sa.Column("alterado_na_origem_em", sa.DateTime(timezone=False), nullable=True),
    json("atributos_origem"),
    timestamp(),
    base_fk("processos_versoes", "processo_versao_id"),
    sa.ForeignKeyConstraint(
        ["item_versao_id", "processo_versao_id", "base_id"],
        ["itens_versoes.id", "itens_versoes.processo_versao_id", "itens_versoes.base_id"],
    ),
    unique("base_id", "fonte", "chave_origem"),
    unique("id", "base_id"),
    check("classificacao IS NULL OR classificacao >= 1", "classificacao_positiva"),
    *[
        check(f"{name} IS NULL OR {name} >= 0", f"{name}_nao_negativo")
        for name in ("valor_proposta", "valor_lance", "valor_negociado")
    ],
)
sa.Index("ix_participacoes_item", participacoes.c.item_versao_id)
sa.Index("ix_participacoes_fornecedor_base", participacoes.c.fornecedor_id, participacoes.c.base_id)

contratos = table(
    "contratos",
    "identidade",
    pk(),
    text("fonte"),
    text("chave_oficial"),
    timestamp(),
    unique("fonte", "chave_oficial"),
)
contratos_versoes = table(
    "contratos_versoes",
    "dados",
    pk(),
    ref("base_id", "versoes_base"),
    ref("contrato_id", "contratos"),
    ref("orgao_id", "orgaos", nullable=True),
    ref("fornecedor_id", "fornecedores", nullable=True),
    text("numero_contrato"),
    text("numero_controle_pncp", nullable=True),
    text("codigo_unidade_gestora", nullable=True),
    text("fornecedor_nome", nullable=True),
    text("objeto", nullable=True),
    sa.Column("data_assinatura", sa.Date(), nullable=True),
    sa.Column("data_vigencia_inicio", sa.Date(), nullable=True),
    sa.Column("data_vigencia_fim", sa.Date(), nullable=True),
    sa.Column("valor_global", MONEY, nullable=True),
    sa.Column("valor_acumulado", MONEY, nullable=True),
    sa.Column("excluido", sa.Boolean(), nullable=True),
    json("atributos_origem"),
    timestamp(),
    unique("contrato_id", "base_id"),
    unique("id", "base_id"),
    check("valor_global IS NULL OR valor_global >= 0", "global_nao_negativo"),
    check("valor_acumulado IS NULL OR valor_acumulado >= 0", "acumulado_nao_negativo"),
)
sa.Index(
    "ix_contratos_fornecedor_vigencia",
    contratos_versoes.c.fornecedor_id,
    contratos_versoes.c.data_vigencia_inicio,
)
contratos_processos = table(
    "contratos_processos",
    "dados",
    pk(),
    ref("base_id", "versoes_base"),
    uid("contrato_versao_id"),
    uid("processo_versao_id"),
    text("tipo_chave_vinculo"),
    text("chave_vinculo"),
    json("atributos_origem"),
    timestamp(),
    base_fk("contratos_versoes", "contrato_versao_id"),
    base_fk("processos_versoes", "processo_versao_id"),
    unique("base_id", "contrato_versao_id", "processo_versao_id"),
    unique("id", "base_id"),
    check("tipo_chave_vinculo IN ('idCompra', 'numeroControlePncpCompra')", "vinculo_verificavel"),
)
sa.Index("ix_contratos_processos_processo", contratos_processos.c.processo_versao_id)

documentos = table(
    "documentos",
    "dados",
    pk(),
    ref("base_id", "versoes_base"),
    uid("processo_versao_id", nullable=True),
    uid("contrato_versao_id", nullable=True),
    text("fonte"),
    text("chave_origem"),
    sa.Column("sequencial_documento", sa.Integer(), nullable=False),
    text("tipo_codigo", nullable=True),
    text("tipo_nome", nullable=True),
    text("titulo", nullable=True),
    text("url_origem"),
    sa.Column("ativo", sa.Boolean(), nullable=True),
    sa.Column("publicado_na_origem_em", sa.DateTime(timezone=False), nullable=True),
    # Metadados podem ser importados antes de baixar o binário.
    text("chave_objeto", nullable=True),
    text("sha256", nullable=True),
    sa.Column("tamanho_bytes", sa.BigInteger(), nullable=True),
    json("atributos_origem"),
    timestamp(),
    base_fk("processos_versoes", "processo_versao_id"),
    base_fk("contratos_versoes", "contrato_versao_id"),
    unique("base_id", "fonte", "chave_origem"),
    unique("id", "base_id"),
    check("num_nonnulls(processo_versao_id, contrato_versao_id) = 1", "um_alvo"),
    check("sequencial_documento >= 1", "sequencial_positivo"),
    check("sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'", "sha256_hex"),
    check("tamanho_bytes IS NULL OR tamanho_bytes >= 0", "tamanho_nao_negativo"),
    check("num_nonnulls(chave_objeto, sha256, tamanho_bytes) IN (0, 3)", "objeto_completo"),
)
sa.Index("ix_documentos_processo", documentos.c.processo_versao_id)
sa.Index("ix_documentos_contrato", documentos.c.contrato_versao_id)
