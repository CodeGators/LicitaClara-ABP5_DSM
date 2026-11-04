"""Gera base organizada local a partir dos ZIPs, sem acessar rede ou banco."""

import argparse
import json
from pathlib import Path

from licita_ml.organized.pipeline import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrada",
        type=Path,
        nargs="+",
        required=True,
        help="Pastas AAAA-MM com os quatro módulos mensais",
    )
    parser.add_argument(
        "--historico",
        type=Path,
        nargs="*",
        default=[],
        help="ZIPs adicionais, por exemplo material de meses anteriores",
    )
    parser.add_argument("--saida", type=Path, default=Path("data/organizados"))
    args = parser.parse_args()
    result = prepare(args.entrada, args.saida, args.historico)
    print(
        json.dumps(
            {
                "diretorio": result["diretorio"],
                "reutilizada": result["reutilizada"],
                "tabelas": result["manifesto"]["tabelas"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
