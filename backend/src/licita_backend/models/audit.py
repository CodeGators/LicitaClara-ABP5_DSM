import sqlalchemy as sa

from licita_backend.models.helpers import (
    base_fk,
    choices,
    json,
    pk,
    ref,
    table,
    text,
    timestamp,
    uid,
    unique,
)

usuarios = table(
    "usuarios",
    "auditoria",
    pk(),
    text("issuer"),
    text("subject"),
    text("nome"),
    sa.Column("papel", sa.Text(), nullable=False, server_default="leitor"),
    sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    timestamp(),
    choices("papel", ["leitor", "revisor", "administrador"]),
    unique("issuer", "subject"),
)
revisoes = table(
    "revisoes",
    "auditoria",
    pk(),
    ref("usuario_id", "usuarios"),
    ref("processo_versao_id", "processos_versoes"),
    uid("execucao_id"),
    text("status"),
    text("observacao"),
    text("conclusao", nullable=True),
    timestamp(),
    sa.ForeignKeyConstraint(
        ["processo_versao_id", "execucao_id"],
        ["avaliacoes_processo.processo_versao_id", "avaliacoes_processo.execucao_id"],
    ),
    choices("status", ["a_revisar", "em_analise", "revisado"]),
)
sa.Index("ix_revisoes_processo_data", revisoes.c.processo_versao_id, revisoes.c.criado_em)
relatorios = table(
    "relatorios",
    "relatorio",
    pk(),
    ref("usuario_id", "usuarios"),
    uid("base_id"),
    uid("execucao_id"),
    text("titulo"),
    text("formato"),
    json("parametros"),
    json("snapshot"),
    sa.Column("status", sa.Text(), nullable=False, server_default="pendente"),
    text("chave_objeto", nullable=True),
    text("sha256", nullable=True),
    text("erro", nullable=True),
    timestamp(),
    timestamp("concluido_em", nullable=True, now=False),
    base_fk("execucoes_analise", "execucao_id"),
    choices("formato", ["pdf", "csv"]),
    choices("status", ["pendente", "processando", "concluido", "falhou"]),
)
