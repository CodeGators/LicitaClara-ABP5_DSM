"""Exportação verificável do snapshot de inferência, sem treino ou parecer automático."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path


def audit(path, expected_sha):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("Hash do manifesto diverge")
    manifest = json.loads(raw)
    if manifest["configuracao"]["contrato"] != "inferencia-agrupada-v1":
        raise ValueError("Contrato não suportado")
    scores, coverage = manifest["scores"], manifest["cobertura"]
    models = {m["id"]: m for m in manifest["modelos"]}
    pairs = set()
    for score in scores:
        pair = (score["resultado_item_id"], score["modelo_id"])
        if pair in pairs:
            raise ValueError("Resultado/modelo duplicado")
        pairs.add(pair)
        model = models[score["modelo_id"]]
        if (
            score["base_id"] != manifest["base_id"]
            or score["execucao_id"] != manifest["execucao_id"]
            or score["atributos"]["comparacao"]["grupo"] != model["parametros"]["grupo"]
            or not Decimal("0") <= Decimal(score["score_normalizado"]) <= Decimal("100")
        ):
            raise ValueError("Score fora do contrato")
    analyzed = [r for r in coverage if r["status"] == "analisado_experimental"]
    if (
        len(analyzed) != len(scores)
        or {(r["resultado_item_id"], r["modelo_id"]) for r in analyzed} != pairs
        or len(scores) != manifest["contagens"]["scores"]
        or len(coverage) != manifest["contagens"]["alvos_modelos"]
    ):
        raise ValueError("Cobertura e scores divergem")
    return manifest


def csv_bytes(rows):
    out = io.StringIO(newline="")
    fields = sorted({k for row in rows for k in row})
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                k: json.dumps(v, ensure_ascii=False, sort_keys=True)
                if isinstance(v, (dict, list))
                else v
                for k, v in row.items()
            }
        )
    return out.getvalue().encode("utf-8-sig")


def export(path, expected_sha, output):
    manifest = audit(path, expected_sha)
    models = {m["id"]: m for m in manifest["modelos"]}
    # One deterministic case per group, rather than a global ranking of unrelated models.
    cases = {}
    for score in sorted(manifest["scores"], key=lambda r: r["id"]):
        group = score["atributos"]["comparacao"]["grupo"]
        cases.setdefault(group, score)
    sample = []
    for group, row in sorted(cases.items()):
        model = models[row["modelo_id"]]
        sample.append(
            {
                "caso_id": row["id"],
                "grupo": group,
                "item_versao_id": row["item_versao_id"],
                "resultado_item_id": row["resultado_item_id"],
                "especificacao": model["parametros"]["assinatura_catalogo"],
                "referencia": row["atributos"]["referencia"],
                "parecer_humano": "pendente",
                "justificativa": "",
                "revisor": "",
                "data_revisao": "",
                "evidencia_url": "",
            }
        )
    report = {
        "base_id": manifest["base_id"],
        "execucao_id": manifest["execucao_id"],
        "manifesto_sha256": expected_sha,
        "scores": len(manifest["scores"]),
        "itens_analisados": len({r["item_versao_id"] for r in manifest["scores"]}),
        "grupos_analisados": len(cases),
        "casos_revisao": len(sample),
        "motivos_por_par_alvo_modelo": dict(
            Counter(r["motivo"] for r in manifest["cobertura"] if r["motivo"])
        ),
        "escopo": "Integridade do snapshot; não consulta banco, não repete predição.",
        "amostra": "Um caso por grupo, menor ID de score; sem ranking, não cega prospectiva.",
        "utilidade_validada": False,
        "score_integral_processo_validado": False,
    }
    files = {
        "scores.csv": csv_bytes(manifest["scores"]),
        "cobertura.csv": csv_bytes(manifest["cobertura"]),
        "revisao_original.csv": csv_bytes(sample),
        "resumo.json": (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(),
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        destination = output / name
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError(f"Arquivo existente divergente: {name}; use outra saída")
    for name, content in files.items():
        (output / name).write_bytes(content)
    return report


def reconcile_database(manifest, expected_sha):
    """Conferir o snapshot contra o banco usando o reconciliador da inferência."""
    from uuid import UUID

    import sqlalchemy as sa
    from licita_shared.storage.factory import storage

    from licita_ml.config import Settings
    from licita_ml.inference.pipeline import InferencePipeline
    from licita_ml.repository import Repository

    settings = Settings()
    engine = sa.create_engine(
        settings.processing_database_url.get_secret_value(), hide_parameters=True
    )
    try:
        pipeline = InferencePipeline(settings, Repository(engine), storage(settings))
        table = pipeline.tables["execucoes_analise"]
        with engine.connect() as cn:
            row = (
                cn.execute(sa.select(table).where(table.c.id == UUID(manifest["execucao_id"])))
                .mappings()
                .one()
            )
            if (
                str(row["base_id"]) != manifest["base_id"]
                or row["configuracao"]["manifesto"]["sha256"] != expected_sha
            ):
                raise ValueError("Base persistida diverge")
            # Reconcile compares all persisted scores, factors, routing and coverage.
            pipeline.reconcile(cn, row["id"], row["base_id"], row["configuracao"])
        return {
            "execucao_id": manifest["execucao_id"],
            "reconciliacao_banco_aprovada": True,
            "modo": "somente leitura; sem treino ou nova inferencia",
        }
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--conferir-banco", action="store_true")
    args = parser.parse_args()
    report = export(args.manifesto, args.sha256, args.saida)
    if args.conferir_banco:
        report["banco"] = reconcile_database(audit(args.manifesto, args.sha256), args.sha256)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
