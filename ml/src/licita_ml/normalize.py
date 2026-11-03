"""Conversões explícitas, sem inferir números em identificadores nem completar unidades."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class RowError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def text(value, required=False):
    if value is None or str(value).strip() == "":
        if required:
            raise RowError("CAMPO_OBRIGATORIO_AUSENTE")
        return None
    return str(value).strip()


def money(value, positive=False):
    value = text(value)
    if value is None:
        return None
    try:
        result = Decimal(value)
        if (
            not result.is_finite()
            or result < 0
            or (positive and result == 0)
            or result >= Decimal("1e20")
            or result.as_tuple().exponent < -8
        ):
            raise RowError("VALOR_MONETARIO_INVALIDO")
        return result
    except InvalidOperation:
        raise RowError("VALOR_MONETARIO_INVALIDO") from None


def day(value, required=False):
    value = text(value, required)
    if value is None:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        raise RowError("DATA_INVALIDA") from None


def instant(value):
    value = text(value)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise RowError("DATA_HORA_INVALIDA") from None


def boolean(value):
    if value in (None, ""):
        return None
    if value is True or str(value).lower() in ("s", "true", "1"):
        return True
    if value is False or str(value).lower() in ("n", "false", "0"):
        return False
    raise RowError("BOOLEANO_INVALIDO")


def integer(value, required=False):
    value = text(value, required)
    if value is None:
        return None
    try:
        if not value.isdigit():
            raise ValueError()
        return int(value)
    except ValueError:
        raise RowError("INTEIRO_INVALIDO") from None
