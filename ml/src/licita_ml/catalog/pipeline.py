"""Catálogo offline integral com observações preservadas, Decimal e saídas imutáveis."""

import fcntl
import itertools
import json
import logging
import platform
import resource
import sqlite3
import tempfile
import time
from collections import Counter
from contextlib import ExitStack
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow
import pyarrow.parquet as pq

from licita_ml.analytical.rules import canonical, digest, median
from licita_ml.catalog.rules import VERSION, grouping, refine_spec
from licita_ml.diagnostics import checksum
from licita_ml.organized.pipeline import validate_existing
from licita_ml.organized.schema import Export
from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.rules import TemporalPolicy, specification

LOGGER = logging.getLogger(__name__)

PROTOCOL = RESOURCE_DIR / "PROTOCOLO_CATALOGO_ITENS_V1.json"
OBS = {
    "id_observacao": "texto",
    "grupo": "texto",
    "grupo_anterior": "texto",
    "catalogo": "texto",
    "compra": "texto",
    "item": "texto",
    "fornecedor": "texto",
    "preco_unitario": "decimal",
    "quantidade": "decimal",
    "data_compra": "data",
    "data_resultado": "data",
    "particao": "texto",
    "motivos_json": "texto",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
}
GROUPS = {
    "grupo": "texto",
    "catalogo": "texto",
    "descricao_exemplo": "texto",
    "especificacao_json": "texto",
    "referencias": "inteiro",
    "compras_distintas": "inteiro",
    "variantes_descricao": "inteiro",
    "grupos_anteriores": "inteiro",
    "precos_positivos": "inteiro",
    "preco_medio_descritivo": "texto",
    "mediana_descritiva": "texto",
    "preco_minimo": "texto",
    "preco_maximo": "texto",
    "treino_validas_datas": "inteiro",
    "avaliacao_validas_datas": "inteiro",
    "aplicacao_validas_datas": "inteiro",
    "preco_medio_treino_diagnostico": "texto",
    "mediana_treino_diagnostico": "texto",
    "candidato_por_contagens": "booleano",
    "aprovado_treino": "booleano",
}
VARIANTS = {
    "grupo": "texto",
    "descricao_original": "texto",
    "referencias": "inteiro",
    "observacao_exemplo": "texto",
}
ITEMS = {
    "id_item_registro": "texto",
    "compra": "texto",
    "item": "texto",
    "tipo_catalogo": "texto",
    "catalogo_original": "texto",
    "catalogo_referencia_unico": "texto",
    "grupo_candidato": "texto",
    "grupos_candidatos": "inteiro",
    "descricao_original": "texto",
    "unidade_original": "texto",
    "preco_unitario_estimado": "decimal",
    "status": "texto",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
}
RESULTS = {
    "id_resultado": "texto",
    "compra": "texto",
    "item": "texto",
    "fornecedor": "texto",
    "catalogo": "texto",
    "grupo_candidato": "texto",
    "preco_unitario_homologado": "decimal",
    "quantidade": "decimal",
    "data_resultado": "data",
    "cancelamento_informado": "booleano",
    "status": "texto",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
}
PRODUCTS = {
    "tipo_catalogo": "texto",
    "catalogo": "texto",
    "referencias": "inteiro",
    "grupos_comparaveis": "inteiro",
    "itens_com_codigo_original": "inteiro",
    "media_global_catalogo": "texto",
}
SCHEMAS = {
    "observacoes": OBS,
    "grupos": GROUPS,
    "candidatos_estudo": GROUPS,
    "variantes": VARIANTS,
    "itens_catalogados": ITEMS,
    "resultados_catalogados": RESULTS,
    "produtos": PRODUCTS,
}


def records(base, table, columns=None):
    for batch in pq.ParquetFile(base / f"{table}.parquet").iter_batches(
        batch_size=2000, columns=columns
    ):
        yield from batch.to_pylist()


