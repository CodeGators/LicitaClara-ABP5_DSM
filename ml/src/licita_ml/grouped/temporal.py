"""Converter catálogo integral em lotes temporais sem alterar o contrato legado."""

import fcntl
import json
import logging
import re
import tempfile
from collections import Counter
from contextlib import ExitStack
from datetime import date
from pathlib import Path

import pyarrow.dataset as ds
import pyarrow.parquet as pq

from licita_ml.analytical.rules import canonical, digest
from licita_ml.catalog.pipeline import validate as validate_catalog
from licita_ml.diagnostics import checksum
from licita_ml.organized.pipeline import validate_existing
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.pipeline import (
    FEATURES,
    MATRIX,
    TARGET,
    export_references,
    writer,
)
from licita_ml.temporal.pipeline import (
    validate as validate_temporal,
)
from licita_ml.temporal.rules import TemporalPolicy, build_groups, inspect_row

LOGGER = logging.getLogger(__name__)
VERSION = "temporal-agrupado-v1"
PROTOCOL = RESOURCE_DIR / "PROTOCOLO_TEMPORAL_AGRUPADO_UNIDADES_V2.json"
COLUMNS = [
    "id_registro",
    "id_compra",
    "id_compra_item",
    "id_item_fonte",
    "fornecedor",
    "forma",
    "catalogo",
    "descricao",
    "descricao_detalhada",
    "unidade_fornecimento_sigla",
    "capacidade",
    "unidade_medida_sigla",
    "data_compra",
    "data_resultado",
    "preco_unitario",
    "quantidade",
    "orgao_codigo",
    "arquivo_sha256",
    "membro",
    "linha",
    "atualizacao_primaria",
    "atualizacao_secundaria",
]


def code_hash():
    root = Path(__file__).parents[1]
    paths = [
        Path(__file__),
        root / "temporal/pipeline.py",
        root / "temporal/rules.py",
        root / "temporal/export.py",
        root / "catalog/rules.py",
        root / "units.py",
        root / "organized/schema.py",
        root / "analytical/rules.py",
    ]
    return digest([(str(p.relative_to(root)), checksum(p)) for p in sorted(paths)])


def structural_blockers(spec):
    reasons = []
    for key in ("especificacao", "especificacao_catalogo"):
        if spec[key]["modo"] != "atributos_nomeados" or not spec[key].get("atributos"):
            reasons.append("ESPECIFICACAO_NAO_ESTRUTURADA_REQUER_REVISAO")
    if spec.get("unidade") == "un" and spec.get("capacidade") == "0":
        attributes = [
            pair
            for key in ("especificacao", "especificacao_catalogo")
            for pair in spec[key].get("atributos", [])
        ]
        if any(
            "embalagem" in key
            or re.search(
                r"\b(caixa|pacote|frasco|ampola|seringa|garrafa|garrafao|bandeja|saco|fardo)\b",
                value,
            )
            for key, value in attributes
        ):
            reasons.append("CONTEUDO_EMBALAGEM_NAO_CONFIRMADO")
    product = spec["especificacao_catalogo"].get("produto", "")
    if product.startswith("livro"):
        reasons.append("OBRA_EDICAO_ISBN_NAO_CONFIRMADOS")
    if product.startswith("acessorio"):
        reasons.append("MODELO_COMPATIBILIDADE_NAO_CONFIRMADOS")
    return sorted(set(reasons))


