"""Preparar e treinar grupos do catálogo integral."""

import argparse
import json
import logging
from pathlib import Path

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
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.command == "preparar":
        result = temporal.prepare(args.base, args.catalogo, args.saida, args.grupos_por_lote)
    else:
        result = training.run(args.preparacao, args.saida, args.revisoes, args.processos)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
