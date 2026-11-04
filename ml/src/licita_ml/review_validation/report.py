"""Dossiê auditável e resumo público sem atribuir pareceres humanos."""

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from licita_ml.experiments.core import write_json
from licita_ml.resources import REPORT_DIR, RESOURCE_DIR
from licita_ml.review_validation.acquisition import ROOT

DOCS = REPORT_DIR


def load(name):
    return json.loads((ROOT / name).read_text())


def stability(result):
    model = result["modelos"]["preco_quantidade"]
    anchor = model["ancora_predefinida"]
    config = next(
        c
        for c in model["configuracoes"]
        if c["n_estimators"] == anchor["n_estimators"] and c["max_samples"] == anchor["max_samples"]
    )
    return {
        "spearman": config["spearman_mediana"],
        "jaccard": config["jaccard_topk_mediana"],
        "aprovada": model["estabilidade_aprovada"],
        "top_k": result["top_k"],
    }


def dossier(cases):
    path = ROOT / "dossie_revisao_independente.csv"
    if path.exists():
        with path.open() as file:
            if any(
                r["parecer_humano"] != "pendente" or r["justificativa"] or r["evidencia_url"]
                for r in csv.DictReader(file)
            ):
                raise ValueError("Dossiê com pareceres preenchidos não será sobrescrito")
    fields = [
        "id",
        "id_compra",
        "numero_item",
        "preco_unitario",
        "quantidade",
        "unidade",
        "pagina_pncp",
        "documentos",
        "paginas_item",
        "parecer_humano",
        "justificativa",
        "evidencia_url",
    ]
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow(
                {
                    "id": case["id"],
                    "id_compra": case["id_compra"],
                    "numero_item": case["numero_item"],
                    "preco_unitario": case["preco_unitario"],
                    "quantidade": case["quantidade"],
                    "unidade": "UN",
                    "pagina_pncp": case["pncp_url"],
                    "documentos": " | ".join(case["documentos_urls"]),
                    "paginas_item": json.dumps(case["indice_paginas"], ensure_ascii=False),
                    "parecer_humano": "pendente",
                    "justificativa": "",
                    "evidencia_url": "",
                }
            )
    return path


