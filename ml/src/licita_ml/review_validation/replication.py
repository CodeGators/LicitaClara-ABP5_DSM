"""Replicação em janela histórica disjunta; não confirma previsão futura."""

import hashlib
from datetime import date

from licita_ml.experiments.core import profile_group, review_files, write_json
from licita_ml.experiments.data import clean, split_groups
from licita_ml.experiments.evaluate import evaluate
from licita_ml.review_validation.acquisition import ROOT, pages

START, CUT, END = date(2024, 10, 1), date(2025, 6, 30), date(2025, 9, 30)


def main():
    raw, sources = pages(
        "/modulo-pesquisa-preco/1_consultarMaterial",
        {
            "tipo": "codigoItemCatalogo",
            "codigo": "486374",
            "dataCompraInicio": str(START),
            "dataCompraFim": str(END),
        },
    )
    rows, reasons = clean(raw, "486374", start=START, end=END)
    groups = split_groups(rows, train_end=CUT)
    root = ROOT / "replicacao_2024_2025"
    report = {
        "periodo": [str(START), str(END)],
        "treino_ate": str(CUT),
        "fontes": sources,
        "linhas_origem": len(raw),
        "linhas_validadas": len(rows),
        "eventos_validacao": reasons,
        "grupos": [profile_group(g) for g in groups],
        "modelos": [],
        "revisao": [],
        "confirmacao_futura_modelo_original": False,
        "utilidade_real_comprovada": False,
    }
    for group in groups:
        if not group["eligible"]:
            continue
        result, rankings, ratios, bilateral = evaluate(group, root, train_end=CUT)
        report["modelos"].append(result)
        report["revisao"].append(review_files(group, result, rankings, ratios, bilateral, root))
    stable = [
        m for m in report["modelos"] if m["modelos"]["preco_quantidade"]["estabilidade_aprovada"]
    ]
    report["decisao"] = (
        "REPLICACAO_HISTORICA_ESTAVEL_UTILIDADE_PENDENTE"
        if stable
        else "REPLICACAO_HISTORICA_SEM_ESTABILIDADE"
        if report["modelos"]
        else "REPLICACAO_HISTORICA_INCONCLUSIVA_POR_DADOS"
    )
    report["assinaturas_respostas"] = [
        hashlib.sha256(open(m["arquivo"], "rb").read()).hexdigest() for m in sources
    ]
    write_json(ROOT / "replicacao_historica.json", report)
    print(
        {
            "linhas": len(raw),
            "grupos_elegiveis": len(report["modelos"]),
            "decisao": report["decisao"],
        },
        flush=True,
    )


if __name__ == "__main__":
    main()
