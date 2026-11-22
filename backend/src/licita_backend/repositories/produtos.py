"""Preços unitários da base operacional, agrupados sem misturar embalagens."""

import json
import re
from collections import defaultdict
from decimal import Decimal, localcontext
from hashlib import sha256

from licita_backend.repositories.visao import ViewRepository, amounts, wire


def product_signal(product):
    if product["requer_validacao"]:
        return "requer_validacao"
    measure = product["medida_if"]
    if measure is None or not measure.is_finite() or not Decimal(0) <= measure <= Decimal(1):
        return "sem_analise"
    if measure >= Decimal("0.70"):
        return "maior_anomalia"
    if measure >= Decimal("0.50"):
        return "anomalia_intermediaria"
    return "menor_anomalia"


def normalized(value):
    return " ".join(str(value or "").casefold().split())


def specification(item):
    detail = normalized(item["descricao"])
    title = normalized(item.get("descricao_catalogo")).split(",", 1)[0].strip()
    if (
        not title
        or ":" in title
        or not detail.startswith(title)
        or (len(detail) > len(title) and detail[len(title)] not in " ,;|")
    ):
        return detail
    rest = detail[len(title) :].lstrip(" ,;|")
    matches = list(re.finditer(r"(?:^|[,;|])\s*([^,:;|]+?)\s*:", rest))
    if not matches or rest[: matches[0].start()].strip():
        return detail
    attributes = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(rest)
        value = rest[match.end() : end].strip(" ,;|")
        if not value:
            return detail
        attributes.append((match.group(1).strip(), value))
    # Only the order of explicitly labelled attributes changes; no specifications are dropped.
    return json.dumps([title, sorted(attributes)], ensure_ascii=False)


def group_products(items):
    groups = defaultdict(list)
    for item in items:
        key = (
            normalized(item.get("catalogo")),
            normalized(item.get("codigo_catalogo")),
            specification(item),
            normalized(item.get("unidade_medida")),
        )
        # Unknown catalogue/unit cannot establish equivalence across purchases.
        if not all(key):
            key = (*key, str(item["id"]))
        groups[key].append(item)
    output = []
    for key, members in sorted(groups.items()):
        members = sorted(members, key=lambda r: str(r["id"]))
        sample = members[0]
        # A winning result is one observation, irrespective of the quantity bought.
        events = {
            str(e["id"]): e for row in members for e in row["resultados"] if not e["cancelado"]
        }
        prices = sorted(
            e["valor_unitario_homologado"]
            for e in events.values()
            if e["valor_unitario_homologado"] is not None
        )
        with localcontext() as ctx:
            ctx.prec = 60
            n = len(prices)
            median = ((prices[(n - 1) // 2] + prices[n // 2]) / 2) if n else None
            review = bool(median is not None and median > 0 and prices[-1] > 6 * median)
        analyzed = sum(r["status_analise"] == "analisados" for r in members)
        status = (
            "analisados"
            if analyzed == len(members)
            else "nao_analisados"
            if all(r["status_analise"] == "nao_analisados" for r in members)
            else "parcial"
        )
        output.append(
            {
                "id": sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest(),
                "descricao": sample["descricao"],
                "catalogo": sample.get("catalogo"),
                "codigo_catalogo": sample.get("codigo_catalogo"),
                "unidade_medida": sample.get("unidade_medida"),
                "preco_minimo": prices[0] if prices else None,
                "preco_maximo": prices[-1] if prices else None,
                "mediana": median,
                "quantidade_registros": len(prices),
                "registros_sem_preco": len(events) - len(prices),
                "requer_validacao": review,
                "status_analise": status,
                "medida_if": max(
                    (r["medida_if"] for r in members if r["medida_if"] is not None), default=None
                ),
                **amounts(list(events.values())),
                "itens": [
                    {
                        "id": r["id"],
                        "numero_item": r["numero_item"],
                        "numero_compra": r["processo"]["numero_compra"],
                    }
                    for r in members
                ],
            }
        )
    return output


class ProductRepository(ViewRepository):
    def product_page(self, rows, filters):
        if filters.ordenacao == "descricao_asc":
            rows.sort(key=lambda r: (normalized(r["descricao"]), r["id"]))
        else:
            key = "mediana" if filters.ordenacao == "valor_desc" else "preco_maximo"
            rows.sort(key=lambda r: (r[key] is None, (r[key] or Decimal(0)).copy_negate(), r["id"]))
        start = (filters.pagina - 1) * filters.tamanho_pagina
        return {
            "dados": rows[start : start + filters.tamanho_pagina],
            "pagina": filters.pagina,
            "tamanho_pagina": filters.tamanho_pagina,
            "total": len(rows),
            "total_paginas": (len(rows) + filters.tamanho_pagina - 1) // filters.tamanho_pagina,
        }

    def listing(self, filters):
        # Search/analysis filter selects whole products, never truncates their prices.
        context, items, _, _ = self.dataset(
            filters.model_copy(update={"busca": None, "analise": "todos"})
        )
        rows = group_products(items)
        if filters.busca and (search := normalized(filters.busca)):
            rows = [
                r
                for r in rows
                if search in normalized(r["descricao"] + " " + str(r["codigo_catalogo"] or ""))
            ]
        for row in rows:
            row["sinalizacao"] = product_signal(row)
        if filters.sinalizacao:
            selected = set(filters.sinalizacao)
            rows = [r for r in rows if r["sinalizacao"] in selected]
        return wire(
            {
                **context,
                "universo": {
                    **context["universo"],
                    "estatisticas": "precos_unitarios_da_base_atual",
                    "agrupamento": "catalogo_especificacao_unidade_embalagem",
                    "mediana": "nao_ponderada_por_quantidade; inclui precos extremos",
                },
                **self.product_page(rows, filters),
            }
        )
