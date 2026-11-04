"""Critérios explícitos de recorte, cortes e comparabilidade para matrizes numéricas."""

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from licita_ml.analytical.rules import digest, divide, median, normalize


@dataclass(frozen=True)
class TemporalPolicy:
    train_start: date = date(2025, 10, 1)
    train_end: date = date(2025, 12, 31)
    evaluation_start: date = date(2026, 7, 1)
    evaluation_end: date = date(2026, 8, 31)
    application_start: date = date(2026, 9, 1)
    application_end: date = date(2026, 9, 30)
    classes: tuple = ("7510",)
    catalogs: tuple = ("486054", "486374", "637468")
    reference_min: int = 20
    reference_purchases_min: int = 10
    train_min: int = 100
    train_purchases_min: int = 20
    evaluation_min: int = 30
    evaluation_purchases_min: int = 10
    organ_min: int = 3
    supplier_min: int = 3
    max_per_purchase: int = 5
    max_purchase_share: Decimal = Decimal("0.10")
    version: str = "atributos-temporais-v1"

    def __post_init__(self):
        if not (
            self.train_start
            <= self.train_end
            < self.evaluation_start
            <= self.evaluation_end
            < self.application_start
            <= self.application_end
        ):
            raise ValueError("Janelas devem ser ordenadas, não sobrepostas e não vazias")

    def manifest(self):
        return {
            k: str(v) if isinstance(v, (date, Decimal)) else list(v) if isinstance(v, tuple) else v
            for k, v in asdict(self).items()
        }

    def partition(self, value):
        for name, start, end in self.windows():
            if value is not None and start <= value <= end:
                return name
        return None

    def windows(self):
        return (
            ("treino", self.train_start, self.train_end),
            ("avaliacao", self.evaluation_start, self.evaluation_end),
            ("aplicacao", self.application_start, self.application_end),
        )

    def in_scope(self, row):
        return row.get("classe") in self.classes or row.get("catalogo") in self.catalogs


def specification(row):
    code = row.get("catalogo")
    description = normalize(row.get("descricao_detalhada"))
    unit = normalize(row.get("unidade_fornecimento_sigla"))
    capacity = row.get("capacidade")
    if not code or not code.isdigit() or not description or not unit:
        return None, "CATALOGO_ESPECIFICACAO_OU_UNIDADE_AUSENTE"
    if unit not in {"un", "unidade", "unidades"} and (capacity is None or capacity <= 0):
        return None, "CAPACIDADE_EMBALAGEM_AUSENTE"
    spec = (
        code,
        description,
        unit,
        str(capacity.normalize()) if capacity else "0" if capacity == 0 else None,
        normalize(row.get("unidade_medida_sigla")),
    )
    return spec, None


def inspect_row(row, policy, exclusions):
    partition = policy.partition(row.get("data_compra"))
    reasons = []
    if partition is None:
        reasons.append("FORA_JANELAS_OU_DATA_COMPRA_AUSENTE")
    cut = dict((name, end) for name, _, end in policy.windows()).get(partition)
    event, result = row.get("data_compra"), row.get("data_resultado")
    if result is None:
        reasons.append("DATA_RESULTADO_AUSENTE")
    elif cut is not None:
        if result > cut:
            reasons.append("RESULTADO_POSTERIOR_AO_CORTE")
        if event is not None and result < event:
            reasons.append("RESULTADO_ANTERIOR_COMPRA_REQUER_CONFERENCIA")
    for field in ("preco_unitario", "quantidade"):
        if row.get(field) is None or row[field] <= 0:
            reasons.append(f"{field.upper()}_AUSENTE_OU_NAO_POSITIVO")
    spec, reason = specification(row)
    if reason:
        reasons.append(reason)
    legacy_id = digest([row["id_compra"], row["id_item_fonte"], row["fornecedor"], row["forma"]])[
        :20
    ]
    if legacy_id in exclusions:
        reasons.append("DIVERGENCIA_DOCUMENTAL_SUSPENSA")
    return {
        "row": row,
        "partition": partition,
        "spec": spec,
        "group": digest(spec)[:16] if spec else None,
        "reasons": reasons,
        "legacy_id": legacy_id,
        "median": None,
        "ratio": None,
        "x": None,
        "model_ready": False,
        "snapshot_after_cut": bool(
            cut
            and any(
                str(row.get(field) or "")[:10] > str(cut)
                for field in ("atualizacao_primaria", "atualizacao_secundaria")
            )
        ),
    }


