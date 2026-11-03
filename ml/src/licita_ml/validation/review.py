"""Amostras sem ranking e apuração de pareceres externos sem inferir conclusões."""

import csv
import io
from collections import Counter
from datetime import date

from licita_ml.analytical.rules import digest

VERDICTS = {
    "comparavel_e_justificavel",
    "requer_verificacao",
    "erro_dado_ou_unidade",
    "nao_comparavel",
    "inconclusivo",
}
FIELDS = [
    "caso_id",
    "compra",
    "item_fonte",
    "item_oficial",
    "fornecedor_hash",
    "especificacao",
    "data_compra",
    "data_resultado",
    "preco_unitario",
    "quantidade",
    "fonte_arquivo",
    "fonte_pagina",
    "fonte_ordem",
    "parecer_humano",
    "justificativa",
    "evidencia_url",
    "revisor",
    "data_revisao",
]


def sample(rows, n):
    return sorted(rows, key=lambda r: digest(["revisao-v1", r["id"]]))[:n]


def blind_csv(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    for row in sample(rows, len(rows)):
        provenance = next(iter(row.get("proveniencias", [])), {})
        writer.writerow(
            {
                "caso_id": row["id"],
                **{k: row.get(k, "") for k in FIELDS[1:10]},
                "especificacao": " | ".join(str(v or "") for v in row["especificacao"]),
                "fonte_arquivo": provenance.get("arquivo_id", ""),
                "fonte_pagina": provenance.get("membro", ""),
                "fonte_ordem": provenance.get("ordinal", ""),
                "parecer_humano": "pendente",
            }
        )
    return out.getvalue().encode("utf-8-sig")


def summarize(raw, expected_ids, rankings, original_raw=None):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    ids = [r["caso_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise ValueError("IDs da revisão ausentes, duplicados ou estranhos à amostra")
    if original_raw is not None:
        original = {
            r["caso_id"]: r for r in csv.DictReader(io.StringIO(original_raw.decode("utf-8-sig")))
        }
        editable = {"parecer_humano", "justificativa", "evidencia_url", "revisor", "data_revisao"}
        for row in rows:
            if any(
                row.get(k) != v for k, v in original[row["caso_id"]].items() if k not in editable
            ):
                raise ValueError("Contexto da referência alterado na planilha de revisão")
    counts = Counter()
    for row in rows:
        verdict = row["parecer_humano"].strip()
        if verdict in {"", "pendente"}:
            counts["pendente"] += 1
            continue
        if verdict not in VERDICTS:
            raise ValueError("Parecer fora do protocolo")
        if not all(
            row.get(k, "").strip()
            for k in ["justificativa", "evidencia_url", "revisor", "data_revisao"]
        ):
            raise ValueError("Parecer preenchido sem evidência ou identificação")
        date.fromisoformat(row["data_revisao"])
        if not row["evidencia_url"].startswith(("https://", "http://")):
            raise ValueError("Evidência deve identificar uma URL verificável")
        counts[verdict] += 1
    by_id = {r["caso_id"]: r["parecer_humano"].strip() or "pendente" for r in rows}
    return {
        "status": "revisao_pendente" if counts["pendente"] else "pareceres_registrados",
        "total": len(rows),
        "contagens": dict(counts),
        "por_ranking": {
            label: {
                "denominador_original": len(members),
                "pareceres": dict(Counter(by_id[uid] for uid in members)),
            }
            for label, members in rankings.items()
        },
        "utilidade_aprovada_automaticamente": False,
        "limite": (
            "Pareceres declarados por terceiros; independência não verificável pelo software."
        ),
    }
