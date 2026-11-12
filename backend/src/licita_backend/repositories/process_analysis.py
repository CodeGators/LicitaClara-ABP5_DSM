"""Síntese persistida de processo; filtros de itens não recalculam score da licitação."""

from collections import defaultdict
from decimal import Decimal

import sqlalchemy as sa

from licita_backend.api.errors import QueryError
from licita_backend.models import analysis as a
from licita_backend.models import procurement as p


def raw_summary(row, points):
    """Rebuild cached percentile summaries from immutable IF raw observations."""
    signals = []
    for item in row["sinais"].get("itens", []):
        observed = []
        for result in item.get("resultados", []):
            value = points.get(str(result["resultado_modelo_id"]))
            if value is not None:
                observed.append({**result, "medida_if": str(value)})
                observed[-1].pop("indice", None)
        if observed:
            mean = sum((Decimal(r["medida_if"]) for r in observed), Decimal(0)) / len(observed)
            signal = {**item, "media_observada": str(mean), "resultados": observed}
            signal.pop("contribuicao_observada", None)
            signal.pop("peso_no_indice_observado", None)
            signals.append(signal)
    mean = (
        sum((Decimal(s["media_observada"]) for s in signals), Decimal(0)) / len(signals)
        if signals
        else None
    )
    return {
        "id": row["id"],
        "modelo_id": row["modelo_id"],
        "algoritmo": row["algoritmo"],
        "metodo": "media-hierarquica-if-bruto-v1",
        "status": row["status"] if signals else "nao_analisado",
        "medida_if_processo": mean if row["status"] == "analisado_experimental" else None,
        "medida_if_observada": mean,
        "limite_inferior": None,
        "limite_superior": None,
        "motivo": row["motivo"],
        "cobertura": row["cobertura"],
        "sinais": {"itens": signals, "quantidade_itens_observados": len(signals)},
        "contexto": {
            **row["contexto"],
            "escala": "if-bruto-v1",
            "limites": "não recalculados na escala bruta",
            "condicao_limites": None,
            "escopo_indice_observado": "media_das_medidas_IF_dos_itens_observados",
        },
    }


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
        raw = (
            self.session.execute(
                sa.select(a.resultados_modelo, a.versoes_modelo.c.algoritmo)
                .join(a.versoes_modelo, a.versoes_modelo.c.id == a.resultados_modelo.c.modelo_id)
                .join(
                    p.resultados_itens,
                    p.resultados_itens.c.id == a.resultados_modelo.c.resultado_item_id,
                )
                .where(
                    a.resultados_modelo.c.execucao_id == execution["id"],
                    a.resultados_modelo.c.base_id == execution["base_id"],
                    a.resultados_modelo.c.processo_versao_id.in_([r["id"] for r in processes]),
                    a.versoes_modelo.c.algoritmo == "isolation_forest",
                    p.resultados_itens.c.cancelado.is_(False),
                )
            )
            .mappings()
            .all()
        )
        raw_points = {str(r["id"]): r["score_bruto"] for r in raw}
        grouped_coverage = {}
        for process in processes:
            old = (
                execution["configuracao"].get("cobertura_por_processo", {}).get(str(process["id"]))
            )
            if old is not None:
                own = [r for r in raw if r["processo_versao_id"] == process["id"]]
                grouped_coverage[str(process["id"])] = {
                    **old,
                    "itens_com_analise": len({r["item_versao_id"] for r in own}),
                    "resultados_com_analise": len({r["resultado_item_id"] for r in own}),
                    "quantidade_grupos": len({r["modelo_id"] for r in own}),
                    "escala": "if-bruto-v1",
                }
        query_summaries = query_summaries.where(a.versoes_modelo.c.algoritmo == "isolation_forest")
        by_process = defaultdict(list)
        for row in self.session.execute(query_summaries.order_by(table.c.modelo_id)).mappings():
            by_process[row["processo_versao_id"]].append(raw_summary(row, raw_points))
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
                    "cobertura_agrupada": grouped_coverage.get(str(r["id"])),
                    "status": "disponivel"
                    if (
                        by_process[r["id"]]
                        or str(r["id"])
                        in execution["configuracao"].get("cobertura_por_processo", {})
                    )
                    else "sem_sintese",
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
