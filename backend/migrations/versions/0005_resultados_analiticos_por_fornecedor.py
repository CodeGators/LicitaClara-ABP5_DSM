"""Análise por resultado sem agregar vencedores de um item.

Revision ID: 0005_resultados
Revises: 0004_complementos
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_resultados"
down_revision = "0004_complementos"
branch_labels = None
depends_on = None
OLD = "uq_resultados_modelo_execucao_id_modelo_id_processo_versao_id_item_versao_id"
NEW = OLD + "_resultado_item_id"


def upgrade():
    op.create_unique_constraint(
        op.f("uq_resultados_itens_id_item_versao_id_base_id"),
        "resultados_itens",
        ["id", "item_versao_id", "base_id"],
    )
    op.add_column("resultados_modelo", sa.Column("resultado_item_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_resultados_modelo_resultado_item_id_resultados_itens"),
        "resultados_modelo",
        "resultados_itens",
        ["resultado_item_id", "item_versao_id", "base_id"],
        ["id", "item_versao_id", "base_id"],
    )
    op.drop_constraint(op.f(OLD), "resultados_modelo", type_="unique")
    op.create_unique_constraint(
        op.f(NEW),
        "resultados_modelo",
        ["execucao_id", "modelo_id", "processo_versao_id", "item_versao_id", "resultado_item_id"],
        postgresql_nulls_not_distinct=True,
    )
    for name in ["tipo_alvo_valido", "alvo_coerente"]:
        op.drop_constraint(op.f("ck_resultados_modelo_" + name), "resultados_modelo", type_="check")
    op.create_check_constraint(
        op.f("ck_resultados_modelo_tipo_alvo_valido"),
        "resultados_modelo",
        "tipo_alvo IN ('processo','item','resultado')",
    )
    op.create_check_constraint(
        op.f("ck_resultados_modelo_alvo_coerente"),
        "resultados_modelo",
        "(tipo_alvo='processo' AND item_versao_id IS NULL AND resultado_item_id IS NULL) OR "
        "(tipo_alvo='item' AND item_versao_id IS NOT NULL AND resultado_item_id IS NULL) OR "
        "(tipo_alvo='resultado' AND item_versao_id IS NOT NULL "
        "AND resultado_item_id IS NOT NULL)",
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM resultados_modelo WHERE resultado_item_id IS NOT NULL)"
        )
    ):
        raise RuntimeError(
            "Downgrade bloqueado: existem análises por resultado; preservar histórico"
        )
    for name in ["tipo_alvo_valido", "alvo_coerente"]:
        op.drop_constraint(op.f("ck_resultados_modelo_" + name), "resultados_modelo", type_="check")
    op.create_check_constraint(
        op.f("ck_resultados_modelo_tipo_alvo_valido"),
        "resultados_modelo",
        "tipo_alvo IN ('processo','item')",
    )
    op.create_check_constraint(
        op.f("ck_resultados_modelo_alvo_coerente"),
        "resultados_modelo",
        "(tipo_alvo='processo' AND item_versao_id IS NULL) OR "
        "(tipo_alvo='item' AND item_versao_id IS NOT NULL)",
    )
    op.drop_constraint(op.f(NEW), "resultados_modelo", type_="unique")
    op.create_unique_constraint(
        op.f(OLD),
        "resultados_modelo",
        ["execucao_id", "modelo_id", "processo_versao_id", "item_versao_id"],
        postgresql_nulls_not_distinct=True,
    )
    op.drop_constraint(
        op.f("fk_resultados_modelo_resultado_item_id_resultados_itens"),
        "resultados_modelo",
        type_="foreignkey",
    )
    op.drop_column("resultados_modelo", "resultado_item_id")
    op.drop_constraint(
        op.f("uq_resultados_itens_id_item_versao_id_base_id"), "resultados_itens", type_="unique"
    )
