"""Treino/avaliação offline sobre snapshot analítico explicitamente autenticado."""

import copy
import hashlib
import io
import json
import platform
import resource
import time
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow.parquet as pq

from licita_ml.analytical.pipeline import existing, put_immutable
from licita_ml.analytical.rules import Policy, canonical, digest, prepare_references
from licita_ml.experiments.evaluate import evaluate
from licita_ml.resources import RESOURCE_DIR
from licita_ml.validation.review import blind_csv, sample, summarize

PROTOCOL = RESOURCE_DIR / "PROTOCOLO_OPERACIONAL_V1.md"
MAX_BYTES = 32 * 1024**2


def checked(objects, key, checksum, size=None):
    with objects.open(key) as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or (size is not None and len(raw) != size):
        raise ValueError("Artefato excede limite ou tamanho diverge")
    if hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError("SHA-256 do artefato diverge")
    return raw


def read_manifest(objects, key, checksum, schema):
    raw = checked(objects, key, checksum)
    manifest = json.loads(raw)
    if manifest["schema"] != schema:
        raise ValueError("Schema incompatível")
    artifacts = manifest["artefatos"]
    if len({a["chave"] for a in artifacts}) != len(artifacts):
        raise ValueError("Artefatos duplicados")
    contents = {
        a["chave"]: checked(objects, a["chave"], a["sha256"], a["bytes"]) for a in artifacts
    }
    return manifest, contents