def select(base, catalog, policy):
    candidates = pq.ParquetFile(catalog / "candidatos_estudo.parquet").read().to_pylist()
    specs = {r["grupo"]: json.loads(r["especificacao_json"]) for r in candidates}
    obs = (
        ds.dataset(catalog / "observacoes.parquet")
        .to_table(filter=ds.field("grupo").isin(sorted(specs)))
        .to_pylist()
    )
    lookup = {r["id_observacao"]: r for r in obs}
    if len(lookup) != len(obs) or len(obs) > 200000:
        raise ValueError("Recorte excede limite de memória ou contém IDs repetidos")
    # Original catalogue already inspected all purchases before selecting these groups.
    refs = (
        ds.dataset(base / "referencias.parquet")
        .to_table(columns=COLUMNS, filter=ds.field("id_registro").isin(sorted(lookup)))
        .to_pylist()
    )
    if {r["id_registro"] for r in refs} != set(lookup):
        raise ValueError("Observações do catálogo não correspondem à base")
    selected, first = [], {}
    for row in refs:
        observation = lookup[row["id_registro"]]
        for a, b in (
            ("preco_unitario", "preco_unitario"),
            ("quantidade", "quantidade"),
            ("data_compra", "data_compra"),
            ("data_resultado", "data_resultado"),
            ("arquivo_sha256", "arquivo_sha256"),
            ("membro", "membro"),
            ("linha", "linha"),
        ):
            if row[a] != observation[b]:
                raise ValueError("Valor ou proveniência diverge do catálogo")
        spec = specs[observation["grupo"]]
        value = inspect_row(row, policy, set())
        # Dates/documentary exclusions, including global purchase partition, are inherited
        # from the verified catalogue using exactly the same policy and exclusion hashes.
        value.update(
            group=observation["grupo"],
            reasons=json.loads(observation["motivos_json"]),
            spec=(
                spec["catalogo"],
                canonical(spec["especificacao"]),
                spec["unidade"],
                spec["capacidade"],
                spec["medida"],
            ),
        )
        selected.append(value)
        if value["partition"]:
            part = {"treino": 0, "avaliacao": 1, "aplicacao": 2}[value["partition"]]
            first[row["id_compra"]] = min(first.get(row["id_compra"], 3), part)
    reports = build_groups(selected, first, policy)
    for value in selected:
        value["reasons"] = list(dict.fromkeys(value["reasons"]))
    for report in reports:
        spec = specs[report["grupo"]]
        report["assinatura_catalogo"] = spec
        example = next(r["row"] for r in selected if r["group"] == report["grupo"])
        report["descricao_catalogo_original"] = example["descricao"]
        report["impedimentos"] += structural_blockers(spec)
        report["elegivel_tecnicamente"] = not report["impedimentos"]
        if not report["elegivel_tecnicamente"]:
            for value in selected:
                if value["group"] == report["grupo"]:
                    value["model_ready"] = False
            report["aplicacao_referencias_aptas"] = 0
    return selected, reports


