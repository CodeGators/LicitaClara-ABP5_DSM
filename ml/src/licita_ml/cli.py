"""Preparação reproduzível; não executa treinamento nem migrações."""

import argparse
import json
from datetime import date
from importlib.metadata import version
from uuid import UUID

from licita_shared.storage.factory import storage
from sqlalchemy import create_engine

from licita_ml.config import Settings
from licita_ml.pipeline import Pipeline
from licita_ml.repository import Repository


def main():
    parser = argparse.ArgumentParser(description="Preparação e importação Licita Clara")
    parser.add_argument("--version", action="version", version=version("licita-ml"))
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("preparar")
    prepare.add_argument("--inicio", required=True, type=date.fromisoformat)
    prepare.add_argument("--fim", required=True, type=date.fromisoformat)
    prepare.add_argument("--catalogo", required=True)
    prepare.add_argument("--arquivos", nargs="+", type=UUID)
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings()
        engine = create_engine(
            settings.processing_database_url.get_secret_value(),
            pool_size=1,
            max_overflow=0,
            hide_parameters=True,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        result = Pipeline(settings, Repository(engine), storage(settings)).run(
            args.inicio, args.fim, args.catalogo, args.arquivos
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "falhou",
                    "codigo": getattr(error, "code", "FALHA_PREPARACAO"),
                    "diagnostico": getattr(error, "diagnostic", None),
                    "tipo": type(error).__name__,
                }
            ),
            flush=True,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
