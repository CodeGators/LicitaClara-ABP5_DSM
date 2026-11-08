"""Auditar todas as referências organizadas, sem alterar dados ou executar modelos."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from licita_ml.catalog.pipeline import records
from licita_ml.catalog.rules import grouping
from licita_ml.diagnostics import checksum
from licita_ml.units import VERSION, exact_values


def audit(base, output):
    base, output = Path(base), Path(output)
    combinations, reasons, examples, catalog_units = Counter(), Counter(), {}, defaultdict(set)
    total = 0
    columns = [
        "id_registro",
        "catalogo",
        "descricao",
        "descricao_detalhada",
        "unidade_fornecimento_sigla",
        "unidade_fornecimento_nome",
        "capacidade",
        "unidade_medida_sigla",
        "preco_unitario",
        "quantidade",
        "arquivo_sha256",
        "membro",
        "linha",
    ]
    for row in records(base, "referencias", columns):
        total += 1
        value, reason = grouping(row)
        info = value["especificacao"]["unidade_preco"] if value else None
        key = (
            row["unidade_fornecimento_sigla"],
            row["unidade_fornecimento_nome"],
            str(row["capacidade"]),
            row["unidade_medida_sigla"],
            reason,
        )
        combinations[key] += 1
        reasons[reason or "ESTRUTURA_COMPARAVEL"] += 1
        if info:
            catalog_units[row["catalogo"]].add(info["unidade_preco"])
        examples.setdefault(
            key,
            {
                "id_registro": row["id_registro"],
                "unidade_preco": info,
                "valores_base": exact_values(row["preco_unitario"], row["quantidade"], info)
                if info
                else None,
                "membro": row["membro"],
                "linha": row["linha"],
            },
        )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "unidades.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(
            ["sigla", "nome", "capacidade", "medida", "motivo", "linhas", "exemplo_json"]
        )
        for key, count in sorted(combinations.items(), key=lambda p: str(p[0])):
            writer.writerow([*key, count, json.dumps(examples[key], ensure_ascii=False)])
    report = {
        "versao": VERSION,
        "base_sha256": checksum(base / "manifesto.json"),
        "referencias": total,
        "combinacoes": len(combinations),
        "motivos": dict(reasons),
        "catalogos_com_unidades_distintas": {
            k: sorted(v) for k, v in sorted(catalog_units.items()) if len(v) > 1
        },
        "comparabilidade_documental": "nao_inferida_por_equivalencia_fisica",
        "dados_originais_alterados": False,
    }
    (output / "auditoria.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.base, args.saida)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "catalogos_com_unidades_distintas"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
