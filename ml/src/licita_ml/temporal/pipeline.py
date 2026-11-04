"""Prepara dados temporais offline sem executar modelos, escalas ou inferência."""

import fcntl
import json
import platform
import tempfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

import pyarrow
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from licita_ml.analytical.rules import normalize
from licita_ml.diagnostics import checksum
from licita_ml.organized.pipeline import validate_existing
from licita_ml.organized.schema import encode
from licita_ml.temporal.export import NumericExport
from licita_ml.temporal.rules import build_groups, digest, inspect_row

FEATURES = ("log_preco_mediana", "log_quantidade")
MATRIX = {
    "id_observacao": "texto",
    "grupo": "texto",
    "compra": "texto",
    "log_preco_mediana": "real",
    "log_quantidade": "real",
}
AUDIT = {
    "id_observacao": "texto",
    "id_referencia_legado": "texto",
    "grupo": "texto",
    "particao": "texto",
    "compra": "texto",
    "item": "texto",
    "fornecedor": "texto",
    "catalogo": "texto",
    "data_compra": "data",
    "data_resultado": "data",
    "preco_unitario": "decimal",
    "quantidade": "decimal",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
    "motivos_json": "texto",
    "mediana_treino": "texto",
    "razao_preco_mediana": "texto",
    "log_preco_mediana": "real",
    "log_quantidade": "real",
    "apto_modelagem": "booleano",
    "snapshot_revisado_apos_corte": "booleano",
    "comparabilidade_documental": "texto",
}
TARGET = {
    "id_resultado": "texto",
    "id_item_registro": "texto",
    "compra": "texto",
    "item": "texto",
    "fornecedor": "texto",
    "grupo": "texto",
    "id_referencia": "texto",
    "data_resultado": "data",
    "apto_modelagem": "booleano",
    "motivos_json": "texto",
}


def rows(base, table, columns=None):
    for batch in pq.ParquetFile(base / f"{table}.parquet").iter_batches(
        batch_size=2000, columns=columns
    ):
        yield from batch.to_pylist()


def load(base, policy, exclusions, max_selected=200000):
    selected, first_partition = [], {}
    order = {"treino": 0, "avaliacao": 1, "aplicacao": 2}
    total = 0
    for row in rows(base, "referencias", ["id_compra", "data_compra"]):
        total += 1
        partition = policy.partition(row["data_compra"])
        if partition:
            purchase = row["id_compra"]
            first_partition[purchase] = min(first_partition.get(purchase, 3), order[partition])
    scope = ds.field("classe").isin(policy.classes) | ds.field("catalogo").isin(policy.catalogs)
    dataset = ds.dataset(base / "referencias.parquet", format="parquet")
    for batch in dataset.to_batches(filter=scope, batch_size=2000):
        for row in batch.to_pylist():
            if len(selected) >= max_selected:
                raise ValueError(
                    "Recorte excede limite de referências selecionadas; reduzir o escopo"
                )
            selected.append(inspect_row(row, policy, exclusions))
    return selected, first_partition, total


def writer(stack, folder, name, schema):
    result = NumericExport(folder, name, schema)
    stack.callback(result.close)
    return result