def code_hash():
    root = Path(__file__).parents[1]
    paths = [
        *Path(__file__).parent.glob("*.py"),
        *(
            root / name
            for name in (
                "analytical/rules.py",
                "organized/schema.py",
                "temporal/rules.py",
                "diagnostics.py",
            )
        ),
    ]
    return digest([(str(p.relative_to(root)), checksum(p)) for p in sorted(paths)])


def validate(folder, fingerprint):
    manifest = json.loads((folder / "manifesto.json").read_text())
    if (
        manifest["fingerprint"] != fingerprint
        or manifest["versao"] != VERSION
        or digest(manifest["configuracao"]) != fingerprint
    ):
        raise ValueError("Manifesto do catálogo divergente")
    expected = {f"{name}.{ext}" for name in SCHEMAS for ext in ("csv", "parquet")} | {
        "protocolo.json"
    }
    paths = [a["arquivo"] for a in manifest["artefatos"]]
    if set(paths) != expected or len(paths) != len(expected):
        raise ValueError("Catálogo incompleto")
    for artifact in manifest["artefatos"]:
        path = folder / artifact["arquivo"]
        if path.parent != folder or checksum(path) != artifact["sha256"]:
            raise ValueError("Artefato de catálogo corrompido")
        if (
            path.suffix == ".parquet"
            and pq.ParquetFile(path).metadata.num_rows != artifact["linhas"]
        ):
            raise ValueError("Contagem de catálogo divergente")
    return manifest


def setup(cn):
    cn.executescript("""
    PRAGMA journal_mode=OFF;
    PRAGMA synchronous=OFF;
    PRAGMA cache_size=-65536;
    CREATE TABLE specs(gid TEXT PRIMARY KEY,catalog TEXT,spec TEXT,example TEXT);
    CREATE TABLE refs(uid TEXT PRIMARY KEY,gid TEXT,old_gid TEXT,catalog TEXT,
                      purchase TEXT,item TEXT,supplier TEXT,price TEXT,quantity TEXT,event TEXT,
                      result TEXT,part TEXT,reasons TEXT,sha TEXT,member TEXT,line INTEGER);
    CREATE TABLE variants(gid TEXT,description TEXT,n INTEGER,example TEXT,
                          PRIMARY KEY(gid,description));
    CREATE TABLE native(purchase TEXT,item TEXT,catalog TEXT,gid TEXT,PRIMARY KEY(purchase,item));
    """)


