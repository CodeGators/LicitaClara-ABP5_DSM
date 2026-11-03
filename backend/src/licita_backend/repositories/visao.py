"""Agregações de um universo explícito, sem produto de joins ou valores imputados."""

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, localcontext
from uuid import UUID

import sqlalchemy as sa

from licita_backend.api.errors import QueryError
from licita_backend.models import analysis as a
from licita_backend.models import complementary as k
from licita_backend.models import procurement as p
from licita_backend.repositories.analises import AnalysisRepository
from licita_backend.repositories.consultas import QueryRepository

LIMIT = 20000


def wire(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: wire(v) for key, v in value.items()}
    if isinstance(value, list):
        return [wire(v) for v in value]
    return value


def amounts(events):
    known = [e["valor_total_homologado"] for e in events if e["valor_total_homologado"] is not None]
    with localcontext() as ctx:
        ctx.prec = 60
        subtotal = sum(known, Decimal(0)) if known else None
    return {
        "valor_homologado": subtotal if events and len(known) == len(events) else None,
        "soma_valores_conhecidos": subtotal,
        "resultados_sem_total": len(events) - len(known),
    }


def concentration(events, supplier_id):
    sums = amounts(events)
    total = sums["valor_homologado"]
    if total is None or total <= 0:
        return {
            **sums,
            "hhi": None,
            "participacao": None,
            "motivo": "TOTAIS_INCOMPLETOS"
            if sums["resultados_sem_total"]
            else "DENOMINADOR_AUSENTE_OU_ZERO",
        }
    with localcontext() as ctx:
        ctx.prec = 60
        by_supplier = defaultdict(Decimal)
        for event in events:
            by_supplier[event["fornecedor_id"]] += event["valor_total_homologado"]
        return {
            **sums,
            "hhi": sum((v / total) ** 2 for v in by_supplier.values()),
            "participacao": by_supplier[supplier_id] / total,
            "motivo": None,
        }


