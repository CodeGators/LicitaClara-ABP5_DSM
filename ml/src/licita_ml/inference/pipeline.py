"""Lotes imutáveis, cobertura explícita e ativação atômica somente experimental."""

import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pyarrow.parquet as pq
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from licita_ml.analytical.operational import operational_features, read_base
from licita_ml.analytical.pipeline import put_immutable
from licita_ml.analytical.rules import canonical, digest, normalize
from licita_ml.inference.registry import (
    POLICY,
    code_hash,
    percentile,
    predict,
    prepare_models,
    tables,
)
from licita_ml.repository import identifier
from licita_ml.validation.pipeline import load_groups, read_manifest


def numeric(value):
    return Decimal(str(value)).quantize(Decimal("0.000000000001"))


def snapshot(rows):
    return digest(
        sorted(
            (
                r["id"],
                str(r["preco_unitario"]),
                str(r["quantidade"]),
                str(r["data_compra"]),
                str(r["data_resultado"]),
            )
            for r in rows
        )
    )


def stable_targets(rows):
    return sorted(
        [{**r, "proveniencias": sorted(r["proveniencias"], key=canonical)} for r in rows],
        key=lambda r: (r["item_versao_id"], r["id"]),
    )


def infer_targets(models, base, data, references, policy):
    targets = stable_targets(operational_features(base, data, references, policy))
    if len(targets) * len(models) > 40000:
        raise ValueError("Lote excede 40 mil pares alvo/modelo; dividir recorte")
    items = {str(r["id"]): r for r in data["itens_versoes"]}
    events = {str(r["id"]): r for r in data["resultados_itens"]}
    scores, coverage, factors = [], [], []
    for target in targets:
        item = items[target["item_versao_id"]]
        event = events.get(target["id"])
        for model in models:
            reason = target["atributos"]["preco_mediana"]["motivo"]
            if policy.train_end != model["bundle"]["train_end"]:
                reason = "CORTE_TREINO_DIVERGENTE"
            matched = []
            if reason is None and event:
                official = item["atributos_origem"].get("idCompraItem") or item[
                    "atributos_origem"
                ].get("id_compra_item")
                supplier = event["atributos_origem"].get("niFornecedor") or event[
                    "atributos_origem"
                ].get("ni_fornecedor")
                matched = [
                    r
                    for r in references
                    if r["grupo"] == model["group"]
                    and not r["motivos_exclusao"]
                    and r["item_oficial"] == str(official)
                    and r["fornecedor_hash"] == digest(str(supplier))[:16]
                    and r["preco_unitario"] == event["valor_unitario_homologado"]
                    and r["quantidade"] == event["quantidade_homologada"]
                    and r["data_resultado"] <= event["data_resultado"]
                ]
                if len(matched) != 1:
                    reason = "GRUPO_MODELO_SEM_VINCULO_EXATO"
                elif normalize(item["unidade_medida"]) not in {"un", "unidade", "unidades"}:
                    capacity = item["atributos_origem"].get("capacidadeUnidadeFornecimento")
                    measure = item["atributos_origem"].get("siglaUnidadeMedida")
                    if (
                        capacity is None
                        or Decimal(str(capacity)) != Decimal(model["spec"][3])
                        or normalize(measure) != model["spec"][4]
                    ):
                        reason = "EMBALAGEM_NAO_COMPROVADA"
                train = [
                    r
                    for r in references
                    if r["grupo"] == model["group"]
                    and r["particao"] == "treino"
                    and not r["motivos_exclusao"]
                ]
                if snapshot(train) != model["train_snapshot"]:
                    reason = "TREINO_REFERENCIA_DIVERGENTE"
                if (
                    Decimal(target["atributos"]["preco_mediana"]["mediana"])
                    != model["bundle"]["mediana_treino"]
                ):
                    reason = "MEDIANA_DIVERGENTE_DO_MODELO"
            row = {
                "item_id": str(item["item_id"]),
                "item_versao_id": str(item["id"]),
                "processo_versao_id": str(item["processo_versao_id"]),
                "resultado_item_id": str(event["id"]) if event else None,
                "modelo_id": str(model["id"]),
                "algoritmo": model["algorithm"],
                "status": "nao_analisado" if reason else "analisado_experimental",
                "motivo": reason,
                "score_bruto": None,
                "indice_experimental": None,
            }
            if reason is None:
                value, errors = predict(
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
                raw = float(value[0])
                row.update(
                    score_bruto=str(numeric(raw)),
                    indice_experimental=str(percentile(model["calibration"], raw)),
                )
                record = {
                    "id": identifier(
                        "resultados_modelo", str(event["id"]) + ":" + str(model["id"])
                    ),
                    "base_id": base["id"],
                    "modelo_id": model["id"],
                    "processo_versao_id": item["processo_versao_id"],
                    "item_versao_id": item["id"],
                    "resultado_item_id": event["id"],
                    "tipo_alvo": "resultado",
                    "score_bruto": numeric(raw),
                    "score_normalizado": Decimal(row["indice_experimental"]),
                    "versao_normalizacao": "cdf-treino-v1",
                    "atributos": {
                        "observados": target["atributos"],
                        "resultado_item_id": str(event["id"]),
                        "referencia_historica_id": matched[0]["id"],
                        "proveniencias": target["proveniencias"],
                        "comparacao": {
                            "grupo": model["group"],
                            "mediana": str(model["bundle"]["mediana_treino"]),
                            "manifesto_treino": model["record"]["preprocessamento"][
                                "manifesto_treino"
                            ],
                            "n_treino": len(model["train_ids"]),
                        },
                        "explicacao": "parcelas_reconstrucao"
                        if errors is not None
                        else "indisponivel_metodo_if",
                        "experimental": True,
                        "prioridade": None,
                    },
                }
                scores.append(record)
                if errors is not None:
                    total = float(errors[0].sum())
                    for name, error in zip(model["bundle"]["features"], errors[0], strict=True):
                        factors.append(
                            {
                                "resultado_modelo_id": record["id"],
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
            coverage.append(row)
    return scores, coverage, factors


class InferencePipeline:
    def __init__(self, settings, repository, objects):
        self.settings, self.repo, self.objects = settings, repository, objects
        self.tables = tables(repository)

    def run(self, comparison_key, comparison_sha, target_key, target_sha, fail_after=None):
        models, bases = prepare_models(self.objects, comparison_key, comparison_sha)
        source, contents = read_manifest(
            self.objects, target_key, target_sha, "licita-atributos-v1"
        )
        references, _, policy = load_groups(source, contents)
        base_id = UUID(source["configuracao"]["base_operacional"]["id"])
        config = {
            "comparacao": {"chave": comparison_key, "sha256": comparison_sha},
            "atributos": {"chave": target_key, "sha256": target_sha},
            "codigo": code_hash(),
            "politica_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
            "experimental": True,
            "normalizacao": "cdf-treino-v1",
            "modelos": [str(m["id"]) for m in models],
        }
        with self.repo.locked() as cn:
            base, data = read_base(self.repo, cn, base_id)
            with self.objects.open(base["chave_manifesto"]) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != base["sha256_manifesto"]:
                    raise ValueError("Manifesto operacional diverge do registro SQL")
            if base["recorte"].get("tipo") == "treino_modelo":
                raise ValueError("Base de treino não é alvo operacional")
            if (
                base["sha256_manifesto"]
                != source["configuracao"]["base_operacional"]["manifesto_sha256"]
            ):
                raise ValueError("Atributos não correspondem à versão operacional")
            art = next(a for a in source["artefatos"] if a["entidade"] == "resultados_operacionais")
            frozen = [
                json.loads(r["registro_json"])
                for r in pq.read_table(io.BytesIO(contents[art["chave"]])).to_pylist()
            ]
            actual = operational_features(base, data, references, policy)
            if canonical(stable_targets(actual)) != canonical(stable_targets(frozen)):
                raise ValueError("Atributos operacionais divergem do snapshot SQL")
            scores, coverage, factors = infer_targets(models, base, data, references, policy)
            return self.persist(
                cn, models, bases, base, data, config, scores, coverage, factors, fail_after
            )

    def persist(
        self,
        cn,
        models,
        bases,
        base,
        data,
        config,
        scores,
        coverage,
        factors,
        fail_after=None,
        process_summaries=None,
    ):
        """Reconciliação/transação comum aos contratos antigo e temporal."""
        base_id = base["id"]
        fingerprint = digest(config)
        execution_id = identifier("execucoes_analise", fingerprint)
        execution = self.tables["execucoes_analise"]
        score_ids = {}
        for record in scores:
            old_id = record["id"]
            record["id"] = identifier("resultados_modelo", str(execution_id) + ":" + str(old_id))
            score_ids[old_id] = record["id"]
            record["execucao_id"] = execution_id
        for factor in factors:
            factor["resultado_modelo_id"] = score_ids[factor["resultado_modelo_id"]]
        if process_summaries is not None:
            for row in process_summaries:
                row["execucao_id"] = execution_id
                row["id"] = identifier(
                    "sinteses_processo_modelo",
                    f"{execution_id}:{row['processo_versao_id']}:{row['modelo_id']}",
                )
                for item in row["sinais"]["itens"]:
                    for result in item["resultados"]:
                        result["resultado_modelo_id"] = str(
                            score_ids[UUID(result["resultado_modelo_id"])]
                        )
        summary = {
            "itens": len(data["itens_versoes"]),
            "alvos_modelos": len(coverage),
            "scores": len(scores),
            "motivos": dict(Counter(r["motivo"] for r in coverage if r["motivo"])),
        }
        manifest = {
            "schema": "licita-inferencia-v1",
            "execucao_id": str(execution_id),
            "configuracao": config,
            "base_id": str(base_id),
            "cobertura": coverage,
            "contagens": summary,
            "scores": scores,
            "fatores": factors,
            "modelos": [m["record"] for m in models],
            "bases_treino": bases,
            "processos": sorted(str(r["id"]) for r in data["processos_versoes"]),
            "prioridade_auditoria": None,
            "agregacao_processo": "indisponivel_sem_politica_validada",
        }
        if process_summaries is not None:
            manifest["sinteses_processo"] = process_summaries
            manifest["agregacao_processo"] = config["sintese_processo"]
            summary["sinteses_processo"] = len(process_summaries)
            summary["processos_modelos_com_score_integral"] = sum(
                r["score"] is not None for r in process_summaries
            )
        serialized = (canonical(manifest) + "\n").encode()
        if len(serialized) > 64 * 1024**2:
            raise ValueError("Manifesto excede 64 MiB; dividir lote")
        stored = put_immutable(
            self.objects,
            f"inferencia/execucao={fingerprint}/manifesto.json",
            serialized,
        )
        recorded_config = {
            **config,
            "manifesto": stored,
            "cobertura": coverage,
            "contagens": summary,
        }
        old = (
            cn.execute(sa.select(execution).where(execution.c.id == execution_id))
            .mappings()
            .one_or_none()
        )
        cn.commit()
        if old:
            if old["configuracao"] != recorded_config:
                raise ValueError("Execução existente diverge")
            if old["status"] == "concluida":
                self.reconcile(cn, execution_id, base_id, recorded_config)
                cn.rollback()
                return {
                    "execucao_id": str(execution_id),
                    "base_id": str(base_id),
                    "status": "concluida",
                    "reutilizada": True,
                    "contagens": summary,
                    "manifesto": stored,
                }
        with cn.begin():
            cn.execute(
                insert(execution)
                .values(
                    id=execution_id,
                    base_id=base_id,
                    versao_politica_score=config.get("sintese_processo", "experimental-v1"),
                    configuracao=recorded_config,
                )
                .on_conflict_do_nothing()
            )
            cn.execute(
                execution.update()
                .where(execution.c.id == execution_id)
                .values(status="executando", erro=None, concluido_em=None)
            )
        try:
            with cn.begin():
                for b in bases:
                    cn.execute(
                        insert(self.tables["versoes_base"]).values(**b).on_conflict_do_nothing()
                    )
                    saved = (
                        cn.execute(
                            sa.select(self.tables["versoes_base"]).where(
                                self.tables["versoes_base"].c.id == b["id"]
                            )
                        )
                        .mappings()
                        .one()
                    )
                    if canonical({k: saved[k] for k in b}) != canonical(b):
                        raise ValueError("Registro imutável de treino diverge")
                for model in models:
                    cn.execute(
                        insert(self.tables["versoes_modelo"])
                        .values(**model["record"])
                        .on_conflict_do_nothing()
                    )
                    saved = (
                        cn.execute(
                            sa.select(self.tables["versoes_modelo"]).where(
                                self.tables["versoes_modelo"].c.id == model["id"]
                            )
                        )
                        .mappings()
                        .one()
                    )
                    if canonical({k: saved[k] for k in model["record"]}) != canonical(
                        model["record"]
                    ):
                        raise ValueError("Registro imutável do modelo diverge")
                    cn.execute(
                        insert(self.tables["execucoes_modelos"]).values(
                            execucao_id=execution_id, modelo_id=model["id"]
                        )
                    )
                for n, row in enumerate(scores, 1):
                    cn.execute(self.tables["resultados_modelo"].insert().values(**row))
                    if fail_after and n >= fail_after:
                        raise RuntimeError("Falha controlada no lote")
                if fail_after == 0:
                    raise RuntimeError("Falha controlada antes da cobertura")
                if factors:
                    cn.execute(self.tables["fatores_sinalizacao"].insert(), factors)
                if process_summaries:
                    cn.execute(self.tables["sinteses_processo_modelo"].insert(), process_summaries)
                for process in data["processos_versoes"]:
                    cn.execute(
                        self.tables["avaliacoes_processo"]
                        .insert()
                        .values(
                            base_id=base_id,
                            execucao_id=execution_id,
                            processo_versao_id=process["id"],
                            prioridade="nao_analisado",
                            motivo_indisponibilidade=(
                                "PRIORIDADE_AUDITORIA_NAO_VALIDADA"
                                if process_summaries is not None
                                else "SEM_POLITICA_AGREGACAO_PROCESSO"
                            ),
                            politica={
                                "experimental": True,
                                "score_processo": None,
                                **(
                                    {"sintese_por_modelo": config["sintese_processo"]}
                                    if process_summaries is not None
                                    else {}
                                ),
                            },
                        )
                    )
                self.reconcile(cn, execution_id, base_id, recorded_config)
                cn.execute(
                    execution.update()
                    .where(execution.c.id == execution_id)
                    .values(status="concluida", concluido_em=datetime.now(timezone.utc))
                )
        except Exception:
            cn.rollback()
            with cn.begin():
                cn.execute(
                    execution.update()
                    .where(execution.c.id == execution_id)
                    .values(
                        status="falhou",
                        erro="FALHA_LOTE",
                        concluido_em=datetime.now(timezone.utc),
                    )
                )
            raise
        return {
            "execucao_id": str(execution_id),
            "base_id": str(base_id),
            "status": "concluida",
            "reutilizada": False,
            "contagens": summary,
            "manifesto": stored,
        }

    def reconcile(self, cn, execution_id, base_id, config):
        info = config["manifesto"]
        with self.objects.open(info["chave"]) as stream:
            raw = stream.read(64 * 1024**2 + 1)
        if len(raw) > 64 * 1024**2 or hashlib.sha256(raw).hexdigest() != info["sha256"]:
            raise ValueError("Manifesto da execução diverge")
        manifest = json.loads(raw)
        if (
            manifest["execucao_id"] != str(execution_id)
            or manifest["base_id"] != str(base_id)
            or canonical(manifest["cobertura"]) != canonical(config["cobertura"])
            or manifest["contagens"] != config["contagens"]
            or any(config[k] != v for k, v in manifest["configuracao"].items())
        ):
            raise ValueError("Snapshot não corresponde à execução")
        results = self.tables["resultados_modelo"]
        actual = (
            cn.execute(
                sa.select(results).where(
                    results.c.execucao_id == execution_id, results.c.base_id == base_id
                )
            )
            .mappings()
            .all()
        )
        expected = {r["id"]: r for r in manifest["scores"]}
        if len(actual) != config["contagens"]["scores"] or {str(r["id"]) for r in actual} != set(
            expected
        ):
            raise ValueError("Lote não reconciliado")
        for row in actual:
            frozen = expected[str(row["id"])]
            if canonical({k: row[k] for k in frozen}) != canonical(frozen):
                raise ValueError("Score persistido diverge do snapshot")
        models = self.tables["execucoes_modelos"]
        if {
            str(m)
            for m in cn.scalars(
                sa.select(models.c.modelo_id).where(models.c.execucao_id == execution_id)
            )
        } != set(config["modelos"]):
            raise ValueError("Modelos associados incompletos")
        factors = self.tables["fatores_sinalizacao"]
        actual_factors = (
            cn.execute(
                sa.select(factors).where(
                    factors.c.resultado_modelo_id.in_([r["id"] for r in actual])
                )
            )
            .mappings()
            .all()
        )
        expected_factors = {
            (r["resultado_modelo_id"], r["atributo"], r["metodo"]): r for r in manifest["fatores"]
        }
        if len(actual_factors) != len(expected_factors):
            raise ValueError("Explicações incompletas")
        for factor in actual_factors:
            frozen = expected_factors.get(
                (str(factor["resultado_modelo_id"]), factor["atributo"], factor["metodo"])
            )
            if frozen is None or canonical({k: factor[k] for k in frozen}) != canonical(frozen):
                raise ValueError("Explicação persistida diverge")
        summaries = self.tables["sinteses_processo_modelo"]
        actual_summaries = (
            cn.execute(sa.select(summaries).where(summaries.c.execucao_id == execution_id))
            .mappings()
            .all()
        )
        frozen_summaries = {r["id"]: r for r in manifest.get("sinteses_processo", [])}
        if len(actual_summaries) != len(frozen_summaries):
            raise ValueError("Sínteses de processo incompletas")
        for row in actual_summaries:
            frozen = frozen_summaries.get(str(row["id"]))
            if frozen is None or canonical({k: row[k] for k in frozen}) != canonical(frozen):
                raise ValueError("Síntese de processo diverge do snapshot")
        if "sinteses_processo" in manifest:
            expected_pairs = {(p, m) for p in manifest["processos"] for m in config["modelos"]}
            if {
                (str(r["processo_versao_id"]), str(r["modelo_id"])) for r in actual_summaries
            } != expected_pairs:
                raise ValueError("Cobertura de sínteses por processo/modelo incompleta")
        assessments = self.tables["avaliacoes_processo"]
        processes = list(
            cn.scalars(
                sa.select(assessments.c.processo_versao_id).where(
                    assessments.c.execucao_id == execution_id
                )
            )
        )
        if set(map(str, processes)) != set(manifest["processos"]) or len(processes) != len(
            manifest["processos"]
        ):
            raise ValueError("Cobertura de processos incompleta")
        item_ids = list(
            cn.scalars(
                sa.select(self.tables["itens_versoes"].c.id).where(
                    self.tables["itens_versoes"].c.base_id == base_id
                )
            )
        )
        events = self.tables["resultados_itens"]
        by_item = {str(uid): [] for uid in item_ids}
        for event in cn.execute(
            sa.select(events.c.id, events.c.item_versao_id).where(events.c.base_id == base_id)
        ):
            by_item[str(event.item_versao_id)].append(str(event.id))
        expected_coverage = {
            (uid, event, model)
            for uid, ids in by_item.items()
            for event in (ids or [None])
            for model in config["modelos"]
        }
        observed = [
            (r["item_versao_id"], r["resultado_item_id"], r["modelo_id"])
            for r in config["cobertura"]
        ]
        if len(observed) != len(expected_coverage) or set(observed) != expected_coverage:
            raise ValueError("Cobertura não contém todos os itens/resultados/modelos")

    def publish(self, execution_id, fail=False):
        executions, publications = (
            self.tables["execucoes_analise"],
            self.tables["publicacoes_analise"],
        )
        with self.repo.locked() as cn:
            execution = (
                cn.execute(sa.select(executions).where(executions.c.id == execution_id))
                .mappings()
                .one_or_none()
            )
            if (
                not execution
                or execution["status"] != "concluida"
                or execution["configuracao"].get("experimental") is not True
            ):
                raise ValueError("Somente execução experimental completa pode ser ativada")
            info = execution["configuracao"]["manifesto"]
            with self.objects.open(info["chave"]) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != info["sha256"]:
                    raise ValueError("Manifesto da inferência corrompido")
            self.reconcile(cn, execution_id, execution["base_id"], execution["configuracao"])
            name = "experimental:" + str(execution["base_id"])
            active = (
                cn.execute(
                    sa.select(publications).where(
                        publications.c.nome == name, publications.c.ativa.is_(True)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if active and active["execucao_id"] == execution_id:
                cn.rollback()
                return {
                    "status": "publicada_experimental",
                    "execucao_id": str(execution_id),
                    "reutilizada": True,
                }
            prior = (
                cn.execute(
                    sa.select(publications).where(
                        publications.c.nome == name, publications.c.execucao_id == execution_id
                    )
                )
                .mappings()
                .one_or_none()
            )
            cn.commit()
            with cn.begin():
                cn.execute(
                    publications.update()
                    .where(publications.c.nome == name, publications.c.ativa.is_(True))
                    .values(ativa=False)
                )
                if fail:
                    raise RuntimeError("Falha controlada na troca de publicação")
                if prior:
                    cn.execute(
                        publications.update()
                        .where(publications.c.id == prior["id"])
                        .values(ativa=True)
                    )
                else:
                    cn.execute(
                        publications.insert().values(
                            nome=name,
                            base_id=execution["base_id"],
                            execucao_id=execution_id,
                            ativa=True,
                        )
                    )
        return {
            "status": "publicada_experimental",
            "execucao_id": str(execution_id),
            "reutilizada": False,
        }
