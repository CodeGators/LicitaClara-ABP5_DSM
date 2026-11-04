"""Perfil offline dos ZIPs locais; não importa dados nem executa modelos.

python -m licita_ml.diagnostics --entrada data/diagnostico/compras/2026-09 \
    --saida data/diagnostico/ml01/perfil.json
"""

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZipFile

KINDS = ("compra", "compra_item", "item_resultado", "material")
DATE_FIELDS = {
    "compra": ("data_publicacao_pncp", "data_abertura_proposta_pncp"),
    "compra_item": ("data_resultado", "data_inclusao_pncp"),
    "item_resultado": ("data_resultado_pncp", "data_cancelamento_pncp"),
    "material": ("data_compra", "data_resultado"),
}
NUMBER_FIELDS = {
    "compra": ("valor_total_estimado", "valor_total_homologado"),
    "compra_item": ("valor_unitario_estimado", "quantidade", "valor_unitario_resultado"),
    "item_resultado": (
        "quantidade_homologada",
        "valor_unitario_homologado",
        "valor_total_homologado",
    ),
    "material": ("preco_unitario", "quantidade", "capacidade_unidade_fornecimento"),
}


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(c if c.isalnum() else " " for c in value if not unicodedata.combining(c)).split()
    )


def day(value):
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def number_status(value):
    try:
        value = Decimal(value)
        if not value.is_finite():
            return "invalido"
        return "negativo" if value < 0 else "zero" if value == 0 else "positivo"
    except InvalidOperation:
        return "invalido"


def records(path):
    with ZipFile(path) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Esperado um CSV por ZIP: {path}")
        with archive.open(members[0]) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter=";")
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError(f"Cabeçalho inválido: {path}")
            for ordinal, row in enumerate(reader, 2):
                if None in row or any(v is None for v in row.values()):
                    raise ValueError(f"Linha com largura inválida: {path}:{ordinal}")
                yield row


def profile(connection, kind, path):
    connection.execute(f"""CREATE TABLE {kind} (
        purchase TEXT, item TEXT, supplier TEXT, org TEXT, code TEXT, class TEXT,
        grp TEXT, unit TEXT, capacity TEXT, measure TEXT, description TEXT,
        event TEXT, result TEXT, price TEXT, qty TEXT, estimated TEXT, cancelled TEXT,
        identity TEXT, digest TEXT)""")
    empty, dates, months, invalid_dates = Counter(), {}, {}, Counter()
    numbers = {name: Counter() for name in NUMBER_FIELDS[kind]}
    source_sha = checksum(path)
    rows = 0
    columns = []
    batch = []
    for row in records(path):
        required = {"id_compra"}
        if kind != "compra":
            required.add("id_compra_item")
        if kind == "material":
            required.update({"codigo_item_catalogo", "preco_unitario", "quantidade", "data_compra"})
        if required - row.keys():
            raise ValueError(
                f"Colunas obrigatórias ausentes em {path}: {sorted(required - row.keys())}"
            )
        rows += 1
        columns = list(row)
        row = {k: v.strip() for k, v in row.items()}
        empty.update(k for k, v in row.items() if not v)
        for name in DATE_FIELDS[kind]:
            value = row.get(name, "")
            if not value:
                continue
            parsed = day(value)
            if parsed is None:
                invalid_dates[name] += 1
            else:
                bounds = dates.setdefault(name, [parsed, parsed])
                bounds[:] = [min(bounds[0], parsed), max(bounds[1], parsed)]
                months.setdefault(name, Counter())[parsed[:7]] += 1
        for name in numbers:
            value = row.get(name, "")
            numbers[name][number_status(value) if value else "ausente"] += 1
        get = lambda key: row.get(key, "")  # noqa: E731
        purchase, item = get("id_compra"), get("id_compra_item")
        if kind == "compra":
            identity = [purchase]
        elif kind == "item_resultado":
            identity = [purchase, item, get("sequencial_resultado")]
        elif kind == "material":
            identity = [purchase, get("id_item_compra"), get("ni_fornecedor"), get("forma")]
        else:
            identity = [purchase, item]
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        description = get("descricao_detalhada_item") or get("descricao_item")
        if kind == "material":
            group = [
                get("codigo_item_catalogo"),
                normalized(description),
                get("sigla_unidade_fornecimento") or get("nome_unidade_fornecimento"),
                get("capacidade_unidade_fornecimento"),
                get("sigla_unidade_medida"),
            ]
            group_key = hashlib.sha256(json.dumps(group).encode()).hexdigest()[:16]
        else:
            group_key = ""
        batch.append(
            (
                purchase,
                item,
                get("ni_fornecedor") or get("cod_fornecedor"),
                get("codigo_orgao") or get("orgao_entidade_cnpj"),
                get("codigo_item_catalogo") or get("cod_item_catalogo"),
                get("codigo_classe"),
                group_key,
                get("sigla_unidade_fornecimento") or get("unidade_medida"),
                get("capacidade_unidade_fornecimento"),
                get("sigla_unidade_medida"),
                normalized(description),
                day(get("data_compra")) or "",
                day(get("data_resultado_pncp") or get("data_resultado")) or "",
                get("preco_unitario") or get("valor_unitario_homologado"),
                get("quantidade_homologada") or get("quantidade"),
                get("valor_unitario_estimado"),
                get("data_cancelamento_pncp"),
                json.dumps(identity),
                digest,
            )
        )
        if len(batch) == 2000:
            connection.executemany(f"INSERT INTO {kind} VALUES ({','.join(['?'] * 19)})", batch)
            batch.clear()
    if batch:
        connection.executemany(f"INSERT INTO {kind} VALUES ({','.join(['?'] * 19)})", batch)
    connection.commit()
    for column in ("purchase", "item", "code", "grp", "identity"):
        connection.execute(f"CREATE INDEX idx_{kind}_{column} ON {kind} ({column})")
    scalar = lambda sql: connection.execute(sql).fetchone()[0]  # noqa: E731
    identities = scalar(f"SELECT COUNT(DISTINCT identity) FROM {kind}")
    return {
        "arquivo": str(path),
        "sha256": source_sha,
        "bytes_zip": path.stat().st_size,
        "linhas": rows,
        "colunas": columns,
        "ausentes_por_coluna": {c: empty[c] for c in columns},
        "datas_min_max": dates,
        "datas_por_mes": months,
        "datas_invalidas": invalid_dates,
        "numericos": numbers,
        "identidades_distintas": identities,
        "linhas_excedentes_por_identidade": rows - identities,
        "duplicatas_exatas": rows - scalar(f"SELECT COUNT(DISTINCT digest) FROM {kind}"),
        "compras_distintas": scalar(
            f"SELECT COUNT(DISTINCT purchase) FROM {kind} WHERE purchase!=''"
        ),
        "itens_distintos": scalar(f"SELECT COUNT(DISTINCT item) FROM {kind} WHERE item!=''"),
    }


