"""Consome apenas treino e avaliação; IDs e atributos são reconciliados antes do fit."""

import json
from datetime import date
from decimal import Decimal

import numpy as np
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from licita_ml.analytical.rules import median
from licita_ml.experiments.evaluate import features
from licita_ml.temporal.pipeline import FEATURES, validate


def load(base):
    manifest = json.loads((base / "manifesto.json").read_text())
    validate(base, manifest["fingerprint"])
    if manifest["status"] != "apto_avaliacao_tecnica" or manifest["grupos_elegiveis"] < 1:
        raise ValueError("Dataset temporal insuficiente; nenhum modelo será treinado")
    reports = json.loads((base / "grupos.json").read_text())
    eligible = {g["grupo"]: g for g in reports if g["elegivel_tecnicamente"]}
    if len(eligible) != manifest["grupos_elegiveis"] or len(eligible) > 20:
        raise ValueError("Grupos elegíveis divergentes ou limite de 20 grupos excedido")
    matrices = {}
    ids = set()
    for name in ("treino", "avaliacao"):
        path = base / f"{name}.parquet"
        if pq.ParquetFile(path).metadata.num_rows > 200000:
            raise ValueError("Matriz excede limite de 200 mil linhas")
        records = pq.ParquetFile(path).read().to_pylist()
        if len({r["id_observacao"] for r in records}) != len(records):
            raise ValueError("IDs repetidos na matriz temporal")
        if ids & {r["id_observacao"] for r in records}:
            raise ValueError("Observações compartilhadas entre treino e avaliação")
        ids.update(r["id_observacao"] for r in records)
        matrices[name] = records
    if {r["compra"] for r in matrices["treino"]} & {r["compra"] for r in matrices["avaliacao"]}:
        raise ValueError("Compras compartilhadas entre treino e avaliação")
    # Predicate excludes application rows; application matrices are never deserialized here.
    table = ds.dataset(base / "referencias_temporais.parquet", format="parquet")
    audit = {
        r["id_observacao"]: r
        for r in table.to_table(filter=ds.field("id_observacao").isin(sorted(ids))).to_pylist()
    }
    if set(audit) != ids:
        raise ValueError("Observações sem contexto temporal")
    policy = manifest["configuracao"]["politica"]
    groups = {}
    for gid, report in sorted(eligible.items()):
        values = {
            "id": gid,
            "group": report["especificacao"],
            "eligible": True,
            "report": report,
            "audit": {},
            "matrices": {},
        }
        for name, output_key in (("treino", "train"), ("avaliacao", "test")):
            selected = sorted(
                [r for r in matrices[name] if r["grupo"] == gid], key=lambda r: r["id_observacao"]
            )
            expected = report["treino" if name == "treino" else "avaliacao"]
            if len(selected) != expected:
                raise ValueError("Contagem da coorte diverge do grupo")
            converted = []
            start = date.fromisoformat(
                policy["train_start" if name == "treino" else "evaluation_start"]
            )
            end = date.fromisoformat(policy["train_end" if name == "treino" else "evaluation_end"])
            for row in selected:
                context = audit[row["id_observacao"]]
                if (
                    context["grupo"] != gid
                    or context["particao"] != name
                    or context["compra"] != row["compra"]
                    or not context["apto_modelagem"]
                    or json.loads(context["motivos_json"])
                ):
                    raise ValueError("Matriz diverge da auditoria de elegibilidade")
                if not (start <= context["data_compra"] <= context["data_resultado"] <= end):
                    raise ValueError("Coorte contém data fora do corte")
                if any(
                    context[k] is None or context[k] <= 0 for k in ("preco_unitario", "quantidade")
                ):
                    raise ValueError("Coorte contém preço/quantidade inválidos")
                if any(row[k] != context[k] for k in FEATURES):
                    raise ValueError("Matriz não corresponde aos atributos congelados")
                converted.append(
                    {
                        "id": context["id_observacao"],
                        "price": context["preco_unitario"],
                        "quantity": context["quantidade"],
                        "date": context["data_compra"],
                    }
                )
                values["audit"][context["id_observacao"]] = context
            x = np.asarray([[r[k] for k in FEATURES] for r in selected], dtype=np.float64)
            if x.shape != (expected, 2) or not np.isfinite(x).all():
                raise ValueError("Matriz numérica inválida")
            values[output_key], values["matrices"][name] = converted, x
        med = median([r["price"] for r in values["train"]])
        if med != Decimal(report["mediana_treino"]):
            raise ValueError("Mediana do treino não reproduz a referência congelada")
        for name, key in (("treino", "train"), ("avaliacao", "test")):
            if not np.array_equal(
                features(values[key], med, list(FEATURES)), values["matrices"][name]
            ):
                raise ValueError("Transformação do motor de treino diverge das matrizes ML03")
        if np.any(np.ptp(values["matrices"]["treino"], axis=0) == 0):
            raise ValueError("Atributos de treino constantes")
        groups[gid] = values
    if sum(len(g["train"]) for g in groups.values()) != len(matrices["treino"]) or sum(
        len(g["test"]) for g in groups.values()
    ) != len(matrices["avaliacao"]):
        raise ValueError("Matriz contém grupo não elegível")
    return manifest, groups
