"""Média hierárquica descritiva com identificação explícita do que não foi observado."""

import json
from collections import defaultdict
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext

import sqlalchemy as sa

from licita_ml.analytical.operational import read_base
from licita_ml.analytical.rules import canonical, digest
from licita_ml.diagnostics import checksum
from licita_ml.inference.process_sources import event_key, field, official_universes
from licita_ml.resources import RESOURCE_DIR

POLICY = RESOURCE_DIR / "POLITICA_SINTESE_PROCESSO_V1.json"
METHOD = "media-hierarquica-cobertura-integral-v1"


def rounded(value, rounding=None):
    if value is None:
        return None
    return value.quantize(Decimal("0.001"), **({"rounding": rounding} if rounding else {}))


def summarize(process, items, events, scores, model_id, universe):
    """Nenhum algoritmo, grupo, covencedor ou item recebe peso implícito por valor."""
    universe = universe or {
        "status": "nao_confirmado",
        "motivo": "UNIVERSO_OFICIAL_NAO_CONFIRMADO",
        "fontes": [],
    }
    confirmed = universe["status"] == "confirmado_no_snapshot"
    purchase = field(process["atributos_origem"], "idCompra", "id_compra")
    indexed = {}
    for item in items:
        uid = str(field(item["atributos_origem"], "idCompraItem", "id_compra_item"))
        if uid in indexed:
            raise ValueError("Itens SQL repetem identidade oficial")
        indexed[uid] = item
    if confirmed and not set(indexed) <= set(universe["itens"]):
        raise ValueError("Itens SQL fora do universo oficial")
    active = defaultdict(dict)
    for event in events:
        if not event["cancelado"]:
            key = event_key(event["atributos_origem"])
            if key in active[event["item_versao_id"]]:
                raise ValueError("Resultado SQL duplica identidade oficial")
            active[event["item_versao_id"]][key] = event
    points = {}
    for row in scores:
        if row["modelo_id"] != model_id or row["processo_versao_id"] != process["id"]:
            continue
        value = Decimal(row["score_normalizado"])
        if (
            row["versao_normalizacao"] != "cdf-treino-v1"
            or not value.is_finite()
            or not 0 <= value <= 100
        ):
            raise ValueError("Índice de entrada incompatível")
        if row["resultado_item_id"] in points:
            raise ValueError("Resultado pontuado mais de uma vez por modelo")
        points[row["resultado_item_id"]] = row
    observed, signals, lower, upper, full, known_events = [], [], Decimal(0), Decimal(0), 0, 0
    official_ids = universe["itens"] if confirmed else sorted(indexed)
    n = len(official_ids) if confirmed else None
    with localcontext() as ctx:
        ctx.prec = 60
        for official in official_ids:
            item = indexed.get(official)
            own = active.get(item["id"], {}) if item else {}
            expected = (
                {tuple(k) for k in universe["resultados_ativos"][official]}
                if confirmed
                else set(own)
            )
            if confirmed and not set(own) <= expected:
                raise ValueError("Resultados SQL divergem do snapshot oficial")
            selected = [points[e["id"]] for e in own.values() if e["id"] in points]
            selected.sort(key=lambda r: str(r["id"]))
            k, m = len(selected), len(expected)
            known_events += k
            total = sum((Decimal(r["score_normalizado"]) for r in selected), Decimal(0))
            # Item sem resultado ou cadeia incompleta permanece [0,100], nunca zero imputado.
            lo = total / m if confirmed and m else Decimal(0)
            hi = (total + 100 * (m - k)) / m if confirmed and m else Decimal(100)
            lower += lo
            upper += hi
            complete = bool(confirmed and m and k == m)
            full += int(complete)
            if k:
                mean = total / k
                observed.append(mean)
                signals.append(
                    {
                        "item_oficial": official,
                        "numero_item": item.get("numero_item"),
                        "item_id": str(item["item_id"]),
                        "item_versao_id": str(item["id"]),
                        "media_observada": str(mean),
                        "resultados_analisados": k,
                        "resultados_oficiais": m if confirmed else None,
                        "item_completo": complete,
                        "resultados": [
                            {
                                "resultado_modelo_id": str(r["id"]),
                                "resultado_item_id": str(r["resultado_item_id"]),
                                "indice": str(r["score_normalizado"]),
                                "peso_no_item_observado": f"1/{k}",
                            }
                            for r in selected
                        ],
                    }
                )
        if len(points) != known_events:
            raise ValueError("Score órfão de resultado ativo ou de item do processo")
        mean_observed = sum(observed, Decimal(0)) / len(observed) if observed else None
        complete = bool(confirmed and n and full == n)
        mean = lower / n if complete else None
        bounds = (
            (rounded(lower / n, ROUND_FLOOR), rounded(upper / n, ROUND_CEILING))
            if n
            else (None, None)
        )
        for signal in signals:
            signal["peso_no_indice_observado"] = f"1/{len(signals)}"
            signal["contribuicao_observada"] = str(
                Decimal(signal["media_observada"]) / len(signals)
            )
    return {
        "base_id": process["base_id"],
        "modelo_id": model_id,
        "processo_versao_id": process["id"],
        "metodo": METHOD,
        "status": "analisado_experimental"
        if complete
        else "parcial"
        if observed
        else "nao_analisado",
        "score": rounded(mean),
        "indice_observado": rounded(mean_observed),
        "limite_inferior": bounds[0],
        "limite_superior": bounds[1],
        "motivo": None
        if complete
        else "UNIVERSO_OFICIAL_NAO_CONFIRMADO"
        if not confirmed
        else "COBERTURA_INSUFICIENTE",
        "cobertura": {
            "compra_oficial": purchase,
            "universo": universe["status"],
            "fontes": universe["fontes"],
            "motivo_universo": universe.get("motivo"),
            "itens_oficiais": n,
            "itens_importados": len(items),
            "itens_com_sinal": len(observed),
            "itens_integralmente_analisados": full,
            "resultados_analisados": known_events,
            "percentual_itens_completos": str(rounded(Decimal(full) * 100 / n)) if n else None,
            "completo": complete,
        },
        "sinais": {"itens": signals, "quantidade_itens_observados": len(signals)},
        "contexto": {
            "experimental": True,
            "prioridade_auditoria": None,
            "utilidade_validada": False,
            "modalidade_id": str(process["modalidade_id"])
            if process.get("modalidade_id")
            else None,
            "valor_global_homologado": str(process["valor_homologado"])
            if process.get("valor_homologado") is not None
            else None,
            "concorrencia": {"valor": None, "motivo": "VENCEDORES_NAO_SAO_TOTAL_DE_PARTICIPANTES"},
            "historico_fornecedor": {
                "valor": None,
                "motivo": "SEM_HISTORICO_COMPLETO_TEMPORAL_POR_PROCESSO",
            },
            "limites": "identificacao_deterministica_nao_intervalo_de_confianca",
            "condicao_limites": "hipotese_de_indices_compativeis_0_100_para_todos_os_alvos",
            "escopo_indice_observado": "somente_resultados_com_score_nos_itens_observados",
        },
    }


