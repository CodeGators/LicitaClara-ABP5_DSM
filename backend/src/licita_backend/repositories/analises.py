"""Leitura de execuções publicadas, fixada em base/execução e sem carregar modelos."""

from collections import defaultdict

import sqlalchemy as sa

from licita_backend.api.errors import QueryError
from licita_backend.models import analysis as a
from licita_backend.models import procurement as p
from licita_backend.repositories.consultas import QueryRepository


def price_unit(parameters):
    """Expose the trained signature; never guess the median unit from the current item."""
    spec = parameters.get("assinatura_catalogo", {})
    if spec.get("unidade_preco"):
        return spec["unidade_preco"]
    supply, measure, capacity = spec.get("unidade"), spec.get("medida"), spec.get("capacidade")
    if not supply or capacity is None:
        return None
    from decimal import Decimal, InvalidOperation

    try:
        amount = Decimal(capacity)
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount < 0:
        return None
    if amount == 0 and supply == measure:
        label = supply
    elif amount > 0 and measure:
        label = f"{supply} de {amount.normalize():f} {measure}"
    else:
        return None
    return {
        "unidade_preco": label,
        "fornecimento": supply,
        "capacidade": capacity,
        "medida": measure,
        "origem": "assinatura_modelo_legada",
    }


class AnalysisRepository:
    def __init__(self, session):
        self.session = session

    def base(self, base_id):
        return QueryRepository(self.session).base(base_id)

    def active(self, base_id):
        self.base(base_id)
        uid = self.session.scalar(
            sa.select(a.publicacoes_analise.c.execucao_id).where(
                a.publicacoes_analise.c.nome == "experimental:" + str(base_id),
                a.publicacoes_analise.c.base_id == base_id,
                a.publicacoes_analise.c.ativa.is_(True),
            )
        )
        return {
            "base_id": base_id,
            "status": "publicada_experimental" if uid else "nao_publicada",
            "execucao_id": uid,
        }

    def query(self, base_id):
        e, pub = a.execucoes_analise, a.publicacoes_analise
        return sa.select(e).where(
            e.c.base_id == base_id,
            e.c.status == "concluida",
            e.c.configuracao["experimental"].as_boolean().is_(True),
            sa.exists(
                sa.select(pub.c.id).where(
                    pub.c.execucao_id == e.c.id,
                    pub.c.base_id == base_id,
                    pub.c.nome == "experimental:" + str(base_id),
                )
            ),
        )

    def serialize_run(self, row):
        models = (
            self.session.execute(
                sa.select(a.versoes_modelo)
                .join(a.execucoes_modelos, a.execucoes_modelos.c.modelo_id == a.versoes_modelo.c.id)
                .where(a.execucoes_modelos.c.execucao_id == row["id"])
            )
            .mappings()
            .all()
        )
        return {
            "id": row["id"],
            "base_id": row["base_id"],
            "status": row["status"],
            "politica": row["versao_politica_score"],
            "roteamento_automatico": row["configuracao"].get("contrato")
            == "inferencia-agrupada-v1",
            "contagens": row["configuracao"]["contagens"],
            "manifesto": row["configuracao"]["manifesto"],
            "criado_em": row["criado_em"],
            "concluido_em": row["concluido_em"],
            "modelos": [
                {
                    "id": m["id"],
                    "algoritmo": m["algoritmo"],
                    "grupo": m["parametros"].get("grupo"),
                    "catalogo": m["parametros"].get("assinatura_catalogo", {}).get("catalogo"),
                    "base_treino_id": m["base_treino_id"],
                    "versao": m["versao"],
                    "sha256_artefato": m["sha256_artefato"],
                    "metricas": m["metricas"],
                    "manifesto_treino": m["preprocessamento"]["manifesto_treino"],
                }
                for m in models
            ],
        }

    def runs(self, params):
        self.base(params.base_id)
        query = self.query(params.base_id)
        total = self.session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
        rows = (
            self.session.execute(
                query.order_by(a.execucoes_analise.c.criado_em.desc(), a.execucoes_analise.c.id)
                .limit(params.tamanho_pagina)
                .offset((params.pagina - 1) * params.tamanho_pagina)
            )
            .mappings()
            .all()
        )
        return {
            "dados": [self.serialize_run(r) for r in rows],
            "base_id": params.base_id,
            "pagina": params.pagina,
            "tamanho_pagina": params.tamanho_pagina,
            "total": total,
            "total_paginas": (total + params.tamanho_pagina - 1) // params.tamanho_pagina,
        }

    def execution(self, base_id, execution_id):
        self.base(base_id)
        row = (
            self.session.execute(
                self.query(base_id).where(a.execucoes_analise.c.id == execution_id)
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise QueryError("analise_nao_publicada", "Execução não publicada nesta base.")
        return row

    def items(self, execution, params, item_id=None):
        base_id, execution_id = execution["base_id"], execution["id"]
        query = sa.select(p.itens_versoes).where(p.itens_versoes.c.base_id == base_id)
        if item_id is not None:
            query = query.where(p.itens_versoes.c.item_id == item_id)
        total = self.session.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
        if item_id is not None and total == 0:
            raise QueryError("item_nao_encontrado", "Item não encontrado nesta base.")
        rows = (
            self.session.execute(
                query.order_by(p.itens_versoes.c.id)
                .limit(params.tamanho_pagina)
                .offset((params.pagina - 1) * params.tamanho_pagina)
            )
            .mappings()
            .all()
        )
        ids = [r["id"] for r in rows]
        scores = (
            self.session.execute(
                sa.select(
                    a.resultados_modelo,
                    a.versoes_modelo.c.algoritmo,
                    a.versoes_modelo.c.parametros.label("parametros_modelo"),
                )
                .join(a.versoes_modelo, a.versoes_modelo.c.id == a.resultados_modelo.c.modelo_id)
                .where(
                    a.resultados_modelo.c.execucao_id == execution_id,
                    a.resultados_modelo.c.base_id == base_id,
                    a.resultados_modelo.c.item_versao_id.in_(ids),
                )
            )
            .mappings()
            .all()
        )
        factors = defaultdict(list)
        for factor in self.session.execute(
            sa.select(a.fatores_sinalizacao).where(
                a.fatores_sinalizacao.c.resultado_modelo_id.in_([r["id"] for r in scores])
            )
        ).mappings():
            factors[factor["resultado_modelo_id"]].append(
                {
                    "atributo": factor["atributo"],
                    "metodo": factor["metodo"],
                    "parcela_score_bruto": str(factor["contribuicao"]),
                    "observado": factor["observado"],
                    "descricao": factor["descricao"],
                }
            )
        by_item, coverage = defaultdict(list), defaultdict(list)
        for row in execution["configuracao"]["cobertura"]:
            coverage[row["item_versao_id"]].append(row)
        for row in scores:
            by_item[row["item_versao_id"]].append(
                {
                    "id": row["id"],
                    "modelo_id": row["modelo_id"],
                    "algoritmo": row["algoritmo"],
                    "resultado_item_id": row["resultado_item_id"],
                    "score_bruto": row["score_bruto"],
                    "indice_experimental": row["score_normalizado"],
                    "normalizacao": row["versao_normalizacao"],
                    "atributos": {
                        **row["atributos"],
                        "comparacao": {
                            **row["atributos"].get("comparacao", {}),
                            "unidade_preco": price_unit(row["parametros_modelo"]),
                        },
                    },
                    "explicacao": {
                        "status": "disponivel" if factors[row["id"]] else "indisponivel",
                        "motivo": None
                        if factors[row["id"]]
                        else "METODO_ATRIBUICAO_IF_NAO_IMPLEMENTADO",
                        "parcelas": factors[row["id"]],
                    },
                }
            )
        output = []
        for row in rows:
            known = coverage[str(row["id"])]
            complete = known and all(r["status"] == "analisado_experimental" for r in known)
            output.append(
                {
                    "id": row["item_id"],
                    "item_versao_id": row["id"],
                    "processo_versao_id": row["processo_versao_id"],
                    "status": "analisado_experimental"
                    if complete
                    else "parcial"
                    if by_item[row["id"]]
                    else "nao_analisado",
                    "cobertura": known,
                    "resultados": by_item[row["id"]],
                }
            )
        return {
            "execucao_id": execution_id,
            "base_id": base_id,
            "dados": output,
            "pagina": params.pagina,
            "tamanho_pagina": params.tamanho_pagina,
            "total": total,
            "total_paginas": (total + params.tamanho_pagina - 1) // params.tamanho_pagina,
        }
