"""Catalogar todos os itens e referências de uma base organizada local."""

import argparse
import json
import logging
from pathlib import Path

from licita_ml.catalog.pipeline import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--saida", type=Path, default=Path("data/catalogo_itens"))
    parser.add_argument("--catalogo-anterior", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    result = prepare(args.base, args.saida, previous=args.catalogo_anterior)
    print(
        json.dumps(
            {
                "diretorio": result["diretorio"],
                "reutilizada": result["reutilizada"],
                "tabelas": result["manifesto"]["tabelas"],
                "grupos_reunidos": result["manifesto"]["grupos_com_reuniao_de_grupos_anteriores"],
                "candidatos_apenas_por_contagens": result["manifesto"][
                    "candidatos_apenas_por_contagens"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