def build_groups(rows, first_partition, policy):
    order = {"treino": 0, "avaliacao": 1, "aplicacao": 2}
    for row in rows:
        if (
            row["partition"] is not None
            and first_partition[row["row"]["id_compra"]] < order[row["partition"]]
        ):
            row["reasons"].append("COMPRA_OBSERVADA_EM_PARTICAO_ANTERIOR")
    counts = Counter(
        (r["group"], r["partition"], r["row"]["id_compra"]) for r in rows if not r["reasons"]
    )
    for row in rows:
        if (
            counts[row["group"], row["partition"], row["row"]["id_compra"]]
            > policy.max_per_purchase
        ):
            row["reasons"].append("EXCESSO_REFERENCIAS_MESMA_COMPRA")
    grouped = defaultdict(list)
    for row in rows:
        if row["group"]:
            grouped[row["group"]].append(row)
    reports = []
    for group, members in sorted(grouped.items()):
        train = [r["row"] for r in members if r["partition"] == "treino" and not r["reasons"]]
        evaluation = [
            r["row"] for r in members if r["partition"] == "avaliacao" and not r["reasons"]
        ]
        purchases = Counter(r["id_compra"] for r in train)
        reference_ok = (
            len(train) >= policy.reference_min and len(purchases) >= policy.reference_purchases_min
        )
        med = median([r["preco_unitario"] for r in train]) if reference_ok else None
        limits = {
            "PRECO_TREINO_CONSTANTE": len({r["preco_unitario"] for r in train}) > 1,
            "QUANTIDADE_TREINO_CONSTANTE": len({r["quantidade"] for r in train}) > 1,
            "TREINO_INSUFICIENTE": len(train) >= policy.train_min,
            "COMPRAS_TREINO_INSUFICIENTES": len(purchases) >= policy.train_purchases_min,
            "AVALIACAO_INSUFICIENTE": len(evaluation) >= policy.evaluation_min,
            "COMPRAS_AVALIACAO_INSUFICIENTES": len({r["id_compra"] for r in evaluation})
            >= policy.evaluation_purchases_min,
            "ORGAOS_TREINO_INSUFICIENTES": len(
                {r["orgao_codigo"] for r in train if r["orgao_codigo"]}
            )
            >= policy.organ_min,
            "FORNECEDORES_TREINO_INSUFICIENTES": len({r["fornecedor"] for r in train})
            >= policy.supplier_min,
            "CONCENTRACAO_COMPRA_TREINO": bool(train)
            and divide(Decimal(max(purchases.values(), default=0)), Decimal(len(train)))
            <= policy.max_purchase_share,
        }
        blockers = [reason for reason, passed in limits.items() if not passed]
        for row in members:
            row["median"] = med
            if not row["reasons"] and med is not None:
                ratio = divide(row["row"]["preco_unitario"], med)
                x = (math.log(float(ratio)), math.log1p(float(row["row"]["quantidade"])))
                if not all(math.isfinite(value) for value in x):
                    row["reasons"].append("ATRIBUTO_NAO_FINITO")
                else:
                    row["ratio"], row["x"] = ratio, x
            row["model_ready"] = not blockers and not row["reasons"] and row["x"] is not None
        reports.append(
            {
                "grupo": group,
                "especificacao": members[0]["spec"],
                "treino": len(train),
                "avaliacao": len(evaluation),
                "compras_treino": len(purchases),
                "compras_avaliacao": len({r["id_compra"] for r in evaluation}),
                "mediana_treino": str(med) if med is not None else None,
                "elegivel_tecnicamente": not blockers,
                "impedimentos": blockers,
                "aplicacao_referencias_aptas": sum(
                    r["model_ready"] and r["partition"] == "aplicacao" for r in members
                ),
            }
        )
    return reports
