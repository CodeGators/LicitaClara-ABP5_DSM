"""Construção explícita de tabelas SQLAlchemy Core sobre a metadata compartilhada."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from licita_backend.models.base import Base

MONEY = sa.Numeric(28, 8)
SCORE = sa.Numeric(6, 3)


def table(name, domain, *columns):
    return sa.Table(name, Base.metadata, *columns, info={"domain": domain})


def pk():
    return sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def ref(name, target, nullable=False):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(f"{target}.id"), nullable=nullable)


def uid(name, nullable=False):
    return sa.Column(name, sa.Uuid(), nullable=nullable)


def text(name, nullable=False):
    return sa.Column(name, sa.Text(), nullable=nullable)


def timestamp(name="criado_em", nullable=False, now=True):
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if now else None,
    )


def json(name):
    return sa.Column(name, JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))


def choices(column, values):
    permitted = ", ".join(repr(value) for value in values)
    return sa.CheckConstraint(f"{column} IN ({permitted})", name=f"{column}_valido")


def check(expression, name):
    return sa.CheckConstraint(expression, name=name)


def unique(*columns):
    return sa.UniqueConstraint(*columns)


def base_fk(table_name, column, id_column="id"):
    return sa.ForeignKeyConstraint(
        [column, "base_id"], [f"{table_name}.{id_column}", f"{table_name}.base_id"]
    )