class ViewRepository:
    def __init__(self, session):
        self.session = session

    def read(self, query):
        rows = self.session.execute(query.limit(LIMIT + 1)).mappings().all()
        if len(rows) > LIMIT:
            raise QueryError(
                "recorte_excede_limite",
                "Recorte excede limite desta versão; preparar base menor.",
                503,
            )
        return [dict(r) for r in rows]

    def dataset(self, filters):
        base = QueryRepository(self.session).base(filters.base_id)
        execution, model = None, None
        if filters.execucao_id:
            execution = AnalysisRepository(self.session).execution(
                filters.base_id, filters.execucao_id
            )
            models = (
                self.session.execute(
                    sa.select(a.versoes_modelo)
                    .join(
                        a.execucoes_modelos,
                        a.execucoes_modelos.c.modelo_id == a.versoes_modelo.c.id,
                    )
                    .where(a.execucoes_modelos.c.execucao_id == filters.execucao_id)
                )
                .mappings()
                .all()
            )
            if filters.modelo_id:
                model = next((m for m in models if m["id"] == filters.modelo_id), None)
                if model is None:
                    raise QueryError(
                        "modelo_fora_execucao", "Modelo não pertence à execução selecionada.", 422
                    )
        rows = self.read(QueryRepository(self.session).item_query(base["id"]))
        events = self.read(
            sa.select(p.resultados_itens).where(
                p.resultados_itens.c.base_id == base["id"],
                p.resultados_itens.c.cancelado.is_(False),
            )
        )
        by_item = defaultdict(list)
        for event in events:
            when = event["data_resultado"]
            if filters.homologacao_inicio and (when is None or when < filters.homologacao_inicio):
                continue
            if filters.homologacao_fim and (when is None or when > filters.homologacao_fim):
                continue
            by_item[event["item_versao_id"]].append(event)
        scores = {}
        coverage = defaultdict(list)
        if model:
            for row in self.read(
                sa.select(a.resultados_modelo).where(
                    a.resultados_modelo.c.base_id == base["id"],
                    a.resultados_modelo.c.execucao_id == execution["id"],
                    a.resultados_modelo.c.modelo_id == model["id"],
                    a.resultados_modelo.c.tipo_alvo == "resultado",
                )
            ):
                scores[row["resultado_item_id"]] = row
            for row in execution["configuracao"]["cobertura"]:
                if row["modelo_id"] == str(model["id"]):
                    coverage[row["item_versao_id"]].append(row)
        selected = []
        for row in rows:
            process = {
                key.removeprefix("processo_"): row[key]
                for key in row
                if key.startswith("processo_")
            }
            candidates = by_item[row["item_versao_id"]]
            if filters.orgao_id and process["orgao_id"] != filters.orgao_id:
                continue
            if filters.modalidade_id and process["modalidade_id"] != filters.modalidade_id:
                continue
            if (filters.homologacao_inicio or filters.homologacao_fim) and not candidates:
                continue
            if filters.fornecedor_id and not any(
                e["fornecedor_id"] == filters.fornecedor_id for e in candidates
            ):
                continue
            if (
                filters.busca
                and filters.busca.strip().casefold()
                not in " ".join(
                    str(v or "")
                    for v in [
                        row["descricao"],
                        row["numero_item"],
                        row["chave_oficial"],
                        process["numero_compra"],
                        process["objeto"],
                        *(e["fornecedor_nome"] for e in candidates),
                    ]
                ).casefold()
            ):
                continue
            values = amounts(candidates)
            total = values["valor_homologado"]
            if filters.valor_minimo is not None and (total is None or total < filters.valor_minimo):
                continue
            if filters.valor_maximo is not None and (total is None or total > filters.valor_maximo):
                continue
            observed = [scores[e["id"]] for e in candidates if e["id"] in scores]
            status = (
                "nao_analisados"
                if not observed
                else "analisados"
                if len(observed) == len(candidates)
                else "parcial"
            )
            if filters.analise != "todos" and status != filters.analise:
                continue
            ids = {str(e["id"]) for e in candidates}
            reasons = Counter(
                r["motivo"]
                for r in coverage[str(row["item_versao_id"])]
                if r["motivo"] and (r["resultado_item_id"] in ids or not candidates)
            )
            if not reasons and not observed:
                reasons[
                    "ANALISE_NAO_PUBLICADA"
                    if execution is None
                    else "MODELO_NAO_SELECIONADO"
                    if model is None
                    else "SEM_RESULTADO_OU_COBERTURA"
                ] += 1
            selected.append(
                {
                    "id": row["id"],
                    "item_versao_id": row["item_versao_id"],
                    "descricao": row["descricao"],
                    "numero_item": row["numero_item"],
                    "processo": process,
                    "resultados": candidates,
                    "status_analise": status,
                    "indice_experimental": max(
                        (r["score_normalizado"] for r in observed), default=None
                    ),
                    "resultados_analisados": len(observed),
                    "resultados_ativos": len(candidates),
                    "motivos": dict(reasons),
                    "scores": observed,
                    **values,
                }
            )
        links = self.read(
            sa.select(k.contratos_processos).where(k.contratos_processos.c.base_id == base["id"])
        )
        contracts = self.read(
            sa.select(k.contratos_versoes).where(k.contratos_versoes.c.base_id == base["id"])
        )
        processes = {r["processo"]["processo_versao_id"] for r in selected}
        contract_ids = {
            r["contrato_versao_id"] for r in links if r["processo_versao_id"] in processes
        }
        all_events = [e for r in selected for e in r["resultados"]]
        all_suppliers = {e["fornecedor_id"] for e in all_events}
        counts = Counter(r["status_analise"] for r in selected)
        summary = {
            "itens": len(selected),
            "processos": len(processes),
            "orgaos": len({r["processo"]["orgao_id"] for r in selected}),
            "fornecedores": len(all_suppliers & {filters.fornecedor_id})
            if filters.fornecedor_id
            else len(all_suppliers),
            "fornecedores_no_denominador": len(all_suppliers),
            "contratos_vinculados": len(contract_ids),
            "resultados": len(all_events),
            "analisados": counts["analisados"],
            "parcial": counts["parcial"],
            "nao_analisados": counts["nao_analisados"],
            **amounts(all_events),
        }
        context = {
            "base_id": base["id"],
            "execucao_id": execution["id"] if execution else None,
            "modelo_id": model["id"] if model else None,
            "resumo": summary,
            "universo": {
                "tipo": "resultados_nao_cancelados_dos_itens_filtrados",
                "periodo_base": [base["periodo_inicio"], base["periodo_fim"]],
                "homologacao_inicio": filters.homologacao_inicio,
                "homologacao_fim": filters.homologacao_fim,
                "data_sem_filtro": "incluída em valores; grupo sem_data na evolução",
                "prioridade_validada": False,
                "valor": (
                    "totais homologados dos resultados selecionados; "
                    "não estimativa, contrato ou pagamento"
                ),
                "fornecedor": (
                    "seleciona itens; valores/HHI conservam todos os covencedores no período"
                ),
                "hhi": (
                    "todos os fornecedores dos itens filtrados por órgão; "
                    "não universo completo do órgão"
                ),
                "indice_item": (
                    "máximo dos resultados no mesmo modelo; não combina algoritmos; "
                    "cobertura parcial explícita"
                ),
            },
        }
        return context, selected, [r for r in contracts if r["id"] in contract_ids], links

    def context(self, filters):
        return self.dataset(filters)[0]

    def dashboard(self, filters):
        context, rows, _, _ = self.dataset(filters)
        buckets = [0] * 10
        months = defaultdict(lambda: Counter())
        reasons = Counter()
        for row in rows:
            if row["indice_experimental"] is not None:
                buckets[min(9, int(row["indice_experimental"] // 10))] += 1
            when = max(
                (r["data_resultado"] for r in row["resultados"] if r["data_resultado"]),
                default=None,
            )
            months[str(when)[:7] if when else "sem_data"][row["status_analise"]] += 1
            reasons.update(row["motivos"])
        return wire(
            {
                **context,
                "distribuicao": [
                    {"inicio": i * 10, "fim": 100 if i == 9 else (i + 1) * 10, "itens": n}
                    for i, n in enumerate(buckets)
                ],
                "evolucao": [
                    {
                        "mes": month,
                        "itens": sum(counts.values()),
                        "analisados": counts["analisados"],
                        "parcial": counts["parcial"],
                        "nao_analisados": counts["nao_analisados"],
                    }
                    for month, counts in sorted(months.items())
                ],
                "motivos_indisponibilidade": dict(reasons),
            }
        )

    def page(self, rows, filters):
        if filters.ordenacao == "descricao_asc":
            rows = sorted(
                rows, key=lambda r: (r.get("descricao", r.get("nome", "")).casefold(), str(r["id"]))
            )
        else:
            key = (
                "indice_experimental" if filters.ordenacao == "indice_desc" else "valor_homologado"
            )
            rows = sorted(
                rows, key=lambda r: (r[key] is None, -(r[key] or Decimal(0)), str(r["id"]))
            )
        start = (filters.pagina - 1) * filters.tamanho_pagina
        return {
            "dados": rows[start : start + filters.tamanho_pagina],
            "pagina": filters.pagina,
            "tamanho_pagina": filters.tamanho_pagina,
            "total": len(rows),
            "total_paginas": (len(rows) + filters.tamanho_pagina - 1) // filters.tamanho_pagina,
        }

    def ranking(self, filters):
        context, rows, _, _ = self.dataset(filters)
        return wire({**context, **self.page(rows, filters)})

    def supplier_rows(self, rows, contracts, links, filters):
        grouped = {}
        for item in rows:
            for event in item["resultados"]:
                uid = event["fornecedor_id"]
                supplier = grouped.setdefault(
                    uid,
                    {
                        "id": uid,
                        "nome": event["fornecedor_nome"],
                        "items": set(),
                        "processes": set(),
                        "organs": set(),
                        "events": [],
                        "scores": [],
                    },
                )
                supplier["items"].add(item["id"])
                supplier["processes"].add(item["processo"]["processo_versao_id"])
                supplier["organs"].add(item["processo"]["orgao_id"])
                supplier["events"].append(event)
                supplier["scores"].extend(
                    r["score_normalizado"]
                    for r in item["scores"]
                    if r["resultado_item_id"] == event["id"]
                )
        return [
            {
                "id": uid,
                "nome": s["nome"],
                "itens": len(s["items"]),
                "compras_com_resultado": len(s["processes"]),
                "orgaos": len(s["organs"]),
                "resultados": len(s["events"]),
                "contratos_vinculados": sum(c["fornecedor_id"] == uid for c in contracts),
                "indice_experimental": max(s["scores"], default=None),
                **amounts(s["events"]),
            }
            for uid, s in grouped.items()
            if not filters.fornecedor_id or uid == filters.fornecedor_id
        ]

    def suppliers(self, filters):
        context, rows, contracts, links = self.dataset(filters)
        suppliers = self.supplier_rows(rows, contracts, links, filters)
        return wire({**context, **self.page(suppliers, filters)})

    def supplier(self, filters, supplier_id):
        context, rows, contracts, links = self.dataset(filters)
        suppliers = self.supplier_rows(rows, contracts, links, filters)
        found = next((r for r in suppliers if r["id"] == supplier_id), None)
        if found is None:
            raise QueryError(
                "fornecedor_nao_encontrado", "Fornecedor não encontrado neste recorte."
            )
        by_organ, related, names = defaultdict(list), [], {}
        for item in rows:
            own = [r for r in item["resultados"] if r["fornecedor_id"] == supplier_id]
            if own:
                indices = [
                    s["score_normalizado"]
                    for s in item["scores"]
                    if any(s["resultado_item_id"] == e["id"] for e in own)
                ]
                related.append(
                    {
                        **item,
                        "resultados": own,
                        "resultados_ativos": len(own),
                        "resultados_analisados": len(indices),
                        "status_analise": "nao_analisados"
                        if not indices
                        else "analisados"
                        if len(indices) == len(own)
                        else "parcial",
                        "motivos": {} if indices else {"SEM_SCORE_DESTE_FORNECEDOR": 1},
                        "indice_experimental": max(indices, default=None),
                        **amounts(own),
                    }
                )
            organ = item["processo"]["orgao_id"]
            stamp = (
                item["processo"]["data_publicacao"] or date.min,
                str(item["processo"]["processo_versao_id"]),
            )
            if organ not in names or stamp > names[organ][0]:
                names[organ] = (stamp, item["processo"]["orgao_nome"])
            for event in item["resultados"]:
                by_organ[organ].append((event, item["processo"]["processo_versao_id"]))
        relations = []
        for uid, pairs in sorted(by_organ.items(), key=lambda pair: str(pair[0])):
            name = names[uid][1]
            own = [event for event, process in pairs if event["fornecedor_id"] == supplier_id]
            if not own:
                continue
            relations.append(
                {
                    "orgao_id": uid,
                    "orgao_nome": name,
                    "compras_com_resultado": len(
                        {proc for event, proc in pairs if event["fornecedor_id"] == supplier_id}
                    ),
                    "valor_fornecedor": amounts(own)["valor_homologado"],
                    **concentration([event for event, _ in pairs], supplier_id),
                }
            )
        return wire(
            {
                **context,
                "fornecedor": found,
                "relacoes": relations,
                "itens": self.page(related, filters),
            }
        )
