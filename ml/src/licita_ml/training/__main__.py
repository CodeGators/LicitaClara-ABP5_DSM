"""Treina/compara sobre dataset temporal ou confere pareceres declarados."""

import argparse
import json
from pathlib import Path

from licita_ml.training.pipeline import prepare, review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("treinar")
    train.add_argument("--base", type=Path, required=True)
    train.add_argument("--saida", type=Path, default=Path("data/treinamento_temporal"))
    train.add_argument("--revisoes", type=Path, default=Path("data/revisoes_ml04"))
    check = commands.add_parser("revisar")
    check.add_argument("--execucao", type=Path, required=True)
    check.add_argument("--grupo", required=True)
    check.add_argument("--treino", type=Path, required=True)
    check.add_argument("--avaliacao", type=Path, required=True)
    check.add_argument("--natureza", choices=("interna", "independente_declarada"), required=True)
    args = parser.parse_args()
    if args.command == "treinar":
        result = prepare(args.base, args.saida, args.revisoes)
        manifest = result.pop("manifesto")
        result.update(
            status=manifest["status"],
            decisao_utilidade=manifest["decisao_utilidade"],
            grupos=[
                {
                    "grupo": g["grupo"],
                    "treino": g["treino"],
                    "avaliacao": g["avaliacao"],
                    "ajustes": g["total_ajustes"],
                    "revisao": g["revisao"],
                }
                for g in manifest["grupos"]
            ],
        )
    else:
        result = review(args.execucao, args.grupo, args.treino, args.avaliacao, args.natureza)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
