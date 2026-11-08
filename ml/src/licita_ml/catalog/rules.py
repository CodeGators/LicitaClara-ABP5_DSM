"""Agrupar diferenças de formato preservando todos os atributos e a embalagem."""

import re
import unicodedata
from decimal import Decimal
from functools import lru_cache

from licita_ml.analytical.rules import digest
from licita_ml.units import ALIASES as UNIT_ALIASES
from licita_ml.units import FACTORS, measurement

VERSION = "catalogo-itens-v2"
ALIASES = {
    "un": "un",
    "unidade": "un",
    "unidades": "un",
    "cx": "cx",
    "caixa": "cx",
    "kg": "kg",
    "quilograma": "kg",
    "g": "g",
    "grama": "g",
    "l": "l",
    "litro": "l",
    "ml": "ml",
    "mililitro": "ml",
    "m": "m",
    "metro": "m",
    "m 2": "m2",
    "m 3": "m3",
}
ALIASES.update(UNIT_ALIASES)
SIMPLE_UNITS = set(FACTORS)
LABEL = re.compile(r"(?:^|[,;|])\s*([a-z][a-z0-9 /()_-]{0,80}?)\s*:")


@lru_cache(maxsize=32768)
def _text(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", value)
    value = re.sub(r"\s*/\s*", "/", value)
    return re.sub(r"\s+", " ", value).strip()


def text(value):
    return _text(str(value or ""))


def description(detail, catalog_description=None):
    """Ordenar atributos nomeados; texto livre e qualificadores não são descartados."""
    detail = text(detail)
    if not detail:
        return None
    title = text(catalog_description)
    comma, colon = title.find(","), title.find(":")
    if comma >= 0 and (colon < 0 or comma < colon):
        title = title[:comma].strip()
    elif colon >= 0 or len(title.split()) > 8:
        title = ""
    # Nome do produto separado dos atributos apenas quando fornecido explicitamente.
    rest = detail
    prefix = ""
    if (
        title
        and detail.startswith(title)
        and (len(detail) == len(title) or detail[len(title)] in " ,;|")
    ):
        candidate = detail[len(title) :].lstrip(" ,;|")
        if LABEL.match(candidate):
            prefix, rest = title, candidate
    matches = list(LABEL.finditer(rest))
    if not matches:
        return {"modo": "texto_preservado", "texto": detail}
    prefix = prefix or rest[: matches[0].start()].strip(" ,;|")
    attributes = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(rest)
        value = rest[match.end() : end].strip(" ,;|")
        attributes.append((text(match.group(1)), value))
    if any(not value for _, value in attributes):
        return {"modo": "texto_preservado", "texto": detail}
    return {"modo": "atributos_nomeados", "produto": prefix, "atributos": sorted(attributes)}


def grouping(row):
    code = row.get("catalogo")
    if not code or re.fullmatch(r"[0-9]+", code) is None or not code.strip("0"):
        return None, "CATALOGO_AUSENTE_OU_INVALIDO"
    detailed = row.get("descricao_detalhada")
    if not detailed or not str(detailed).strip():
        return None, "ESPECIFICACAO_DETALHADA_AUSENTE"
    raw_unit = text(row.get("unidade_fornecimento_sigla"))
    if not raw_unit:
        name = text(row.get("unidade_fornecimento_nome"))
        raw_unit = name if name in ALIASES else ""
    if not raw_unit:
        return None, "UNIDADE_FORNECIMENTO_AUSENTE"
    name = text(row.get("unidade_fornecimento_nome"))
    if name in ALIASES and raw_unit in ALIASES and ALIASES[name] != ALIASES[raw_unit]:
        return None, "UNIDADE_NOME_SIGLA_DIVERGENTES"
    unit = ALIASES.get(raw_unit, raw_unit)
    measure = text(row.get("unidade_medida_sigla"))
    measure = ALIASES.get(measure, measure)
    capacity = row.get("capacidade")
    if capacity is not None:
        capacity = Decimal(str(capacity))
        if not capacity.is_finite() or capacity < 0:
            return None, "CAPACIDADE_INVALIDA"
    if unit in SIMPLE_UNITS and capacity in (None, Decimal(0), Decimal(1)):
        if not measure or measure == unit:
            capacity, measure = Decimal(0), unit
        elif capacity in (None, Decimal(0)):
            capacity = Decimal(0)
    elif capacity is None or capacity <= 0:
        return None, "CAPACIDADE_EMBALAGEM_AUSENTE"
    physical, reason = measurement(unit, capacity, measure)
    if reason:
        return None, reason
    spec = {
        "tipo_catalogo": "CATMAT",
        "unidade_preco": physical,
        "catalogo": code,
        "unidade": unit,
        "capacidade": format(capacity.normalize(), "f"),
        "medida": measure,
        "especificacao": description(detailed, row.get("descricao")),
        "especificacao_catalogo": description(row.get("descricao"), row.get("descricao")),
    }
    spec = refine_spec(spec)
    return {"id": digest([VERSION, spec]), "especificacao": spec}, None


@lru_cache(maxsize=4096)
def _catalog_patterns(signature):
    import json

    value = json.loads(signature)
    attributes = value.get("atributos", [])
    if not attributes or len({k for k, _ in attributes}) != len(attributes):
        return None
    product = value.get("produto", "")
    prefix = re.compile(r"^" + re.escape(product) + r"(?=$|[ ,;|])") if product else None
    patterns = []
    for key, expected in attributes:
        label = r"\s*".join(re.escape(word) for word in key.split())
        expected = re.escape(expected).replace(r"\ ", r"\s+")
        patterns.append(re.compile(r"^" + label + r"\s*:?\s*" + expected + r"(?=$|[,;|])"))
    return prefix, tuple(patterns)


def refine_spec(spec):
    """Reconhecer cópia literal dos atributos conhecidos sem inventar valores."""
    import copy
    import json

    detail, catalog = spec["especificacao"], spec["especificacao_catalogo"]
    if (
        not detail
        or not catalog
        or detail["modo"] != "texto_preservado"
        or catalog["modo"] != "atributos_nomeados"
    ):
        return spec
    compiled = _catalog_patterns(json.dumps(catalog, sort_keys=True, ensure_ascii=False))
    if compiled is None:
        return spec
    prefix, patterns = compiled
    rest = detail["texto"]
    if prefix:
        match = prefix.match(rest)
        if match is None:
            return spec
        rest = rest[match.end() :].lstrip(" ,;|")
    pending = list(patterns)
    while pending:
        for index, pattern in enumerate(pending):
            match = pattern.match(rest)
            if match:
                rest = rest[match.end() :].lstrip(" ,;|")
                pending.pop(index)
                break
        else:
            return spec
    if rest:
        return spec
    return {**spec, "especificacao": copy.deepcopy(catalog)}