def links(connection):
    def count(sql):
        return connection.execute(sql).fetchone()[0]

    result = {}
    for source, target, column in (
        ("compra_item", "compra", "purchase"),
        ("item_resultado", "compra", "purchase"),
        ("item_resultado", "compra_item", "item"),
        ("material", "compra_item", "item"),
    ):
        for exists, label in (("EXISTS", "com_vinculo"), ("NOT EXISTS", "sem_vinculo")):
            result[f"{source}_{target}_{label}"] = count(f"""
                SELECT COUNT(DISTINCT s.{column}) FROM {source} s WHERE s.{column}!=''
                AND {exists} (SELECT 1 FROM {target} t WHERE t.{column}=s.{column}
                AND t.purchase=s.purchase)""")
    result["material_item_id_igual_sem_conferir_compra"] = count("""
        SELECT COUNT(DISTINCT m.item) FROM material m WHERE m.item!=''
        AND EXISTS (SELECT 1 FROM compra_item i WHERE i.item=m.item)""")
    result["ids_material_com_catalogos_conflitantes"] = count("""
        SELECT COUNT(*) FROM (SELECT item FROM material WHERE item!=''
        GROUP BY item HAVING COUNT(DISTINCT code)>1)""")
    result["resultado_item_fornecedor_preco_quantidade_data_exatos"] = count("""
        SELECT COUNT(DISTINCT r.identity) FROM item_resultado r
        WHERE r.cancelled='' AND r.price!='' AND r.qty!='' AND r.result!=''
        AND EXISTS (SELECT 1 FROM material m
        WHERE m.purchase=r.purchase AND m.item=r.item AND m.supplier=r.supplier
        AND m.price=r.price AND m.qty=r.qty AND m.result=r.result)
        AND EXISTS (SELECT 1 FROM compra_item i WHERE i.item=r.item AND i.purchase=r.purchase)
        """)
    return result