def export_references(folder, stack, selected, groups):
    audit = writer(stack, folder, "referencias_temporais", AUDIT)
    matrices = {
        name: writer(stack, folder, name, MATRIX)
        for name in ("treino", "avaliacao", "aplicacao_referencias")
    }
    reports = {g["grupo"]: g for g in groups}
    reasons, partitions = Counter(), Counter()
    for value in sorted(selected, key=lambda r: r["row"]["id_registro"]):
        row, x = value["row"], value["x"]
        blockers = value["reasons"][:]
        if not value["model_ready"] and not blockers:
            blockers = reports.get(value["group"], {}).get("impedimentos", [])
        if not blockers and x is None:
            blockers = ["REFERENCIA_TREINO_INSUFICIENTE"]
        reasons.update(blockers)
        partitions[value["partition"] or "fora_janelas"] += 1
        audit.add(
            {
                "id_observacao": row["id_registro"],
                "id_referencia_legado": value["legacy_id"],
                "grupo": value["group"],
                "particao": value["partition"],
                "compra": row["id_compra"],
                "item": row["id_compra_item"],
                "fornecedor": row["fornecedor"],
                "catalogo": row["catalogo"],
                "data_compra": row["data_compra"],
                "data_resultado": row["data_resultado"],
                "preco_unitario": row["preco_unitario"],
                "quantidade": row["quantidade"],
                "arquivo_sha256": row["arquivo_sha256"],
                "membro": row["membro"],
                "linha": row["linha"],
                "motivos_json": encode(blockers),
                "mediana_treino": str(value["median"]) if value["median"] is not None else None,
                "razao_preco_mediana": str(value["ratio"]) if value["ratio"] is not None else None,
                "log_preco_mediana": x[0] if x else None,
                "log_quantidade": x[1] if x else None,
                "apto_modelagem": value["model_ready"],
                "snapshot_revisado_apos_corte": value["snapshot_after_cut"],
                "comparabilidade_documental": "nao_verificada",
            }
        )
        if value["model_ready"]:
            name = (
                "aplicacao_referencias" if value["partition"] == "aplicacao" else value["partition"]
            )
            matrices[name].add(
                {
                    "id_observacao": row["id_registro"],
                    "grupo": value["group"],
                    "compra": row["id_compra"],
                    FEATURES[0]: x[0],
                    FEATURES[1]: x[1],
                }
            )
    return {"referencias_temporais": audit, **matrices}, dict(reasons), dict(partitions)


def export_targets(base, folder, stack, selected, first_partition, policy):
    # Application references and operational results remain distinct observations.
    application = {r["row"]["id_registro"]: r for r in selected if r["partition"] == "aplicacao"}
    matches = {}
    for link in rows(base, "vinculos"):
        if (
            link["origem_tabela"] == "referencias"
            and link["destino_tabela"] == "resultados"
            and link["origem_id"] in application
            and link["destino_id"]
            and link["status"] == "coincidencia_campos_nao_valida_comparabilidade"
        ):
            matches.setdefault(link["destino_id"], []).append(application[link["origem_id"]])
    result_rows = list(rows(base, "resultados"))
    item_keys = {(r["id_compra"], r["id_compra_item"]) for r in result_rows}
    items = {
        (r["id_compra"], r["id_compra_item"]): r
        for r in rows(base, "itens")
        if (r["id_compra"], r["id_compra_item"]) in item_keys
    }
    purchases = {r["id_compra"]: r for r in rows(base, "compras")}
    audit = writer(stack, folder, "alvos_resultados", TARGET)
    matrix = writer(stack, folder, "aplicacao_resultados", MATRIX)
    reasons = Counter()
    for result in sorted(result_rows, key=lambda r: r["id_registro"]):
        blockers = []
        item = items.get((result["id_compra"], result["id_compra_item"]))
        parent = purchases.get(result["id_compra"])
        candidates = matches.get(result["id_registro"], [])
        candidate = candidates[0] if len(candidates) == 1 else None
        if item is None or parent is None:
            blockers.append("CADEIA_COMPRA_ITEM_NAO_RESOLVIDA")
        if parent is not None and parent["excluida"] is not False:
            blockers.append("COMPRA_EXCLUIDA_OU_SITUACAO_NAO_CONFIRMADA")
        if (
            result["cancelamento_informado"]
            or result["situacao_codigo"] != "1"
            or normalize(result["situacao"]) != "informado"
        ):
            blockers.append("RESULTADO_CANCELADO_OU_SITUACAO_NAO_CONFIRMADA")
        if result.get("moeda_estrangeira_id") is not None:
            blockers.append("MOEDA_ESTRANGEIRA_REQUER_POLITICA")
        if (
            result["data_resultado"] is None
            or not policy.application_start <= result["data_resultado"] <= policy.application_end
        ):
            blockers.append("RESULTADO_FORA_JANELA_APLICACAO")
        if first_partition.get(result["id_compra"], 2) < 2:
            blockers.append("COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR")
        if candidate is None:
            blockers.append("REFERENCIA_DO_RECORTE_AUSENTE_OU_AMBIGUA")
        else:
            blockers.extend(candidate["reasons"])
            if not candidate["model_ready"]:
                blockers.append("GRUPO_NAO_APROVADO_PARA_MODELAGEM")
            ref = candidate["row"]
            if item is not None:
                description = normalize(item["descricao_detalhada"] or item["descricao_resumida"])
                if description != normalize(ref["descricao_detalhada"]):
                    blockers.append("ESPECIFICACAO_ITEM_DIVERGENTE")
                # Explicit name/symbol of the same linked supply unit; no inferred conversion.
                if normalize(item["unidade"]) not in {
                    normalize(ref["unidade_fornecimento_sigla"]),
                    normalize(ref["unidade_fornecimento_nome"]),
                } or not normalize(item["unidade"]):
                    blockers.append("UNIDADE_ITEM_DIVERGENTE_OU_AUSENTE")
                if (
                    item["catalogo_original"] is not None
                    and item["catalogo_original"] != ref["catalogo"]
                ):
                    blockers.append("CATALOGO_ITEM_DIVERGENTE")
        blockers = sorted(set(blockers))
        ready = not blockers
        reasons.update(blockers)
        audit.add(
            {
                "id_resultado": result["id_registro"],
                "id_item_registro": item["id_registro"] if item else None,
                "compra": result["id_compra"],
                "item": result["id_compra_item"],
                "fornecedor": result["fornecedor"],
                "grupo": candidate["group"] if candidate else None,
                "id_referencia": candidate["row"]["id_registro"] if candidate else None,
                "data_resultado": result["data_resultado"],
                "apto_modelagem": ready,
                "motivos_json": encode(blockers),
            }
        )
        if ready:
            matrix.add(
                {
                    "id_observacao": result["id_registro"],
                    "grupo": candidate["group"],
                    "compra": result["id_compra"],
                    FEATURES[0]: candidate["x"][0],
                    FEATURES[1]: candidate["x"][1],
                }
            )
    return {"alvos_resultados": audit, "aplicacao_resultados": matrix}, dict(reasons)


