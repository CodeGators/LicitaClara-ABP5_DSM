"""Inferência dos modelos ML-04: referências posteriores e alvos SQL são distintos."""

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal
from importlib.metadata import version

import joblib
import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor

from licita_ml.analytical.operational import read_base
from licita_ml.analytical.pipeline import put_immutable
from licita_ml.analytical.rules import canonical, digest, normalize
from licita_ml.diagnostics import checksum
from licita_ml.experiments.evaluate import features
from licita_ml.inference.pipeline import numeric
from licita_ml.inference.registry import POLICY, code_hash, percentile, predict
from licita_ml.repository import identifier
from licita_ml.temporal.pipeline import FEATURES
from licita_ml.training.dataset import load
from licita_ml.training.pipeline import code_hash as training_code_hash
from licita_ml.training.pipeline import validate


def frozen_models(training, dataset, expected_sha, objects, approved_only=False):
    # CLI local administrativa, sem upload HTTP. O hash fixado é exigido antes do pickle.
    if checksum(training / "manifesto.json") != expected_sha:
        raise ValueError("Hash do manifesto de treino diverge")
    manifest = validate(training)
    config = manifest["configuracao"]
    if config["codigo_sha256"] != training_code_hash():
        raise ValueError("Código de treino incompatível")
    for name, required in config["dependencias"].items():
        if version(name) != required:
            raise ValueError("Dependência incompatível; não carregar modelo")
    if checksum(dataset / "manifesto.json") != config["dataset"]["sha256"]:
        raise ValueError("Dataset temporal diverge do treino")
    temporal, groups = load(dataset)
    if temporal["fingerprint"] != config["dataset"]["fingerprint"]:
        raise ValueError("Fingerprint temporal divergente")
    prefix = "modelagem/temporal=" + manifest["fingerprint"]
    source = put_immutable(
        objects, prefix + "/manifesto.json", (training / "manifesto.json").read_bytes()
    )
    models, bases = [], []
    for report in manifest["grupos"]:
        gid = report["grupo"]
        group = groups[gid]
        ids = [r["id"] for r in group["train"]]
        med = Decimal(report["autoencoder"]["mediana_treino"])
        raw = io.BytesIO()
        pq.write_table(pa.Table.from_pylist([group["audit"][uid] for uid in ids]), raw)
        train_art = put_immutable(
            objects, prefix + f"/{gid}/referencias_treino.parquet", raw.getvalue()
        )
        train_manifest = {
            "schema": "licita-base-treino-v1",
            "codigo_treino": config["codigo_sha256"],
            "dataset": config["dataset"],
            "grupo": gid,
            "especificacao": group["group"],
            "ids": ids,
            "mediana": str(med),
            "artefatos": [train_art],
            "entidades_dominio_sql": False,
            "revisao_humana_concluida": False,
        }
        stored = put_immutable(
            objects,
            prefix + f"/{gid}/registro_treino.json",
            (canonical(train_manifest) + "\n").encode(),
        )
        base_id = identifier("versoes_base", "treino-temporal:" + digest(train_manifest))
        policy = config["politica_temporal"]
        bases.append(
            {
                "id": base_id,
                "versao": "treino-temporal:" + digest(train_manifest),
                "versao_transformador": "registro-treino-temporal-v1",
                "versao_codigo": config["codigo_sha256"],
                "chave_manifesto": stored["chave"],
                "sha256_manifesto": stored["sha256"],
                "periodo_inicio": date.fromisoformat(policy["train_start"]),
                "periodo_fim": date.fromisoformat(policy["train_end"]),
                "status": "validada",
                "recorte": {"tipo": "treino_modelo", "grupo": gid},
                "qualidade": {
                    "referencias_manifesto": len(ids),
                    "entidades_dominio_sql": False,
                    "validacao": "integridade; utilidade inconclusiva",
                },
            }
        )
        if_fit = report["isolation_forest"]["modelos"]["preco_quantidade"]
        ae_fit = next(a for a in report["autoencoder"]["ajustes"] if a["seed"] == 42)
        if not approved_only and (
            not if_fit["estabilidade_aprovada"]
            or not report["autoencoder"]["aprovado_tecnicamente"]
        ):
            raise ValueError("Âncoras sem aprovação técnica")
        frozen_scores = (
            pq.ParquetFile(training / gid / "pontuacoes_avaliacao.parquet").read().to_pylist()
        )
        train_scores = (
            pq.ParquetFile(training / gid / "pontuacoes_treino.parquet").read().to_pylist()
        )
        for algorithm, method, fit, sha_field in (
            ("isolation_forest", "if_preco_quantidade", if_fit, "sha256_artefato"),
            ("autoencoder", "ae", ae_fit, "sha256"),
        ):
            if approved_only and not (
                if_fit["estabilidade_aprovada"]
                if algorithm == "isolation_forest"
                else report["autoencoder"]["aprovado_tecnicamente"]
            ):
                continue
            path = training / fit["artefato"]
            if checksum(path) != fit[sha_field]:
                raise ValueError("Artefato de modelo divergente")
            bundle = joblib.load(io.BytesIO(path.read_bytes()))
            expected_type = IsolationForest if algorithm == "isolation_forest" else MLPRegressor
            if (
                type(bundle["model"]) is not expected_type
                or bundle["model"].n_features_in_ != 2
                or bundle["features"] != list(FEATURES)
                or bundle["grupo_id"] != gid
                or bundle["ids_treino"] != ids
                or bundle["mediana_treino"] != med
                or bundle["dataset_fingerprint"] != temporal["fingerprint"]
                or bundle["dataset_manifesto_sha256"] != config["dataset"]["sha256"]
                or bundle["train_end"] != date.fromisoformat(policy["train_end"])
            ):
                raise ValueError("Contrato do modelo incompatível")
            model = {
                "algorithm": algorithm,
                "group": gid,
                "spec": group["group"],
                "bundle": bundle,
                "train_ids": ids,
            }
            for members, expected in (
                (group["test"], frozen_scores),
                (group["train"], train_scores),
            ):
                selected = [r for r in expected if r["metodo"] == method]
                replay, _ = predict(model, members)
                if [r["id_observacao"] for r in selected] != [
                    r["id"] for r in members
                ] or not np.array_equal(replay, [r["score_bruto"] for r in selected]):
                    raise ValueError("Recarga não reproduz scores congelados")
            calibration, _ = predict(model, group["train"])
            model["calibration"] = calibration.tolist()
            artifact = put_immutable(objects, prefix + "/" + fit["artefato"], path.read_bytes())
            descriptor = {
                "algorithm": algorithm,
                "grupo": gid,
                "comparacao": source,
                "artefato": artifact,
                "normalizacao": "cdf-treino-v1",
                "codigo": code_hash(),
                "calibracao": model["calibration"],
            }
            fp = digest(descriptor)
            model["id"] = identifier("versoes_modelo", fp)
            model["record"] = {
                "id": model["id"],
                "base_treino_id": base_id,
                "algoritmo": algorithm,
                "versao": fp,
                "versao_codigo": code_hash(),
                "chave_artefato": artifact["chave"],
                "sha256_artefato": artifact["sha256"],
                "parametros": descriptor,
                "metricas": {
                    "replay_exato": True,
                    "experimental": True,
                    "utilidade_comprovada": False,
                },
                "preprocessamento": {
                    "features": list(FEATURES),
                    "mediana_treino": str(med),
                    "manifesto_treino": stored,
                    "cdf_treino": model["calibration"],
                },
            }
            models.append(model)
    return manifest, temporal, models, bases


