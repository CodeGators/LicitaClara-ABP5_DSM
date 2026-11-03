"""Ensaio offline/reproduzível, sem publicação na API ou tabelas de análise."""

import argparse
import csv
import hashlib
import json
import resource
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from licita_ml.experiments.data import (
    END,
    START,
    TRAIN_END,
    clean,
    history,
    split_groups,
)

DATA = Path("data/validacao_nucleo")
DOCS = Path("docs/validacao_nucleo")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False) + "\n"
    )


def profile_group(group):
    return {key: value for key, value in group.items() if key not in ("train", "test")} | {
        "n_train": len(group["train"]),
        "n_test": len(group["test"]),
        "compras_train": len({r["purchase"] for r in group["train"]}),
        "compras_test": len({r["purchase"] for r in group["test"]}),
        "orgaos_train": len({r["organ"] for r in group["train"] if r["organ"]}),
        "fornecedores_train": len({r["supplier_hash"] for r in group["train"]}),
    }


def review_files(group, result, rankings, ratios, bilateral, root):
    ids = [r["id"] for r in group["test"]]
    selected = set(result["baseline_sobrepreco"]) | set(result["baseline_bilateral"])
    for ranking in rankings.values():
        selected.update(ids[i] for i in ranking["indices"])
    # Controles determinísticos, sem escolhê-los por um rótulo desconhecido.
    controls = sorted([r["id"] for r in group["test"] if r["id"] not in selected])[:5]
    selected.update(controls)
    folder = root / "revisao"
    folder.mkdir(parents=True, exist_ok=True)
    sheet = folder / (group["id"] + "-revisao-cega.csv")
    fields = [
        "id",
        "id_compra",
        "id_item_fonte",
        "data_compra",
        "catalogo",
        "especificacao",
        "unidade",
        "capacidade",
        "medida",
        "preco_unitario",
        "quantidade",
        "parecer",
        "justificativa",
        "evidencia_url",
    ]
    if sheet.exists():
        with sheet.open(newline="") as existing:
            if any(
                row.get("parecer", "pendente") != "pendente"
                or row.get("justificativa")
                or row.get("evidencia_url")
                for row in csv.DictReader(existing)
            ):
                raise ValueError(
                    "Revisão já preenchida: use --saida diferente para preservar pareceres"
                )
    with sheet.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in sorted(group["test"], key=lambda r: r["id"]):
            if row["id"] in selected:
                writer.writerow(
                    dict(
                        id=row["id"],
                        id_compra=row["purchase"],
                        id_item_fonte=row["item"],
                        data_compra=str(row["date"]),
                        catalogo=row["catalog"],
                        especificacao=row["description"],
                        unidade=row["unit"],
                        capacidade=row["capacity"],
                        medida=row["measure"],
                        preco_unitario=str(row["price"]),
                        quantidade=str(row["quantity"]),
                        parecer="pendente",
                        justificativa="",
                        evidencia_url="",
                    )
                )
    # Este gabarito de procedência não é um gabarito de irregularidade.
    origin = {
        row["id"]: {
            "controle": row["id"] in controls,
            "baseline_sobrepreco": row["id"] in result["baseline_sobrepreco"],
            "baseline_bilateral": row["id"] in result["baseline_bilateral"],
            **{label: row["id"] in result["modelos"][label]["top_ids"] for label in rankings},
        }
        for row in group["test"]
        if row["id"] in selected
    }
    write_json(folder / (group["id"] + "-procedencia-reservada.json"), origin)
    rankings_file = folder / (group["id"] + "-ranking-experimental.csv")
    with rankings_file.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["id", "preco_mediana", "desvio_bilateral", "IF_preco", "IF_preco_quantidade"]
        )
        for i, row in enumerate(group["test"]):
            writer.writerow(
                [
                    row["id"],
                    float(ratios[i]),
                    float(bilateral[i]),
                    rankings["preco"]["scores"][i],
                    rankings["preco_quantidade"]["scores"][i],
                ]
            )
    return {
        "amostra": len(selected),
        "controles": len(controls),
        "planilha": str(sheet),
        "ranking_diagnostico": str(rankings_file),
        "pareceres_preenchidos": 0,
        "instrucao": (
            "Revisor não deve consultar ranking/procedência antes do parecer. "
            "Nada está rotulado como fraude."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--catalogos", nargs="+", default=["486054", "486374"])
    parser.add_argument("--saida", type=Path, default=DATA / "resultados")
    args = parser.parse_args()
    # Importar dependências opcionais somente quando este ensaio for executado.
    from licita_ml.experiments.evaluate import evaluate

    protocol = DOCS / "PROTOCOLO.md"
    code_files = sorted(Path(__file__).parent.glob("*.py"))
    code_sha = hashlib.sha256(
        b"".join(p.name.encode() + p.read_bytes() for p in code_files)
    ).hexdigest()
    report = {
        "protocolo": "v1",
        "sha256_protocolo": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "codigo_sha256": code_sha,
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "periodo": [str(START), str(END)],
        "treino_ate": str(TRAIN_END),
        "versoes": {name: version(name) for name in ["numpy", "scipy", "scikit-learn", "joblib"]},
        "coortes": [],
        "modelos": [],
        "revisao": [],
        "fraude_rotulada": False,
        "modelos_publicados_producao": False,
    }
    selection = DATA / "selecao_alternativa.json"
    if selection.exists():
        recorded_selection = json.loads(selection.read_text())
        report["selecao_alternativa"] = {
            "arquivo": str(selection),
            "sha256": hashlib.sha256(selection.read_bytes()).hexdigest(),
            "registro": {
                key: value for key, value in recorded_selection.items() if key != "candidatos"
            },
            "total_candidatos": len(recorded_selection["candidatos"]),
            "primeiros_candidatos": recorded_selection["candidatos"][:10],
        }
    for catalog in args.catalogos:
        raw, sources = history(catalog, DATA, args.offline)
        cleaned, reasons = clean(raw, catalog)
        groups = split_groups(cleaned)
        purchases = Counter(r["purchase"] for r in cleaned)
        profile = {
            "catalogo": catalog,
            "linhas_origem": len(raw),
            "linhas_apos_validacao": len(cleaned),
            "removidas": len(raw) - len(cleaned),
            "eventos_exclusao": reasons,
            "paginas": sources,
            "compras_distintas": len(purchases),
            "maior_compra_linhas": max(purchases.values(), default=0),
            "grupos": [profile_group(group) for group in groups],
            "grupos_elegiveis": sum(g["eligible"] for g in groups),
        }
        report["coortes"].append(profile)
        selected = [g for g in groups if g["eligible"]]
        if not selected:
            exploratory = sorted(
                [g for g in groups if g["exploratory"]],
                key=lambda g: (-len(g["test"]), -len(g["train"]), g["id"]),
            )
            selected = exploratory[:1]
        for group in selected:
            print(
                (
                    f"CATMAT {catalog}: {len(group['train'])} treino / {len(group['test'])} teste; "
                    f"principal={group['eligible']}"
                ),
                flush=True,
            )
            result, rankings, ratios, bilateral = evaluate(group, args.saida)
            result["catalogo"] = catalog
            report["modelos"].append(result)
            report["revisao"].append(
                review_files(group, result, rankings, ratios, bilateral, args.saida)
            )
    primary = [r for r in report["modelos"] if r["modo"] == "principal"]
    stable = [r for r in primary if r["modelos"]["preco_quantidade"]["estabilidade_aprovada"]]
    report["decisao"] = (
        "INCONCLUSIVO_POR_DADOS"
        if not primary
        else "NAO_APROVADO_ESTABILIDADE"
        if not stable
        else "VIAVEL_TECNICAMENTE_UTILIDADE_PENDENTE"
    )
    report["utilidade_real_comprovada"] = False
    report["validacao_humana_pendente"] = True
    report["memoria_pico_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    report["limites"] = [
        "Não há rótulos reais de fraude ou revisão documental humana concluída.",
        "Correlação e estabilidade não são acurácia nem comprovação de ganho de utilidade.",
        "Alterações sintéticas somente verificam sensibilidade; não estimam desempenho real.",
        (
            "Snapshots atuais podem conter revisões posteriores ao corte; "
            "não é backtest ponto-no-tempo estrito."
        ),
        "Grupos exatos e unidades iguais ainda exigem confirmação comercial/documental.",
        "Nenhum score de produção, ranking de processo ou Autoencoder foi publicado.",
    ]
    write_json(args.saida / "resultado.json", report)
    write_json(DOCS / "resultado_agregado.json", report)
    print(report["decisao"], flush=True)
    print(DOCS / "resultado_agregado.json", flush=True)


if __name__ == "__main__":
    main()