def main():
    documentary = load("conferencia_documental.json")
    documents = load("documentos_extraidos.json")
    confirmation = load("confirmacao_temporal.json")
    replication = load("replicacao_historica.json")
    corrected = load("ensaio_data_resultado.json")
    original = json.loads((DOCS / "resultado_agregado.json").read_text())
    main_result = next(m for m in original["modelos"] if m["catalogo"] == "486374")
    with Path(
        "data/validacao_nucleo/resultados/revisao/c2c61e3e795a3068-revisao-cega.csv"
    ).open() as file:
        blind = {r["id"]: r for r in csv.DictReader(file)}
    by_url = {d["url"]: d for d in documents["documentos"]}
    findings = json.loads((DOCS / "achados_documentais.json").read_text())
    cases = []
    for review in documentary["revisoes"]:
        case_id = review["id"]
        links = documents["documentos_por_caso"][case_id]
        pages = [
            {"url": link, "membro": pdf["membro"], "paginas": pdf["paginas_marca_texto"]}
            for link in links
            for pdf in by_url[link].get("pdfs", [])
            if pdf["paginas_marca_texto"]
        ]
        cases.append(
            {
                "id": case_id,
                "id_compra": review["id_compra"],
                "id_compra_original": review["id_compra_original"],
                "vinculo_textual_explicito": review["vinculo_textual_explicito"],
                "numero_item": int(review["conferencia"]["id_item_fonte"][-5:]),
                "preco_unitario": blind[case_id]["preco_unitario"],
                "quantidade": blind[case_id]["quantidade"],
                "estado_documental": review["conferencia"]["estado"],
                "catalogo_complementar_status": review["conferencia"].get(
                    "catalogo_complementar_status"
                ),
                "pncp_url": review["pncp_url"],
                "documentos_urls": links,
                "indice_paginas": pages,
                "texto_disponivel": any(
                    by_url[link]["estado"] == "texto_extraido" for link in links
                ),
                "top5_if_preco_quantidade": case_id
                in main_result["modelos"]["preco_quantidade"]["top_ids"],
                "top5_regra_preco": case_id in main_result["baseline_sobrepreco"],
                "parecer_humano": "pendente",
                "achados_assistidos": [a for a in findings["achados"] if a["id_caso"] == case_id],
            }
        )
    review_path = dossier(cases)
    summary = {
        "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "sha256_protocolo": hashlib.sha256(
            (RESOURCE_DIR / "PROTOCOLO_REVISAO_E_CONFIRMACAO.md").read_bytes()
        ).hexdigest(),
        "sha256_codigo": hashlib.sha256(
            b"".join(
                p.name.encode() + p.read_bytes()
                for folder in (Path("ml/src/licita_ml/experiments"), Path(__file__).parent)
                for p in sorted(folder.glob("*.py"))
            )
        ).hexdigest(),
        "codigo_experimento_original_preservado": str(ROOT / "experiments_original.tar.gz"),
        "sha256_codigo_original_arquivado": hashlib.sha256(
            (ROOT / "experiments_original.tar.gz").read_bytes()
        ).hexdigest(),
        "conferencia": {
            "amostra": documentary["amostra"],
            "compras_distintas": len({c["id_compra"] for c in cases}),
            "estados": documentary["estados"],
            "casos": cases,
        },
        "documentos": {
            "total": len(documents["documentos"]),
            "estados": dict(Counter(d["estado"] for d in documents["documentos"])),
            "casos_com_texto": sum(c["texto_disponivel"] for c in cases),
            "casos_com_paginas_item_localizadas": sum(bool(c["indice_paginas"]) for c in cases),
        },
        "cobertura_top5": {
            "if": sum(
                c["top5_if_preco_quantidade"]
                and c["estado_documental"] == "corroborado_estruturalmente"
                for c in cases
            ),
            "regra_preco": sum(
                c["top5_regra_preco"] and c["estado_documental"] == "corroborado_estruturalmente"
                for c in cases
            ),
            "nao_e_precisao": True,
        },
        "ensaio_data_resultado": {
            "decisao": corrected["decisao"],
            "modelos": [
                {"treino": m["treino"], "teste": m["teste"], "estabilidade": stability(m)}
                for m in corrected["modelos"]
            ],
        },
        "replicacao_historica": {
            "linhas_origem": replication["linhas_origem"],
            "decisao": replication["decisao"],
            "modelos": [
                {"treino": m["treino"], "teste": m["teste"], "estabilidade": stability(m)}
                for m in replication["modelos"]
            ],
        },
        "confirmacao_temporal": {
            key: confirmation[key]
            for key in (
                "periodo",
                "linhas_origem",
                "eventos_validacao",
                "referencias_avaliaveis",
                "minimos_atingidos",
                "decisao",
            )
        },
        "dossie_revisao_independente": str(review_path),
        "achados_documentais": findings,
        "pareceres_humanos_preenchidos": 0,
        "quarentena_experimental_recomendada": [
            a["id_caso"]
            for a in findings["achados"]
            if a["tipo"] == "divergencia_especificacao_documental"
        ],
        "superioridade_sobre_regra_simples_comprovada": False,
        "validado_para_publicacao": False,
        "decisao": "NUCLEO_TECNICO_REPRODUZIDO_UTILIDADE_NAO_COMPROVADA",
    }
    write_json(DOCS / "revisao_e_confirmacao_agregado.json", summary)
    write_json(ROOT / "resumo.json", summary)
    lines = [
        "# Conferência dos 18 casos — revisão assistida",
        "",
        "Dados oficiais corroborados não são rótulos de utilidade ou fraude. "
        "Este arquivo revela os rankings; entregar ao revisor independente "
        "somente depois dos pareceres.",
        "",
        "| Caso | Compra / item | Preço UN | Quantidade | IF top-5 | Regra top-5 "
        "| Conferência | Anexos com texto |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for c in cases:
        price = f"R$ {Decimal(c['preco_unitario']):.2f}"
        cells = [
            c["id"],
            f"[{c['id_compra']} / {c['numero_item']}]({c['pncp_url']})",
            price,
            f"{Decimal(c['quantidade']):.0f}",
            "Sim" if c["top5_if_preco_quantidade"] else "—",
            "Sim" if c["top5_regra_preco"] else "—",
            c["estado_documental"],
            "Sim" if c["texto_disponivel"] else "Não",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    (DOCS / "CASOS_REVISAO_ASSISTIDA.md").write_text("\n".join(lines) + "\n")
    print(summary["decisao"], summary["documentos"], flush=True)


if __name__ == "__main__":
    main()
