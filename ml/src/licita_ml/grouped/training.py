"""Executar todos os lotes elegíveis com os mesmos 45 ajustes por grupo."""

import fcntl
import json
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

from threadpoolctl import threadpool_limits

from licita_ml.analytical.rules import digest
from licita_ml.diagnostics import checksum
from licita_ml.grouped.temporal import validate as validate_source
from licita_ml.training.pipeline import PROTOCOL, code_hash, prepare, validate

LOGGER = logging.getLogger(__name__)
VERSION = "treino-agrupado-lotes-v1"


def worker(dataset, output, reviews):
    with threadpool_limits(limits=1):
        result = prepare(Path(dataset), Path(output), Path(reviews))
    return {
        "dataset": str(dataset),
        "dataset_sha256": checksum(Path(dataset) / "manifesto.json"),
        "treino": result["diretorio"],
        "treino_sha256": checksum(Path(result["diretorio"]) / "manifesto.json"),
        "grupos": [
            {
                "grupo": g["grupo"],
                "treino": g["treino"],
                "avaliacao": g["avaliacao"],
                "isolation_forest_apto": g["isolation_forest"]["modelos"]["preco_quantidade"][
                    "estabilidade_aprovada"
                ],
                "autoencoder_apto": g["autoencoder"]["aprovado_tecnicamente"],
            }
            for g in result["manifesto"]["grupos"]
        ],
    }


def checked(folder):
    result = json.loads((folder / "manifesto.json").read_text())
    if result["versao"] != VERSION or digest(result["configuracao"]) != result["fingerprint"]:
        raise ValueError("Manifesto de lotes treinados divergente")
    groups = set()
    for item in result["lotes"]:
        training, dataset = Path(item["treino"]), Path(item["dataset"])
        if (
            checksum(training / "manifesto.json") != item["treino_sha256"]
            or checksum(dataset / "manifesto.json") != item["dataset_sha256"]
        ):
            raise ValueError("Lote treinado ou dataset divergente")
        manifest = validate(training)
        ids = {g["grupo"] for g in manifest["grupos"]}
        if groups & ids or ids != {g["grupo"] for g in item["grupos"]}:
            raise ValueError("Grupos treinados incompletos ou repetidos")
        groups |= ids
    if len(groups) != result["grupos_treinados"]:
        raise ValueError("Contagem de grupos treinados divergente")
    return result


def run(source, output, reviews, workers=2):
    source, output, reviews = Path(source), Path(output), Path(reviews)
    if not 1 <= workers <= 3:
        raise ValueError("Usar entre um e três processos de treino")
    origin = validate_source(source)
    if not origin["grupos_selecionados"]:
        raise ValueError("Nenhum grupo elegível; treino não executado")
    config = {
        "origem_sha256": checksum(source / "manifesto.json"),
        "codigo_treino": code_hash(),
        "codigo_orquestrador": checksum(Path(__file__)),
        "protocolo_sha256": checksum(PROTOCOL),
    }
    fp = digest(config)
    folder = output / ("execucao=" + fp)
    folder.mkdir(parents=True, exist_ok=True)
    with (output / ".lotes-treino.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (folder / "manifesto.json").exists():
            return {"diretorio": str(folder), "reutilizada": True, "manifesto": checked(folder)}
        jobs = [source / b["diretorio"] for b in origin["lotes"]]
        results = []
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as executor:
            pending = {
                executor.submit(
                    worker, dataset, output / "modelos" / dataset.name, reviews
                ): dataset
                for dataset in jobs
            }
            for future in as_completed(pending):
                results.append(future.result())
                LOGGER.info(
                    "Treinados %s/%s lotes (%s grupos)",
                    len(results),
                    len(jobs),
                    sum(len(r["grupos"]) for r in results),
                )
                (folder / "progresso.json").write_text(
                    json.dumps(
                        {"lotes_concluidos": len(results), "lotes_totais": len(jobs)}, indent=2
                    )
                    + "\n"
                )
        groups = [g for r in results for g in r["grupos"]]
        result = {
            "versao": VERSION,
            "fingerprint": fp,
            "configuracao": config,
            "lotes": sorted(results, key=lambda r: r["dataset"]),
            "grupos_treinados": len(groups),
            "modelos_if_estaveis": sum(g["isolation_forest_apto"] for g in groups),
            "modelos_ae_estaveis": sum(g["autoencoder_apto"] for g in groups),
            "ajustes": 45 * len(groups),
            "revisao_humana_concluida": False,
            "probabilidade_fraude": False,
            "publicacao_autorizada": False,
        }
        if len(groups) != origin["grupos_selecionados"]:
            raise ValueError("Nem todos os grupos foram treinados")
        temporary = folder / ".manifesto.json"
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(folder / "manifesto.json")
    checked(folder)
    return {"diretorio": str(folder), "reutilizada": False, "manifesto": result}