def batch(folder, selected, groups, config):
    folder.mkdir()
    with ExitStack() as stack:
        writers, reasons, partitions = export_references(folder, stack, selected, groups)
        # Operational targets are reconciled against SQL in A3, not borrowed as training rows.
        writers["alvos_resultados"] = writer(stack, folder, "alvos_resultados", TARGET)
        writers["aplicacao_resultados"] = writer(stack, folder, "aplicacao_resultados", MATRIX)
    for name, content in {
        "grupos.json": groups,
        "medianas_treino.json": {g["grupo"]: g["mediana_treino"] for g in groups},
        "contrato.json": {
            "versao": VERSION,
            "colunas_modelo": FEATURES,
            "alvos_operacionais": "reconciliar_no_SQL_em_ML_A3",
            "comparabilidade_documental": "nao_verificada",
        },
    }.items():
        (folder / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    artifacts = [
        {
            "arquivo": p.name,
            "sha256": checksum(p),
            "bytes": p.stat().st_size,
            "linhas": writers[p.stem].count if p.stem in writers else None,
        }
        for p in sorted(folder.iterdir())
    ]
    manifest = {
        "fingerprint": digest(config),
        "configuracao": config,
        "referencias_lidas": len(selected),
        "referencias_recorte": len(selected),
        "referencias_fora_recorte": 0,
        "particoes_recorte": partitions,
        "grupos": len(groups),
        "grupos_elegiveis": len(groups),
        "status": "apto_avaliacao_tecnica",
        "modelos_executados": False,
        "tabelas": {k: w.count for k, w in writers.items()},
        "motivos_referencias": reasons,
        "motivos_alvos": {},
        "artefatos": artifacts,
    }
    (folder / "manifesto.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    validate_temporal(folder, manifest["fingerprint"])
    return manifest


def validate(folder):
    manifest = json.loads((folder / "manifesto.json").read_text())
    if manifest["versao"] != VERSION or digest(manifest["configuracao"]) != manifest["fingerprint"]:
        raise ValueError("Manifesto agrupado divergente")
    if checksum(folder / "triagem.json") != manifest["triagem_sha256"]:
        raise ValueError("Triagem corrompida")
    seen = set()
    for item in manifest["lotes"]:
        target = folder / item["diretorio"]
        if target.parent != folder or checksum(target / "manifesto.json") != item["sha256"]:
            raise ValueError("Lote agrupado divergente")
        loaded = validate_temporal(target, item["fingerprint"])["manifesto"]
        ids = set(loaded["configuracao"]["grupos"])
        if seen & ids:
            raise ValueError("Grupo repetido entre lotes")
        seen |= ids
    if len(seen) != manifest["grupos_selecionados"]:
        raise ValueError("Grupos/lotes incompletos")
    return manifest


def prepare(base, catalog, output, batch_size=20):
    base, catalog, output = Path(base), Path(catalog), Path(output)
    if not 1 <= batch_size <= 20:
        raise ValueError("Lote deve ter entre 1 e 20 grupos")
    parent = json.loads((base / "manifesto.json").read_text())
    validate_existing(base, parent["fingerprint"])
    cat = json.loads((catalog / "manifesto.json").read_text())
    validate_catalog(catalog, cat["fingerprint"])
    policy = TemporalPolicy(train_start=date(2025, 7, 1), classes=(), catalogs=())
    diagnostic = dict(cat["configuracao"]["politica_temporal_diagnostica"])
    expected = policy.manifest()
    # Catalogue inventories all categories; its historical scope fields never filtered rows.
    for key in ("classes", "catalogs"):
        diagnostic.pop(key)
        expected.pop(key)
    if diagnostic != expected:
        raise ValueError("Política temporal deve coincidir com a catalogação")
    if cat["configuracao"]["base_sha256"] != checksum(base / "manifesto.json"):
        raise ValueError("Catálogo pertence a outra base")
    exclusions = checksum(RESOURCE_DIR / "exclusoes_v1.json")
    if cat["configuracao"]["exclusoes_sha256"] != exclusions:
        raise ValueError("Exclusões documentais divergentes")
    config = {
        "politica": policy.manifest(),
        "base_manifesto_sha256": checksum(base / "manifesto.json"),
        "catalogo_manifesto_sha256": checksum(catalog / "manifesto.json"),
        "codigo_sha256": code_hash(),
        "protocolo_sha256": checksum(PROTOCOL),
        "exclusoes_sha256": exclusions,
        "grupos_por_lote": batch_size,
    }
    fp = digest(config)
    output.mkdir(parents=True, exist_ok=True)
    dest = output / ("execucao=" + fp)
    with (output / ".agrupado.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if dest.exists():
            return {"diretorio": str(dest), "reutilizada": True, "manifesto": validate(dest)}
        selected, reports = select(base, catalog, policy)
        eligible = sorted(
            (g for g in reports if g["elegivel_tecnicamente"]), key=lambda g: g["grupo"]
        )
        with tempfile.TemporaryDirectory(prefix=".agrupado-", dir=output) as temp:
            root = Path(temp) / "execucao"
            root.mkdir()
            (root / "triagem.json").write_text(
                json.dumps(reports, ensure_ascii=False, indent=2) + "\n"
            )
            batches = []
            for start in range(0, len(eligible), batch_size):
                groups = eligible[start : start + batch_size]
                ids = {g["grupo"] for g in groups}
                rows = [r for r in selected if r["group"] in ids]
                cfg = {**config, "grupos": sorted(ids)}
                name = "lote=" + digest(cfg)
                leaf = batch(root / name, rows, groups, cfg)
                batches.append(
                    {
                        "diretorio": name,
                        "fingerprint": leaf["fingerprint"],
                        "sha256": checksum(root / name / "manifesto.json"),
                    }
                )
                LOGGER.info(
                    "Preparados %s/%s grupos", min(start + batch_size, len(eligible)), len(eligible)
                )
            result = {
                "versao": VERSION,
                "fingerprint": fp,
                "configuracao": config,
                "lotes": batches,
                "triagem_sha256": checksum(root / "triagem.json"),
                "candidatos": len(reports),
                "grupos_selecionados": len(eligible),
                "aprovacao_comercial": False,
                "impedimentos": dict(Counter(x for g in reports for x in g["impedimentos"])),
            }
            (root / "manifesto.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
            validate(root)
            root.rename(dest)
    return {"diretorio": str(dest), "reutilizada": False, "manifesto": result}