def application(dataset, temporal, models, result_end=None):
    """Reconciliar todos os candidatos da janela, inclusive exclusões, sem fit."""
    table = ds.dataset(dataset / "referencias_temporais.parquet", format="parquet")
    rows = table.to_table(filter=ds.field("particao") == "aplicacao").to_pylist()
    if len(rows) * len(models) > 40000:
        raise ValueError("Aplicação excede 40 mil pares; dividir recorte")
    matrix = pq.ParquetFile(dataset / "aplicacao_referencias.parquet").read().to_pylist()
    ready = {r["id_observacao"]: r for r in rows if r["apto_modelagem"]}
    if len(ready) != len(matrix) or set(ready) != {r["id_observacao"] for r in matrix}:
        raise ValueError("Matriz de aplicação incompleta")
    for row in matrix:
        audit = ready[row["id_observacao"]]
        if (
            row["grupo"] != audit["grupo"]
            or row["compra"] != audit["compra"]
            or any(row[k] != audit[k] for k in FEATURES)
        ):
            raise ValueError("Matriz de aplicação diverge da auditoria")
    policy = temporal["configuracao"]["politica"]
    start, end = (date.fromisoformat(policy[k]) for k in ("application_start", "application_end"))
    if result_end is not None:
        if result_end < end:
            raise ValueError("Corte da inferência não pode antecipar o corte temporal original")
        end = result_end
        extended = []
        by_group = {m["group"]: m for m in models}
        for original in rows:
            row = dict(original)
            reasons = json.loads(row["motivos_json"])
            row["motivos_temporais_originais"] = reasons
            # Apenas liberação de resultado tardio; nunca relaxar outro impedimento.
            if (
                reasons == ["RESULTADO_POSTERIOR_AO_CORTE"]
                and row["grupo"] in by_group
                and start <= row["data_compra"] <= row["data_resultado"] <= end
            ):
                model = by_group[row["grupo"]]
                values = [
                    {
                        "id": row["id_observacao"],
                        "price": row["preco_unitario"],
                        "quantity": row["quantidade"],
                        "date": row["data_compra"],
                    }
                ]
                x = features(values, model["bundle"]["mediana_treino"], list(FEATURES))[0]
                row.update(
                    apto_modelagem=True,
                    motivos_json="[]",
                    regra_reavaliacao="RESULTADO_CONHECIDO_ATE_CORTE_INFERENCIA",
                    **dict(zip(FEATURES, x.tolist(), strict=True)),
                )
            extended.append(row)
        rows = extended
    scores, coverage = [], []
    for row in sorted(rows, key=lambda r: r["id_observacao"]):
        for model in models:
            reasons = json.loads(row["motivos_json"])
            if row["grupo"] != model["group"]:
                reasons = ["GRUPO_SEM_MODELO_TREINADO"]
            elif not row["apto_modelagem"] and not reasons:
                reasons = ["REFERENCIA_NAO_ELEGIVEL"]
            item = {
                **row,
                "modelo_id": str(model["id"]),
                "algoritmo": model["algorithm"],
                "motivos": reasons,
                "status": "nao_analisado" if reasons else "analisado_experimental",
            }
            coverage.append(item)
            if reasons:
                continue
            if (
                not start <= row["data_compra"] <= row["data_resultado"] <= end
                or row["id_observacao"] in model["train_ids"]
                or row["preco_unitario"] <= 0
                or row["quantidade"] <= 0
                or Decimal(row["mediana_treino"]) != model["bundle"]["mediana_treino"]
            ):
                raise ValueError("Aplicação viola corte, mediana ou valores observados")
            values = [
                {
                    "id": row["id_observacao"],
                    "price": row["preco_unitario"],
                    "quantity": row["quantidade"],
                    "date": row["data_compra"],
                }
            ]
            x = features(values, model["bundle"]["mediana_treino"], list(FEATURES))
            if not np.array_equal(x[0], [row[k] for k in FEATURES]):
                raise ValueError("Atributos de aplicação não reproduzem a transformação")
            raw, errors = predict(model, values)
            scores.append(
                {
                    **item,
                    "score_bruto": str(numeric(raw[0])),
                    "indice_experimental": str(percentile(model["calibration"], raw[0])),
                    "parcelas_ae": None if errors is None else (errors[0] / 2).tolist(),
                    "score_processo": None,
                    "prioridade": None,
                }
            )
    return rows, scores, coverage


