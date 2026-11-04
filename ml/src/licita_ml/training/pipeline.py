"""Treina em coorte congelada; holdout não escolhe parâmetros ou vencedor."""

import fcntl
import itertools
import json
import math
import platform
import resource
import shutil
import tempfile
import time
from contextlib import ExitStack
from datetime import date
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pyarrow.parquet as pq

from licita_ml.analytical.rules import canonical, digest
from licita_ml.comparison import autoencoder as ae_engine
from licita_ml.comparison.pipeline import compare_vectors
from licita_ml.diagnostics import checksum
from licita_ml.experiments import evaluate as if_engine
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.export import NumericExport
from licita_ml.temporal.pipeline import validate as validate_temporal
from licita_ml.training.dataset import load
from licita_ml.validation.review import blind_csv, sample, summarize

PROTOCOL = RESOURCE_DIR / "PROTOCOLO_TREINO_TEMPORAL_V1.json"
SCORES = {
    "id_observacao": "texto",
    "grupo": "texto",
    "particao": "texto",
    "metodo": "texto",
    "compra": "texto",
    "item_oficial": "texto",
    "data_compra": "data",
    "data_resultado": "data",
    "preco_unitario": "decimal",
    "quantidade": "decimal",
    "mediana_treino": "texto",
    "unidade_fornecimento": "texto",
    "capacidade_fonte": "texto",
    "score_bruto": "real",
    "razao_preco_mediana": "real",
    "regra_bilateral": "real",
    "parcela_erro_preco_ae": "real",
    "parcela_erro_quantidade_ae": "real",
}


def protocol_config(path):
    protocol = json.loads(path.read_text())
    forest = protocol["isolation_forest"]
    if (
        protocol["versao"] != "treino-temporal-v1"
        or tuple(protocol["seeds"]) != if_engine.SEEDS
        or tuple(protocol["seeds"]) != ae_engine.SEEDS
        or tuple(itertools.product(forest["arvores"], forest["amostras"])) != if_engine.CONFIGS
        or forest["variantes"] != ["preco", "preco_quantidade"]
        or forest["ancora"] != {"arvores": 200, "amostras_maximas": 256, "seed": 42}
        or forest["contamination"] != "auto"
        or canonical(protocol["autoencoder"]["parametros"]) != canonical(ae_engine.PARAMETERS)
        or protocol["autoencoder"]["arquitetura"] != [2, 1, 2]
        or protocol["autoencoder"]["ancora_seed"] != 42
        or protocol["estabilidade"] != {"spearman_minimo": 0.8, "jaccard_minimo": 0.6}
        or protocol["top_k"] != "min(10,max(3,ceil(0.10*n_avaliacao)))"
        or protocol["sensibilidade"]
        != {"multiplicadores_preco": [3, 10], "razao_controle_min": 0.8, "razao_controle_max": 1.2}
        or protocol["revisao"]
        != {"amostra_treino": 20, "controles_avaliacao": 3, "parecer_automatico": False}
    ):
        raise ValueError("Protocolo não corresponde aos motores e às âncoras predefinidas")
    return protocol


def write_json(path, value):
    path.write_text(canonical(value) + "\n", encoding="utf-8")


def code_hash():
    root = Path(__file__).parents[1]
    dependencies = [
        *Path(__file__).parent.glob("*.py"),
        root / "experiments/evaluate.py",
        root / "experiments/data.py",
        root / "comparison/autoencoder.py",
        root / "comparison/pipeline.py",
        root / "validation/review.py",
        root / "analytical/rules.py",
        root / "temporal/pipeline.py",
        root / "temporal/export.py",
        root / "organized/schema.py",
        root / "diagnostics.py",
    ]
    return digest([(str(p.relative_to(root)), checksum(p)) for p in sorted(dependencies)])


