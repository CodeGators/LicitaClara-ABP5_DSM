"""Organização offline, versionada e atômica; originais e banco não são alterados."""

import fcntl
import hashlib
import itertools
import json
import platform
import re
import sqlite3
import tempfile
from collections import Counter
from contextlib import ExitStack
from datetime import date, timezone
from pathlib import Path
from zipfile import ZipFile

import pyarrow
import pyarrow.parquet as pq

from licita_ml.diagnostics import checksum, records
from licita_ml.normalize import RowError, instant, text
from licita_ml.organized.schema import (
    COMMON,
    FIELDS,
    IDENTITY,
    Export,
    dictionary,
    encode,
    transform,
)

VERSION = "base-organizada-v1"
MODULES = {
    "compra": "compras",
    "compra_item": "itens",
    "item_resultado": "resultados",
    "material": "referencias",
}
LEDGER = {
    "tabela": "texto",
    "id_registro": "texto",
    "arquivo_sha256": "texto",
    "membro": "texto",
    "linha": "inteiro",
    "destino": "texto",
    "motivo": "texto",
}
LINKS = {
    "origem_tabela": "texto",
    "origem_id": "texto",
    "destino_tabela": "texto",
    "destino_id": "texto",
    "tipo": "texto",
    "status": "texto",
}
ENRICHMENT = {
    "item_registro_id": "texto",
    "id_compra": "texto",
    "id_compra_item": "texto",
    "catalogo_original": "texto",
    "catalogo_referencia_unico": "texto",
    "descricao_referencia_unica": "texto",
    "referencias": "inteiro",
    "catalogos_json": "texto",
    "unidades_json": "texto",
    "status": "texto",
}


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def discover(folders, histories):
    paths = []
    for folder in folders:
        year, month = folder.name.split("-")
        date(int(year), int(month), 1)
        paths.extend(folder / f"{module}_{year}_{month}.csv.zip" for module in MODULES)
    paths.extend(histories)
    sources = {}
    for path in sorted(set(paths)):
        match = re.fullmatch(
            r"(compra|compra_item|item_resultado|material)_(\d{4})_(\d{2})\.csv\.zip", path.name
        )
        if not match:
            raise ValueError(f"Nome de arquivo não suportado: {path}")
        module, year, month = match.groups()
        date(int(year), int(month), 1)
        sha = checksum(path)
        key = (module, sha)
        if key in sources:
            sources[key]["copias"].append(str(path))
            continue
        with ZipFile(path) as archive:
            members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Esperado um CSV por ZIP: {path}")
        sources[key] = {
            "arquivo": str(path),
            "sha256": sha,
            "bytes": path.stat().st_size,
            "tabela": MODULES[module],
            "competencia": f"{year}-{month}",
            "membro": members[0],
            "copias": [str(path)],
        }
    return sorted(sources.values(), key=lambda source: (source["tabela"], source["sha256"]))


def rank(raw, table):
    names = (
        ("data_hora_atualizacao_item", "data_hora_atualizacao_compra")
        if table == "referencias"
        else ("data_atualizacao_pncp",)
    )
    ranks, modes = [], []
    for name in names:
        value = instant(raw.get(name))
        if value is None:
            ranks.append("")
            modes.append("")
        else:
            aware = value.utcoffset() is not None
            if aware:
                value = value.astimezone(timezone.utc)
            ranks.append(value.isoformat(timespec="microseconds"))
            modes.append("com_fuso" if aware else "sem_fuso")
    return (ranks + [""])[:2], (modes + [""])[:2]


