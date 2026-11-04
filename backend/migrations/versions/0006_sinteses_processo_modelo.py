"""Síntese experimental por processo/modelo, separada da prioridade validada.

Revision ID: 0006_sinteses
Revises: 0005_resultados
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_sinteses"
down_revision = "0005_resultados"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sinteses_processo_modelo",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("base_id", sa.Uuid(), nullable=False),
        sa.Column("execucao_id", sa.Uuid(), nullable=False),
        sa.Column("modelo_id", sa.Uuid(), nullable=False),
        sa.Column("processo_versao_id", sa.Uuid(), nullable=False),
        sa.Column("metodo", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(6, 3)),
        sa.Column("indice_observado", sa.Numeric(6, 3)),
        sa.Column("limite_inferior", sa.Numeric(6, 3)),
        sa.Column("limite_superior", sa.Numeric(6, 3)),
        sa.Column("motivo", sa.Text()),
        *[
            sa.Column(n, JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))
            for n in ("cobertura", "sinais", "contexto")
        ],
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["execucao_id", "base_id"], ["execucoes_analise.id", "execucoes_analise.base_id"]
        ),
        sa.ForeignKeyConstraint(
            ["processo_versao_id", "base_id"], ["processos_versoes.id", "processos_versoes.base_id"]
        ),
        sa.ForeignKeyConstraint(
            ["execucao_id", "modelo_id"],
            ["execucoes_modelos.execucao_id", "execucoes_modelos.modelo_id"],
        ),
        sa.UniqueConstraint("execucao_id", "modelo_id", "processo_versao_id"),
        sa.CheckConstraint(
            "status IN ('nao_analisado','parcial','analisado_experimental')", name="status_valido"
        ),
        sa.CheckConstraint(
            "(status='analisado_experimental' AND score IS NOT NULL AND motivo IS NULL "
            "AND indice_observado IS NOT NULL) OR "
            "(status='parcial' AND score IS NULL AND indice_observado IS NOT NULL "
            "AND motivo IS NOT NULL) OR "
            "(status='nao_analisado' AND score IS NULL AND indice_observado IS NULL "
            "AND motivo IS NOT NULL)",
            name="estado_score",
        ),
        sa.CheckConstraint("score IS NULL OR score BETWEEN 0 AND 100", name="score_intervalo"),
        sa.CheckConstraint(
            "indice_observado IS NULL OR indice_observado BETWEEN 0 AND 100",
            name="observado_intervalo",
        ),
        sa.CheckConstraint(
            "(limite_inferior IS NULL AND limite_superior IS NULL) OR "
            "(limite_inferior IS NOT NULL AND limite_superior IS NOT NULL "
            "AND limite_inferior BETWEEN 0 AND 100 "
            "AND limite_superior BETWEEN limite_inferior AND 100)",
            name="limites_coerentes",
        ),
        info={"domain": "analise"},
    )
    bind = op.get_bind()
    schema = bind.scalar(sa.text("SELECT current_schema()"))
    quoted = bind.dialect.identifier_preparer.quote_schema(schema)
    for role in ("licita_processing", "licita_api"):
        if bind.scalar(
            sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:r)"), {"r": role}
        ):
            permissions = "SELECT, INSERT" if role == "licita_processing" else "SELECT"
            op.execute(
                sa.text(f"GRANT {permissions} ON {quoted}.sinteses_processo_modelo TO {role}")
            )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM sinteses_processo_modelo)")):
        raise RuntimeError("Downgrade bloqueado: preservar sínteses existentes")
    op.drop_table("sinteses_processo_modelo")
