"""Resumo descritivo por compra, com peso igual por item e cobertura explícita."""

from collections import defaultdict
from decimal import Decimal, localcontext

from licita_backend.api.errors import QueryError
from licita_backend.repositories.consultas import QueryRepository
from licita_backend.repositories.visao import ViewRepository, amounts, wire


def group_purchases(processes, items, filters):
    grouped = defaultdict(list)
    for item in items:
        grouped[item["processo"]["id"]].append(item)
    rows = []
    for process in processes:
        selected = grouped[process["id"]]
        events = [event for item in selected for event in item["resultados"]]
        if filters.orgao_id and process["orgao_id"] != filters.orgao_id:
            continue
        if filters.modalidade_id and process["modalidade_id"] != filters.modalidade_id:
            continue
        if filters.fornecedor_id and not any(
            e["fornecedor_id"] == filters.fornecedor_id for e in events
        ):
            continue
        if (filters.homologacao_inicio or filters.homologacao_fim) and not any(
            e["data_resultado"] is not None
            and (
                not filters.homologacao_inicio or e["data_resultado"] >= filters.homologacao_inicio
            )
            and (not filters.homologacao_fim or e["data_resultado"] <= filters.homologacao_fim)
            for e in events
        ):
            continue
        text = " ".join(
            str(v or "")
            for v in [
                process["numero_compra"],
                process.get("numero_processo"),
                process.get("numero_controle_pncp"),
                process["objeto"],
                process["orgao_nome"],
                *(i["descricao"] for i in selected),
                *(e["fornecedor_nome"] for e in events),
            ]
        )
        if filters.busca and filters.busca.strip().casefold() not in text.casefold():
            continue
        total = process["valor_homologado_processo"]
        if filters.valor_minimo is not None and (total is None or total < filters.valor_minimo):
            continue
        if filters.valor_maximo is not None and (total is None or total > filters.valor_maximo):
            continue
        scores = [
            i["indice_experimental"] for i in selected if i["indice_experimental"] is not None
        ]
        with localcontext() as ctx:
            ctx.prec = 60
            mean = (
                (sum(scores, Decimal(0)) / len(scores)).quantize(Decimal("0.001"))
                if scores
                else None
            )
        complete = sum(i["status_analise"] == "analisados" for i in selected)
        status = (
            "nao_analisados"
            if not scores
            else ("analisados" if complete == len(selected) else "parcial")
        )
        if filters.analise != "todos" and status != filters.analise:
            continue
        rows.append(
            {
                "id": process["id"],
                "processo": process,
                "descricao": process["objeto"],
                "score_medio": mean,
                "maior_score": max(scores, default=None),
                "itens_importados": len(selected),
                "itens_com_score": len(scores),
                "itens_analise_completa": complete,
                "itens_analise_parcial": sum(i["status_analise"] == "parcial" for i in selected),
                "itens_sem_score": len(selected) - len(scores),
                "itens_oficiais": None,
                "status_analise": status,
                "valor_homologado": total,
                "valor_estimado": process["valor_estimado_processo"],
                "valores_itens_importados": amounts(events),
            }
        )
    return rows


class TenderRepository:
    def __init__(self, session):
        self.view = ViewRepository(session)

    def dataset(self, filters):
        # Select purchases first; never shrink the mean to the items matching a search/date/value.
        unfiltered = filters.model_copy(
            update={
                "busca": None,
                "fornecedor_id": None,
                "orgao_id": None,
                "modalidade_id": None,
                "homologacao_inicio": None,
                "homologacao_fim": None,
                "valor_minimo": None,
                "valor_maximo": None,
                "analise": "todos",
            }
        )
        context, items, _, _ = self.view.dataset(unfiltered)
        processes = self.view.read(
            QueryRepository(self.view.session).process_query(filters.base_id)
        )
        rows = group_purchases(processes, items, filters)
        context["resumo"] = {
            "licitacoes": len(rows),
            "com_score": sum(r["score_medio"] is not None for r in rows),
            "itens_importados": sum(r["itens_importados"] for r in rows),
            "itens_com_score": sum(r["itens_com_score"] for r in rows),
        }
        context["universo"] = {
            "tipo": "todos_os_itens_importados_das_compras_selecionadas",
            "selecao_modelo": context["universo"]["selecao_modelo"],
            "media": "media_simples_dos_maximos_por_item_com_score_arredondada_3_casas",
            "peso": "igual_por_item_sem_ponderacao_por_preco_ou_quantidade",
            "ausencias": "excluidas_da_media_nao_recebem_zero",
            "cobertura": "itens_importados_na_base_nao_confirma_total_oficial",
            "filtros": "selecionam_compras_sem_restringir_itens_do_resumo",
            "valor": "valor_global_homologado_da_compra_na_origem",
            "prioridade_validada": False,
        }
        return context, rows, items

    def listing(self, filters):
        context, rows, _ = self.dataset(filters)
        return wire({**context, **self.view.page(rows, filters, score_key="score_medio")})

    def detail(self, filters, process_id):
        # Detail always keeps the full imported purchase regardless of list filters.
        clean = filters.model_copy(
            update={
                "busca": None,
                "fornecedor_id": None,
                "orgao_id": None,
                "modalidade_id": None,
                "homologacao_inicio": None,
                "homologacao_fim": None,
                "valor_minimo": None,
                "valor_maximo": None,
                "analise": "todos",
            }
        )
        context, rows, items = self.dataset(clean)
        found = next((r for r in rows if r["id"] == process_id), None)
        if found is None:
            raise QueryError("licitacao_nao_encontrada", "Licitação não encontrada nesta base.")
        related = [i for i in items if i["processo"]["id"] == process_id]
        return wire({**context, "licitacao": found, "itens": self.view.page(related, clean)})