def validate(folder, fingerprint=None):
    manifest = json.loads((folder / "manifesto.json").read_text())
    if (
        manifest["schema"] != "licita-treino-temporal-v1"
        or digest(manifest["configuracao"]) != manifest["fingerprint"]
        or (fingerprint is not None and manifest["fingerprint"] != fingerprint)
    ):
        raise ValueError("Manifesto de treino incompatível")
    expected = {"protocolo.json"}
    group_ids = [g["grupo"] for g in manifest["grupos"]]
    if not group_ids or len(set(group_ids)) != len(group_ids):
        raise ValueError("Grupos ausentes ou repetidos no manifesto de treino")
    for group in manifest["grupos"]:
        gid = group["grupo"]
        if set(group["isolation_forest"]["modelos"]) != {"preco", "preco_quantidade"}:
            raise ValueError("Variantes IF incompletas")
        if {fit["seed"] for fit in group["autoencoder"]["ajustes"]} != set(if_engine.SEEDS):
            raise ValueError("Sementes AE incompletas")
        expected.update(
            f"{gid}/{name}"
            for name in (
                "pontuacoes_treino.csv",
                "pontuacoes_treino.parquet",
                "pontuacoes_avaliacao.csv",
                "pontuacoes_avaliacao.parquet",
                "revisao_treino.csv",
                "revisao_avaliacao.csv",
                "reservado_rankings.json",
                "treino_manifesto.json",
                "comparacao.json",
                "checagem_tecnica.json",
            )
        )
        expected.update(
            f"{gid}/modelos/{gid}-{label}.joblib" for label in ("preco", "preco_quantidade")
        )
        expected.update(f"{gid}/modelos/autoencoder-{seed}.joblib" for seed in if_engine.SEEDS)
    names = [a["arquivo"] for a in manifest["artefatos"]]
    if set(names) != expected:
        raise ValueError("Manifesto de treino incompleto")
    if len(names) != len(set(names)) or not names:
        raise ValueError("Manifesto de treino com artefatos ausentes ou repetidos")
    for artifact in manifest["artefatos"]:
        path = folder / artifact["arquivo"]
        if not path.is_relative_to(folder) or ".." in Path(artifact["arquivo"]).parts:
            raise ValueError("Caminho de artefato inválido")
        if checksum(path) != artifact["sha256"]:
            raise ValueError("Artefato de treino corrompido; não sobrescrever")
        if (
            path.suffix == ".parquet"
            and pq.ParquetFile(path).metadata.num_rows != artifact["linhas"]
        ):
            raise ValueError("Contagem de pontuações divergente")
    # Do not load any persisted pickle during replay/review.
    return manifest


def review_rows(group, members):
    output = []
    for row in members:
        context = group["audit"][row["id"]]
        output.append(
            {
                "id": row["id"],
                "compra": context["compra"],
                "item_oficial": context["item"],
                "fornecedor_hash": digest(context["fornecedor"])[:16],
                "especificacao": group["group"],
                "data_compra": context["data_compra"],
                "data_resultado": context["data_resultado"],
                "preco_unitario": context["preco_unitario"],
                "quantidade": context["quantidade"],
                "proveniencias": [
                    {
                        "arquivo_id": context["arquivo_sha256"],
                        "membro": context["membro"],
                        "ordinal": context["linha"],
                    }
                ],
            }
        )
    return output


def copy_reviews(folder, manifest, root):
    destination = root / manifest["fingerprint"]
    for group in manifest["grupos"]:
        target = destination / group["grupo"]
        target.mkdir(parents=True, exist_ok=True)
        for name in ("revisao_treino.csv", "revisao_avaliacao.csv"):
            source = folder / group["grupo"] / name
            try:
                with (target / name).open("xb") as stream:
                    stream.write(source.read_bytes())
            except FileExistsError:
                pass  # Never overwrite human work, including partial or invalid answers.
    return str(destination)


