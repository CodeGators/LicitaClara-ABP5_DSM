"""Registros de treino/modelo sobre artefatos privados verificados da aplicação."""

import hashlib
import io
import json
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import sqlalchemy as sa
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor

from licita_ml.analytical.pipeline import parquet, put_immutable
from licita_ml.analytical.rules import canonical, digest
from licita_ml.comparison.autoencoder import NAMES
from licita_ml.comparison.autoencoder import score as ae_score
from licita_ml.comparison.pipeline import code_hash as comparison_code_hash
from licita_ml.comparison.pipeline import convert
from licita_ml.experiments.evaluate import features, train_reference
from licita_ml.repository import identifier
from licita_ml.resources import RESOURCE_DIR
from licita_ml.validation.pipeline import load_groups, read_manifest

EXTRA = [
    "versoes_modelo",
    "execucoes_analise",
    "execucoes_modelos",
    "resultados_modelo",
    "avaliacoes_processo",
    "fatores_sinalizacao",
    "publicacoes_analise",
]
POLICY = RESOURCE_DIR / "POLITICA_INFERENCIA_EXPERIMENTAL_V1.md"


def tables(repo):
    metadata = sa.MetaData()
    return {
        **repo.tables,
        **{
            name: sa.Table(name, metadata, autoload_with=repo.engine, resolve_fks=False)
            for name in EXTRA
        },
    }


