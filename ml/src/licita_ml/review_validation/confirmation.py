"""Inferência no período novo, com artefatos e referências congelados."""

import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

import joblib
import numpy as np

from licita_ml.experiments.core import write_json
from licita_ml.experiments.data import clean, history
from licita_ml.experiments.evaluate import features, top_indices
from licita_ml.review_validation.acquisition import ROOT, pages

START, END = date(2026, 10, 1), date(2026, 10, 19)


def eligible_new(rows, original_rows, group):
    historical_purchases = {r["purchase"] for r in original_rows}
    same = [r for r in rows if r["group"] == tuple(group)]
    frequencies = Counter(r["purchase"] for r in same)
    exclusions = Counter()
    selected = []
    for row in same:
        if row["purchase"] in historical_purchases:
            exclusions["compra_presente_historico"] += 1
        elif frequencies[row["purchase"]] > 5:
            exclusions["compra_com_mais_de_cinco_referencias"] += 1
        elif row["quantity"] is None:
            exclusions["quantidade_ausente"] += 1
        else:
            selected.append(row)
    return selected, dict(exclusions)


def main():
    old_path = Path("docs/validacao_nucleo/resultado_agregado.json")
    old_report = json.loads(old_path.read_text())
    principal = next(
        m for m in old_report["modelos"] if m["catalogo"] == "486374" and m["modo"] == "principal"
    )
    profile = next(c for c in old_report["coortes"] if c["catalogo"] == "486374")
    group = next(g for g in profile["grupos"] if g["id"] == principal["group_id"])["group"]
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
    original, _ = history("486374", Path("data/validacao_nucleo"), True)
    original_cleaned, _ = clean(original, "486374")
    selected, exclusions = eligible_new(rows, original_cleaned, group)
    ids = [r["id"] for r in selected]
    purchases = len({r["purchase"] for r in selected})
    report = {
        "periodo": [str(START), str(END)],
        "mes_incompleto": True,
        "sha256_resultado_original": hashlib.sha256(old_path.read_bytes()).hexdigest(),
        "fontes": sources,
        "linhas_origem": len(raw),
        "apos_validacao": len(rows),
        "eventos_validacao": reasons,
        "exclusoes_grupo_novo": exclusions,
        "mesmo_grupo_antes_filtros": sum(r["group"] == tuple(group) for r in rows),
        "referencias_avaliaveis": len(selected),
        "compras_distintas": purchases,
        "minimos_atingidos": len(selected) >= 30 and purchases >= 10,
        "modelos_retreinados": False,
        "modelos": {},
        "utilidade_real_comprovada": False,
        "referencias": [
            {
                key: row[key]
                for key in ("id", "purchase", "date", "price", "quantity", "official_item")
            }
            for row in selected
        ],
    }
    for label in ("preco", "preco_quantidade"):
        artifact = principal["modelos"][label]
        path = Path(artifact["artefato"])
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != artifact["sha256_artefato"]:
            raise ValueError("Artefato difere do ensaio original")
        bundle = joblib.load(path)  # Somente artefato próprio com hash previamente registrado.
        info = {
            "artefato": str(path),
            "sha256": actual_sha,
            "mediana_congelada": str(bundle["mediana_treino"]),
        }
        if selected:
            scores = -bundle["model"].score_samples(
                features(selected, bundle["mediana_treino"], bundle["features"])
            )
            if not np.isfinite(scores).all():
                raise ValueError("Score não finito no período novo")
            k = min(len(selected), 10, max(3, math.ceil(0.10 * len(selected))))
            ratios = [float(r["price"] / bundle["mediana_treino"]) for r in selected]
            top = top_indices(scores, ids, k)
            base = top_indices(ratios, ids, k)
            info.update(
                scores_finitos=True,
                top_k=k,
                top_ids=[ids[i] for i in top],
                baseline_top_ids=[ids[i] for i in base],
                sobreposicao_baseline=len(set(top) & set(base)) / k,
                scores={ids[i]: float(score) for i, score in enumerate(scores)},
            )
        report["modelos"][label] = info
    report["decisao"] = (
        "INFERENCIA_EXECUTADA_REVISAO_E_ESTABILIDADE_PENDENTES"
        if report["minimos_atingidos"]
        else "CONFIRMACAO_TEMPORAL_INCONCLUSIVA_POR_AMOSTRA"
    )
    write_json(ROOT / "confirmacao_temporal.json", report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "linhas_origem",
                    "referencias_avaliaveis",
                    "compras_distintas",
                    "decisao",
                )
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