def validate(folder, fingerprint):
    manifest = json.loads((folder / "manifesto.json").read_text())
    if manifest["fingerprint"] != fingerprint or digest(manifest["configuracao"]) != fingerprint:
        raise ValueError("Fingerprint temporal divergente")
    tables = {
        "referencias_temporais",
        "treino",
        "avaliacao",
        "aplicacao_referencias",
        "alvos_resultados",
        "aplicacao_resultados",
    }
    expected = {f"{name}.{suffix}" for name in tables for suffix in ("csv", "parquet")}
    expected.update({"grupos.json", "medianas_treino.json", "contrato.json"})
    if (
        set(manifest["tabelas"]) != tables
        or len(manifest["artefatos"]) != len(expected)
        or {a["arquivo"] for a in manifest["artefatos"]} != expected
    ):
        raise ValueError("Manifesto temporal incompleto")
    for artifact in manifest["artefatos"]:
        path = folder / artifact["arquivo"]
        if path.parent != folder or checksum(path) != artifact["sha256"]:
            raise ValueError("Artefato temporal corrompido")
        if path.suffix == ".parquet":
            count = pq.ParquetFile(path).metadata.num_rows
            if count != artifact["linhas"] or count != manifest["tabelas"][path.stem]:
                raise ValueError("Contagem temporal divergente")
    return {"diretorio": str(folder), "reutilizada": True, "manifesto": manifest}