def categories(connection, selected_codes=None):
    output = []
    condition = "code!=''"
    parameters = []
    if selected_codes is not None:
        if not selected_codes:
            return []
        condition += f" AND code IN ({','.join('?' for _ in selected_codes)})"
        parameters = list(selected_codes)
    query = f"""SELECT code,COUNT(*),COUNT(DISTINCT purchase),COUNT(DISTINCT NULLIF(org,'')),
        COUNT(DISTINCT NULLIF(supplier,'')) FROM material WHERE {condition}
        GROUP BY code ORDER BY COUNT(DISTINCT purchase) DESC,code LIMIT 20"""
    for code, count, purchases, orgs, suppliers in connection.execute(query, parameters):
        groups = []
        for row in connection.execute(
            """SELECT grp,COUNT(*),COUNT(DISTINCT purchase),
            COUNT(DISTINCT NULLIF(org,'')),COUNT(DISTINCT NULLIF(supplier,'')),
            MIN(description),MIN(unit),MIN(capacity),MIN(event),MAX(event)
            FROM material WHERE code=? GROUP BY grp
            ORDER BY COUNT(DISTINCT purchase) DESC,grp LIMIT 3""",
            (code,),
        ):
            groups.append(
                dict(
                    zip(
                        (
                            "grupo",
                            "linhas",
                            "compras",
                            "orgaos",
                            "fornecedores",
                            "descricao",
                            "unidade",
                            "capacidade",
                            "inicio",
                            "fim",
                        ),
                        row,
                    )
                )
            )
        linked = connection.execute(
            """SELECT COUNT(DISTINCT m.item) FROM material m WHERE code=?
            AND EXISTS (SELECT 1 FROM compra_item i
            WHERE i.item=m.item AND i.purchase=m.purchase)""",
            (code,),
        ).fetchone()[0]
        matching_results = connection.execute(
            """SELECT COUNT(DISTINCT r.identity)
            FROM item_resultado r WHERE r.cancelled='' AND r.price!='' AND r.qty!=''
            AND r.result!='' AND EXISTS (SELECT 1 FROM material m WHERE m.code=?
                AND m.purchase=r.purchase AND m.item=r.item AND m.supplier=r.supplier
                AND m.price=r.price AND m.qty=r.qty AND m.result=r.result)
            AND EXISTS (SELECT 1 FROM compra_item i
                WHERE i.item=r.item AND i.purchase=r.purchase)""",
            (code,),
        ).fetchone()[0]
        output.append(
            {
                "catalogo": code,
                "resultados_com_campos_textuais_coincidentes": matching_results,
                "linhas": count,
                "compras": purchases,
                "orgaos": orgs,
                "fornecedores": suppliers,
                "itens_vinculados_no_mes": linked,
                "grupos_estruturais_exploratorios": groups,
            }
        )
    return output


def diagnose(folder):
    year, month = folder.name.split("-")
    with tempfile.TemporaryDirectory(prefix="licita-ml01-") as temp:
        with sqlite3.connect(str(Path(temp) / "perfil.sqlite")) as connection:
            profiles = {
                kind: profile(connection, kind, folder / f"{kind}_{year}_{month}.csv.zip")
                for kind in KINDS
            }
            office = categories(
                connection,
                [
                    r[0]
                    for r in connection.execute(
                        "SELECT DISTINCT code FROM material WHERE class='7510'"
                    )
                ],
            )
            for code in ("486054", "486374"):
                if code not in {c["catalogo"] for c in office}:
                    office.extend(categories(connection, [code]))
            result = {
                "versao": "diagnostico-ml01-v1",
                "competencia_arquivos": folder.name,
                "perfis": profiles,
                "vinculos_por_chaves": links(connection),
                "categorias_por_compras_distintas": categories(connection),
                "categorias_escritorio_e_modelos_anteriores": office,
                "limites": [
                    "Perfil bruto: não resolve versões nem comprova elegibilidade de treino.",
                    "Vínculos por ID não comprovam equivalência de especificação/unidade.",
                    "Grupos exploratórios não substituem a política analítica versionada.",
                    "Preços e quantidades exatos são comparados como texto da fonte.",
                    "Um mês não comprova histórico completo nem cobertura nacional.",
                ],
            }
        for kind, info in profiles.items():
            if checksum(Path(info["arquivo"])) != info["sha256"]:
                raise ValueError(f"Arquivo mudou durante a leitura: {kind}")
        return result


def inventory(root):
    """Identifica cópias pelo conteúdo; não soma cópias como nova cobertura."""
    contents = {}
    for path in sorted(root.rglob("*.zip")):
        digest = checksum(path)
        if digest not in contents:
            with ZipFile(path) as archive:
                members = archive.namelist()
            contents[digest] = {
                "sha256": digest,
                "bytes": path.stat().st_size,
                "membros": members,
                "copias": [],
            }
        contents[digest]["copias"].append(str(path))
    histories = []
    for path in sorted((root / "validacao_nucleo").glob("historico*.json")):
        if path.name.endswith(".meta.json"):
            continue
        document = json.loads(path.read_text())
        rows = document.get("resultado", [])
        if not isinstance(rows, list):
            raise ValueError(f"Envelope histórico inválido: {path}")
        dates = {}
        for field in ("dataCompra", "dataResultado"):
            values = [parsed for r in rows if (parsed := day(str(r.get(field) or "")))]
            dates[field] = [min(values), max(values)] if values else None
        histories.append(
            {
                "arquivo": str(path),
                "sha256": checksum(path),
                "linhas": len(rows),
                "datas_min_max": dates,
                "catalogos": sorted({str(r.get("codigoItemCatalogo")) for r in rows}),
            }
        )
    return {"zips_distintos_por_conteudo": list(contents.values()), "historicos_api": histories}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--inventario-raiz", type=Path)
    args = parser.parse_args()
    # Never let a diagnostic destination overwrite an input or a previous unrelated artifact.
    if args.saida.exists():
        raise ValueError("Saída já existe; escolha outro caminho para preservar evidências.")
    result = diagnose(args.entrada)
    if args.inventario_raiz:
        result["inventario"] = inventory(args.inventario_raiz)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Diagnóstico salvo em {args.saida}; fontes preservadas, sem rede ou banco operacional.")


if __name__ == "__main__":
    main()
