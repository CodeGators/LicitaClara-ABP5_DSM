"""Preparar e treinar grupos do catálogo integral."""

import argparse
import json
import logging
from datetime import date
from pathlib import Path
from uuid import UUID

from licita_ml.grouped import temporal, training


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("preparar")
    prep.add_argument("--base", type=Path, required=True)
    prep.add_argument("--catalogo", type=Path, required=True)
    prep.add_argument("--saida", type=Path, default=Path("data/temporal_agrupado"))
    prep.add_argument("--grupos-por-lote", type=int, default=20)
    fit = commands.add_parser("treinar")
    fit.add_argument("--preparacao", type=Path, required=True)
    fit.add_argument("--saida", type=Path, default=Path("data/treino_agrupado"))
    fit.add_argument("--revisoes", type=Path, default=Path("data/revisoes_agrupadas"))
    fit.add_argument("--processos", type=int, default=2)
    imp = commands.add_parser("importar")
    imp.add_argument("--preparacao", type=Path, required=True)
    imp.add_argument("--arquivos", type=UUID, nargs="+")
    imp.add_argument("--preservar-base", type=UUID)
    infer = commands.add_parser("inferir")
    infer.add_argument("--treino", type=Path, required=True)
    infer.add_argument("--base-id", type=UUID, required=True)
    infer.add_argument("--resultado-ate", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.command == "preparar":
        result = temporal.prepare(args.base, args.catalogo, args.saida, args.grupos_por_lote)
    elif args.command == "treinar":
        result = training.run(args.preparacao, args.saida, args.revisoes, args.processos)
    else:
        from licita_shared.storage.factory import storage
        from sqlalchemy import create_engine

        from licita_ml.config import Settings
        from licita_ml.grouped import inference, operational
        from licita_ml.inference.pipeline import InferencePipeline
        from licita_ml.repository import Repository

        settings = Settings()
        engine = create_engine(
            settings.processing_database_url.get_secret_value(), hide_parameters=True
        )
        try:
            repo, objects = Repository(engine), storage(settings)
            if args.command == "importar":
                result = operational.run(
                    args.preparacao,
                    settings,
                    repo,
                    objects,
                    args.arquivos,
                    preserve_base_id=args.preservar_base,
                )
            else:
                result = inference.infer(
                    InferencePipeline(settings, repo, objects),
                    args.treino,
                    args.base_id,
                    args.resultado_ate,
                )
        finally:
            engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
