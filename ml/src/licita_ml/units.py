"""Unidades de preço: equivalência exata, sem inferir peso, volume ou embalagem."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation, localcontext

VERSION = "unidades-preco-v1"
ALIASES = {
    "un": "un",
    "und": "un",
    "unidade": "un",
    "unidades": "un",
    "kg": "kg",
    "kgs": "kg",
    "quilograma": "kg",
    "quilogramas": "kg",
    "g": "g",
    "gr": "g",
    "grama": "g",
    "gramas": "g",
    "mg": "mg",
    "miligrama": "mg",
    "miligramas": "mg",
    "t": "t",
    "tonelada": "t",
    "toneladas": "t",
    "l": "l",
    "lt": "l",
    "litro": "l",
    "litros": "l",
    "ml": "ml",
    "mililitro": "ml",
    "mililitros": "ml",
    "m": "m",
    "metro": "m",
    "metros": "m",
    "cm": "cm",
    "centimetro": "cm",
    "mm": "mm",
    "milimetro": "mm",
    "km": "km",
    "quilometro": "km",
    "m 2": "m2",
    "m2": "m2",
    "metro quadrado": "m2",
    "m 3": "m3",
    "m3": "m3",
    "metro cubico": "m3",
    "par": "par",
    "pares": "par",
    "dose(s)": "dose",
    "dose": "dose",
    "doses": "dose",
    "cx": "cx",
    "caixa": "cx",
    "caixas": "cx",
    "pct": "pct",
    "pacote": "pct",
    "emb": "emb",
    "embalagem": "emb",
    "am": "am",
    "ampola": "am",
    "fr": "fr",
    "frasco": "fr",
    "fr-am": "fr-am",
    "frasco-ampola": "fr-am",
    "grf": "grf",
    "garrafa": "grf",
    "grr": "grr",
    "garrafao": "grr",
    "bis": "bis",
    "bisnaga": "bis",
    "rl": "rl",
    "ro": "rl",
    "rolo": "rl",
    "bj": "bj",
    "bandeja": "bj",
    "btj": "btj",
    "botijao": "btj",
    "tbte": "tbte",
    "tubete": "tbte",
    "ser": "ser",
    "seringa": "ser",
    "copo": "copo",
    "balde": "balde",
    "saco": "saco",
    "fardo": "fardo",
}
# Preserve commercially distinct units/groups even if their SI conversions are exact.
# These factors provide traceable informational prices, not a licence to merge packaging.
FACTORS = {
    "kg": ("massa", "kg", "1"),
    "g": ("massa", "kg", "0.001"),
    "mg": ("massa", "kg", "0.000001"),
    "t": ("massa", "kg", "1000"),
    "l": ("volume", "l", "1"),
    "ml": ("volume", "l", "0.001"),
    "m": ("comprimento", "m", "1"),
    "cm": ("comprimento", "m", "0.01"),
    "mm": ("comprimento", "m", "0.001"),
    "km": ("comprimento", "m", "1000"),
    "m2": ("area", "m2", "1"),
    "m3": ("volume_espacial", "m3", "1"),
    "un": ("contagem", "un", "1"),
    "par": ("pares", "par", "1"),
    "dose": ("doses", "dose", "1"),
}
PACKAGES = set(ALIASES.values()) - set(FACTORS)


def text(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip()


def unit(value):
    raw = text(value)
    return ALIASES.get(raw, raw)


def decimal(value):
    try:
        value = Decimal(str(value))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def measurement(supply, capacity=None, measure=None):
    supply, measure = unit(supply), unit(measure)
    amount = decimal(capacity) if capacity is not None else None
    if supply not in FACTORS and supply not in PACKAGES:
        return None, "UNIDADE_FORNECIMENTO_NAO_RECONHECIDA"
    if capacity is not None and (amount is None or amount < 0):
        return None, "CAPACIDADE_INVALIDA"
    if (
        supply in FACTORS
        and amount in (None, Decimal(0), Decimal(1))
        and not (supply == "un" and amount == 1 and measure and measure != "un")
    ):
        if measure and measure != supply:
            return None, "UNIDADE_MEDIDA_CONTRADITORIA"
        measure, amount, packed = supply, Decimal(1), False
    else:
        if amount is None or amount <= 0:
            return None, "CAPACIDADE_EMBALAGEM_AUSENTE"
        if measure not in FACTORS:
            return None, "MEDIDA_EMBALAGEM_AUSENTE_OU_NAO_RECONHECIDA"
        if supply in FACTORS and supply != "un" and FACTORS[supply][0] != FACTORS[measure][0]:
            return None, "UNIDADE_MEDIDA_CONTRADITORIA"
        packed = True
    dimension, canonical, factor = FACTORS[measure]
    with localcontext() as ctx:
        ctx.prec = 60
        factor = amount * Decimal(factor)
    price_unit = f"{supply} de {amount.normalize():f} {measure}" if packed else supply
    return {
        "versao": VERSION,
        "unidade_preco": price_unit,
        "fornecimento": supply,
        "embalagem": packed,
        "capacidade": format(amount.normalize(), "f"),
        "medida": measure,
        "dimensao": dimension,
        "unidade_base": canonical,
        "fator_base": format(factor.normalize(), "f"),
    }, None


def exact_values(price, quantity, info):
    """Preço por unidade-base e quantidade-base; nunca misturar massa e volume."""
    price, quantity = decimal(price), decimal(quantity)
    if price is None or quantity is None or price <= 0 or quantity <= 0:
        return None
    factor = Decimal(info["fator_base"])
    with localcontext() as ctx:
        ctx.prec = 60
        return {
            "preco_por_unidade_base": format(price / factor, "f"),
            "quantidade_base": format(quantity * factor, "f"),
            "unidade_base": info["unidade_base"],
        }


def operational_matches(observed, info):
    """Rótulo genérico de caixa/pacote não prova seu conteúdo, mesmo com preço igual."""
    label = text(observed)
    if not info["embalagem"]:
        if unit(label) == info["fornecimento"]:
            return True
    # Accept explicit capacity, including decimal comma and no space (e.g. Ampola 2ML).
    label = re.sub(r"(?<=\d)(?=[a-z])", " ", label)
    match = re.fullmatch(r"([a-z -]+?)\s+(?:com\s+)?(\d+(?:[.,]\d+)?)\s+(.+)", label)
    if not match:
        return False
    supply, capacity, measure = match.groups()
    capacity = Decimal(capacity.replace(",", "."))
    if not info["embalagem"]:
        return unit(supply) == unit(measure) == info["fornecimento"] and capacity == 1
    observed, reason = measurement(unit(supply), capacity, unit(measure))
    return (
        not reason
        and unit(supply) == info["fornecimento"]
        and observed["dimensao"] == info["dimensao"]
        and Decimal(observed["fator_base"]) == Decimal(info["fator_base"])
    )