def export_scores(folder, partition, group, vectors, bundles):
    members = group["train" if partition == "treino" else "test"]
    med = bundles["ae"]["mediana_treino"]
    with ExitStack() as stack:
        writer = NumericExport(folder, f"pontuacoes_{partition}", SCORES)
        stack.callback(writer.close)
        ae_scores, errors = ae_engine.score(bundles["ae"], members)
        if not np.array_equal(ae_scores, np.asarray(vectors["ae"])):
            raise ValueError("Scores AE não reproduzem a coorte")
        for index, row in enumerate(members):
            for method in ("if_preco", "if_preco_quantidade", "ae"):
                parts = errors[index] / 2 if method == "ae" else None
                score = float(vectors[method][index])
                if parts is not None and not math.isclose(
                    float(parts.sum()), score, abs_tol=1e-14, rel_tol=1e-12
                ):
                    raise ValueError("Parcelas AE não conciliam com o score")
                writer.add(
                    {
                        "id_observacao": row["id"],
                        "grupo": group["id"],
                        "particao": partition,
                        "metodo": method,
                        "compra": group["audit"][row["id"]]["compra"],
                        "item_oficial": group["audit"][row["id"]]["item"],
                        "data_compra": row["date"],
                        "data_resultado": group["audit"][row["id"]]["data_resultado"],
                        "preco_unitario": row["price"],
                        "quantidade": row["quantity"],
                        "mediana_treino": str(med),
                        "unidade_fornecimento": group["group"][2],
                        "capacidade_fonte": group["group"][3],
                        "score_bruto": score,
                        "razao_preco_mediana": float(row["price"] / med),
                        "regra_bilateral": abs(math.log(float(row["price"] / med))),
                        "parcela_erro_preco_ae": float(parts[0]) if parts is not None else None,
                        "parcela_erro_quantidade_ae": float(parts[1])
                        if parts is not None
                        else None,
                    }
                )
    return writer.count


