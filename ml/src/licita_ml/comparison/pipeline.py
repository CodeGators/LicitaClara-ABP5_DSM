"""Compara AE e resultados IF congelados, sempre nas mesmas referências."""

import hashlib
import itertools
import json
import math
import platform
import resource
import time
from datetime import datetime, timezone
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from licita_ml.analytical.pipeline import existing, put_immutable
from licita_ml.analytical.rules import canonical, digest
from licita_ml.comparison.autoencoder import NAMES, evaluate_autoencoder
from licita_ml.experiments.evaluate import (
    correlation,
    features,
    overlap,
    top_indices,
    train_reference,
)
from licita_ml.resources import RESOURCE_DIR
from licita_ml.validation.pipeline import load_groups, read_manifest
from licita_ml.validation.review import blind_csv, sample, summarize

PROTOCOL = RESOURCE_DIR / "PROTOCOLO_AUTOENCODER_V1.md"


def code_hash():
    root = Path(__file__).parent
    paths = list(root.glob("*.py")) + [
        root.parent / name
        for name in [
            "experiments/evaluate.py",
            "validation/pipeline.py",
            "validation/review.py",
            "analytical/rules.py",
            "analytical/pipeline.py",
        ]
    ]
    return digest(
        [
            (str(p.relative_to(root.parent)), hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(paths)
        ]
    )


def convert(row):
    return {
        "id": row["id"],
        "price": row["preco_unitario"],
        "quantity": row["quantidade"],
        "date": row["data_compra"],
    }


def compare_vectors(vectors, ids, k):
    for scores in vectors.values():
        if len(scores) != len(ids) or not np.isfinite(scores).all():
            raise ValueError("Scores não correspondem ao universo da comparação")
    tops = {label: top_indices(scores, ids, k) for label, scores in vectors.items()}
    return [
        {
            "a": a,
            "b": b,
            "spearman": correlation(vectors[a], vectors[b]),
            "sobreposicao_topk": len(set(tops[a]) & set(tops[b])) / k,
            "jaccard_topk": overlap(tops[a], tops[b]),
        }
        for a, b in itertools.combinations(vectors, 2)
    ]


class ComparisonPipeline:
    def __init__(self, objects):
        self.objects = objects

    def run(self, if_key, if_checksum):
        started = time.monotonic()
        previous_if, if_contents = read_manifest(
            self.objects, if_key, if_checksum, "licita-validacao-if-v1"
        )
        dataset = previous_if["configuracao"]["dataset"]
        source, contents = read_manifest(
            self.objects, dataset["chave"], dataset["sha256"], "licita-atributos-v1"
        )
        if source["fingerprint"] != dataset["fingerprint"]:
            raise ValueError("Dataset IF não corresponde ao manifesto analítico")
        rows, groups, policy = load_groups(source, contents)
        if_groups = {g["group_id"]: g for g in previous_if["grupos"]}
        eligible = {g["grupo"] for g in groups if g["elegivel_tecnicamente"]}
        if len(if_groups) != len(previous_if["grupos"]) or set(if_groups) != eligible:
            raise ValueError("Grupos IF divergem da política analítica")
        protocol = PROTOCOL.read_bytes()
        config = {
            "avaliacao_if": {"chave": if_key, "sha256": if_checksum},
            "dataset": dataset,
            "codigo_sha256": code_hash(),
            "protocolo_sha256": hashlib.sha256(protocol).hexdigest(),
            "dependencias": {
                name: version(name)
                for name in ["scikit-learn", "numpy", "scipy", "joblib", "pyarrow", "threadpoolctl"]
            },
            "python": platform.python_version(),
        }
        fingerprint = digest(config)
        prefix = f"validacao/comparacao/{fingerprint}"
        key = prefix + "/manifesto.json"
        prior = existing(self.objects, key)
        if prior is not None:
            checksum = hashlib.sha256(prior).hexdigest()
            manifest, _ = read_manifest(self.objects, key, checksum, "licita-comparacao-v1")
            if manifest["configuracao"] != config:
                raise ValueError("Configuração da comparação diverge")
            return {
                "status": manifest["decisao"],
                "reutilizada": True,
                "fingerprint": fingerprint,
                "manifesto": key,
                "sha256_manifesto": checksum,
                "grupos": len(manifest["grupos"]),
            }
        artifacts, results, reviews = [], [], {}

        def store(name, raw, entity):
            info = {**put_immutable(self.objects, prefix + "/" + name, raw), "entidade": entity}
            artifacts.append(info)
            return info

        store("protocolo.md", protocol, "protocolo")
        for gid in sorted(eligible):
            report_if = if_groups[gid]
            members = [r for r in rows if r["grupo"] == gid and not r["motivos_exclusao"]]
            train = sorted([r for r in members if r["particao"] == "treino"], key=lambda r: r["id"])
            test = sorted(
                [r for r in members if r["particao"] == "avaliacao"], key=lambda r: r["id"]
            )
            train_rows, test_rows = [convert(r) for r in train], [convert(r) for r in test]
            ids = [r["id"] for r in test]
            k = min(10, max(3, math.ceil(0.1 * len(test))))
            if (report_if["treino"], report_if["teste"], report_if["top_k"]) != (
                len(train),
                len(test),
                k,
            ):
                raise ValueError("Cortes IF não correspondem ao dataset")
            if_prefix = if_key.rsplit("/", 1)[0] + "/" + gid
            reserved = json.loads(if_contents[if_prefix + "/reservado_rankings.json"])
            training_manifest = json.loads(if_contents[if_prefix + "/treino_manifesto.json"])
            if reserved["ids_avaliacao"] != ids or training_manifest["ids_treino"] != [
                r["id"] for r in train
            ]:
                raise ValueError("IDs IF não correspondem ao treino/avaliação")
            med = train_reference(train_rows, train_end=policy.train_end)
            if med != Decimal(report_if["mediana_treino"]):
                raise ValueError("Mediana IF não corresponde ao treino")
            store(
                f"{gid}/treino_manifesto.json",
                if_contents[if_prefix + "/treino_manifesto.json"],
                "manifesto_treino",
            )
            if np.any(np.ptp(features(train_rows, med, NAMES), axis=0) == 0):
                results.append(
                    {
                        "grupo": gid,
                        "treino": len(train),
                        "avaliacao": len(test),
                        "autoencoder": {
                            "status": "indisponivel_atributo_constante",
                            "aprovado_tecnicamente": False,
                        },
                    }
                )
                continue
            with TemporaryDirectory(prefix="licita-ae-") as temp:
                ae, scores, contributions = evaluate_autoencoder(
                    train_rows, test_rows, policy.train_end, Path(temp), k
                )
                for model in ae["ajustes"]:
                    path = Path(model.pop("artefato"))
                    artifact = store(f"{gid}/modelos/{path.name}", path.read_bytes(), "modelo_ae")
                    model["artefato_chave"] = artifact["chave"]
            ratios = [float(row["price"] / med) for row in test_rows]
            bilateral = np.abs(np.log(ratios)).tolist()
            if reserved["unilateral"] != ratios or reserved["bilateral"] != bilateral:
                raise ValueError("Regras IF não correspondem à avaliação")
            vectors = {
                "ae": scores,
                "if_preco_quantidade": reserved["scores"]["preco_quantidade"]["scores"],
                "if_preco": reserved["scores"]["preco"]["scores"],
                "unilateral": ratios,
                "bilateral": bilateral,
            }
            pairs = compare_vectors(vectors, ids, k)
            rankings = {
                name: [ids[i] for i in top_indices(values, ids, k)]
                for name, values in vectors.items()
            }
            for name in ["preco", "preco_quantidade"]:
                if rankings["if_" + name] != report_if["modelos"][name]["top_ids"]:
                    raise ValueError("Ranking IF não reproduz scores congelados")
            selection = set(uid for ranking in rankings.values() for uid in ranking)
            selection.update(
                r["id"] for r in sample([r for r in test if r["id"] not in selection], 3)
            )
            evaluation_sample = [r for r in test if r["id"] in selection]
            training_sample = sample(train, 20)
            store(f"{gid}/revisao_avaliacao.csv", blind_csv(evaluation_sample), "revisao_avaliacao")
            store(f"{gid}/revisao_treino.csv", blind_csv(training_sample), "revisao_treino")
            store(
                f"{gid}/reservado_rankings.json",
                (
                    canonical(
                        {
                            "ids_avaliacao": ids,
                            "ids_revisao_avaliacao": [r["id"] for r in evaluation_sample],
                            "ids_revisao_treino": [r["id"] for r in training_sample],
                            "rankings": rankings,
                            "scores": vectors,
                            "parcelas_ae": contributions,
                        }
                    )
                    + "\n"
                ).encode(),
                "reservado_rankings",
            )
            reviews[gid] = {
                "treino_pendente": len(training_sample),
                "avaliacao_pendente": len(evaluation_sample),
            }
            results.append(
                {
                    "grupo": gid,
                    "treino": len(train),
                    "avaliacao": len(test),
                    "top_k": k,
                    "autoencoder": ae,
                    "isolation_forest": report_if["modelos"],
                    "comparacoes": pairs,
                }
            )
        manifest = {
            "schema": "licita-comparacao-v1",
            "fingerprint": fingerprint,
            "configuracao": config,
            "artefatos": artifacts,
            "grupos": results,
            "revisoes": reviews,
            "criado_em_utc": datetime.now(timezone.utc).isoformat(),
            "decisao": "inconclusivo_por_revisao" if reviews else "inconclusivo_por_dados",
            "vencedor_validado": None,
            "publicacao_autorizada": False,
            "scores_combinados": False,
            "utilidade_comprovada": False,
            "snapshot_ponto_no_tempo": False,
            "confirmacao_temporal": "inconclusiva_sem_lote_posterior_elegivel",
            "politica_ranking": "sem escolha de vencedor validado; somente comparação experimental",
            "medicoes": {
                "duracao_segundos": round(time.monotonic() - started, 3),
                "rss_pico_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
            },
        }
        stored = put_immutable(self.objects, key, (canonical(manifest) + "\n").encode())
        return {
            "status": manifest["decisao"],
            "reutilizada": False,
            "fingerprint": fingerprint,
            "manifesto": key,
            "sha256_manifesto": stored["sha256"],
            "grupos": len(results),
            "revisoes": reviews,
            "medicoes": manifest["medicoes"],
        }

    def review(self, key, checksum, group, training_path, evaluation_path):
        _, contents = read_manifest(self.objects, key, checksum, "licita-comparacao-v1")
        prefix = key.rsplit("/", 1)[0] + "/" + group
        reserved = json.loads(contents[prefix + "/reservado_rankings.json"])
        raw_train, raw_test = Path(training_path).read_bytes(), Path(evaluation_path).read_bytes()
        return {
            "manifesto_sha256": checksum,
            "grupo": group,
            "planilhas_sha256": {
                "treino": hashlib.sha256(raw_train).hexdigest(),
                "avaliacao": hashlib.sha256(raw_test).hexdigest(),
            },
            "treino": summarize(
                raw_train,
                reserved["ids_revisao_treino"],
                {},
                contents[prefix + "/revisao_treino.csv"],
            ),
            "avaliacao": summarize(
                raw_test,
                reserved["ids_revisao_avaliacao"],
                reserved["rankings"],
                contents[prefix + "/revisao_avaliacao.csv"],
            ),
            "publicacao_autorizada": False,
            "vencedor_validado": None,
        }