def prepare(base, output, policy, exclusions_path):
    base = Path(base)
    parent = json.loads((base / "manifesto.json").read_text())
    validate_existing(base, parent["fingerprint"])
    exclusions_raw = Path(exclusions_path).read_bytes()
    exclusions_doc = json.loads(exclusions_raw)
    if exclusions_doc["versao"] != "exclusoes-documentais-v1":
        raise ValueError("Política de exclusões incompatível")
    exclusions = {row["id_referencia"] for row in exclusions_doc["exclusoes"]}
    if len(exclusions) != len(exclusions_doc["exclusoes"]):
        raise ValueError("Exclusões duplicadas")
    dependencies = [
        *Path(__file__).parent.glob("*.py"),
        Path(__file__).parents[1] / "organized/schema.py",
        Path(__file__).parents[1] / "organized/pipeline.py",
        Path(__file__).parents[1] / "analytical/rules.py",
        Path(__file__).parents[1] / "diagnostics.py",
    ]
    code = digest(
        [(str(p.relative_to(Path(__file__).parents[1])), checksum(p)) for p in sorted(dependencies)]
    )
    config = {
        "politica": policy.manifest(),
        "base_manifesto_sha256": checksum(base / "manifesto.json"),
        "exclusoes_sha256": checksum(Path(exclusions_path)),
        "codigo_sha256": code,
        "ambiente": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
    }
    fingerprint = digest(config)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"base={fingerprint}"
    with (output / ".temporal.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists():
            return validate(destination, fingerprint)
        selected, purchases, total = load(base, policy, exclusions)
        if total != parent["tabelas"]["referencias"]:
            raise ValueError("Contagem de referências da base divergente")
        groups = build_groups(selected, purchases, policy)
        with tempfile.TemporaryDirectory(prefix=".temporal-", dir=output) as temporary:
            folder = Path(temporary) / "base"
            folder.mkdir()
            with ExitStack() as stack:
                writers, reference_reasons, partitions = export_references(
                    folder, stack, selected, groups
                )
                targets, target_reasons = export_targets(
                    base, folder, stack, selected, purchases, policy
                )
                writers.update(targets)
            (folder / "grupos.json").write_text(
                json.dumps(groups, ensure_ascii=False, indent=2) + "\n"
            )
            medians = {
                g["grupo"]: g["mediana_treino"] for g in groups if g["mediana_treino"] is not None
            }
            (folder / "medianas_treino.json").write_text(json.dumps(medians, indent=2) + "\n")
            contract = {
                "configuracao": config,
                "colunas_modelo": FEATURES,
                "treinar_separadamente_por": "grupo",
                "escala_aprendida": "somente_em_ML04_no_treino",
                "schemas": {name: str(w.schema) for name, w in writers.items()},
                "snapshot_ponto_no_tempo": False,
                "comparabilidade_documental": "nao_verificada",
                "indice_risco_ou_probabilidade": False,
            }
            (folder / "contrato.json").write_text(
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
            )
            artifacts = []
            for path in sorted(folder.iterdir()):
                count = writers[path.stem].count if path.stem in writers else None
                if path.suffix == ".parquet" and pq.ParquetFile(path).metadata.num_rows != count:
                    raise ValueError("Contagem de saída temporal divergente")
                artifacts.append(
                    {
                        "arquivo": path.name,
                        "sha256": checksum(path),
                        "bytes": path.stat().st_size,
                        "linhas": count,
                    }
                )
            if checksum(base / "manifesto.json") != config["base_manifesto_sha256"]:
                raise ValueError("Base de entrada mudou durante o processamento")
            validate_existing(base, parent["fingerprint"])
            manifest = {
                "fingerprint": fingerprint,
                "configuracao": config,
                "referencias_lidas": total,
                "referencias_recorte": len(selected),
                "referencias_fora_recorte": total - len(selected),
                "particoes_recorte": partitions,
                "grupos": len(groups),
                "grupos_elegiveis": sum(g["elegivel_tecnicamente"] for g in groups),
                "status": "apto_avaliacao_tecnica"
                if any(g["elegivel_tecnicamente"] for g in groups)
                else "insuficiente_para_modelagem",
                "tabelas": {name: w.count for name, w in writers.items()},
                "motivos_referencias": reference_reasons,
                "motivos_alvos": target_reasons,
                "revisados_apos_corte": sum(r["snapshot_after_cut"] for r in selected),
                "modelos_executados": False,
                "artefatos": artifacts,
            }
            (folder / "manifesto.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            )
            folder.rename(destination)
    return {"diretorio": str(destination), "reutilizada": False, "manifesto": manifest}
