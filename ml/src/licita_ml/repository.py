"""Reflete o contrato migrado sem importar a aplicação FastAPI."""

from contextlib import contextmanager
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

TABLES = [
    "arquivos_coletados",
    "execucoes_arquivos",
    "importacoes",
    "versoes_base",
    "base_importacoes",
    "orgaos",
    "fornecedores",
    "modalidades",
    "itens_catalogo",
    "processos",
    "itens_processo",
    "processos_versoes",
    "itens_versoes",
    "resultados_itens",
    "referencias_precos",
    "participacoes",
    "contratos",
    "contratos_versoes",
    "contratos_processos",
    "documentos",
    "proveniencias_registros",
]


def identifier(table, key):
    return uuid5(NAMESPACE_URL, "licita-clara/" + table + "/" + str(key))


class Repository:
    def __init__(self, engine):
        self.engine = engine
        metadata = sa.MetaData()
        self.tables = {
            name: sa.Table(name, metadata, autoload_with=engine, resolve_fks=False)
            for name in TABLES
        }

    @contextmanager
    def locked(self):
        # Serializa publicação/importação e criação das identidades globais.
        with self.engine.connect() as connection:
            if not connection.scalar(sa.text("SELECT pg_try_advisory_lock(582701005)")):
                raise ValueError("Já há uma preparação ativa")
            connection.commit()
            try:
                yield connection
            finally:
                try:
                    connection.rollback()
                    connection.execute(sa.text("SELECT pg_advisory_unlock(582701005)"))
                    connection.commit()
                except Exception:
                    connection.invalidate()

    def sources(self, connection, start, end, ids=None):
        files, links = self.tables["arquivos_coletados"], self.tables["execucoes_arquivos"]
        if ids:
            rows = connection.execute(sa.select(files).where(files.c.id.in_(ids))).mappings().all()
            if len(rows) != len(set(ids)):
                raise ValueError("Arquivo solicitado não encontrado")
            return sorted(
                [dict(r) for r in rows],
                key=lambda r: (r["fonte"], r["modulo"], str(r["competencia"]), str(r["id"])),
            )
        observed = (
            sa.select(links.c.arquivo_id, sa.func.max(links.c.observado_em).label("last"))
            .group_by(links.c.arquivo_id)
            .subquery()
        )
        rows = connection.execute(
            sa.select(files, observed.c.last)
            .join(observed, files.c.id == observed.c.arquivo_id)
            .where(
                files.c.competencia >= start.replace(day=1),
                files.c.competencia <= end.replace(day=1),
            )
            .order_by(files.c.fonte, files.c.modulo, files.c.competencia, observed.c.last.desc())
        ).mappings()
        result, seen = [], {}
        for row in rows:
            key = (row["fonte"], row["modulo"], row["competencia"])
            if key in seen:
                if seen[key] == row["last"]:
                    raise ValueError(
                        "Versões com o mesmo instante de observação; informe IDs explícitos"
                    )
                continue
            seen[key] = row["last"]
            result.append({k: v for k, v in row.items() if k != "last"})
        return result

    def batch(self, connection, name, rows, size=500):
        table = self.tables[name]
        for offset in range(0, len(rows), size):
            # Preenchimento uniforme para impedir descarte de colunas opcionais em executemany.
            chunk = rows[offset : offset + size]
            keys = set().union(*(row.keys() for row in chunk))
            connection.execute(
                insert(table).on_conflict_do_nothing(),
                [{key: row.get(key) for key in keys} for row in chunk],
            )

    def sizes(self, connection):
        return {
            name: connection.scalar(sa.text("SELECT pg_total_relation_size(:name)"), {"name": name})
            for name in TABLES
            if name not in ("arquivos_coletados", "execucoes_arquivos")
        }
