"""Ensaio corretivo: resultado conhecido até o corte, sem substituir o original."""

from datetime import date
from pathlib import Path

from licita_ml.experiments.core import profile_group, write_json
from licita_ml.experiments.data import END, TRAIN_END, clean, history, split_groups
from licita_ml.experiments.evaluate import evaluate
from licita_ml.review_validation.acquisition import ROOT


def result_known(raw, cut):
    value = raw.get("dataResultado")
    if not value:
        return False
    try:
        return date.fromisoformat(str(value)[:10]) <= cut
    except ValueError:
        return False


def main():
    raw, sources = history("486374", Path("data/validacao_nucleo"), True)
    rows, reasons = clean(raw, "486374")
    selected = [
        row
        for row in rows
        if result_known(
            raw[row["source_ordinal"] - 1], TRAIN_END if row["date"] <= TRAIN_END else END
        )
    ]
    groups = split_groups(selected)
    report = {
        "mesmo_snapshot_original": True,
        "teste_independente": False,
        "fontes": sources,
        "eventos_validacao": reasons,
        "referencias_sem_resultado_ate_corte": len(rows) - len(selected),
        "grupos": [profile_group(g) for g in groups],
        "modelos": [],
        "utilidade_real_comprovada": False,
        "snapshot_ponto_no_tempo": False,
    }
    for group in groups:
        if group["eligible"]:
            result, _, _, _ = evaluate(group, ROOT / "ensaio_data_resultado")
            report["modelos"].append(result)
    report["decisao"] = (
        "ESTAVEL_APOS_FILTRO_RESULTADO_UTILIDADE_PENDENTE"
        if any(m["modelos"]["preco_quantidade"]["estabilidade_aprovada"] for m in report["modelos"])
        else "SEM_ESTABILIDADE_APOS_FILTRO_RESULTADO"
        if report["modelos"]
        else "INCONCLUSIVO_APOS_FILTRO_RESULTADO"
    )
    write_json(ROOT / "ensaio_data_resultado.json", report)
    print(report["decisao"], [(m["treino"], m["teste"]) for m in report["modelos"]], flush=True)


if __name__ == "__main__":
    main()