def load_groups(manifest, contents):
    artifact = next(a for a in manifest["artefatos"] if a["entidade"] == "referencias")
    table = pq.read_table(io.BytesIO(contents[artifact["chave"]]))
    if table.num_rows > 20000 or table.num_rows != artifact["linhas"]:
        raise ValueError("Quantidade de referências inválida")
    rows = []
    for record in table.to_pylist():
        row = json.loads(record.pop("registro_json"))
        for key, value in record.items():
            if key in row and canonical(row[key]) != canonical(value):
                raise ValueError("Colunas e metadados da referência divergem")
            row[key] = value
        rows.append(row)
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Referências repetidas")
    config = manifest["configuracao"]["politica"].copy()
    for name in ["start", "train_end", "end"]:
        config[name] = date.fromisoformat(config[name])
    config["max_purchase_share"] = Decimal(config["max_purchase_share"])
    policy = Policy(**config)
    exclusion = next(a for a in manifest["artefatos"] if a["entidade"] == "politica_exclusoes")
    exclusions = json.loads(contents[exclusion["chave"]])["exclusoes"]
    recalculated = copy.deepcopy(rows)
    groups = prepare_references(recalculated, policy, {e["id_referencia"]: e for e in exclusions})

    def numeric_metadata(value, key=None):
        # Arrow fixa escala 8; 0.90 e 0.90000000 têm o mesmo valor decimal.
        if isinstance(value, dict):
            return {k: numeric_metadata(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [numeric_metadata(v) for v in value]
        if isinstance(value, str) and key in {"mediana_treino", "mediana", "valor"}:
            with localcontext() as context:
                context.prec = 100
                return str(Decimal(value).normalize())
        return value

    if canonical(numeric_metadata(groups)) != canonical(numeric_metadata(manifest["grupos"])):
        raise ValueError("Grupos não reproduzem política congelada")
    for original, recomputed in zip(rows, recalculated, strict=True):
        for key in ["particao", "motivos_exclusao", "atributos"]:
            if canonical(numeric_metadata(original[key])) != canonical(
                numeric_metadata(recomputed[key])
            ):
                raise ValueError("Referência não reproduz política congelada")
    return rows, groups, policy


def source_code_hash():
    root = Path(__file__).parent
    paths = list(root.glob("*.py")) + [
        root.parent / "experiments/evaluate.py",
        root.parent / "analytical/rules.py",
    ]
    return digest(
        [
            (str(p.relative_to(root.parent)), hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(paths)
        ]
    )


class ValidationPipeline:
    def __init__(self, objects):
        self.objects = objects

    def run(self, manifest_key, checksum):
        started = time.monotonic()
        source, contents = read_manifest(
            self.objects, manifest_key, checksum, "licita-atributos-v1"
        )
        rows, groups, policy = load_groups(source, contents)
        protocol = PROTOCOL.read_bytes()
        config = {
            "dataset": {
                "chave": manifest_key,
                "sha256": checksum,
                "fingerprint": source["fingerprint"],
            },
            "codigo_sha256": source_code_hash(),
            "protocolo_sha256": hashlib.sha256(protocol).hexdigest(),
            "dependencias": {
                name: version(name)
                for name in ["scikit-learn", "numpy", "scipy", "joblib", "pyarrow"]
            },
            "python": platform.python_version(),
        }
        fingerprint = digest(config)
        prefix = f"validacao/isolation-forest/{fingerprint}"
        key = prefix + "/manifesto.json"
        previous = existing(self.objects, key)
        if previous is not None:
            checksum_previous = hashlib.sha256(previous).hexdigest()
            old, _ = read_manifest(self.objects, key, checksum_previous, "licita-validacao-if-v1")
            if old["configuracao"] != config:
                raise ValueError("Configuração da avaliação diverge")
            return {
                "status": old["decisao"],
                "reutilizada": True,
                "fingerprint": fingerprint,
                "manifesto": key,
                "sha256_manifesto": checksum_previous,
                "grupos_avaliados": len(old["grupos"]),
            }
        artifacts, results, reviews = [], [], {}

        def store(name, raw, entity):
            info = {**put_immutable(self.objects, prefix + "/" + name, raw), "entidade": entity}
            artifacts.append(info)
            return info

        store("protocolo.md", protocol, "protocolo")
        for group in groups:
            if not group["elegivel_tecnicamente"]:
                continue
            members = [
                r for r in rows if r["grupo"] == group["grupo"] and not r["motivos_exclusao"]
            ]
            train = sorted([r for r in members if r["particao"] == "treino"], key=lambda r: r["id"])
            test = sorted(
                [r for r in members if r["particao"] == "avaliacao"], key=lambda r: r["id"]
            )
            # Amostra do treino fixada sem consultar rankings.
            training_sample = sample(train, 20)

            def convert(row):
                return {
                    "id": row["id"],
                    "price": row["preco_unitario"],
                    "quantity": row["quantidade"],
                    "date": row["data_compra"],
                }

            prepared = {
                "id": group["grupo"],
                "eligible": True,
                "group": group["especificacao"],
                "train": [convert(r) for r in train],
                "test": [convert(r) for r in test],
            }
            with TemporaryDirectory(prefix="licita-if-") as temp:
                result, rankings, ratios, bilateral = evaluate(
                    prepared, Path(temp), train_end=policy.train_end
                )
                for label, model in result["modelos"].items():
                    local = Path(model.pop("artefato"))
                    info = store(
                        f"{group['grupo']}/modelos/{label}.joblib", local.read_bytes(), "modelo"
                    )
                    model["artefato_chave"] = info["chave"]
            mapping = {
                "if_" + label: model["top_ids"] for label, model in result["modelos"].items()
            }
            mapping.update(
                unilateral=result["baseline_sobrepreco"], bilateral=result["baseline_bilateral"]
            )
            selected = set(uid for ids in mapping.values() for uid in ids)
            selected.update(
                r["id"] for r in sample([r for r in test if r["id"] not in selected], 3)
            )
            evaluation_sample = [r for r in test if r["id"] in selected]
            gid = group["grupo"]
            store(
                f"{gid}/treino_manifesto.json",
                (
                    canonical(
                        {
                            "grupo": gid,
                            "ids_treino": [r["id"] for r in train],
                            "mediana": result["mediana_treino"],
                            "dataset": config["dataset"],
                            "corte_resultado": str(policy.train_end),
                            "fontes": source["fontes"],
                            "politica": source["configuracao"]["politica"],
                            "base_sql_treino_registrada": False,
                        }
                    )
                    + "\n"
                ).encode(),
                "manifesto_treino",
            )
            for label, members_sample in [
                ("treino", training_sample),
                ("avaliacao", evaluation_sample),
            ]:
                store(f"{gid}/revisao_{label}.csv", blind_csv(members_sample), "revisao_" + label)
            store(
                f"{gid}/reservado_rankings.json",
                (
                    canonical(
                        {
                            "rankings": mapping,
                            "ids_avaliacao": [r["id"] for r in test],
                            "ids_revisao_avaliacao": [r["id"] for r in evaluation_sample],
                            "ids_revisao_treino": [r["id"] for r in training_sample],
                            "scores": rankings,
                            "unilateral": ratios.tolist(),
                            "bilateral": bilateral.tolist(),
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
            results.append(result)
        manifest = {
            "schema": "licita-validacao-if-v1",
            "fingerprint": fingerprint,
            "configuracao": config,
            "artefatos": artifacts,
            "grupos": results,
            "criado_em_utc": datetime.now(timezone.utc).isoformat(),
            "decisao": "inconclusivo_por_revisao" if results else "inconclusivo_por_dados",
            "revisoes": reviews,
            "utilidade_aprovada": False,
            "publicacao_autorizada": False,
            "confirmacao_temporal": "inconclusiva_sem_lote_posterior_elegivel",
            "snapshot_ponto_no_tempo": False,
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
            "grupos_avaliados": len(results),
            "revisoes": reviews,
            "medicoes": manifest["medicoes"],
        }

    def review(self, key, checksum, group, training_path, evaluation_path):
        manifest, contents = read_manifest(self.objects, key, checksum, "licita-validacao-if-v1")
        reserved = json.loads(contents[key.rsplit("/", 1)[0] + f"/{group}/reservado_rankings.json"])
        training_raw = Path(training_path).read_bytes()
        evaluation_raw = Path(evaluation_path).read_bytes()
        return {
            "manifesto_sha256": checksum,
            "grupo": group,
            "planilhas_sha256": {
                "treino": hashlib.sha256(training_raw).hexdigest(),
                "avaliacao": hashlib.sha256(evaluation_raw).hexdigest(),
            },
            "treino": summarize(
                training_raw,
                reserved["ids_revisao_treino"],
                {},
                contents[key.rsplit("/", 1)[0] + f"/{group}/revisao_treino.csv"],
            ),
            "avaliacao": summarize(
                evaluation_raw,
                reserved["ids_revisao_avaliacao"],
                reserved["rankings"],
                contents[key.rsplit("/", 1)[0] + f"/{group}/revisao_avaliacao.csv"],
            ),
            "publicacao_autorizada": False,
            "nota": (
                "Revisão interna ou independente deve ser identificada pela equipe; "
                "não há aprovação automática."
            ),
        }