def run(pipeline, source_id, fail_after=None):
    """Derivar execução imutável sem desserializar modelos ou reescrever a anterior."""
    from licita_ml.inference.registry import code_hash

    t = pipeline.tables
    with pipeline.repo.locked() as cn:
        source = (
            cn.execute(
                sa.select(t["execucoes_analise"]).where(t["execucoes_analise"].c.id == source_id)
            )
            .mappings()
            .one_or_none()
        )
        if (
            source is None
            or source["status"] != "concluida"
            or source["configuracao"].get("experimental") is not True
        ):
            raise ValueError("Inferência experimental de origem não concluída")
        if source["configuracao"].get("sintese_processo"):
            raise ValueError("Selecionar inferência de itens, não outra síntese derivada")
        pipeline.reconcile(cn, source_id, source["base_id"], source["configuracao"])
        base, data = read_base(pipeline.repo, cn, source["base_id"])
        universes = official_universes(pipeline.repo, cn, pipeline.objects, base["id"])
        models = (
            cn.execute(
                sa.select(t["versoes_modelo"])
                .join(
                    t["execucoes_modelos"],
                    t["execucoes_modelos"].c.modelo_id == t["versoes_modelo"].c.id,
                )
                .where(t["execucoes_modelos"].c.execucao_id == source_id)
            )
            .mappings()
            .all()
        )
        models = sorted(models, key=lambda r: str(r["id"]))
        scores = [
            dict(r)
            for r in cn.execute(
                sa.select(t["resultados_modelo"]).where(
                    t["resultados_modelo"].c.execucao_id == source_id
                )
            ).mappings()
        ]
        scores = [
            {k: v for k, v in row.items() if k not in {"criado_em", "execucao_id"}}
            for row in scores
        ]
        factors = [
            dict(r)
            for r in cn.execute(
                sa.select(t["fatores_sinalizacao"]).where(
                    t["fatores_sinalizacao"].c.resultado_modelo_id.in_([r["id"] for r in scores])
                )
            ).mappings()
        ]
        factors = [
            {k: v for k, v in row.items() if k not in {"id", "criado_em"}} for row in factors
        ]
        scores.sort(key=lambda r: str(r["id"]))
        factors.sort(key=lambda r: (str(r["resultado_modelo_id"]), r["atributo"], r["metodo"]))
        if len(data["processos_versoes"]) * len(models) > 40000:
            raise ValueError("Lote excede 40 mil pares processo/modelo")
        items_by_process, events_by_process, scores_by_process = (
            defaultdict(list),
            defaultdict(list),
            defaultdict(list),
        )
        item_process = {}
        for item in data["itens_versoes"]:
            items_by_process[item["processo_versao_id"]].append(item)
            item_process[item["id"]] = item["processo_versao_id"]
        for event in data["resultados_itens"]:
            events_by_process[item_process[event["item_versao_id"]]].append(event)
        for score in scores:
            scores_by_process[score["processo_versao_id"]].append(score)
        summaries = []
        for process in sorted(data["processos_versoes"], key=lambda r: str(r["id"])):
            items = items_by_process[process["id"]]
            events = events_by_process[process["id"]]
            uid = str(field(process["atributos_origem"], "idCompra", "id_compra"))
            summaries.extend(
                summarize(
                    process,
                    items,
                    events,
                    scores_by_process[process["id"]],
                    m["id"],
                    universes.get(uid),
                )
                for m in models
            )
        config = {
            "sintese_processo": METHOD,
            "politica_sha256": checksum(POLICY),
            "codigo": code_hash(),
            "experimental": True,
            "modelos": [str(m["id"]) for m in models],
            "origem": {
                "execucao_id": str(source_id),
                "manifesto": source["configuracao"]["manifesto"],
            },
            "universos_sha256": digest(universes),
            "snapshot_ponto_no_tempo": False,
        }
        coverage = json.loads(canonical(source["configuracao"]["cobertura"]))
        return pipeline.persist(
            cn,
            [{"id": m["id"], "record": dict(m)} for m in models],
            [],
            base,
            data,
            config,
            scores,
            coverage,
            factors,
            fail_after,
            summaries,
        )
