"""Roteamento por assinatura, modelos congelados e cobertura sem média entre grupos."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import pyarrow.dataset as ds

from licita_ml.analytical.operational import read_base
from licita_ml.analytical.rules import digest
from licita_ml.catalog.rules import ALIASES, grouping
from licita_ml.catalog.rules import VERSION as CATALOG_VERSION
from licita_ml.diagnostics import checksum
from licita_ml.experiments.evaluate import features
from licita_ml.grouped.training import checked
from licita_ml.inference.process_sources import official_universes
from licita_ml.inference.registry import code_hash as inference_hash
from licita_ml.inference.temporal import frozen_models, sql_targets
from licita_ml.repository import identifier
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.pipeline import FEATURES
from licita_ml.units import measurement, operational_matches

VERSION = "inferencia-agrupada-v1"
PROTOCOL = RESOURCE_DIR / "POLITICA_INFERENCIA_AGRUPADA_UNIDADES_V2.json"
UNIT_NAMES = {
    **ALIASES,
    "embalagem": "emb",
    "pacote": "pct",
    "ampola": "am",
    "frasco": "fr",
    "garrafa": "grf",
    "garrafao": "grr",
    "bisnaga": "bis",
    "rolo": "rl",
    "bandeja": "bj",
    "botijao": "btj",
    "tubete": "tbte",
}


def code_hash():
    root = Path(__file__).parents[1]
    paths = [
        Path(__file__),
        root / "catalog/rules.py",
        root / "grouped/training.py",
        root / "units.py",
    ]
    return digest([inference_hash(), [(str(p.relative_to(root)), checksum(p)) for p in paths]])


def unit_matches(observed, model):
    spec = model["canonical_spec"]
    info, reason = measurement(spec["unidade"], spec["capacidade"], spec["medida"])
    return not reason and operational_matches(observed, info)


def description_matches(item, row, model):
    spec = model["canonical_spec"]
    value, _ = grouping(
        {
            "catalogo": spec["catalogo"],
            "descricao": model["catalog_description"],
            "descricao_detalhada": item["descricao"],
            "unidade_fornecimento_sigla": spec["unidade"],
            "capacidade": spec["capacidade"],
            "unidade_medida_sigla": spec["medida"],
        }
    )
    return bool(value and value["id"] == row["grupo"] == model["group"])


def load_models(folder, objects, result_end):
    source = checked(Path(folder))
    models, bases, rows = [], [], []
    ids = set()
    purchase_limit = None
    for batch in source["lotes"]:
        training, dataset = Path(batch["treino"]), Path(batch["dataset"])
        _, temporal, own, train_bases = frozen_models(
            training, dataset, batch["treino_sha256"], objects, approved_only=True
        )
        reports = {g["grupo"]: g for g in json.loads((dataset / "grupos.json").read_text())}
        policy = temporal["configuracao"]["politica"]
        if purchase_limit is not None and purchase_limit != policy["max_per_purchase"]:
            raise ValueError("Política de concentração diverge entre lotes")
        purchase_limit = policy["max_per_purchase"]
        start, end = (
            date.fromisoformat(policy[k]) for k in ("application_start", "application_end")
        )
        if result_end < end:
            raise ValueError("Corte de inferência não pode antecipar a aplicação original")
        for model in own:
            report = reports[model["group"]]
            model["canonical_spec"] = report["assinatura_catalogo"]
            model["catalog_description"] = report["descricao_catalogo_original"]
            descriptor = {
                **model["record"]["parametros"],
                "contrato": VERSION,
                "assinatura_catalogo": model["canonical_spec"],
                "catalogo_versao": CATALOG_VERSION,
            }
            fp = digest(descriptor)
            model["id"] = identifier("versoes_modelo", fp)
            model["record"].update(id=model["id"], versao=fp, parametros=descriptor)
        by_group = {m["group"]: m for m in own}
        observed = (
            ds.dataset(dataset / "referencias_temporais.parquet")
            .to_table(filter=ds.field("particao") == "aplicacao")
            .to_pylist()
        )
        for original in observed:
            row = dict(original)
            if row["id_observacao"] in ids:
                raise ValueError("Referência repetida entre lotes")
            ids.add(row["id_observacao"])
            report = reports[row["grupo"]]
            if Decimal(row["mediana_treino"]) != Decimal(report["mediana_treino"]):
                raise ValueError("Mediana de aplicação diverge do treino")
            reasons = json.loads(row["motivos_json"])
            if (
                reasons == ["RESULTADO_POSTERIOR_AO_CORTE"]
                and start <= row["data_compra"] <= row["data_resultado"] <= result_end
            ):
                row.update(
                    apto_modelagem=True,
                    motivos_json="[]",
                    motivos_temporais_originais=reasons,
                    regra_reavaliacao="RESULTADO_CONHECIDO_ATE_CORTE_INFERENCIA",
                )
                reasons = []
            if row["apto_modelagem"]:
                if (
                    reasons
                    or not start <= row["data_compra"] <= row["data_resultado"] <= result_end
                ):
                    raise ValueError("Referência de aplicação viola corte ou elegibilidade")
                values = [
                    {
                        "id": row["id_observacao"],
                        "price": row["preco_unitario"],
                        "quantity": row["quantidade"],
                        "date": row["data_compra"],
                    }
                ]
                if any(row[k] is None or row[k] <= 0 for k in ("preco_unitario", "quantidade")):
                    raise ValueError("Preço/quantidade de aplicação inválido")
                x = features(values, Decimal(report["mediana_treino"]), list(FEATURES))[0]
                # Original late results have no vector; other ready vectors must replay exactly.
                if not row.get("regra_reavaliacao") and not np.array_equal(
                    x, [row[k] for k in FEATURES]
                ):
                    raise ValueError("Vetor de aplicação diverge da transformação congelada")
                row.update(dict(zip(FEATURES, x.tolist(), strict=True)))
                if (
                    row["grupo"] in by_group
                    and row["id_observacao"] in by_group[row["grupo"]]["train_ids"]
                ):
                    raise ValueError("Observação de treino reutilizada na aplicação")
            rows.append(row)
        models.extend(own)
        bases.extend(train_bases)
    apply_purchase_limit(rows, purchase_limit)
    if not models:
        raise ValueError("Nenhum modelo tecnicamente estável para inferência")
    return source, models, bases, rows


def apply_purchase_limit(rows, maximum):
    """Resultado tardio não pode contornar o limite existente de uma mesma compra."""
    counts = Counter((r["grupo"], r["compra"]) for r in rows if r["apto_modelagem"])
    for row in rows:
        if row["apto_modelagem"] and counts[row["grupo"], row["compra"]] > maximum:
            reasons = json.loads(row["motivos_json"])
            row.update(
                apto_modelagem=False,
                motivos_json=json.dumps(reasons + ["EXCESSO_REFERENCIAS_MESMA_COMPRA"]),
            )


def target_key(item_id, event_id):
    return f"{item_id}:{event_id or '-'}"


def route(base, data, rows, models):
    references = defaultdict(list)
    item_groups = defaultdict(set)
    groups = defaultdict(list)
    events = defaultdict(list)
    for row in rows:
        references[row["compra"], row["item"], row["fornecedor"]].append(row)
        item_groups[row["compra"], row["item"]].add(row["grupo"])
    for model in models:
        groups[model["group"]].append(model)
    for group in groups.values():
        if len({m["algorithm"] for m in group}) != len(group):
            raise ValueError("Mais de um modelo do mesmo algoritmo para um grupo")
    for event in data["resultados_itens"]:
        events[event["item_versao_id"]].append(event)
    scores, coverage, factors, routing = [], [], [], {}
    for item in sorted(data["itens_versoes"], key=lambda r: str(r["id"])):
        for event in sorted(
            events.get(item["id"], [None]), key=lambda e: str(e["id"]) if e else ""
        ):
            origin = item["atributos_origem"]
            raw = event["atributos_origem"] if event else {}
            key = (
                str(origin.get("idCompra", origin.get("id_compra"))),
                str(origin.get("idCompraItem", origin.get("id_compra_item"))),
                str(raw.get("niFornecedor", raw.get("ni_fornecedor"))),
            )
            candidates = references.get(key, [])
            exact = [
                r
                for r in candidates
                if event
                and r["preco_unitario"] == event["valor_unitario_homologado"]
                and r["quantidade"] == event["quantidade_homologada"]
                and r["data_resultado"] == event["data_resultado"]
            ]
            ambiguous_item = len(item_groups.get(key[:2], set())) > 1
            gid = exact[0]["grupo"] if len(exact) == 1 and not ambiguous_item else None
            chosen = sorted(groups.get(gid, []), key=lambda m: str(m["id"]))
            routing[target_key(item["id"], event["id"] if event else None)] = {
                "grupo": gid,
                "modelos": [str(m["id"]) for m in chosen],
            }
            if chosen:
                subset = {
                    **data,
                    "itens_versoes": [item],
                    "resultados_itens": [event] if event else [],
                }
                own, known, parts = sql_targets(
                    base, subset, candidates, chosen, description_matches, unit_matches
                )
                for row in known:
                    row["grupo"] = gid
                    row["motivos_referencia"] = json.loads(exact[0]["motivos_json"])
                    if row["motivo"] == "REFERENCIA_NAO_ELEGIVEL" and row["motivos_referencia"]:
                        row["motivo"] = row["motivos_referencia"][0]
                scores.extend(own)
                coverage.extend(known)
                factors.extend(parts)
            else:
                reason = (
                    "SEM_RESULTADO_CONHECIDO"
                    if event is None
                    else "GRUPO_ITEM_AMBIGUO"
                    if ambiguous_item
                    else "VINCULO_REFERENCIA_AMBIGUO"
                    if len(exact) > 1
                    else "GRUPO_SEM_MODELO_TECNICAMENTE_ESTAVEL"
                    if gid
                    else "DATA_RESULTADO_DIVERGENTE_DA_REFERENCIA"
                    if any(
                        r["preco_unitario"] == event["valor_unitario_homologado"]
                        and r["quantidade"] == event["quantidade_homologada"]
                        for r in candidates
                    )
                    else "SEM_REFERENCIA_OPERACIONAL_EXATA"
                )
                coverage.append(
                    {
                        "item_id": str(item["item_id"]),
                        "item_versao_id": str(item["id"]),
                        "processo_versao_id": str(item["processo_versao_id"]),
                        "resultado_item_id": str(event["id"]) if event else None,
                        "modelo_id": None,
                        "algoritmo": None,
                        "grupo": gid,
                        "status": "nao_analisado",
                        "motivo": reason,
                        "score_bruto": None,
                        "indice_experimental": None,
                    }
                )
    return scores, coverage, factors, routing


def process_coverage(data, scores, models, universes):
    by_item = defaultdict(list)
    by_process = defaultdict(list)
    for event in data["resultados_itens"]:
        if not event["cancelado"]:
            by_item[event["item_versao_id"]].append(event)
    for item in data["itens_versoes"]:
        by_process[item["processo_versao_id"]].append(item)
    score_events = {s["resultado_item_id"] for s in scores}
    model_groups = {m["id"]: m["group"] for m in models}
    output = {}
    for process in data["processos_versoes"]:
        items = by_process[process["id"]]
        ids = {i["id"] for i in items}
        events = [e for i in items for e in by_item[i["id"]]]
        own = [s for s in scores if s["item_versao_id"] in ids]
        groups = sorted({model_groups[s["modelo_id"]] for s in own})
        purchase = str(
            process["atributos_origem"].get(
                "idCompra", process["atributos_origem"].get("id_compra")
            )
        )
        universe = universes.get(purchase, {})
        output[str(process["id"])] = {
            "itens_importados": len(items),
            "itens_com_analise": sum(
                any(e["id"] in score_events for e in by_item[i["id"]]) for i in items
            ),
            "resultados_ativos_importados": len(events),
            "resultados_com_analise": sum(e["id"] in score_events for e in events),
            "grupos_com_analise": groups,
            "quantidade_grupos": len(groups),
            "universo_oficial": universe.get("status", "nao_confirmado"),
            "itens_oficiais": len(universe["itens"])
            if universe.get("status") == "confirmado_no_snapshot"
            else None,
            "score_processo": None,
            "indice_observado": None,
            "prioridade_auditoria": None,
            "motivo": "MULTIPLOS_GRUPOS_SEM_ESCALA_COMUM"
            if len(groups) > 1
            else "SCORE_PROCESSO_NAO_VALIDADO_PARA_ROTEAMENTO",
            "filtros_modelo": "cobertura_total_da_execucao_sem_recalcular_pelo_filtro",
        }
    return output


def infer(pipeline, training_root, base_id, result_end=date(2026, 10, 31), fail_after=None):
    if json.loads(PROTOCOL.read_text())["versao"] != VERSION:
        raise ValueError("Política de inferência agrupada incompatível")
    origin, models, bases, rows = load_models(training_root, pipeline.objects, result_end)
    with pipeline.repo.locked() as cn:
        base, data = read_base(pipeline.repo, cn, base_id, max_rows=200000)
        if base["recorte"].get("tipo") == "treino_modelo":
            raise ValueError("Base de treino não é alvo operacional")
        with pipeline.objects.open(base["chave_manifesto"]) as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != base["sha256_manifesto"]:
                raise ValueError("Manifesto operacional divergente")
        if len(data["itens_versoes"]) + len(data["resultados_itens"]) > 20000:
            raise ValueError("Recorte agrupado excede 20 mil alvos; preparar lotes operacionais")
        scores, coverage, factors, routing = route(base, data, rows, models)
        universes = official_universes(pipeline.repo, cn, pipeline.objects, base_id)
        config = {
            "contrato": VERSION,
            "politica_sha256": checksum(PROTOCOL),
            "experimental": True,
            "normalizacao": "cdf-treino-v1",
            "codigo": code_hash(),
            "treino_agrupado_sha256": checksum(Path(training_root) / "manifesto.json"),
            "treino_fingerprint": origin["fingerprint"],
            "base_id": str(base_id),
            "base_sha256": base["sha256_manifesto"],
            "resultado_ate": str(result_end),
            "modelos": [str(m["id"]) for m in models],
            "roteamento": routing,
            "cobertura_por_processo": process_coverage(data, scores, models, universes),
            "score_processo": None,
            "scores_combinados": False,
            "snapshot_ponto_no_tempo": False,
        }
        return pipeline.persist(
            cn, models, bases, base, data, config, scores, coverage, factors, fail_after
        )


def validate_routing(by_item, config, model_rows, coverage, scores):
    """Reconciliar todos os alvos SQL e somente seus modelos de grupo aplicáveis."""
    indexed = {str(m["id"]): m for m in model_rows}
    if set(indexed) != set(config["modelos"]):
        raise ValueError("Modelos do roteamento divergentes")
    grouped = defaultdict(set)
    for uid, model in indexed.items():
        params = model["parametros"]
        if params.get("contrato") != VERSION or model["versao"] != digest(params):
            raise ValueError("Contrato de modelo agrupado divergente")
        spec = params["assinatura_catalogo"]
        if digest([params.get("catalogo_versao", "catalogo-itens-v1"), spec]) != params["grupo"]:
            raise ValueError("Assinatura do modelo agrupado divergente")
        grouped[params["grupo"]].add(uid)
    routes = config["roteamento"]
    targets = {
        target_key(item, event): (item, event)
        for item, events in by_item.items()
        for event in (events or [None])
    }
    if set(routes) != set(targets):
        raise ValueError("Roteamento não cobre todos os itens/resultados")
    expected = set()
    for key, (item, event) in targets.items():
        route = routes[key]
        models = route["modelos"]
        if len(models) != len(set(models)) or set(models) != grouped.get(route["grupo"], set()):
            raise ValueError("Roteamento usa modelos de outro grupo ou omite modelo aplicável")
        expected.update((item, event, model) for model in (models or [None]))
    observed = [(r["item_versao_id"], r["resultado_item_id"], r["modelo_id"]) for r in coverage]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Cobertura agrupada incompleta ou com pares indevidos")
    scored = {
        (str(s["item_versao_id"]), str(s["resultado_item_id"]), str(s["modelo_id"])): s
        for s in scores
    }
    for row in coverage:
        pair = (row["item_versao_id"], row["resultado_item_id"], row["modelo_id"])
        route = routes[target_key(pair[0], pair[1])]
        if row["grupo"] != route["grupo"]:
            raise ValueError("Grupo da cobertura diverge do roteamento")
        if (row["status"] == "analisado_experimental") != (pair in scored):
            raise ValueError("Status da cobertura não corresponde aos scores")
        if pair in scored and scored[pair]["atributos"]["referencia"]["grupo"] != route["grupo"]:
            raise ValueError("Score registrado no grupo incorreto")
    if not set(scored) <= expected:
        raise ValueError("Score fora do roteamento")
