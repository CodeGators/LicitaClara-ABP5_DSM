"""Preparação e avaliação reproduzíveis; não executa migrações ou publica scores."""

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
    attributes = commands.add_parser("atributos")
    attributes.add_argument("--base-id", required=True, type=UUID)
    attributes.add_argument("--historicos", required=True, nargs="+", type=UUID)
    attributes.add_argument("--inicio", required=True, type=date.fromisoformat)
    attributes.add_argument("--treino-fim", required=True, type=date.fromisoformat)
    attributes.add_argument("--fim", required=True, type=date.fromisoformat)
    attributes.add_argument("--exclusoes", required=True)
    validation = commands.add_parser("validar-if")
    validation.add_argument("--manifesto", required=True)
    validation.add_argument("--sha256", required=True)
    review = commands.add_parser("revisao-if")
    review.add_argument("--manifesto", required=True)
    review.add_argument("--sha256", required=True)
    review.add_argument("--grupo", required=True)
    review.add_argument("--treino", required=True)
    review.add_argument("--avaliacao", required=True)
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
        if args.command in {"validar-if", "revisao-if"}:
            from licita_ml.validation.pipeline import ValidationPipeline

            validation_pipeline = ValidationPipeline(storage(settings))
            if args.command == "validar-if":
                with Repository(engine).locked():
                    result = validation_pipeline.run(args.manifesto, args.sha256)
            else:
                result = validation_pipeline.review(
                    args.manifesto, args.sha256, args.grupo, args.treino, args.avaliacao
                )
        elif args.command == "atributos":
            from licita_ml.analytical.pipeline import AnalyticalPipeline
            from licita_ml.analytical.rules import Policy

            result = AnalyticalPipeline(settings, Repository(engine), storage(settings)).run(
                args.base_id,
                args.historicos,
                Policy(args.inicio, args.treino_fim, args.fim),
                args.exclusoes,
            )
        else:
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