def code_hash():
    root = Path(__file__).parent
    paths = list(root.glob("*.py")) + [
        root.parent / p
        for p in [
            "analytical/operational.py",
            "analytical/rules.py",
            "analytical/pipeline.py",
            "validation/pipeline.py",
            "comparison/autoencoder.py",
            "comparison/pipeline.py",
            "experiments/evaluate.py",
        ]
    ]
    return digest(
        [
            (str(p.relative_to(root.parent)), hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(paths)
        ]
    )


def predict(model, rows):
    bundle = model["bundle"]
    if model["algorithm"] == "autoencoder":
        return ae_score(bundle, rows)
    return -bundle["model"].score_samples(features(rows, bundle["mediana_treino"], NAMES)), None


def percentile(calibration, value):
    if not len(calibration) or not np.isfinite(calibration).all() or not np.isfinite(value):
        raise ValueError("Calibração/score inválido")
    return (
        Decimal(int(np.count_nonzero(np.asarray(calibration) <= value))) * 100 / len(calibration)
    ).quantize(Decimal("0.001"))


def prepare_models(objects, key, checksum):
    comparison, model_contents = read_manifest(objects, key, checksum, "licita-comparacao-v1")
    if comparison["configuracao"]["codigo_sha256"] != comparison_code_hash():
        raise ValueError("Comparação não foi produzida pelo código compatível desta aplicação")
    for name in ["scikit-learn", "numpy", "scipy", "joblib", "pyarrow"]:
        if comparison["configuracao"]["dependencias"][name] != version(name):
            raise ValueError("Dependências divergentes do modelo; não carregar artefato")
    dataset = comparison["configuracao"]["dataset"]
    source, contents = read_manifest(
        objects, dataset["chave"], dataset["sha256"], "licita-atributos-v1"
    )
    rows, groups, policy = load_groups(source, contents)
    if_source = comparison["configuracao"]["avaliacao_if"]
    _, if_contents = read_manifest(
        objects, if_source["chave"], if_source["sha256"], "licita-validacao-if-v1"
    )
    eligible = {g["grupo"]: g for g in groups if g["elegivel_tecnicamente"]}
    models, bases = [], {}
    for group in comparison["grupos"]:
        gid = group["grupo"]
        if not group.get("isolation_forest"):
            continue
        if gid not in eligible:
            raise ValueError("Grupo do modelo não corresponde à política")
        train = sorted(
            [
                r
                for r in rows
                if r["grupo"] == gid and r["particao"] == "treino" and not r["motivos_exclusao"]
            ],
            key=lambda r: r["id"],
        )
        test = sorted(
            [
                r
                for r in rows
                if r["grupo"] == gid and r["particao"] == "avaliacao" and not r["motivos_exclusao"]
            ],
            key=lambda r: r["id"],
        )
        median = train_reference([convert(r) for r in train], train_end=policy.train_end)
        train_config = {
            "grupo": gid,
            "ids": [r["id"] for r in train],
            "dataset": dataset,
            "mediana": str(median),
            "especificacao": eligible[gid]["especificacao"],
            "inicio": str(policy.start),
            "fim": str(policy.train_end),
            "registrador_codigo": code_hash(),
        }
        fp = digest(train_config)
        prefix = f"modelagem/treino={fp}"
        raw, _ = parquet(train, "referencias")
        artifact = put_immutable(objects, prefix + "/referencias.parquet", raw)
        manifest = {
            "schema": "licita-base-treino-v1",
            "configuracao": train_config,
            "artefatos": [artifact],
            "fontes": source["fontes"],
            "linhas": len(train),
            "entidades_dominio_sql": False,
            "revisao_humana_concluida": False,
        }
        stored = put_immutable(
            objects, prefix + "/manifesto.json", (canonical(manifest) + "\n").encode()
        )
        base_id = identifier("versoes_base", "treino:" + fp)
        bases[base_id] = {
            "id": base_id,
            "versao": "treino:" + fp,
            "versao_transformador": "registro-treino-v1",
            "versao_codigo": code_hash(),
            "chave_manifesto": stored["chave"],
            "sha256_manifesto": stored["sha256"],
            "periodo_inicio": policy.start,
            "periodo_fim": policy.train_end,
            "status": "validada",
            "recorte": {"tipo": "treino_modelo", "grupo": gid},
            "qualidade": {
                "referencias_manifesto": len(train),
                "entidades_dominio_sql": False,
                "validacao": "integridade do dataset; não utilidade",
            },
        }
        reserved_key = key.rsplit("/", 1)[0] + f"/{gid}/reservado_rankings.json"
        if reserved_key not in model_contents:
            continue
        reserved = json.loads(model_contents[reserved_key])
        if reserved["ids_avaliacao"] != [r["id"] for r in test]:
            raise ValueError("IDs da avaliação do modelo divergem")
        choices = []
        primary = group["isolation_forest"]["preco_quantidade"]
        if primary["estabilidade_aprovada"]:
            choices.append(
                (
                    "isolation_forest",
                    primary["artefato_chave"],
                    primary["sha256_artefato"],
                    if_contents,
                    reserved["scores"]["if_preco_quantidade"],
                )
            )
        ae = group["autoencoder"]
        if ae.get("aprovado_tecnicamente"):
            anchor = next(m for m in ae["ajustes"] if m["seed"] == 42)
            choices.append(
                (
                    "autoencoder",
                    anchor["artefato_chave"],
                    anchor["sha256"],
                    model_contents,
                    reserved["scores"]["ae"],
                )
            )
        for algorithm, artifact_key, artifact_sha, blobs, replay in choices:
            raw = blobs[artifact_key]
            if hashlib.sha256(raw).hexdigest() != artifact_sha:
                raise ValueError("Modelo diverge do manifesto fixado")
            # Armazenamento privado + manifesto produzido pelo código verificado acima.
            bundle = joblib.load(io.BytesIO(raw))
            expected_type = MLPRegressor if algorithm == "autoencoder" else IsolationForest
            if (
                type(bundle["model"]) is not expected_type
                or bundle["model"].n_features_in_ != 2
                or bundle["features"] != NAMES
                or bundle["mediana_treino"] != median
                or bundle["train_end"] != policy.train_end
            ):
                raise ValueError("Artefato incompatível com o treino declarado")
            if (
                algorithm == "isolation_forest"
                and bundle["group"] != eligible[gid]["especificacao"]
            ):
                raise ValueError("Especificação do IF diverge")
            if algorithm == "autoencoder" and bundle["ids_treino"] != [r["id"] for r in train]:
                raise ValueError("IDs de treino do AE divergem")
            model = {
                "algorithm": algorithm,
                "group": gid,
                "spec": eligible[gid]["especificacao"],
                "bundle": bundle,
                "train_ids": [r["id"] for r in train],
                "train_snapshot": digest(
                    sorted(
                        (
                            r["id"],
                            str(r["preco_unitario"]),
                            str(r["quantidade"]),
                            str(r["data_compra"]),
                            str(r["data_resultado"]),
                        )
                        for r in train
                    )
                ),
            }
            replay_scores, _ = predict(model, [convert(r) for r in test])
            if not np.array_equal(replay_scores, replay):
                raise ValueError("Recarga não reproduz avaliação congelada")
            calibration, _ = predict(model, [convert(r) for r in train])
            if not np.isfinite(calibration).all():
                raise ValueError("Calibração de treino não finita")
            model["calibration"] = calibration.tolist()
            descriptor = {
                "algorithm": algorithm,
                "grupo": gid,
                "base_treino_id": str(base_id),
                "comparacao": {"chave": key, "sha256": checksum},
                "artefato": artifact_key,
                "sha256": artifact_sha,
                "normalizacao": "cdf-treino-v1",
                "codigo": code_hash(),
                "calibracao": model["calibration"],
            }
            version_id = digest(descriptor)
            model["id"] = identifier("versoes_modelo", version_id)
            model["record"] = {
                "id": model["id"],
                "base_treino_id": base_id,
                "algoritmo": algorithm,
                "versao": version_id,
                "versao_codigo": code_hash(),
                "chave_artefato": artifact_key,
                "sha256_artefato": artifact_sha,
                "parametros": descriptor,
                "metricas": {
                    "replay_exato": True,
                    "experimental": True,
                    "utilidade_comprovada": False,
                },
                "preprocessamento": {
                    "features": NAMES,
                    "mediana_treino": str(median),
                    "manifesto_treino": stored,
                    "cdf_treino": model["calibration"],
                },
            }
            models.append(model)
    if not models:
        raise ValueError("Nenhum modelo tecnicamente elegível registrado na comparação")
    return models, list(bases.values())