def train_group(group, folder, config):
    folder.mkdir()
    train_end = date.fromisoformat(config["politica_temporal"]["train_end"])
    if_report, rankings_if, ratios, bilateral = if_engine.evaluate(
        group, folder, train_end=train_end
    )
    k = if_report["top_k"]
    ae_report, ae_scores, contributions = ae_engine.evaluate_autoencoder(
        group["train"], group["test"], train_end, folder / "modelos", k
    )
    bundles, all_ae_vectors = {}, {}
    metadata = {
        "dataset_fingerprint": config["dataset"]["fingerprint"],
        "dataset_manifesto_sha256": config["dataset"]["sha256"],
        "grupo_id": group["id"],
        "ids_treino": [r["id"] for r in group["train"]],
        "dependencias": config["dependencias"],
    }
    # Load only files created above by this process, after their recorded hash matches.
    for label, model_report in if_report["modelos"].items():
        path = Path(model_report["artefato"])
        if checksum(path) != model_report["sha256_artefato"]:
            raise ValueError("Modelo IF recém-gerado diverge do hash")
        bundle = joblib.load(path)
        bundle.update(metadata)
        joblib.dump(bundle, path, compress=3)
        restored = joblib.load(path)
        replay = -restored["model"].score_samples(
            if_engine.features(group["test"], restored["mediana_treino"], restored["features"])
        )
        if not np.array_equal(replay, rankings_if[label]["scores"]):
            raise ValueError("IF não reproduziu os scores após gravar metadados")
        bundles["if_" + label] = restored
        model_report["artefato"] = str(path.relative_to(folder.parent))
        model_report["sha256_artefato"] = checksum(path)
    for fit in ae_report["ajustes"]:
        path = Path(fit["artefato"])
        if checksum(path) != fit["sha256"]:
            raise ValueError("Modelo AE recém-gerado diverge do hash")
        bundle = joblib.load(path)
        bundle.update(metadata)
        joblib.dump(bundle, path, compress=3)
        restored = joblib.load(path)
        scores, _ = ae_engine.score(restored, group["test"])
        all_ae_vectors[str(fit["seed"])] = scores.tolist()
        if fit["seed"] == 42:
            if not np.array_equal(scores, ae_scores):
                raise ValueError("AE âncora não reproduziu os scores")
            bundles["ae"] = restored
        fit["artefato"] = str(path.relative_to(folder.parent))
        fit["sha256"] = checksum(path)
    ids = [r["id"] for r in group["test"]]
    vectors = {
        "if_preco": rankings_if["preco"]["scores"],
        "if_preco_quantidade": rankings_if["preco_quantidade"]["scores"],
        "ae": ae_scores,
        "regra_sobrepreco": ratios.tolist(),
        "regra_bilateral": bilateral.tolist(),
    }
    comparisons = compare_vectors(vectors, ids, k)
    rankings = {
        method: [ids[i] for i in if_engine.top_indices(scores, ids, k)]
        for method, scores in vectors.items()
    }
    # Calibration uses training scores, never evaluation percentiles.
    train_vectors = {
        method: (
            -bundle["model"].score_samples(
                if_engine.features(group["train"], bundle["mediana_treino"], bundle["features"])
            )
        ).tolist()
        for method, bundle in bundles.items()
        if method.startswith("if_")
    }
    train_vectors["ae"] = ae_engine.score(bundles["ae"], group["train"])[0].tolist()
    counts = {
        "treino": export_scores(folder, "treino", group, train_vectors, bundles),
        "avaliacao": export_scores(folder, "avaliacao", group, vectors, bundles),
    }
    train_review = sample(review_rows(group, group["train"]), 20)
    selected = set(uid for rank in rankings.values() for uid in rank)
    selected.update(
        r["id"] for r in sample([r for r in group["test"] if r["id"] not in selected], 3)
    )
    evaluation_review = [r for r in review_rows(group, group["test"]) if r["id"] in selected]
    (folder / "revisao_treino.csv").write_bytes(blind_csv(train_review))
    (folder / "revisao_avaliacao.csv").write_bytes(blind_csv(evaluation_review))
    write_json(
        folder / "reservado_rankings.json",
        {
            "rankings": rankings,
            "scores": vectors,
            "ids_avaliacao": ids,
            "scores_ae_por_semente": all_ae_vectors,
            "ids_revisao_treino": [r["id"] for r in train_review],
            "ids_revisao_avaliacao": [r["id"] for r in evaluation_review],
            "parcelas_ae": contributions,
        },
    )
    write_json(
        folder / "treino_manifesto.json",
        {
            **metadata,
            "mediana_treino": str(bundles["ae"]["mediana_treino"]),
            "train_end": str(train_end),
            "features": list(ae_engine.NAMES),
            "ids_avaliacao": ids,
            "especificacao": group["group"],
            "escalas_ajustadas_na_avaliacao": False,
        },
    )
    cases = []
    by_id = {r["id"]: r for r in group["test"]}
    for uid in sorted(selected):
        row = by_id[uid]
        index = ids.index(uid)
        cases.append(
            {
                "id": uid,
                "preco_unitario": str(row["price"]),
                "quantidade": str(row["quantity"]),
                "preco_dividido_mediana": float(row["price"] / bundles["ae"]["mediana_treino"]),
                "posicoes": {
                    method: 1 + if_engine.top_indices(scores, ids, len(ids)).index(index)
                    for method, scores in vectors.items()
                },
                "origem": {
                    key: group["audit"][uid][key] for key in ("arquivo_sha256", "membro", "linha")
                },
            }
        )
    write_json(
        folder / "checagem_tecnica.json",
        {
            "tipo": "checagem_numerica_automatizada",
            "parecer_humano": False,
            "comparabilidade_documental_aprovada": False,
            "casos": cases,
            "limite": "Posição e diferença de ranking não comprovam fraude ou superioridade.",
        },
    )
    return {
        "grupo": group["id"],
        "especificacao": group["group"],
        "treino": len(group["train"]),
        "avaliacao": len(ids),
        "top_k": k,
        "isolation_forest": if_report,
        "autoencoder": ae_report,
        "comparacoes": comparisons,
        "pontuacoes": counts,
        "revisao": {
            "treino_pendente": len(train_review),
            "avaliacao_pendente": len(evaluation_review),
        },
        "total_ajustes": len(if_engine.CONFIGS) * len(if_engine.SEEDS) * 2 + len(ae_engine.SEEDS),
        "vencedor_validado": None,
        "utilidade_comprovada": False,
    }