def infer_references(training, dataset, expected_sha, objects, result_end=None):
    manifest, temporal, models, bases = frozen_models(training, dataset, expected_sha, objects)
    rows, scores, coverage = application(dataset, temporal, models, result_end)
    config = {
        "treino_sha256": expected_sha,
        "dataset_sha256": checksum(dataset / "manifesto.json"),
        "codigo": code_hash(),
        "politica_sha256": checksum(POLICY),
        "experimental": True,
        "normalizacao": "cdf-treino-v1",
        "resultado_ate": str(result_end)
        if result_end
        else temporal["configuracao"]["politica"]["application_end"],
    }
    result = {
        "schema": "licita-inferencia-referencias-v1",
        "configuracao": config,
        "fingerprint": digest(config),
        "scores": scores,
        "cobertura": coverage,
        "contagens": {
            "referencias": len(rows),
            "pares": len(coverage),
            "scores": len(scores),
            "motivos": dict(Counter(m for r in coverage for m in r["motivos"])),
        },
        "persistido_dominio_sql": False,
        "utilidade_comprovada": False,
        "snapshot_ponto_no_tempo": False,
        "modelos": [m["record"] for m in models],
        "bases_treino": bases,
        "treino_fingerprint": manifest["fingerprint"],
    }
    prefix = f"inferencia/referencias={digest(config)}"
    exports = []
    flat = [
        {
            k: str(row[k]) if row[k] is not None else None
            for k in (
                "id_observacao",
                "grupo",
                "modelo_id",
                "algoritmo",
                "compra",
                "item",
                "fornecedor",
                "data_compra",
                "data_resultado",
                "preco_unitario",
                "quantidade",
                "mediana_treino",
                "score_bruto",
                "indice_experimental",
                "arquivo_sha256",
                "membro",
                "linha",
            )
        }
        | {"parcelas_ae_json": canonical(row["parcelas_ae"])}
        for row in scores
    ]
    columns = list(flat[0]) if flat else ["id_observacao", "modelo_id", "score_bruto"]
    buffer = io.BytesIO()
    pq.write_table(
        pa.Table.from_pylist(flat, schema=pa.schema([(k, pa.string()) for k in columns])), buffer
    )
    exports.append(put_immutable(objects, prefix + "/pontuacoes.parquet", buffer.getvalue()))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
    writer.writeheader()
    writer.writerows(flat)
    exports.append(
        put_immutable(objects, prefix + "/pontuacoes.csv", stream.getvalue().encode("utf-8-sig"))
    )
    result["artefatos"] = exports
    stored = put_immutable(
        objects,
        prefix + "/manifesto.json",
        (canonical(result) + "\n").encode(),
    )
    return {"manifesto": stored, "contagens": result["contagens"], "scores": scores}


