import sqlalchemy as sa

from licita_backend.models.helpers import (
    MONEY,
    SCORE,
    base_fk,
    check,
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

versoes_modelo = table(
    "versoes_modelo",
    "analise",
    pk(),
    ref("base_treino_id", "versoes_base"),
    text("algoritmo"),
    text("versao"),
    text("versao_codigo"),
    text("chave_artefato"),
    text("sha256_artefato"),
    json("parametros"),
    json("metricas"),
    json("preprocessamento"),
    timestamp(),
    unique("algoritmo", "versao"),
    check("sha256_artefato ~ '^[0-9a-f]{64}$'", "sha256_artefato_hex"),
)
execucoes_analise = table(
    "execucoes_analise",
    "analise",
    pk(),
    ref("base_id", "versoes_base"),
    text("versao_politica_score"),
    json("configuracao"),
    sa.Column("status", sa.Text(), nullable=False, server_default="pendente"),
    timestamp(),
    timestamp("concluido_em", nullable=True, now=False),
    text("erro", nullable=True),
    choices("status", ["pendente", "executando", "concluida", "falhou"]),
    unique("id", "base_id"),
)
execucoes_modelos = table(
    "execucoes_modelos",
    "analise",
    sa.Column("execucao_id", sa.Uuid(), sa.ForeignKey("execucoes_analise.id"), primary_key=True),
    sa.Column("modelo_id", sa.Uuid(), sa.ForeignKey("versoes_modelo.id"), primary_key=True),
)
resultados_modelo = table(
    "resultados_modelo",
    "analise",
    pk(),
    uid("base_id"),
    uid("execucao_id"),
    uid("modelo_id"),
    uid("processo_versao_id"),
    uid("item_versao_id", nullable=True),
    uid("resultado_item_id", nullable=True),
    text("tipo_alvo"),
    sa.Column("score_bruto", sa.Numeric(30, 12), nullable=False),
    sa.Column("score_normalizado", SCORE, nullable=False),
    text("versao_normalizacao"),
    json("atributos"),
    timestamp(),
    base_fk("execucoes_analise", "execucao_id"),
    base_fk("processos_versoes", "processo_versao_id"),
    sa.ForeignKeyConstraint(
        ["execucao_id", "modelo_id"],
        ["execucoes_modelos.execucao_id", "execucoes_modelos.modelo_id"],
    ),
    sa.ForeignKeyConstraint(
        ["item_versao_id", "processo_versao_id", "base_id"],
        ["itens_versoes.id", "itens_versoes.processo_versao_id", "itens_versoes.base_id"],
    ),
    sa.ForeignKeyConstraint(
        ["resultado_item_id", "item_versao_id", "base_id"],
        ["resultados_itens.id", "resultados_itens.item_versao_id", "resultados_itens.base_id"],
    ),
    choices("tipo_alvo", ["processo", "item", "resultado"]),
    check(
        "(tipo_alvo = 'processo' AND item_versao_id IS NULL AND resultado_item_id IS NULL) OR "
        "(tipo_alvo = 'item' AND item_versao_id IS NOT NULL AND resultado_item_id IS NULL) OR "
        "(tipo_alvo = 'resultado' AND item_versao_id IS NOT NULL "
        "AND resultado_item_id IS NOT NULL)",
        "alvo_coerente",
    ),
    check("score_normalizado BETWEEN 0 AND 100", "score_intervalo"),
    sa.UniqueConstraint(
        "execucao_id",
        "modelo_id",
        "processo_versao_id",
        "item_versao_id",
        "resultado_item_id",
        postgresql_nulls_not_distinct=True,
    ),
)
sa.Index(
    "ix_modelo_execucao_score",
    resultados_modelo.c.execucao_id,
    resultados_modelo.c.score_normalizado,
)
avaliacoes_processo = table(
    "avaliacoes_processo",
    "analise",
    pk(),
    uid("base_id"),
    uid("execucao_id"),
    uid("processo_versao_id"),
    sa.Column("score", SCORE, nullable=True),
    text("prioridade"),
    text("motivo_indisponibilidade", nullable=True),
    json("politica"),
    timestamp(),
    base_fk("execucoes_analise", "execucao_id"),
    base_fk("processos_versoes", "processo_versao_id"),
    unique("processo_versao_id", "execucao_id"),
    choices("prioridade", ["nao_analisado", "baixa", "media", "alta"]),
    check(
        "(prioridade = 'nao_analisado' AND score IS NULL AND "
        "motivo_indisponibilidade IS NOT NULL) OR (prioridade <> 'nao_analisado' "
        "AND score IS NOT NULL AND score BETWEEN 0 AND 100)",
        "score_cobertura",
    ),
)
sa.Index(
    "ix_avaliacoes_execucao_prioridade_score",
    avaliacoes_processo.c.execucao_id,
    avaliacoes_processo.c.prioridade,
    avaliacoes_processo.c.score,
)
fatores_sinalizacao = table(
    "fatores_sinalizacao",
    "analise",
    pk(),
    ref("resultado_modelo_id", "resultados_modelo"),
    text("atributo"),
    text("metodo"),
    text("versao_metodo"),
    json("observado"),
    json("referencia"),
    sa.Column("contribuicao", sa.Numeric(30, 12), nullable=True),
    text("descricao"),
    unique("resultado_modelo_id", "atributo", "metodo"),
)
comparacoes_itens = table(
    "comparacoes_itens",
    "analise",
    pk(),
    uid("base_id"),
    uid("execucao_id"),
    uid("item_versao_id"),
    text("versao_criterio"),
    json("grupo_comparavel"),
    sa.Column("periodo_inicio", sa.Date(), nullable=False),
    sa.Column("periodo_fim", sa.Date(), nullable=False),
    sa.Column("tamanho_amostra", sa.Integer(), nullable=False),
    sa.Column("mediana", MONEY, nullable=False),
    sa.Column("limite_inferior", MONEY, nullable=True),
    sa.Column("limite_superior", MONEY, nullable=True),
    base_fk("execucoes_analise", "execucao_id"),
    base_fk("itens_versoes", "item_versao_id"),
    unique("execucao_id", "item_versao_id"),
    unique("id", "base_id"),
    check("tamanho_amostra >= 1 AND mediana > 0", "referencia_valida"),
    check("periodo_inicio <= periodo_fim", "periodo_ordenado"),
    check(
        "limite_inferior IS NULL OR limite_superior IS NULL OR limite_inferior <= limite_superior",
        "faixa_ordenada",
    ),
)
comparacoes_referencias = table(
    "comparacoes_referencias",
    "analise",
    uid("base_id"),
    sa.Column("comparacao_id", sa.Uuid(), primary_key=True),
    sa.Column("referencia_id", sa.Uuid(), primary_key=True),
    base_fk("comparacoes_itens", "comparacao_id"),
    base_fk("referencias_precos", "referencia_id"),
)
publicacoes_analise = table(
    "publicacoes_analise",
    "publicacao",
    pk(),
    text("nome"),
    uid("base_id"),
    uid("execucao_id"),
    sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
    timestamp(),
    base_fk("execucoes_analise", "execucao_id"),
    unique("nome", "execucao_id"),
)
sa.Index(
    "uq_publicacao_ativa_nome",
    publicacoes_analise.c.nome,
    unique=True,
    postgresql_where=publicacoes_analise.c.ativa.is_(True),
)

# Síntese descritiva por modelo: prioridade de auditoria permanece separada.
sinteses_processo_modelo = table(
    "sinteses_processo_modelo",
    "analise",
    pk(),
    uid("base_id"),
    uid("execucao_id"),
    uid("modelo_id"),
    uid("processo_versao_id"),
    text("metodo"),
    text("status"),
    sa.Column("score", SCORE, nullable=True),
    sa.Column("indice_observado", SCORE, nullable=True),
    sa.Column("limite_inferior", SCORE, nullable=True),
    sa.Column("limite_superior", SCORE, nullable=True),
    text("motivo", nullable=True),
    json("cobertura"),
    json("sinais"),
    json("contexto"),
    timestamp(),
    base_fk("execucoes_analise", "execucao_id"),
    base_fk("processos_versoes", "processo_versao_id"),
    sa.ForeignKeyConstraint(
        ["execucao_id", "modelo_id"],
        ["execucoes_modelos.execucao_id", "execucoes_modelos.modelo_id"],
    ),
    unique("execucao_id", "modelo_id", "processo_versao_id"),
    choices("status", ["nao_analisado", "parcial", "analisado_experimental"]),
    check(
        "(status='analisado_experimental' AND score IS NOT NULL AND motivo IS NULL "
        "AND indice_observado IS NOT NULL) OR "
        "(status='parcial' AND score IS NULL AND indice_observado IS NOT NULL "
        "AND motivo IS NOT NULL) OR "
        "(status='nao_analisado' AND score IS NULL AND indice_observado IS NULL "
        "AND motivo IS NOT NULL)",
        "estado_score",
    ),
    check("score IS NULL OR score BETWEEN 0 AND 100", "score_intervalo"),
    check("indice_observado IS NULL OR indice_observado BETWEEN 0 AND 100", "observado_intervalo"),
    check(
        "(limite_inferior IS NULL AND limite_superior IS NULL) OR "
        "(limite_inferior IS NOT NULL AND limite_superior IS NOT NULL "
        "AND limite_inferior BETWEEN 0 AND 100 "
        "AND limite_superior BETWEEN limite_inferior AND 100)",
        "limites_coerentes",
    ),
)