def prepare(base, output, review_root, protocol_path=PROTOCOL):
    started = time.monotonic()
    protocol_config(protocol_path)
    source, groups = load(base)
    config = {
        "dataset": {
            "fingerprint": source["fingerprint"],
            "sha256": checksum(base / "manifesto.json"),
        },
        "politica_temporal": source["configuracao"]["politica"],
        "protocolo_sha256": checksum(protocol_path),
        "codigo_sha256": code_hash(),
        "dependencias": {
            name: version(name)
            for name in ("scikit-learn", "numpy", "scipy", "joblib", "pyarrow", "threadpoolctl")
        },
        "python": platform.python_version(),
    }
    fingerprint = digest(config)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"execucao={fingerprint}"
    with (output / ".treino.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists():
            manifest = validate(destination, fingerprint)
            return {
                "diretorio": str(destination),
                "reutilizada": True,
                "manifesto": manifest,
                "revisoes_editaveis": copy_reviews(destination, manifest, review_root),
            }
        with tempfile.TemporaryDirectory(prefix=".treino-", dir=output) as temporary:
            folder = Path(temporary) / "execucao"
            folder.mkdir()
            shutil.copyfile(protocol_path, folder / "protocolo.json")
            results = [train_group(group, folder / gid, config) for gid, group in groups.items()]
            for result in results:
                write_json(folder / result["grupo"] / "comparacao.json", result)
            artifacts = []
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    count = (
                        pq.ParquetFile(path).metadata.num_rows
                        if path.suffix == ".parquet"
                        else None
                    )
                    artifacts.append(
                        {
                            "arquivo": str(path.relative_to(folder)),
                            "sha256": checksum(path),
                            "bytes": path.stat().st_size,
                            "linhas": count,
                        }
                    )
            validate_temporal(base, source["fingerprint"])
            if checksum(base / "manifesto.json") != config["dataset"]["sha256"]:
                raise ValueError("Dataset mudou durante o treino")
            manifest = {
                "schema": "licita-treino-temporal-v1",
                "fingerprint": fingerprint,
                "configuracao": config,
                "artefatos": artifacts,
                "grupos": results,
                "status": "comparacao_tecnica_concluida",
                "decisao_utilidade": "inconclusiva_por_revisao",
                "vencedor_validado": None,
                "publicacao_autorizada": False,
                "scores_combinados": False,
                "aplicacao_pontuada": False,
                "banco_operacional_alterado": False,
                "snapshot_ponto_no_tempo": False,
                "medicoes": {
                    "duracao_segundos": round(time.monotonic() - started, 3),
                    "rss_pico_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
                    ),
                },
            }
            write_json(folder / "manifesto.json", manifest)
            folder.rename(destination)
    return {
        "diretorio": str(destination),
        "reutilizada": False,
        "manifesto": manifest,
        "revisoes_editaveis": copy_reviews(destination, manifest, review_root),
    }


def review(folder, group, training_path, evaluation_path, nature):
    manifest = validate(folder)
    if group not in {r["grupo"] for r in manifest["grupos"]} or nature not in {
        "interna",
        "independente_declarada",
    }:
        raise ValueError("Grupo ou natureza da revisão inválidos")
    source = folder / group
    reserved = json.loads((source / "reservado_rankings.json").read_text())
    training = summarize(
        training_path.read_bytes(),
        reserved["ids_revisao_treino"],
        {},
        (source / "revisao_treino.csv").read_bytes(),
    )
    evaluation = summarize(
        evaluation_path.read_bytes(),
        reserved["ids_revisao_avaliacao"],
        reserved["rankings"],
        (source / "revisao_avaliacao.csv").read_bytes(),
    )
    return {
        "execucao_fingerprint": manifest["fingerprint"],
        "grupo": group,
        "natureza_declarada": nature,
        "treino": training,
        "avaliacao": evaluation,
        "vencedor_validado": None,
        "publicacao_autorizada": False,
        "utilidade_aprovada_automaticamente": False,
    }
