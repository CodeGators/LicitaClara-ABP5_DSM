"""Conexão lazy e sessões com fechamento/rollback garantidos."""

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from licita_backend.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_connect_timeout,
        connect_args={
            "connect_timeout": settings.db_connect_timeout,
            "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
        },
        hide_parameters=True,
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    # Fechar sem commit implícito desfaz transações pendentes.
    with request.app.state.sessions() as session:
        yield session


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Usar dentro do serviço: commit no sucesso, rollback em qualquer exceção."""
    with factory.begin() as session:
        yield session