def stage(cn, base, policy):
    exclusion = json.loads((RESOURCE_DIR / "exclusoes_v1.json").read_text())
    # Exclusions are documentary IDs; no feedback or rule is learned from application prices.
    exclusions = {e["id_referencia"] for e in exclusion["exclusoes"]}
    count = 0
    columns = [
        "id_registro",
        "catalogo",
        "descricao",
        "descricao_detalhada",
        "unidade_fornecimento_sigla",
        "unidade_fornecimento_nome",
        "capacidade",
        "unidade_medida_sigla",
        "data_compra",
        "data_resultado",
        "preco_unitario",
        "quantidade",
        "id_compra",
        "id_compra_item",
        "id_item_fonte",
        "fornecedor",
        "forma",
        "arquivo_sha256",
        "membro",
        "linha",
    ]
    for row in records(base, "referencias", columns):
        group, reason = grouping(row)
        part = policy.partition(row["data_compra"])
        reasons = [reason] if reason else []
        if part is None:
            reasons.append("FORA_JANELAS_OU_DATA_AUSENTE")
        end = dict((name, end) for name, _, end in policy.windows()).get(part)
        if row["data_resultado"] is None:
            reasons.append("DATA_RESULTADO_AUSENTE")
        elif end and row["data_resultado"] > end:
            reasons.append("RESULTADO_POSTERIOR_AO_CORTE")
        elif row["data_compra"] and row["data_resultado"] < row["data_compra"]:
            reasons.append("RESULTADO_ANTERIOR_COMPRA")
        if row["preco_unitario"] is None or row["preco_unitario"] <= 0:
            reasons.append("PRECO_NAO_POSITIVO_OU_AUSENTE")
        if row["quantidade"] is None or row["quantidade"] <= 0:
            reasons.append("QUANTIDADE_NAO_POSITIVA_OU_AUSENTE")
        legacy = digest([row["id_compra"], row["id_item_fonte"], row["fornecedor"], row["forma"]])[
            :20
        ]
        if legacy in exclusions:
            reasons.append("DIVERGENCIA_DOCUMENTAL_SUSPENSA")
        old, _ = specification(row)
        old_gid = digest(old)[:16] if old else None
        gid = group["id"] if group else None
        if group:
            spec = canonical(group["especificacao"])
            cn.execute(
                "INSERT INTO specs VALUES(?,?,?,?) ON CONFLICT(gid) "
                "DO UPDATE SET example=MIN(example,excluded.example)",
                (gid, row["catalogo"], spec, row["descricao_detalhada"]),
            )
            cn.execute(
                "INSERT INTO variants VALUES(?,?,1,?) ON CONFLICT(gid,description) "
                "DO UPDATE SET n=n+1,example=MIN(example,excluded.example)",
                (gid, row["descricao_detalhada"], row["id_registro"]),
            )
        values = (
            row["id_registro"],
            gid,
            old_gid,
            row["catalogo"],
            row["id_compra"],
            row["id_compra_item"],
            row["fornecedor"],
            format(row["preco_unitario"], "f") if row["preco_unitario"] is not None else None,
            format(row["quantidade"], "f") if row["quantidade"] is not None else None,
            str(row["data_compra"]) if row["data_compra"] else None,
            str(row["data_resultado"]) if row["data_resultado"] else None,
            part,
            canonical(reasons),
            row["arquivo_sha256"],
            row["membro"],
            row["linha"],
        )
        cn.execute("INSERT INTO refs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        count += 1
        if count % 100000 == 0:
            LOGGER.info("Referências catalogadas: %s", count)
    finalize_stage(cn)
    return count


def finalize_stage(cn):
    cn.executescript("""
    CREATE INDEX ref_group ON refs(gid,uid);
    CREATE INDEX ref_item ON refs(purchase,item);
    CREATE TABLE first_partition AS
      SELECT purchase,MIN(CASE part WHEN 'treino' THEN 0 WHEN 'avaliacao' THEN 1 ELSE 2 END) first
      FROM refs WHERE part IS NOT NULL GROUP BY purchase;
    CREATE UNIQUE INDEX purchase_partition ON first_partition(purchase);
    CREATE TABLE ref_items AS SELECT purchase,item,COUNT(DISTINCT catalog) catalogs,
      MIN(catalog) catalog,
      COUNT(DISTINCT gid) groups_count,MIN(gid) gid FROM refs GROUP BY purchase,item;
    CREATE UNIQUE INDEX reference_item ON ref_items(purchase,item);
    """)
    # Rows in a later partition cannot reuse a purchase already observed in an earlier one.
    for r in cn.execute(
        "SELECT uid,reasons FROM refs r JOIN first_partition f ON r.purchase=f.purchase "
        "WHERE CASE part WHEN 'treino' THEN 0 WHEN 'avaliacao' THEN 1 "
        "WHEN 'aplicacao' THEN 2 ELSE -1 END > f.first"
    ):
        cn.execute(
            "UPDATE refs SET reasons=? WHERE uid=?",
            (
                canonical(
                    list(
                        dict.fromkeys(
                            json.loads(r["reasons"]) + ["COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR"]
                        )
                    )
                ),
                r["uid"],
            ),
        )


def restage(cn, previous):
    """Reaproveitar observações verificadas; somente refinar assinaturas existentes."""
    mapping = {}
    for row in records(previous, "grupos"):
        original = json.loads(row["especificacao_json"])
        if digest([VERSION, original]) != row["grupo"]:
            raise ValueError("Assinatura do grupo anterior divergente")
        spec = refine_spec(original)
        gid = digest([VERSION, spec])
        mapping[row["grupo"]] = gid
        cn.execute(
            "INSERT INTO specs VALUES(?,?,?,?) ON CONFLICT(gid) "
            "DO UPDATE SET example=MIN(example,excluded.example)",
            (gid, row["catalogo"], canonical(spec), row["descricao_exemplo"]),
        )
    count = 0
    for row in records(previous, "observacoes"):
        gid = mapping[row["grupo"]] if row["grupo"] is not None else None
        values = (
            row["id_observacao"],
            gid,
            row["grupo_anterior"],
            row["catalogo"],
            row["compra"],
            row["item"],
            row["fornecedor"],
            format(row["preco_unitario"], "f") if row["preco_unitario"] is not None else None,
            format(row["quantidade"], "f") if row["quantidade"] is not None else None,
            str(row["data_compra"]) if row["data_compra"] else None,
            str(row["data_resultado"]) if row["data_resultado"] else None,
            row["particao"],
            row["motivos_json"],
            row["arquivo_sha256"],
            row["membro"],
            row["linha"],
        )
        cn.execute("INSERT INTO refs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        count += 1
        if count % 200000 == 0:
            LOGGER.info("Observações verificadas reagrupadas: %s", count)
    for row in records(previous, "variantes"):
        cn.execute(
            "INSERT INTO variants VALUES(?,?,?,?) ON CONFLICT(gid,description) "
            "DO UPDATE SET n=n+excluded.n,example=MIN(example,excluded.example)",
            (
                mapping[row["grupo"]],
                row["descricao_original"],
                row["referencias"],
                row["observacao_exemplo"],
            ),
        )
    finalize_stage(cn)
    return count


def mean(values):
    with localcontext() as ctx:
        ctx.prec = 60
        return (
            format((sum(values, Decimal(0)) / len(values)).quantize(Decimal("0.00000001")), "f")
            if values
            else None
        )


def export(cn, folder, stack, manifest):
    writers = {name: Export(folder, name, schema) for name, schema in SCHEMAS.items()}
    for writer in writers.values():
        stack.callback(writer.close)
    reasons = Counter()
    for r in cn.execute("SELECT * FROM refs ORDER BY uid"):
        reasons.update(json.loads(r["reasons"]))
        writers["observacoes"].add(
            dict(
                zip(
                    OBS,
                    [
                        r[k]
                        for k in (
                            "uid",
                            "gid",
                            "old_gid",
                            "catalog",
                            "purchase",
                            "item",
                            "supplier",
                            "price",
                            "quantity",
                            "event",
                            "result",
                            "part",
                            "reasons",
                            "sha",
                            "member",
                            "line",
                        )
                    ],
                    strict=True,
                )
            )
        )
    merged = 0
    candidates = 0
    candidate_rows = []
    query = (
        "SELECT gid,uid,old_gid,purchase,price,part,reasons FROM refs "
        "WHERE gid IS NOT NULL ORDER BY gid,uid"
    )
    for gid, members in itertools.groupby(cn.execute(query), key=lambda r: r["gid"]):
        prices = []
        train = []
        counts = Counter()
        purchases = set()
        old = set()
        n = 0
        for r in members:
            n += 1
            purchases.add(r["purchase"])
            if r["old_gid"]:
                old.add(r["old_gid"])
            value = Decimal(r["price"]) if r["price"] is not None else None
            if (
                value is not None
                and value > 0
                and "DIVERGENCIA_DOCUMENTAL_SUSPENSA" not in json.loads(r["reasons"])
            ):
                prices.append(value)
            if r["reasons"] == "[]":
                counts[r["part"]] += 1
                if r["part"] == "treino":
                    train.append(value)
        spec = cn.execute("SELECT * FROM specs WHERE gid=?", (gid,)).fetchone()
        variants = cn.execute("SELECT COUNT(*) FROM variants WHERE gid=?", (gid,)).fetchone()[0]
        candidate = counts["treino"] >= 100 and counts["avaliacao"] >= 30
        candidates += int(candidate)
        merged += int(len(old) > 1)
        if writers["grupos"].count and writers["grupos"].count % 50000 == 0:
            LOGGER.info("Grupos exportados: %s", writers["grupos"].count)
        record = {
            "grupo": gid,
            "catalogo": spec["catalog"],
            "descricao_exemplo": spec["example"],
            "especificacao_json": spec["spec"],
            "referencias": n,
            "compras_distintas": len(purchases),
            "variantes_descricao": variants,
            "grupos_anteriores": len(old),
            "precos_positivos": len(prices),
            "preco_medio_descritivo": mean(prices),
            "mediana_descritiva": format(median(prices), "f") if prices else None,
            "preco_minimo": format(min(prices), "f") if prices else None,
            "preco_maximo": format(max(prices), "f") if prices else None,
            "treino_validas_datas": counts["treino"],
            "avaliacao_validas_datas": counts["avaliacao"],
            "aplicacao_validas_datas": counts["aplicacao"],
            "preco_medio_treino_diagnostico": mean(train),
            "mediana_treino_diagnostico": format(median(train), "f") if train else None,
            "candidato_por_contagens": candidate,
            "aprovado_treino": False,
        }
        writers["grupos"].add(record)
        if candidate:
            candidate_rows.append(record)
    for record in sorted(
        candidate_rows,
        key=lambda r: (-r["treino_validas_datas"], -r["avaliacao_validas_datas"], r["grupo"]),
    ):
        writers["candidatos_estudo"].add(record)
    for r in cn.execute("SELECT * FROM variants ORDER BY gid,description"):
        writers["variantes"].add(
            {
                "grupo": r["gid"],
                "descricao_original": r["description"],
                "referencias": r["n"],
                "observacao_exemplo": r["example"],
            }
        )
    manifest.update(
        {
            "grupos_com_reuniao_de_grupos_anteriores": merged,
            "candidatos_apenas_por_contagens": candidates,
            "motivos_observacoes": dict(reasons),
            "grupos_anteriores_distintos": cn.execute(
                "SELECT COUNT(DISTINCT old_gid) FROM refs"
            ).fetchone()[0],
            "grupos_anteriores_desdobrados": cn.execute(
                "SELECT COUNT(*) FROM (SELECT old_gid FROM refs WHERE old_gid IS NOT NULL "
                "AND gid IS NOT NULL GROUP BY old_gid HAVING COUNT(DISTINCT gid)>1)"
            ).fetchone()[0],
        }
    )
    return writers


def export_native(cn, base, writers):
    item_status = Counter()
    result_status = Counter()
    for row in records(base, "itens"):
        linked = cn.execute(
            "SELECT * FROM ref_items WHERE purchase=? AND item=?",
            (row["id_compra"], row["id_compra_item"]),
        ).fetchone()
        original = row["catalogo_original"]
        code = linked["catalog"] if linked and linked["catalogs"] == 1 else None
        count = linked["groups_count"] if linked else 0
        gid = linked["gid"] if linked and linked["catalogs"] == 1 and count == 1 else None
        kind = (
            "CATMAT"
            if row["material_ou_servico"] == "M"
            else "CATSER"
            if row["material_ou_servico"] == "S"
            else "NAO_CONFIRMADO"
        )
        status = (
            "catalogo_original"
            if original
            else "catalogo_referencia_por_chave"
            if code
            else "catalogo_ausente"
        )
        if kind != "CATMAT":
            code = gid = None
            status = "catalogo_original" if original else "catalogo_ausente"
        if original and code and original != code:
            status = "catalogo_divergente"
            gid = None
        if linked and (linked["catalogs"] > 1 or count > 1):
            status = "referencias_ambiguas"
            gid = None
        item_status[status] += 1
        if writers["itens_catalogados"].count and writers["itens_catalogados"].count % 100000 == 0:
            LOGGER.info("Itens de compras catalogados: %s", writers["itens_catalogados"].count)
        cn.execute(
            "INSERT INTO native VALUES(?,?,?,?)",
            (row["id_compra"], row["id_compra_item"], original or code, gid),
        )
        writers["itens_catalogados"].add(
            {
                "id_item_registro": row["id_registro"],
                "compra": row["id_compra"],
                "item": row["id_compra_item"],
                "tipo_catalogo": kind,
                "catalogo_original": original,
                "catalogo_referencia_unico": code,
                "grupo_candidato": gid,
                "grupos_candidatos": count,
                "descricao_original": row["descricao_detalhada"] or row["descricao_resumida"],
                "unidade_original": row["unidade"],
                "preco_unitario_estimado": format(row["preco_unitario_estimado"], "f")
                if row["preco_unitario_estimado"] is not None
                else None,
                "status": status,
                "arquivo_sha256": row["arquivo_sha256"],
                "membro": row["membro"],
                "linha": row["linha"],
            }
        )
    for row in records(base, "resultados"):
        linked = cn.execute(
            "SELECT * FROM native WHERE purchase=? AND item=?",
            (row["id_compra"], row["id_compra_item"]),
        ).fetchone()
        status = "item_catalogado_comparabilidade_pendente" if linked else "item_nao_resolvido"
        result_status[status] += 1
        writers["resultados_catalogados"].add(
            {
                "id_resultado": row["id_registro"],
                "compra": row["id_compra"],
                "item": row["id_compra_item"],
                "fornecedor": row["fornecedor"],
                "catalogo": linked["catalog"] if linked else None,
                "grupo_candidato": linked["gid"] if linked else None,
                "preco_unitario_homologado": str(row["preco_unitario"])
                if row["preco_unitario"] is not None
                else None,
                "quantidade": format(row["quantidade"], "f")
                if row["quantidade"] is not None
                else None,
                "data_resultado": str(row["data_resultado"]) if row["data_resultado"] else None,
                "cancelamento_informado": row["cancelamento_informado"],
                "status": status,
                "arquivo_sha256": row["arquivo_sha256"],
                "membro": row["membro"],
                "linha": row["linha"],
            }
        )
    native_counts = Counter()
    # Original native codes are inventory only; no price average mixes CATMAT/CATSER/variants.
    for r in records(base, "itens", ["catalogo_original", "material_ou_servico"]):
        if r["catalogo_original"]:
            kind = (
                "CATMAT"
                if r["material_ou_servico"] == "M"
                else "CATSER"
                if r["material_ou_servico"] == "S"
                else "NAO_CONFIRMADO"
            )
            native_counts[kind, r["catalogo_original"]] += 1
    products = {
        (r["catalog"], r["n"], r["g"])
        for r in cn.execute(
            "SELECT catalog,COUNT(*) n,COUNT(DISTINCT gid) g FROM refs "
            "WHERE catalog IS NOT NULL GROUP BY catalog"
        )
    }
    for code, n, g in sorted(products):
        writers["produtos"].add(
            {
                "tipo_catalogo": "CATMAT",
                "catalogo": code,
                "referencias": n,
                "grupos_comparaveis": g,
                "itens_com_codigo_original": native_counts.pop(("CATMAT", code), 0),
                "media_global_catalogo": None,
            }
        )
    for (kind, code), n in sorted(native_counts.items()):
        writers["produtos"].add(
            {
                "tipo_catalogo": kind,
                "catalogo": code,
                "referencias": 0,
                "grupos_comparaveis": 0,
                "itens_com_codigo_original": n,
                "media_global_catalogo": None,
            }
        )
    return {"itens": dict(item_status), "resultados": dict(result_status)}


def prepare(base, output, policy=None, previous=None):
    started = time.monotonic()
    base = Path(base)
    output = Path(output)
    policy = policy or TemporalPolicy(train_start=date(2025, 7, 1))
    source = json.loads((base / "manifesto.json").read_text())
    validate_existing(base, source["fingerprint"])
    protocol = json.loads(PROTOCOL.read_text())
    if protocol["versao"] != VERSION:
        raise ValueError("Protocolo do catálogo incompatível")
    for f in source["fontes"]:
        if checksum(Path(f["arquivo"])) != f["sha256"]:
            raise ValueError("Fonte original divergente")
    config = {
        "base_sha256": checksum(base / "manifesto.json"),
        "base_fingerprint": source["fingerprint"],
        "codigo_sha256": code_hash(),
        "protocolo_sha256": checksum(PROTOCOL),
        "exclusoes_sha256": checksum(RESOURCE_DIR / "exclusoes_v1.json"),
        "politica_temporal_diagnostica": policy.manifest(),
        "dependencias": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
        "escopo": "todos_catalogos",
    }
    if previous is not None:
        previous = Path(previous)
        prior = json.loads((previous / "manifesto.json").read_text())
        validate(previous, prior["fingerprint"])
        for key in ("base_sha256", "politica_temporal_diagnostica", "exclusoes_sha256", "escopo"):
            if prior["configuracao"][key] != config[key]:
                raise ValueError("Catálogo anterior usa outra base, período ou exclusões")
        previous_protocol = json.loads((previous / "protocolo.json").read_text())
        current_protocol = dict(protocol)
        previous_protocol.pop("copia_catalogo_sem_marcadores", None)
        current_protocol.pop("copia_catalogo_sem_marcadores", None)
        if previous_protocol != current_protocol:
            raise ValueError("Reaproveitamento exige protocolo-base idêntico")
        config["catalogo_anterior_sha256"] = checksum(previous / "manifesto.json")
    fp = digest(config)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"catalogo={fp}"
    with (output / ".catalogo.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists():
            return {
                "diretorio": str(destination),
                "reutilizada": True,
                "manifesto": validate(destination, fp),
            }
        with tempfile.TemporaryDirectory(prefix=".catalogo-", dir=output) as temporary:
            root = Path(temporary)
            folder = root / "catalogo"
            folder.mkdir()
            result = {
                "versao": VERSION,
                "fingerprint": fp,
                "configuracao": config,
                "fontes": source["fontes"],
                "treino_executado": False,
                "banco_alterado": False,
                "comparabilidade_comercial_aprovada": False,
            }
            with sqlite3.connect(root / "stage.sqlite") as cn:
                cn.row_factory = sqlite3.Row
                setup(cn)
                LOGGER.info(
                    "Iniciando catálogo integral; %s referências na base",
                    source["tabelas"]["referencias"],
                )
                n = restage(cn, previous) if previous is not None else stage(cn, base, policy)
                LOGGER.info("Referências consolidadas; exportando grupos e estatísticas")
                with ExitStack() as stack:
                    writers = export(cn, folder, stack, result)
                    result["cobertura_catalogacao"] = export_native(cn, base, writers)
                counts = {name: w.count for name, w in writers.items()}
                if (
                    counts["observacoes"] != n
                    or n != source["tabelas"]["referencias"]
                    or counts["itens_catalogados"] != source["tabelas"]["itens"]
                    or counts["resultados_catalogados"] != source["tabelas"]["resultados"]
                ):
                    raise ValueError("Catálogo perdeu observações/itens/resultados")
            (folder / "protocolo.json").write_bytes(PROTOCOL.read_bytes())
            artifacts = []
            for p in sorted(folder.iterdir()):
                count = counts.get(p.stem)
                if p.suffix == ".parquet" and pq.ParquetFile(p).metadata.num_rows != count:
                    raise ValueError("Parquet divergente")
                artifacts.append(
                    {
                        "arquivo": p.name,
                        "sha256": checksum(p),
                        "bytes": p.stat().st_size,
                        "linhas": count,
                    }
                )
            validate_existing(base, source["fingerprint"])
            result.update(
                tabelas=counts,
                artefatos=artifacts,
                medicoes={
                    "segundos": round(time.monotonic() - started, 3),
                    "rss_pico_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
                    ),
                },
            )
            (folder / "manifesto.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            )
            folder.rename(destination)
    return {"diretorio": str(destination), "reutilizada": False, "manifesto": result}
