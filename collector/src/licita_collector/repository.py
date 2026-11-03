"""Contrato físico refletido do banco migrado; não importa a aplicação HTTP nem duplica modelos."""

import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from licita_collector.errors import Busy, CollectionError
from licita_collector.source import Scope


class Repository:
    def __init__(self, engine):
        self.engine = engine
        metadata = sa.MetaData()
        self.runs, self.files, self.links = [
            sa.Table(name, metadata, autoload_with=engine, resolve_fks=False)
            for name in ("execucoes_coleta", "arquivos_coletados", "execucoes_arquivos")
        ]

    @contextmanager
    def locked(self, scope):
        value = f"{scope.source}/{scope.module}/{scope.competence.isoformat()}"
        key = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)
        with self.engine.connect() as connection:
            acquired = connection.scalar(sa.text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            connection.commit()
            if not acquired:
                raise Busy("Já há coleta ativa para este arquivo e competência")
            try:
                yield connection
            finally:
                try:
                    connection.rollback()
                    connection.execute(sa.text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                    connection.commit()
                except Exception:
                    connection.invalidate()

    def start(self, connection, scope, run_id=None):
        with connection.begin():
            if run_id is not None:
                row = (
                    connection.execute(sa.select(self.runs).where(self.runs.c.id == run_id))
                    .mappings()
                    .one()
                )
                if (
                    row["fonte"] != scope.source
                    or row["modulo"] != scope.module
                    or row["competencia_inicio"] != scope.competence
                    or row["competencia_fim"] != scope.competence
                ):
                    raise CollectionError("Execução não corresponde ao escopo solicitado")
                if row["status"] == "concluido":
                    return run_id, True
                connection.execute(
                    self.runs.update()
                    .where(self.runs.c.id == run_id)
                    .values(status="executando", concluido_em=None, erro=None)
                )
                return run_id, False
            value = connection.execute(
                self.runs.insert()
                .values(
                    fonte=scope.source,
                    modulo=scope.module,
                    competencia_inicio=scope.competence,
                    competencia_fim=scope.competence,
                    status="executando",
                    iniciado_em=datetime.now(timezone.utc),
                    parametros=scope.parameters,
                )
                .returning(self.runs.c.id)
            ).scalar_one()
            return value, False

    def complete(self, connection, run_id, scope, url, download, info, key):
        with connection.begin():
            identifier = connection.execute(
                insert(self.files)
                .values(
                    fonte=scope.source,
                    modulo=scope.module,
                    competencia=scope.competence,
                    url_origem=url,
                    url_final=download.url_final,
                    sha256=info["sha256"],
                    tamanho_bytes=info["bytes"],
                    chave_objeto=key,
                    etag=download.etag,
                )
                .on_conflict_do_nothing()
                .returning(self.files.c.id)
            ).scalar_one_or_none()
            reused = identifier is None
            if identifier is None:
                row = (
                    connection.execute(
                        sa.select(self.files).where(
                            self.files.c.fonte == scope.source,
                            self.files.c.modulo == scope.module,
                            self.files.c.competencia == scope.competence,
                            self.files.c.sha256 == info["sha256"],
                        )
                    )
                    .mappings()
                    .one()
                )
                identifier = row["id"]
                if row["chave_objeto"] != key:
                    raise CollectionError(
                        "Conteúdo conhecido possui chave de armazenamento diferente"
                    )
            connection.execute(
                insert(self.links)
                .values(execucao_id=run_id, arquivo_id=identifier)
                .on_conflict_do_nothing()
            )
            connection.execute(
                self.runs.update()
                .where(self.runs.c.id == run_id)
                .values(status="concluido", concluido_em=datetime.now(timezone.utc), erro=None)
            )
        return identifier, reused

    def fail(self, connection, run_id, error):
        connection.rollback()
        with connection.begin():
            connection.execute(
                self.runs.update()
                .where(self.runs.c.id == run_id)
                .values(
                    status="falhou",
                    concluido_em=datetime.now(timezone.utc),
                    erro=f"{getattr(error, 'code', 'FALHA_INTERNA')}: {type(error).__name__}",
                )
            )

    def execution(self, run_id):
        with self.engine.connect() as connection:
            row = (
                connection.execute(sa.select(self.runs).where(self.runs.c.id == UUID(str(run_id))))
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise CollectionError("Execução não encontrada")
            if row["parametros"].get("connector") == "json-v1":
                from licita_collector.api import JsonScope

                return JsonScope(
                    row["parametros"]["kind"], row["competencia_inicio"], row["parametros"]["query"]
                )
            module, kind = row["modulo"].split("/", 1)
            scope = Scope(kind, row["competencia_inicio"])
            if row["fonte"] != scope.source or module != scope.module.split("/")[0]:
                raise CollectionError("Execução pertence a outro conector")
            return scope

    def artifact(self, identifier=None, run_id=None):
        query = sa.select(self.files)
        if run_id is not None:
            query = query.join(self.links, self.files.c.id == self.links.c.arquivo_id).where(
                self.links.c.execucao_id == run_id
            )
        else:
            query = query.where(self.files.c.id == UUID(str(identifier)))
        with self.engine.connect() as connection:
            row = connection.execute(query).mappings().one_or_none()
            if row is None:
                raise CollectionError("Arquivo registrado não encontrado")
            return dict(row)
