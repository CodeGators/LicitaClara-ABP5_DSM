"""Universo oficial de itens/resultados dos snapshots API já vinculados à base."""

import hashlib
import json
from collections import defaultdict
from decimal import Decimal

import sqlalchemy as sa

from licita_ml.analytical.rules import canonical
from licita_ml.transform import canonical_row


def field(row, camel, snake):
    return row.get(camel, row.get(snake))


def event_key(raw):
    supplier = field(raw, "niFornecedor", "ni_fornecedor")
    seq = field(raw, "sequencialResultado", "sequencial_resultado")
    if supplier is None or seq is None:
        raise ValueError("Identidade de resultado oficial ausente")
    return str(supplier), int(seq)


def envelope(objects, artifact):
    with objects.open(artifact["chave_objeto"]) as stream:
        raw = stream.read(64 * 1024**2 + 1)
    if len(raw) > 64 * 1024**2 or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
        raise ValueError("Snapshot do universo diverge do registro")
    body = json.loads(raw)
    if body.get("schema") != "licita-json-v1" or body.get("kind") not in {
        "itens_api",
        "resultados_api",
    }:
        raise ValueError("Fonte não descreve universo oficial por compra")
    rows, total, pages = [], None, body["paginas"]
    seen = set()
    for number, page in enumerate(pages, 1):
        original = json.loads(page["resposta_original"], parse_float=Decimal)
        current = int(original["totalRegistros"])
        if (
            page["pagina"] != number
            or max(1, int(original["totalPaginas"])) != len(pages)
            or (total is not None and total != current)
            or canonical(original["resultado"]) != canonical(page["resultado"])
        ):
            raise ValueError("Paginação/original do universo diverge")
        signature = canonical(page["resultado"])
        if signature in seen and page["resultado"]:
            raise ValueError("Universo repete página")
        seen.add(signature)
        total = current
        rows.extend(page["resultado"])
    if not pages or total != len(rows) or len(rows) > 20000:
        raise ValueError("Universo incompleto ou excede limite")
    purchase = body["query"]["idCompra"]
    if not purchase or any(r.get("idCompra") != purchase for r in rows):
        raise ValueError("Universo contém outra compra")
    return body["kind"], purchase, rows


def universe_from_rows(item_rows, result_rows, sources):
    """Deduplicar versões por identidade, jamais tratar cada versão como um item."""
    items = {r["idCompraItem"] for r in item_rows}
    if any(not uid for uid in items):
        raise ValueError("Item oficial sem identidade")
    latest = {}
    for raw in result_rows:
        _, key, rank, value = canonical_row("resultados_api", raw, {})
        old = latest.get(key)
        if old is None or rank > old[0]:
            latest[key] = rank, value, False
        elif rank == old[0] and (old[2] or canonical(old[1]) != canonical(value)):
            latest[key] = rank, value, True
    if any(v[2] for v in latest.values()):
        return {
            "status": "nao_confirmado",
            "motivo": "CONFLITO_RESULTADO_OFICIAL",
            "fontes": sources,
        }
    results = {uid: [] for uid in sorted(items)}
    for _, row, _ in latest.values():
        if row["item"] not in items:
            return {
                "status": "nao_confirmado",
                "motivo": "RESULTADO_FORA_UNIVERSO_ITENS",
                "fontes": sources,
            }
        if not row["cancelado"]:
            results[row["item"]].append([row["fornecedor"], row["sequencial_resultado"]])
    return {
        "status": "confirmado_no_snapshot",
        "itens": sorted(items),
        "resultados_ativos": {uid: sorted(keys) for uid, keys in results.items()},
        "fontes": sources,
    }


def official_universes(repo, cn, objects, base_id):
    files, imports, links = (
        repo.tables[n] for n in ("arquivos_coletados", "importacoes", "base_importacoes")
    )
    rows = (
        cn.execute(
            sa.select(files)
            .join(imports, imports.c.arquivo_id == files.c.id)
            .join(links, links.c.importacao_id == imports.c.id)
            .where(
                links.c.base_id == base_id,
                sa.or_(
                    files.c.modulo.startswith("api/itens_api/"),
                    files.c.modulo.startswith("api/resultados_api/"),
                ),
            )
        )
        .mappings()
        .all()
    )
    grouped = defaultdict(lambda: defaultdict(list))
    for artifact in rows:
        kind, purchase, records = envelope(objects, artifact)
        grouped[purchase][kind].append((artifact, records))
    result = {}
    for purchase, kinds in grouped.items():
        if set(kinds) != {"itens_api", "resultados_api"} or any(
            len(v) != 1 for v in kinds.values()
        ):
            result[purchase] = {
                "status": "nao_confirmado",
                "motivo": "FONTES_UNIVERSO_AUSENTES_OU_AMBIGUAS",
                "fontes": [],
            }
            continue
        sources = [
            {
                "arquivo_id": str(a["id"]),
                "chave": a["chave_objeto"],
                "sha256": a["sha256"],
                "coletado_em": str(a["coletado_em"]),
            }
            for entries in kinds.values()
            for a, _ in entries
        ]
        result[purchase] = universe_from_rows(
            kinds["itens_api"][0][1],
            kinds["resultados_api"][0][1],
            sorted(sources, key=lambda r: r["arquivo_id"]),
        )
    return result