def setup(connection):
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE stage (
          row_id INTEGER PRIMARY KEY, kind TEXT, identity TEXT, id TEXT,
          rank_a TEXT, rank_b TEXT, mode_a TEXT, mode_b TEXT, rank_error INTEGER,
          raw_hash TEXT, value_hash TEXT, data TEXT, source TEXT, member TEXT, line INTEGER,
          disposition TEXT, reason TEXT);
        CREATE TABLE selected (
          kind TEXT, identity TEXT, id TEXT, purchase TEXT, item TEXT, supplier TEXT,
          catalog TEXT, price TEXT, qty TEXT, result TEXT, cancelled INTEGER, data TEXT,
          PRIMARY KEY(kind, identity));
    """)


def stage(connection, sources):
    for source in sources:
        table = source["tabela"]
        batch, rows = [], 0
        absent = set()
        for line, raw in enumerate(records(Path(source["arquivo"])), 2):
            if rows == 0:
                required = set(IDENTITY[table])
                if table in ("resultados", "referencias"):
                    required.add("ni_fornecedor")
                if table == "referencias":
                    required.update(
                        {
                            "id_compra_item",
                            "codigo_item_catalogo",
                            "preco_unitario",
                            "quantidade",
                            "data_compra",
                        }
                    )
                if required - raw.keys():
                    raise ValueError(
                        f"Esquema incompatível: {source['arquivo']}: {required - raw.keys()}"
                    )
                absent = {column for column, _ in FIELDS[table].values()} - raw.keys()
            rows += 1
            identity_values = [text(raw.get(name)) for name in IDENTITY[table]]
            missing = any(value is None for value in identity_values)
            identity = None if missing else encode(identity_values)
            row_id = None if missing else digest([table, identity_values])
            rank_error = False
            try:
                ranks, modes = rank(raw, table)
            except RowError:
                ranks, modes, rank_error = ["", ""], ["", ""], True
            values, warnings = transform(table, raw)
            value_hash = digest([values, warnings])
            values.update(
                id_registro=row_id,
                arquivo_sha256=source["sha256"],
                membro=source["membro"],
                linha=line,
                competencia_arquivo=source["competencia"],
                atualizacao_primaria=ranks[0] or None,
                atualizacao_secundaria=ranks[1] or None,
                avisos_json=encode(warnings),
            )
            batch.append(
                (
                    table,
                    identity,
                    row_id,
                    *ranks,
                    *modes,
                    rank_error,
                    digest(raw),
                    value_hash,
                    encode(values),
                    source["sha256"],
                    source["membro"],
                    line,
                    "rejeitado" if missing else None,
                    "IDENTIDADE_INCOMPLETA" if missing else None,
                )
            )
            if len(batch) >= 2000:
                connection.executemany(
                    "INSERT INTO stage VALUES (NULL," + ",".join("?" * 16) + ")", batch
                )
                batch.clear()
        if not rows:
            raise ValueError(f"Arquivo sem registros: {source['arquivo']}")
        if batch:
            connection.executemany(
                "INSERT INTO stage VALUES (NULL," + ",".join("?" * 16) + ")", batch
            )
        source["linhas"] = rows
        source["colunas_opcionais_ausentes"] = sorted(absent)
        connection.commit()
    connection.execute("CREATE INDEX stage_identity ON stage(kind, identity)")


def decide(group):
    if any(row["rank_error"] for row in group):
        return None, "DATA_VERSAO_INVALIDA"
    for field in ("mode_a", "mode_b"):
        if len({row[field] for row in group if row[field]}) > 1:
            return None, "VERSOES_COM_FUSOS_INCOMPATIVEIS"
    if len({row["value_hash"] for row in group}) > 1 and any(not row["rank_a"] for row in group):
        return None, "VERSOES_DIVERGENTES_SEM_DATA"
    primary = max(row["rank_a"] for row in group)
    peers = [row for row in group if row["rank_a"] == primary]
    if (
        len({row["value_hash"] for row in peers}) > 1
        and any(row["rank_b"] for row in peers)
        and any(not row["rank_b"] for row in peers)
    ):
        return None, "VERSOES_DIVERGENTES_SEM_DATA_SECUNDARIA"
    best_rank = max((row["rank_a"], row["rank_b"]) for row in group)
    best = [row for row in group if (row["rank_a"], row["rank_b"]) == best_rank]
    if len({row["value_hash"] for row in best}) > 1:
        return None, "EMPATE_DE_VERSAO_DIVERGENTE"
    return min(best, key=lambda row: (row["source"], row["line"])), None


def resolve(connection):
    cursor = connection.execute(
        "SELECT * FROM stage WHERE identity IS NOT NULL ORDER BY kind,identity"
    )
    for (kind, identity), items in itertools.groupby(
        cursor, key=lambda row: (row["kind"], row["identity"])
    ):
        group = list(itertools.islice(items, 10001))
        if len(group) > 10000:
            raise ValueError(
                "Mais de dez mil versões da mesma identidade; investigar antes de preparar"
            )
        winner, reason = decide(group)
        updates = []
        for row in group:
            if winner is None:
                disposition = "rejeitado"
            elif row["row_id"] == winner["row_id"]:
                disposition = "aceito"
            elif (row["rank_a"], row["rank_b"]) != (winner["rank_a"], winner["rank_b"]):
                disposition = "versao_superada"
            elif row["raw_hash"] == winner["raw_hash"]:
                disposition = "duplicata_exata"
            else:
                disposition = "projecao_equivalente"
            updates.append((disposition, reason, row["row_id"]))
        connection.executemany("UPDATE stage SET disposition=?,reason=? WHERE row_id=?", updates)
        if winner is not None:
            data = json.loads(winner["data"])
            connection.execute(
                "INSERT INTO selected VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    kind,
                    identity,
                    data["id_registro"],
                    data.get("id_compra"),
                    data.get("id_compra_item"),
                    data.get("fornecedor"),
                    data.get("catalogo") or data.get("catalogo_original"),
                    data.get("preco_unitario"),
                    data.get("quantidade"),
                    data.get("data_resultado"),
                    int(data.get("cancelamento_informado", False)),
                    winner["data"],
                ),
            )
    connection.commit()
    connection.execute("CREATE INDEX selected_parent ON selected(kind,purchase,item)")
    connection.execute("CREATE INDEX selected_item ON selected(kind,item)")
    connection.execute("CREATE INDEX selected_match ON selected(kind,purchase,item,supplier)")


def exporter(stack, folder, name, fields):
    writer = Export(folder, name, fields)
    stack.callback(writer.close)
    return writer


def export_domains(connection, folder, stack):
    writers = {}
    for kind, fields in FIELDS.items():
        schema = {**COMMON, **{name: value[1] for name, value in fields.items()}}
        if kind == "resultados":
            schema["cancelamento_informado"] = "booleano"
        writer = writers[kind] = exporter(stack, folder, kind, schema)
        for row in connection.execute(
            "SELECT data FROM selected WHERE kind=? ORDER BY identity", (kind,)
        ):
            writer.add(json.loads(row["data"]))
    ledger = writers["linhas"] = exporter(stack, folder, "linhas", LEDGER)
    rejects = writers["rejeicoes"] = exporter(stack, folder, "rejeicoes", LEDGER)
    for row in connection.execute("SELECT * FROM stage ORDER BY kind,source,line"):
        if not row["disposition"]:
            raise ValueError("Linha sem destinação")
        record = {
            "tabela": row["kind"],
            "id_registro": row["id"],
            "arquivo_sha256": row["source"],
            "membro": row["member"],
            "linha": row["line"],
            "destino": row["disposition"],
            "motivo": row["reason"],
        }
        ledger.add(record)
        if row["disposition"] == "rejeitado":
            rejects.add(record)
    return writers


def parent_link(connection, row, target):
    if target == "compras":
        parents = connection.execute(
            "SELECT id FROM selected WHERE kind=? AND purchase=?", (target, row["purchase"])
        ).fetchall()
    else:
        parents = connection.execute(
            "SELECT id FROM selected WHERE kind=? AND purchase=? AND item=?",
            (target, row["purchase"], row["item"]),
        ).fetchall()
    if len(parents) > 1:
        raise ValueError("Identidade de pai ambígua")
    if parents:
        return parents[0]["id"], "vinculado_por_chave"
    if (
        target == "itens"
        and connection.execute(
            "SELECT 1 FROM selected WHERE kind='itens' AND item=? LIMIT 1", (row["item"],)
        ).fetchone()
    ):
        return None, "id_item_com_compra_divergente"
    return None, "pai_nao_resolvido"


def reference_result_links(connection, row):
    if not all(row[field] is not None for field in ("supplier", "price", "qty", "result")):
        return [(None, "campos_insuficientes")]
    candidates = connection.execute(
        """SELECT id,cancelled FROM selected
        WHERE kind='resultados' AND purchase=? AND item=? AND supplier=?
        AND price=? AND qty=? AND result=? ORDER BY id""",
        (
            row["purchase"],
            row["item"],
            row["supplier"],
            row["price"],
            row["qty"],
            row["result"],
        ),
    ).fetchall()
    if len(candidates) > 1:
        return [(candidate["id"], "coincidencia_ambigua") for candidate in candidates]
    if candidates:
        candidate = candidates[0]
        return [
            (
                candidate["id"],
                "coincidencia_campos_cancelamento_informado"
                if candidate["cancelled"]
                else "coincidencia_campos_nao_valida_comparabilidade",
            )
        ]
    return [(None, "sem_resultado_com_campos_coincidentes")]


def export_links(connection, folder, stack):
    writer = exporter(stack, folder, "vinculos", LINKS)
    stats = Counter()
    for row in connection.execute(
        "SELECT * FROM selected WHERE kind!='compras' ORDER BY kind,identity"
    ):
        target = "compras" if row["kind"] == "itens" else "itens"
        parent_id, status = parent_link(connection, row, target)
        writer.add(
            {
                "origem_tabela": row["kind"],
                "origem_id": row["id"],
                "destino_tabela": target,
                "destino_id": parent_id,
                "tipo": "chave_oficial",
                "status": status,
            }
        )
        stats[f"{row['kind']}:{target}:{status}"] += 1
        if row["kind"] == "referencias":
            for result_id, status in reference_result_links(connection, row):
                writer.add(
                    {
                        "origem_tabela": row["kind"],
                        "origem_id": row["id"],
                        "destino_tabela": "resultados",
                        "destino_id": result_id,
                        "tipo": "campos_resultado",
                        "status": status,
                    }
                )
                stats[f"referencias:resultados:{status}"] += 1
    return writer, dict(sorted(stats.items()))


def export_enrichment(connection, folder, stack):
    writer = exporter(stack, folder, "enriquecimento_itens", ENRICHMENT)
    stats = Counter()
    for item in connection.execute("SELECT * FROM selected WHERE kind='itens' ORDER BY identity"):
        refs = connection.execute(
            """SELECT data FROM selected WHERE kind='referencias'
            AND purchase=? AND item=?""",
            (item["purchase"], item["item"]),
        ).fetchall()
        rows = [json.loads(row["data"]) for row in refs]
        catalogs = sorted({row["catalogo"] for row in rows if row["catalogo"]})
        descriptions = sorted(
            {row["descricao_detalhada"] for row in rows if row["descricao_detalhada"]}
        )
        units = sorted(
            {
                encode(
                    [
                        row["unidade_fornecimento_sigla"],
                        row["unidade_fornecimento_nome"],
                        row["capacidade"],
                        row["unidade_medida_sigla"],
                    ]
                )
                for row in rows
            }
        )
        catalog = catalogs[0] if len(catalogs) == 1 else None
        status = (
            "sem_referencia"
            if not rows
            else "catalogos_divergentes"
            if len(catalogs) != 1
            else "conflito_com_catalogo_original"
            if item["catalog"] and item["catalog"] != catalog
            else "catalogo_unico_por_vinculo_nao_valida_especificacao"
        )
        writer.add(
            {
                "item_registro_id": item["id"],
                "id_compra": item["purchase"],
                "id_compra_item": item["item"],
                "catalogo_original": item["catalog"],
                "catalogo_referencia_unico": catalog,
                "descricao_referencia_unica": descriptions[0] if len(descriptions) == 1 else None,
                "referencias": len(rows),
                "catalogos_json": encode(catalogs),
                "unidades_json": encode([json.loads(unit) for unit in units]),
                "status": status,
            }
        )
        stats[status] += 1
    return writer, dict(sorted(stats.items()))


def validate_existing(folder, fingerprint):
    manifest = json.loads((folder / "manifesto.json").read_text())
    if manifest["fingerprint"] != fingerprint or manifest["politica"] != VERSION:
        raise ValueError("Fingerprint ou política divergente")
    tables = set(FIELDS) | {"linhas", "rejeicoes", "vinculos", "enriquecimento_itens"}
    expected = {f"{name}.{suffix}" for name in tables for suffix in ("csv", "parquet")}
    expected.add("dicionario.json")
    if (
        {a["arquivo"] for a in manifest["artefatos"]} != expected
        or len(manifest["artefatos"]) != len(expected)
        or set(manifest["tabelas"]) != tables
    ):
        raise ValueError("Manifesto existente incompleto")
    for artifact in manifest["artefatos"]:
        path = folder / artifact["arquivo"]
        if path.parent != folder or checksum(path) != artifact["sha256"]:
            raise ValueError("Artefato existente corrompido ou inválido")
        if path.suffix == ".parquet":
            count = pq.ParquetFile(path).metadata.num_rows
            if count != artifact["linhas"] or count != manifest["tabelas"][path.stem]:
                raise ValueError("Contagem de artefato divergente")
    return {"diretorio": str(folder), "reutilizada": True, "manifesto": manifest}


def prepare(folders, output, histories=()):
    sources = discover(folders, histories)
    if not sources:
        raise ValueError("Nenhuma fonte")
    code_sha = digest([(p.name, checksum(p)) for p in sorted(Path(__file__).parent.glob("*.py"))])
    dependencies = {
        "pyarrow": pyarrow.__version__,
        "python": platform.python_version(),
        "normalizacao_sha256": checksum(Path(__file__).parents[1] / "normalize.py"),
        "leitor_sha256": checksum(Path(__file__).parents[1] / "diagnostics.py"),
    }
    fingerprint = digest(
        {
            "politica": VERSION,
            "codigo": code_sha,
            "ambiente": dependencies,
            "fontes": [(s["tabela"], s["sha256"]) for s in sources],
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"base={fingerprint}"
    with (output / ".preparo.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists():
            return validate_existing(destination, fingerprint)
        with tempfile.TemporaryDirectory(prefix=".preparo-", dir=output) as temporary:
            temp = Path(temporary)
            artifacts = temp / "base"
            artifacts.mkdir()
            with sqlite3.connect(temp / "stage.sqlite") as connection:
                setup(connection)
                stage(connection, sources)
                resolve(connection)
                with ExitStack() as stack:
                    writers = export_domains(connection, artifacts, stack)
                    writers["vinculos"], link_stats = export_links(connection, artifacts, stack)
                    writers["enriquecimento_itens"], enrichment_stats = export_enrichment(
                        connection, artifacts, stack
                    )
                dispositions = {}
                for row in connection.execute(
                    "SELECT kind,disposition,COUNT(*) n FROM stage GROUP BY kind,disposition"
                ):
                    dispositions.setdefault(row["kind"], {})[row["disposition"]] = row["n"]
                for table in FIELDS:
                    source_count = sum(s["linhas"] for s in sources if s["tabela"] == table)
                    if sum(dispositions[table].values()) != source_count:
                        raise ValueError("Contagem de entrada não reconciliada")
                    if dispositions[table].get("aceito", 0) != writers[table].count:
                        raise ValueError("Contagem de saída não reconciliada")
            contract = {
                "versao": VERSION,
                "tabelas": dictionary(),
                "auxiliares": {
                    "linhas": LEDGER,
                    "rejeicoes": LEDGER,
                    "vinculos": LINKS,
                    "enriquecimento_itens": ENRICHMENT,
                },
                "convencoes": [
                    "IDs são texto; decimal128(28,8); CSV UTF-8, ;, ponto decimal, vazio=null.",
                    "Linha é ordinal do registro CSV com cabeçalho=1, não linha física multilinha.",
                    "Data de versão inválida ou empate divergente rejeita toda a identidade.",
                    "Empates usam atributos da entidade; dados de filhos ficam separados.",
                    "Projeção equivalente mantém a rastreabilidade de todas as linhas originais.",
                    "Versões sem/com fuso não são ordenadas entre si.",
                    "Ausência/erro numérico não vira zero; avisos acompanham campos inválidos.",
                    "Todos os campos não exportados permanecem nos ZIPs originais rastreáveis.",
                    "Enriquecimento não altera originais nem comprova comparabilidade.",
                    "Sem mediana, ajuste aprendido, divisão temporal, treino ou score nesta base.",
                ],
            }
            (artifacts / "dicionario.json").write_text(
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
            )
            entries = []
            for path in sorted(artifacts.iterdir()):
                name = path.stem
                count = writers[name].count if name in writers else None
                if path.suffix == ".parquet" and pq.ParquetFile(path).metadata.num_rows != count:
                    raise ValueError("Contagem Parquet divergente")
                entries.append(
                    {
                        "arquivo": path.name,
                        "bytes": path.stat().st_size,
                        "sha256": checksum(path),
                        "linhas": count,
                    }
                )
            for source in sources:
                for path in source["copias"]:
                    if checksum(Path(path)) != source["sha256"]:
                        raise ValueError("Fonte mudou durante o preparo")
            manifest = {
                "politica": VERSION,
                "fingerprint": fingerprint,
                "codigo_sha256": code_sha,
                "ambiente": dependencies,
                "fontes": sources,
                "destinos_linhas": dispositions,
                "vinculos": link_stats,
                "enriquecimento": enrichment_stats,
                "tabelas": {name: writer.count for name, writer in writers.items()},
                "artefatos": entries,
                "modelos_executados": False,
                "banco_operacional_alterado": False,
            }
            (artifacts / "manifesto.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            )
            artifacts.rename(destination)
    return {"diretorio": str(destination), "reutilizada": False, "manifesto": manifest}
