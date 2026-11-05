"""Relatório público por processo, snapshot único para prévia/PDF/CSV."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from decimal import Decimal

import sqlalchemy as sa
from fastapi.encoders import jsonable_encoder

from licita_backend.api.errors import QueryError
from licita_backend.models import analysis as a
from licita_backend.models import procurement as p
from licita_backend.repositories.analises import AnalysisRepository
from licita_backend.repositories.consultas import QueryRepository
from licita_backend.schemas.consultas import Item, Pagination, ProcessDetail

MAX_ITEMS = 200
MAX_RESULTS = 1000
MAX_SCORES = 2000
LIMITATIONS = [
    "Anomalia estatística não é prova de irregularidade. Os sinais exigem verificação documental.",
    (
        "Índices são relativos ao treino de cada grupo; "
        "IF e Autoencoder são apresentados separadamente."
    ),
    (
        "O recorte importado pode não conter todos os itens da compra. "
        "Não há score integral validado da licitação."
    ),
    (
        "Ausência de análise não significa normalidade. "
        "Descrições, unidades e valores da fonte podem conter erros."
    ),
    (
        "Não há revisão humana registrada neste relatório. "
        "Medianas usam somente o treino; não são cotações atuais."
    ),
]


def snapshot(session, process_id, params):
    repository = QueryRepository(session)
    base = repository.base(params.base_id)
    process = repository.process(base["id"], process_id)
    if process["quantidade_itens_recorte"] > MAX_ITEMS:
        raise QueryError("limite_relatorio", "O relatório admite até 200 itens por processo.", 413)
    result_count = session.scalar(
        sa.select(sa.func.count())
        .select_from(
            p.resultados_itens.join(
                p.itens_versoes, p.itens_versoes.c.id == p.resultados_itens.c.item_versao_id
            )
        )
        .where(
            p.resultados_itens.c.base_id == base["id"],
            p.itens_versoes.c.processo_versao_id == process["processo_versao_id"],
        )
    )
    if result_count > MAX_RESULTS:
        raise QueryError("limite_relatorio", "O relatório excede mil resultados de itens.", 413)
    page = repository.items(base["id"], process_id, Pagination(tamanho_pagina=100))
    if page["meta"]["total"] > MAX_ITEMS:
        raise QueryError("limite_relatorio", "O relatório admite até 200 itens por processo.", 413)
    items = page["dados"]
    if page["meta"]["total"] > 100:
        items += repository.items(base["id"], process_id, Pagination(pagina=2, tamanho_pagina=100))[
            "dados"
        ]
    if sum(len(r["resultados"]) for r in items) > MAX_RESULTS:
        raise QueryError("limite_relatorio", "O relatório excede mil resultados de itens.", 413)
    ids = [r["item_versao_id"] for r in items]
    execution = None
    scores, coverage = defaultdict(list), defaultdict(list)
    if params.execucao_id:
        execution = AnalysisRepository(session).execution(base["id"], params.execucao_id)
        rows = (
            session.execute(
                sa.select(a.resultados_modelo, a.versoes_modelo.c.algoritmo)
                .join(a.versoes_modelo, a.versoes_modelo.c.id == a.resultados_modelo.c.modelo_id)
                .where(
                    a.resultados_modelo.c.base_id == base["id"],
                    a.resultados_modelo.c.execucao_id == execution["id"],
                    a.resultados_modelo.c.item_versao_id.in_(ids),
                )
                .order_by(a.resultados_modelo.c.id)
                .limit(MAX_SCORES + 1)
            )
            .mappings()
            .all()
        )
        if len(rows) > MAX_SCORES:
            raise QueryError("limite_relatorio", "O relatório excede duas mil pontuações.", 413)
        for row in rows:
            attrs = row["atributos"]
            reference = attrs.get("referencia", {})
            comparison = attrs.get("comparacao", {})
            scores[str(row["item_versao_id"])].append(
                {
                    "id": row["id"],
                    "resultado_item_id": row["resultado_item_id"],
                    "modelo_id": row["modelo_id"],
                    "algoritmo": row["algoritmo"],
                    "indice": row["score_normalizado"],
                    "score_bruto": row["score_bruto"],
                    "normalizacao": row["versao_normalizacao"],
                    "grupo": comparison.get("grupo"),
                    "mediana_treino": comparison.get("mediana"),
                    "n_treino": comparison.get("n_treino"),
                    "razao_preco_mediana": reference.get("razao_preco_mediana"),
                    "fonte": {
                        k: reference.get(k)
                        for k in ("arquivo_sha256", "membro", "linha", "id_observacao")
                    },
                    "explicacao": attrs.get("explicacao", "indisponivel"),
                }
            )
        for row in execution["configuracao"].get("cobertura", []):
            if row["processo_versao_id"] == str(process["processo_versao_id"]):
                coverage[row["item_versao_id"]].append(
                    {
                        k: row.get(k)
                        for k in ("modelo_id", "resultado_item_id", "status", "motivo", "grupo")
                    }
                )
    output = []
    for item in items:
        record = Item.model_validate(item).model_dump(mode="json")
        record.pop("analise")
        record["scores"] = scores[str(item["item_versao_id"])]
        record["cobertura"] = coverage[str(item["item_versao_id"])]
        output.append(record)
    data = jsonable_encoder(
        {
            "versao": "relatorio-anomalias-v1",
            "titulo": params.titulo,
            "base": {
                "id": base["id"],
                "versao": base["versao"],
                "periodo_inicio": base["periodo_inicio"],
                "periodo_fim": base["periodo_fim"],
                "manifesto_sha256": base["sha256_manifesto"],
            },
            "processo": ProcessDetail.model_validate(process).model_dump(
                mode="json", exclude={"analise"}
            ),
            "analise": {
                "id": execution["id"],
                "concluido_em": execution["concluido_em"],
                "politica": execution["versao_politica_score"],
                "manifesto_sha256": execution["configuracao"].get("manifesto", {}).get("sha256"),
            }
            if execution
            else None,
            "itens": output,
            "limites": LIMITATIONS,
            "resumo": {
                "itens": len(items),
                "itens_analisados": sum(bool(r["scores"]) for r in output),
                "scores": sum(len(r["scores"]) for r in output),
            },
            "fonte": "Compras.gov.br e complementos PNCP vinculados ao recorte importado",
        },
        custom_encoder={Decimal: lambda v: format(v, "f")},
    )
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if len(raw) > 2 * 1024**2:
        raise QueryError("limite_relatorio", "Conteúdo excede o limite de 2 MiB do relatório.", 413)
    return {**data, "snapshot_sha256": hashlib.sha256(raw).hexdigest()}


def safe_cell(value):
    value = "" if value is None else str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def csv_file(data):
    common = {
        "periodo_inicio": data["base"]["periodo_inicio"],
        "periodo_fim": data["base"]["periodo_fim"],
        "manifesto_base_sha256": data["base"]["manifesto_sha256"],
        "manifesto_analise_sha256": (data["analise"] or {}).get("manifesto_sha256"),
        "estimado_global": data["processo"]["valor_estimado_processo"],
        "homologado_global": data["processo"]["valor_homologado_processo"],
        "homologado_recorte": data["processo"]["valor_homologado_itens_recorte"],
        "itens_importados": data["resumo"]["itens"],
        "itens_analisados": data["resumo"]["itens_analisados"],
        "fonte_dados": data["fonte"],
    }
    rows = []
    for item in data["itens"]:
        for result in item["resultados"] or [None]:
            matches = [
                s for s in item["scores"] if result and s["resultado_item_id"] == result["id"]
            ]
            for score in matches or [None]:
                result, score = result or {}, score or {}
                rows.append(
                    {
                        **common,
                        "titulo": data["titulo"],
                        "base_id": data["base"]["id"],
                        "execucao_id": (data["analise"] or {}).get("id"),
                        "snapshot_sha256": data["snapshot_sha256"],
                        "processo_id": data["processo"]["id"],
                        "compra": data["processo"]["numero_compra"],
                        "orgao": data["processo"]["orgao_nome"],
                        "item": item["numero_item"],
                        "descricao": item["descricao"],
                        "item_id": item["id"],
                        "item_versao_id": item["item_versao_id"],
                        "quantidade_item": item["quantidade"],
                        "estimado_unitario": item["valor_unitario_estimado"],
                        "catalogo": item["catalogo"],
                        "codigo_catalogo": item["codigo_catalogo"],
                        "unidade": item["unidade_medida"],
                        "resultado_id": result.get("id"),
                        "fornecedor": result.get("fornecedor_nome"),
                        "cancelado": result.get("cancelado"),
                        "data_resultado": result.get("data_resultado"),
                        "quantidade": result.get("quantidade_homologada"),
                        "preco_unitario": result.get("valor_unitario_homologado"),
                        "valor_total_resultado": result.get("valor_total_homologado"),
                        "modelo_id": score.get("modelo_id"),
                        "algoritmo": score.get("algoritmo"),
                        "indice": score.get("indice"),
                        "score_bruto": score.get("score_bruto"),
                        "normalizacao": score.get("normalizacao"),
                        "grupo": score.get("grupo"),
                        "n_treino": score.get("n_treino"),
                        "mediana_treino": score.get("mediana_treino"),
                        "razao_preco_mediana": score.get("razao_preco_mediana"),
                        "fonte": json.dumps(
                            score.get("fonte", {}), ensure_ascii=False, sort_keys=True
                        ),
                        "cobertura": json.dumps(
                            item["cobertura"], ensure_ascii=False, sort_keys=True
                        ),
                        "limites": " | ".join(data["limites"]),
                        "granularidade": (
                            "resultado/modelo; valores repetem entre modelos: não somar as linhas"
                        ),
                    }
                )
    if not rows:
        rows = [
            {
                **common,
                "titulo": data["titulo"],
                "base_id": data["base"]["id"],
                "processo_id": data["processo"]["id"],
                "execucao_id": (data["analise"] or {}).get("id"),
                "snapshot_sha256": data["snapshot_sha256"],
                "limites": " | ".join(data["limites"]),
            }
        ]
    fields = list(rows[0])
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows({k: safe_cell(v) for k, v in row.items()} for row in rows)
    return out.getvalue().encode("utf-8-sig")