def compatible_unit(observed, spec):
    """Ler embalagem explícita sem converter preço por caixa em preço por unidade."""
    units = {"un", "unidade", "unidades"}
    label = normalize(observed)
    if spec[2] in units:
        return label in units
    # Sigla idêntica é comprovada pelo vínculo exato com a referência de preço.
    if label == spec[2]:
        return True
    match = re.fullmatch(
        r"([A-Za-z]+)\s+(\d+(?:[.,]\d+)?)\s+([A-Za-z]+)", str(observed or "").strip()
    )
    if not match:
        return False
    unit, capacity, measure = match.groups()
    labels = {"cx", "caixa"} if spec[2] == "cx" else {spec[2]}
    return (
        normalize(unit) in labels
        and Decimal(capacity.replace(",", ".")) == Decimal(spec[3])
        and normalize(measure) == spec[4]
    )


def has_foreign_currency(raw):
    """CSV vazio e JSON null são ausência; qualquer identificador informado exige política."""
    return any(
        raw.get(key) is not None and str(raw[key]).strip() != ""
        for key in ("moedaEstrangeiraId", "moeda_estrangeira_id")
    )


def sql_targets(base, data, rows, models, description_match=None, unit_match=None):
    """Vínculo por compra/item/fornecedor, valores, datas e embalagem exatos."""
    processes = {p["id"]: p for p in data["processos_versoes"]}
    references = {}
    for row in rows:
        references.setdefault((row["compra"], row["item"], row["fornecedor"]), []).append(row)
    by_item = {}
    for event in data["resultados_itens"]:
        by_item.setdefault(event["item_versao_id"], []).append(event)
    if (len(data["itens_versoes"]) + len(data["resultados_itens"])) * len(models) > 40000:
        raise ValueError("Lote SQL excede 40 mil pares; dividir recorte")
    scores, coverage, factors = [], [], []
    for item in sorted(data["itens_versoes"], key=lambda r: str(r["id"])):
        parent = processes[item["processo_versao_id"]]
        for event in sorted(
            by_item.get(item["id"], [None]), key=lambda r: str(r["id"]) if r else ""
        ):
            for model in models:
                matched, candidates = [], []
                reason = (
                    "SEM_RESULTADO_CONHECIDO"
                    if event is None
                    else "SEM_REFERENCIA_OPERACIONAL_EXATA"
                )
                if event:
                    origin, raw = item["atributos_origem"], event["atributos_origem"]
                    purchase = origin.get("idCompra") or origin.get("id_compra")
                    official = origin.get("idCompraItem") or origin.get("id_compra_item")
                    supplier = raw.get("niFornecedor") or raw.get("ni_fornecedor")
                    candidates = references.get((str(purchase), str(official), str(supplier)), [])
                    same_values = [
                        r
                        for r in candidates
                        if r["preco_unitario"] == event["valor_unitario_homologado"]
                        and r["quantidade"] == event["quantidade_homologada"]
                    ]
                    matched = [
                        r for r in same_values if r["data_resultado"] == event["data_resultado"]
                    ]
                    if same_values and not matched:
                        reason = "DATA_RESULTADO_DIVERGENTE_DA_REFERENCIA"
                    if len(matched) > 1:
                        reason = "VINCULO_REFERENCIA_AMBIGUO"
                    elif len(matched) == 1:
                        row = matched[0]
                        reason = None
                        if row["grupo"] != model["group"]:
                            reason = "GRUPO_SEM_MODELO_TREINADO"
                        elif not row["apto_modelagem"] or json.loads(row["motivos_json"]):
                            reason = "REFERENCIA_NAO_ELEGIVEL"
                        elif not (
                            description_match(item, row, model)
                            if description_match
                            else normalize(item["descricao"]) == model["spec"][1]
                        ):
                            reason = "ESPECIFICACAO_ITEM_DIVERGENTE"
                        elif data["catalogos"].get(item["catalogo_id"]) != model["spec"][0]:
                            reason = "CATALOGO_ITEM_DIVERGENTE"
                        elif (
                            str(
                                raw.get(
                                    "situacaoCompraItemResultadoId",
                                    raw.get("situacao_compra_item_resultado_id"),
                                )
                            )
                            != "1"
                            or normalize(event["situacao"]) != "informado"
                        ):
                            reason = "SITUACAO_RESULTADO_NAO_CONFIRMADA"
                        elif event["cancelado"]:
                            reason = "RESULTADO_CANCELADO"
                        elif has_foreign_currency(raw):
                            reason = "MOEDA_ESTRANGEIRA_REQUER_POLITICA"
                        elif (
                            str(
                                parent["atributos_origem"].get(
                                    "contratacaoExcluida",
                                    parent["atributos_origem"].get("contratacao_excluida"),
                                )
                            ).lower()
                            != "false"
                        ):
                            reason = "COMPRA_EXCLUIDA_OU_SITUACAO_NAO_CONFIRMADA"
                        # Embalagem provada pela referência exata e unidade SQL concordante.
                        elif not (
                            unit_match(item["unidade_medida"], model)
                            if unit_match
                            else compatible_unit(item["unidade_medida"], model["spec"])
                        ):
                            reason = "UNIDADE_OPERACIONAL_DIVERGENTE"
                        elif (
                            parent["atributos_origem"].get(
                                "idCompra", parent["atributos_origem"].get("id_compra")
                            )
                            != purchase
                        ):
                            reason = "COMPRA_OPERACIONAL_DIVERGENTE"
                        elif raw.get("dataCancelamentoPncp") or raw.get("data_cancelamento_pncp"):
                            reason = "RESULTADO_CANCELADO"
                coverage_row = {
                    "item_id": str(item["item_id"]),
                    "item_versao_id": str(item["id"]),
                    "processo_versao_id": str(item["processo_versao_id"]),
                    "resultado_item_id": str(event["id"]) if event else None,
                    "modelo_id": str(model["id"]),
                    "algoritmo": model["algorithm"],
                    "status": "nao_analisado" if reason else "analisado_experimental",
                    "motivo": reason,
                    "referencias_candidatas": [
                        {"id": r["id_observacao"], "data_resultado": str(r["data_resultado"])}
                        for r in candidates
                    ],
                    "data_resultado_operacional": str(event["data_resultado"]) if event else None,
                    "score_bruto": None,
                    "indice_experimental": None,
                }
                if reason is None:
                    raw_score, errors = predict(
                        model,
                        [
                            {
                                "id": str(event["id"]),
                                "price": event["valor_unitario_homologado"],
                                "quantity": event["quantidade_homologada"],
                                "date": event["data_resultado"],
                            }
                        ],
                    )
                    value = numeric(raw_score[0])
                    index = percentile(model["calibration"], raw_score[0])
                    coverage_row.update(score_bruto=str(value), indice_experimental=str(index))
                    uid = identifier("resultados_modelo", str(event["id"]) + ":" + str(model["id"]))
                    scores.append(
                        {
                            "id": uid,
                            "base_id": base["id"],
                            "modelo_id": model["id"],
                            "processo_versao_id": item["processo_versao_id"],
                            "item_versao_id": item["id"],
                            "resultado_item_id": event["id"],
                            "tipo_alvo": "resultado",
                            "score_bruto": value,
                            "score_normalizado": index,
                            "versao_normalizacao": "cdf-treino-v1",
                            "atributos": {
                                "referencia": json.loads(canonical(row)),
                                "experimental": True,
                                "prioridade": None,
                                "comparacao": {
                                    "grupo": model["group"],
                                    "mediana": str(model["bundle"]["mediana_treino"]),
                                    "n_treino": len(model["train_ids"]),
                                    "manifesto_treino": model["record"]["preprocessamento"][
                                        "manifesto_treino"
                                    ],
                                },
                                "explicacao": "parcelas_reconstrucao"
                                if errors is not None
                                else "indisponivel_metodo_if",
                            },
                        }
                    )
                    if errors is not None:
                        total = float(errors[0].sum())
                        for name, error in zip(FEATURES, errors[0], strict=True):
                            factors.append(
                                {
                                    "resultado_modelo_id": uid,
                                    "atributo": name,
                                    "metodo": "erro_reconstrucao",
                                    "versao_metodo": "ae-mse-v1",
                                    "observado": {
                                        "erro_quadratico": float(error),
                                        "fracao_erro": None if total == 0 else float(error / total),
                                    },
                                    "referencia": {"espaco": "padronizado_treino"},
                                    "contribuicao": numeric(float(error) / 2),
                                    "descricao": (
                                        "Parcela do score bruto AE; não é causa "
                                        "nem parcela do índice normalizado."
                                    ),
                                }
                            )
                coverage.append(coverage_row)
    return scores, coverage, factors


