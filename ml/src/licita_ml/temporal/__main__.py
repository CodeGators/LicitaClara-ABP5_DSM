"""Prepara matrizes temporais a partir de uma base organizada local."""

import argparse
import json
from datetime import date
from pathlib import Path

from licita_ml.resources import RESOURCE_DIR
from licita_ml.temporal.pipeline import prepare
from licita_ml.temporal.rules import TemporalPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--saida", type=Path, default=Path("data/atributos_temporais"))
    parser.add_argument("--exclusoes", type=Path, default=RESOURCE_DIR / "exclusoes_v1.json")
    for name, default in (
        ("treino-inicio", "2025-10-01"),
        ("treino-fim", "2025-12-31"),
        ("avaliacao-inicio", "2026-07-01"),
        ("avaliacao-fim", "2026-08-31"),
        ("aplicacao-inicio", "2026-09-01"),
        ("aplicacao-fim", "2026-09-30"),
    ):
        parser.add_argument(
            f"--{name}", type=date.fromisoformat, default=date.fromisoformat(default)
        )
    args = parser.parse_args()
    policy = TemporalPolicy(
        args.treino_inicio,
        args.treino_fim,
        args.avaliacao_inicio,
        args.avaliacao_fim,
        args.aplicacao_inicio,
        args.aplicacao_fim,
    )
    result = prepare(args.base, args.saida, policy, args.exclusoes)
    manifest = result["manifesto"]
    print(
        json.dumps(
            {
                "diretorio": result["diretorio"],
                "reutilizada": result["reutilizada"],
                "status": manifest["status"],
                "grupos_elegiveis": manifest["grupos_elegiveis"],
                "tabelas": manifest["tabelas"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
