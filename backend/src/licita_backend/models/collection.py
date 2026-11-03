import sqlalchemy as sa

from licita_backend.models.helpers import (
    check,
    choices,
    json,
    pk,
    ref,
    table,
    text,
    timestamp,
    unique,
)

execucoes_coleta = table(
    "execucoes_coleta",
    "coleta",
    pk(),
    text("fonte"),
    text("modulo"),
    sa.Column("competencia_inicio", sa.Date(), nullable=False),
    sa.Column("competencia_fim", sa.Date(), nullable=False),
    sa.Column("status", sa.Text(), nullable=False, server_default="pendente"),
    json("parametros"),
    timestamp(),
    timestamp("iniciado_em", nullable=True, now=False),
    timestamp("concluido_em", nullable=True, now=False),
    text("erro", nullable=True),
    choices("status", ["pendente", "executando", "concluido", "parcial", "falhou"]),
    check("competencia_inicio <= competencia_fim", "intervalo_ordenado"),
    check(
        "extract(day from competencia_inicio) = 1 AND extract(day from competencia_fim) = 1",
        "competencias_mensais",
    ),
    check(
        "concluido_em IS NULL OR (iniciado_em IS NOT NULL AND concluido_em >= iniciado_em)",
        "horarios_ordenados",
    ),
)
# Impede jobs concorrentes conflitantes de um mesmo intervalo; a janela será travada no coletor.
sa.Index(
    "ix_coleta_fonte_modulo_status",
    execucoes_coleta.c.fonte,
    execucoes_coleta.c.modulo,
    execucoes_coleta.c.status,
)

arquivos_coletados = table(
    "arquivos_coletados",
    "coleta",
    pk(),
    text("fonte"),
    text("modulo"),
    sa.Column("competencia", sa.Date(), nullable=False),
    text("url_origem"),
    text("url_final"),
    text("sha256"),
    sa.Column("tamanho_bytes", sa.BigInteger(), nullable=False),
    text("chave_objeto"),
    text("etag", nullable=True),
    timestamp("coletado_em"),
    check("sha256 ~ '^[0-9a-f]{64}$'", "sha256_hex"),
    check("tamanho_bytes >= 0", "tamanho_nao_negativo"),
    check("extract(day from competencia) = 1", "competencia_mensal"),
    unique("fonte", "modulo", "competencia", "sha256"),
    unique("chave_objeto"),
)
execucoes_arquivos = table(
    "execucoes_arquivos",
    "coleta",
    sa.Column("execucao_id", sa.Uuid(), sa.ForeignKey("execucoes_coleta.id"), primary_key=True),
    sa.Column("arquivo_id", sa.Uuid(), sa.ForeignKey("arquivos_coletados.id"), primary_key=True),
    timestamp("observado_em"),
)
importacoes = table(
    "importacoes",
    "importacao",
    pk(),
    ref("arquivo_id", "arquivos_coletados"),
    text("versao_importador"),
    sa.Column("status", sa.Text(), nullable=False, server_default="pendente"),
    sa.Column("aceitos", sa.BigInteger(), nullable=False, server_default="0"),
    sa.Column("rejeitados", sa.BigInteger(), nullable=False, server_default="0"),
    json("diagnostico"),
    timestamp(),
    timestamp("concluido_em", nullable=True, now=False),
    choices("status", ["pendente", "executando", "concluido", "parcial", "falhou"]),
    check("aceitos >= 0 AND rejeitados >= 0", "contagens_nao_negativas"),
    unique("arquivo_id", "versao_importador"),
)
versoes_base = table(
    "versoes_base",
    "base",
    pk(),
    text("versao"),
    text("versao_transformador"),
    text("versao_codigo"),
    text("chave_manifesto"),
    text("sha256_manifesto"),
    sa.Column("periodo_inicio", sa.Date(), nullable=False),
    sa.Column("periodo_fim", sa.Date(), nullable=False),
    sa.Column("status", sa.Text(), nullable=False, server_default="preparando"),
    json("recorte"),
    json("qualidade"),
    timestamp(),
    choices("status", ["preparando", "validada", "rejeitada"]),
    check("periodo_inicio <= periodo_fim", "periodo_ordenado"),
    check("sha256_manifesto ~ '^[0-9a-f]{64}$'", "sha256_manifesto_hex"),
    unique("versao"),
)
base_importacoes = table(
    "base_importacoes",
    "base",
    sa.Column("base_id", sa.Uuid(), sa.ForeignKey("versoes_base.id"), primary_key=True),
    sa.Column("importacao_id", sa.Uuid(), sa.ForeignKey("importacoes.id"), primary_key=True),
)