def infer_sql(pipeline, training, dataset, expected_sha, base_id, fail_after=None, result_end=None):
    _, temporal, models, bases = frozen_models(training, dataset, expected_sha, pipeline.objects)
    rows, _, _ = application(dataset, temporal, models, result_end)
    with pipeline.repo.locked() as cn:
        base, data = read_base(pipeline.repo, cn, base_id)
        if base["recorte"].get("tipo") == "treino_modelo":
            raise ValueError("Base de treino não é alvo operacional")
        with pipeline.objects.open(base["chave_manifesto"]) as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != base["sha256_manifesto"]:
                raise ValueError("Manifesto operacional divergente")
        scores, coverage, factors = sql_targets(base, data, rows, models)
        config = {
            "contrato": "inferencia-temporal-v1",
            "resultado_ate": str(result_end)
            if result_end
            else temporal["configuracao"]["politica"]["application_end"],
            "treino_sha256": expected_sha,
            "dataset_sha256": checksum(dataset / "manifesto.json"),
            "base_id": str(base_id),
            "base_sha256": base["sha256_manifesto"],
            "codigo": code_hash(),
            "politica_sha256": checksum(POLICY),
            "snapshot_ponto_no_tempo": False,
            "experimental": True,
            "normalizacao": "cdf-treino-v1",
            "modelos": [str(m["id"]) for m in models],
        }
        return pipeline.persist(
            cn, models, bases, base, data, config, scores, coverage, factors, fail_after
        )
