"""Preparação e avaliação reproduzíveis; não executa migrações ou publica scores."""

import argparse
import json
from datetime import date
from importlib.metadata import version
from pathlib import Path
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
    comparison = commands.add_parser("comparar-modelos")
    comparison.add_argument("--manifesto-if", required=True)
    comparison.add_argument("--sha256-if", required=True)
    comparison_review = commands.add_parser("revisao-comparacao")
    comparison_review.add_argument("--manifesto", required=True)
    comparison_review.add_argument("--sha256", required=True)
    comparison_review.add_argument("--grupo", required=True)
    comparison_review.add_argument("--treino", required=True)
    comparison_review.add_argument("--avaliacao", required=True)
    inference = commands.add_parser("inferir")
    inference.add_argument("--comparacao", required=True)
    inference.add_argument("--sha256-comparacao", required=True)
    inference.add_argument("--atributos", required=True)
    inference.add_argument("--sha256-atributos", required=True)
    temporal = commands.add_parser("inferir-temporal")
    temporal.add_argument("--treino", required=True, type=Path)
    temporal.add_argument("--sha256-treino", required=True)
    temporal.add_argument("--dataset", required=True, type=Path)
    temporal.add_argument("--base-id", type=UUID)
    temporal.add_argument("--resultado-ate", type=date.fromisoformat)
    process = commands.add_parser("sintetizar-processos")
    process.add_argument("--execucao-origem", required=True, type=UUID)
    publish = commands.add_parser("publicar-experimental")
    publish.add_argument("--execucao", required=True, type=UUID)
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings()
        if args.command == "inferir-temporal" and args.base_id is None:
            from licita_ml.inference.temporal import infer_references

            result = infer_references(
                args.treino, args.dataset, args.sha256_treino, storage(settings), args.resultado_ate
            )
            print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
            return 0
        engine = create_engine(
            settings.processing_database_url.get_secret_value(),
            pool_size=1,
            max_overflow=0,
            hide_parameters=True,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        if args.command == "sintetizar-processos":
            from licita_ml.inference.pipeline import InferencePipeline
            from licita_ml.inference.processes import run

            result = run(
                InferencePipeline(settings, Repository(engine), storage(settings)),
                args.execucao_origem,
            )
        elif args.command == "inferir-temporal":
            from licita_ml.inference.pipeline import InferencePipeline
            from licita_ml.inference.temporal import infer_sql

            result = infer_sql(
                InferencePipeline(settings, Repository(engine), storage(settings)),
                args.treino,
                args.dataset,
                args.sha256_treino,
                args.base_id,
                result_end=args.resultado_ate,
            )
        elif args.command in {"inferir", "publicar-experimental"}:
            from licita_ml.inference.pipeline import InferencePipeline

            inference_pipeline = InferencePipeline(settings, Repository(engine), storage(settings))
            if args.command == "inferir":
                result = inference_pipeline.run(
                    args.comparacao, args.sha256_comparacao, args.atributos, args.sha256_atributos
                )
            else:
                result = inference_pipeline.publish(args.execucao)
        elif args.command in {"comparar-modelos", "revisao-comparacao"}:
            from licita_ml.comparison.pipeline import ComparisonPipeline

            comparison_pipeline = ComparisonPipeline(storage(settings))
            if args.command == "comparar-modelos":
                with Repository(engine).locked():
                    result = comparison_pipeline.run(args.manifesto_if, args.sha256_if)
            else:
                result = comparison_pipeline.review(
                    args.manifesto, args.sha256, args.grupo, args.treino, args.avaliacao
                )
        elif args.command in {"validar-if", "revisao-if"}:
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
