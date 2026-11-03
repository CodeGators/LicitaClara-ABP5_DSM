"""Complementa um recorte explícito; não percorre toda a API nacional."""

import csv
import io
import json
import shutil
import tempfile
from zipfile import ZipFile

from licita_collector.api import JsonScope


def control(value):
    # Controle oficial: CNPJ-tipo-sequencial/ano, sem inferir pelo objeto.
    org, _, rest = value.split("-")
    sequence, year = rest.split("/")
    return {"cnpj": org, "ano": int(year), "sequencial": int(sequence)}


def selected_purchases(repository, objects, artifact_id, catalog):
    row = repository.artifact(artifact_id)
    if row["modulo"] != "pesquisa_precos/material":
        raise ValueError("Selecione um arquivo material de pesquisa de preços")
    with tempfile.TemporaryFile() as temp:
        with objects.open(row["chave_objeto"]) as source:
            shutil.copyfileobj(source, temp)
        temp.seek(0)
        import hashlib

        if hashlib.file_digest(temp, "sha256").hexdigest() != row["sha256"]:
            raise ValueError("Hash do material diverge do registro")
        temp.seek(0)
        with ZipFile(temp) as archive:
            with archive.open(archive.namelist()[0]) as stream:
                reader = csv.DictReader(
                    io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter=";"
                )
                return sorted(
                    {r["id_compra"] for r in reader if r["codigo_item_catalogo"] == catalog}
                )


def complement(service, purchases, competence):
    results, failures = [], []

    def collect(kind, query):
        scope = JsonScope(kind, competence, query)
        try:
            result = service.collect(scope)
            results.append(result)
            artifact = service.repository.artifact(result["arquivo_id"])
            with service.objects.open(artifact["chave_objeto"]) as source:
                data = json.load(source)
            return [row for page in data["paginas"] for row in page["resultado"]]
        except Exception as error:
            failures.append(
                {
                    "kind": kind,
                    "query": query,
                    "execucao_id": getattr(error, "execucao_id", None),
                    "codigo": getattr(error, "code", "FALHA_INTERNA"),
                    "tipo": type(error).__name__,
                }
            )
            return []

    for purchase in purchases:
        query = {"idCompra": purchase}
        rows = collect("compra_api", query)
        collect("itens_api", query)
        collect("resultados_api", query)
        contracts = collect("contratos_api", query)
        for row in rows:
            if row.get("numeroControlePNCP"):
                collect("documentos_compra", control(row["numeroControlePNCP"]))
        for value in sorted(
            {
                r["numeroControlePncpContrato"]
                for r in contracts
                if r.get("numeroControlePncpContrato")
            }
        ):
            key = control(value)
            collect("contrato_pncp", key)
            collect("documentos_contrato", key)
        print(
            json.dumps({"compra": purchase, "coletas": len(results), "falhas": len(failures)}),
            flush=True,
        )
    return {
        "status": "parcial" if failures else "concluido",
        "resultados": results,
        "falhas": failures,
    }
