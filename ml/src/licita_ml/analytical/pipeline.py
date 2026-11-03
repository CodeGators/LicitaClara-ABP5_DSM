"""Dataset analítico imutável em objetos; não altera a base publicada ou treina modelos."""

import hashlib
import io
import json
import platform
import resource
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import sqlalchemy as sa

from licita_ml.analytical.operational import operational_features, read_base
from licita_ml.analytical.rules import canonical, digest, prepare_references
from licita_ml.analytical.sources import read_history


def code_hash():
    root = Path(__file__).parent
    paths = list(root.glob("*.py")) + [
        root.parent / "normalize.py",
        root.parent / "readers.py",
        root.parent / "repository.py",
    ]
    return digest([(p.name, hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(paths)])


def existing(objects, key):
    try:
        with objects.open(key) as source:
            return source.read()
    except FileNotFoundError:
        return None
    except Exception as error:
        if getattr(error, "response", {}).get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
            return None
        raise


def put_immutable(objects, key, raw):
    previous = existing(objects, key)
    if previous is not None and previous != raw:
        raise ValueError("Objeto analítico existente diverge; não sobrescrever")
    stored = objects.put(key, io.BytesIO(raw)) if previous is None else None
    checksum = hashlib.sha256(raw).hexdigest()
    if stored and (stored.sha256 != checksum or stored.size_bytes != len(raw)):
        raise ValueError("Armazenamento não confirmou o objeto analítico")
    return {"chave": key, "sha256": checksum, "bytes": len(raw)}


def parquet(rows, kind):
    # Dinheiro fica Decimal no Arrow; estruturas variáveis têm JSON textual explícito.
    if kind == "referencias":
        schema = pa.schema(
            [
                ("id", pa.string()),
                ("grupo", pa.string()),
                ("particao", pa.string()),
                ("data_compra", pa.date32()),
                ("data_resultado", pa.date32()),
                ("preco_unitario", pa.decimal128(28, 8)),
                ("quantidade", pa.decimal128(28, 8)),
                ("registro_json", pa.string()),
            ]
        )
        records = [
            {
                **{k: row[k] for k in schema.names if k != "registro_json"},
                "registro_json": canonical(
                    {k: v for k, v in row.items() if k not in {"preco_unitario", "quantidade"}}
                ),
            }
            for row in rows
        ]
    else:
        schema = pa.schema(
            [("id", pa.string()), ("item_versao_id", pa.string()), ("registro_json", pa.string())]
        )
        records = [
            {
                "id": row["id"],
                "item_versao_id": row["item_versao_id"],
                "registro_json": canonical(row),
            }
            for row in rows
        ]
    batch = pa.Table.from_pylist(records, schema=schema)
    output = pa.BufferOutputStream()
    pq.write_table(batch, output, compression="zstd", version="2.6")
    return output.getvalue().to_pybytes(), str(schema)


class AnalyticalPipeline:
    def __init__(self, settings, repository, objects):
        self.settings, self.repo, self.objects = settings, repository, objects

    def run(self, base_id, history_ids, policy, exclusion_path):
        if not history_ids or len(set(history_ids)) != len(history_ids):
            raise ValueError("Informar IDs históricos distintos")
        started = time.monotonic()
        exclusion_raw = Path(exclusion_path).read_bytes()
        exclusion_doc = json.loads(exclusion_raw)
        if exclusion_doc.get("versao") != "exclusoes-documentais-v1":
            raise ValueError("Versão das exclusões documentais incompatível")
        exclusions = {entry["id_referencia"]: entry for entry in exclusion_doc["exclusoes"]}
        if len(exclusions) != len(exclusion_doc["exclusoes"]) or any(
            not entry.get("evidencia_url") or not entry.get("motivo")
            for entry in exclusions.values()
        ):
            raise ValueError("Exclusões duplicadas ou sem evidência/motivo")
        with self.repo.locked() as connection:
            base, operational = read_base(self.repo, connection, base_id)
            with self.objects.open(base["chave_manifesto"]) as stream:
                base_manifest = stream.read(self.settings.processing_max_file_bytes + 1)
            if hashlib.sha256(base_manifest).hexdigest() != base["sha256_manifesto"]:
                raise ValueError("Manifesto da base operacional diverge do banco")
            files_table = self.repo.tables["arquivos_coletados"]
            files = (
                connection.execute(sa.select(files_table).where(files_table.c.id.in_(history_ids)))
                .mappings()
                .all()
            )
            if len(files) != len(history_ids):
                raise ValueError("Histórico solicitado não registrado")
            config = {
                "versao": policy.version,
                "codigo_sha256": code_hash(),
                "politica": policy.manifest(),
                "base_operacional": {
                    "id": str(base_id),
                    "manifesto_sha256": base["sha256_manifesto"],
                    "manifesto_chave": base["chave_manifesto"],
                },
                "fontes": sorted(
                    [
                        {"id": str(f["id"]), "sha256": f["sha256"], "bytes": f["tamanho_bytes"]}
                        for f in files
                    ],
                    key=lambda f: f["id"],
                ),
                "exclusoes_sha256": hashlib.sha256(exclusion_raw).hexdigest(),
                "ambiente": {"python": platform.python_version(), "pyarrow": pa.__version__},
            }
            fingerprint = digest(config)
            prefix = f"analitica/base={fingerprint}"
            key = prefix + "/manifesto.json"
            previous = existing(self.objects, key)
            if previous is not None:
                manifest = json.loads(previous)
                if manifest["configuracao"] != config:
                    raise ValueError("Configuração do manifesto analítico diverge")
                from licita_ml.readers import staged

                for source_file in files:
                    with staged(self.objects, source_file, self.settings):
                        pass
                for artifact in manifest["artefatos"]:
                    raw = existing(self.objects, artifact["chave"])
                    if (
                        raw is None
                        or len(raw) != artifact["bytes"]
                        or hashlib.sha256(raw).hexdigest() != artifact["sha256"]
                    ):
                        raise ValueError("Artefato analítico diverge do manifesto")
                return {
                    "status": "atributos_preparados",
                    "reutilizada": True,
                    "fingerprint": fingerprint,
                    "manifesto": key,
                    "contagens": manifest["contagens"],
                    "duracao_segundos": round(time.monotonic() - started, 3),
                }
            rows, rejects, sources, reconciliation = read_history(
                self.objects, files, self.settings
            )
            groups = prepare_references(rows, policy, exclusions)
            targets = operational_features(base, operational, rows, policy)
            artifacts = []
            artifacts.append(
                {
                    **put_immutable(
                        self.objects, prefix + "/base_operacional_manifesto.json", base_manifest
                    ),
                    "entidade": "manifesto_base_operacional",
                }
            )
            for name, content in [("referencias", rows), ("resultados_operacionais", targets)]:
                raw, schema = parquet(content, name)
                artifacts.append(
                    {
                        **put_immutable(self.objects, f"{prefix}/{name}.parquet", raw),
                        "entidade": name,
                        "linhas": len(content),
                        "esquema_arrow": schema,
                    }
                )
            artifacts.append(
                {
                    **put_immutable(
                        self.objects,
                        prefix + "/rejeicoes.jsonl",
                        "".join(canonical(r) + "\n" for r in rejects).encode(),
                    ),
                    "entidade": "rejeicoes",
                    "linhas": len(rejects),
                }
            )
            artifacts.append(
                {
                    **put_immutable(
                        self.objects, prefix + "/exclusoes_documentais.json", exclusion_raw
                    ),
                    "entidade": "politica_exclusoes",
                }
            )
            exclusions_counts = Counter(reason for r in rows for reason in r["motivos_exclusao"])
            unavailable = Counter(
                value["motivo"]
                for r in targets
                for value in r["atributos"].values()
                if value["valor"] is None
            )
            counts = {
                "referencias_normalizadas": len(rows),
                "referencias_treino": sum(
                    r["particao"] == "treino" and not r["motivos_exclusao"] for r in rows
                ),
                "referencias_avaliacao": sum(
                    r["particao"] == "avaliacao" and not r["motivos_exclusao"] for r in rows
                ),
                "referencias_excluidas": sum(bool(r["motivos_exclusao"]) for r in rows),
                "rejeicoes_leitura_resolucao": len(rejects),
                "alvos_operacionais": len(targets),
                "grupos_elegiveis_tecnicamente": sum(g["elegivel_tecnicamente"] for g in groups),
            }
            manifest = {
                "schema": "licita-atributos-v1",
                "fingerprint": fingerprint,
                "configuracao": config,
                "criado_em_utc": datetime.now(timezone.utc).isoformat(),
                "fontes": sources,
                "contagens": counts,
                "reconciliacao_origem": reconciliation,
                "grupos": groups,
                "motivos_exclusao": dict(exclusions_counts),
                "atributos_indisponiveis": dict(unavailable),
                "snapshots_revisados_apos_corte": sum(
                    r["snapshot_revisado_apos_corte"] for r in rows
                ),
                "artefatos": artifacts,
                "snapshot_ponto_no_tempo": False,
                "comparabilidade_documental_aprovada": False,
                "utilidade_modelo_comprovada": False,
                "medicoes": {
                    "duracao_segundos": round(time.monotonic() - started, 3),
                    "rss_pico_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
                    ),
                    "bytes_fontes": sum(f["tamanho_bytes"] for f in files),
                    "bytes_artefatos": sum(a["bytes"] for a in artifacts),
                },
                "limitacoes": [
                    "Não é publicação de base/score na API nem registro de modelo.",
                    (
                        "Base operacional identifica os alvos; histórico de treino é descrito "
                        "separadamente pelas aquisições do manifesto."
                    ),
                    (
                        "Agrupamento estrutural estrito não comprova equivalência comercial "
                        "ou revisão documental do treino."
                    ),
                    (
                        "Mediana congelada e logs são ajustados no treino; nenhuma informação "
                        "da avaliação ajusta a referência."
                    ),
                    (
                        "Dados atuais podem incorporar revisões posteriores; data de resultado "
                        "não garante disponibilidade histórica do snapshot."
                    ),
                    (
                        "HHI e frequência do recorte não representam o universo completo do órgão; "
                        "pagamentos não estão cobertos."
                    ),
                    "IDs de fornecedor/órgão são contexto, não atributos numéricos dos modelos.",
                ],
            }
            stored = put_immutable(self.objects, key, (canonical(manifest) + "\n").encode())
            return {
                "status": "atributos_preparados",
                "reutilizada": False,
                "fingerprint": fingerprint,
                "manifesto": key,
                "sha256_manifesto": stored["sha256"],
                "contagens": counts,
                "medicoes": manifest["medicoes"],
            }
