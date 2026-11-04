"""Síntese persistida de processo; filtros de itens não recalculam score da licitação."""

from collections import defaultdict

import sqlalchemy as sa

from licita_backend.api.errors import QueryError
from licita_backend.models import analysis as a
from licita_backend.models import procurement as p


class ProcessAnalysisRepository:
    def __init__(self, session):
        self.session = session

    def page(self, execution, params, process_id=None):
        if params.modelo_id is not None:
            exists = self.session.scalar(
                sa.select(a.execucoes_modelos.c.modelo_id).where(
                    a.execucoes_modelos.c.execucao_id == execution["id"],
                    a.execucoes_modelos.c.modelo_id == params.modelo_id,
                )
            )
            if exists is None:
                raise QueryError(
                    "modelo_fora_execucao", "Modelo não pertence à execução selecionada.", 422
                )
        query = sa.select(p.processos_versoes).where(
            p.processos_versoes.c.base_id == execution["base_id"]
        )
        if process_id is not None:
            query = query.where(p.processos_versoes.c.processo_id == process_id)
        total = self.session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
        if process_id is not None and total == 0:
            raise QueryError("processo_nao_encontrado", "Processo não encontrado nesta base.")
        processes = (
            self.session.execute(
                query.order_by(p.processos_versoes.c.id)
                .limit(params.tamanho_pagina)
                .offset((params.pagina - 1) * params.tamanho_pagina)
            )
            .mappings()
            .all()
        )
        table = a.sinteses_processo_modelo
        query_summaries = (
            sa.select(table, a.versoes_modelo.c.algoritmo)
            .join(a.versoes_modelo, a.versoes_modelo.c.id == table.c.modelo_id)
            .where(
                table.c.execucao_id == execution["id"],
                table.c.base_id == execution["base_id"],
                table.c.processo_versao_id.in_([r["id"] for r in processes]),
            )
        )
        if params.modelo_id:
            query_summaries = query_summaries.where(table.c.modelo_id == params.modelo_id)
        by_process = defaultdict(list)
        for row in self.session.execute(query_summaries.order_by(table.c.modelo_id)).mappings():
            by_process[row["processo_versao_id"]].append(
                {
                    "id": row["id"],
                    "modelo_id": row["modelo_id"],
                    "algoritmo": row["algoritmo"],
                    "metodo": row["metodo"],
                    "status": row["status"],
                    "score_processo": row["score"],
                    "indice_observado": row["indice_observado"],
                    "limite_inferior": row["limite_inferior"],
                    "limite_superior": row["limite_superior"],
                    "motivo": row["motivo"],
                    "cobertura": row["cobertura"],
                    "sinais": row["sinais"],
                    "contexto": row["contexto"],
                }
            )
        return {
            "base_id": execution["base_id"],
            "execucao_id": execution["id"],
            "dados": [
                {
                    "id": r["processo_id"],
                    "processo_versao_id": r["id"],
                    "numero_compra": r["numero_compra"],
                    "objeto": r["objeto"],
                    "orgao_nome": r["orgao_nome"],
                    "status": "disponivel" if by_process[r["id"]] else "sem_sintese",
                    "resultados": by_process[r["id"]],
                    "prioridade_auditoria": None,
                }
                for r in processes
            ],
            "pagina": params.pagina,
            "tamanho_pagina": params.tamanho_pagina,
            "total": total,
            "total_paginas": (total + params.tamanho_pagina - 1) // params.tamanho_pagina,
        }
