"""Regras puras; Decimal para dinheiro, motivos explícitos e universos identificados."""

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext

from licita_ml.normalize import day, money, text


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def feature(value=None, reason=None, **metadata):
    return {
        "valor": str(value) if isinstance(value, Decimal) else value,
        "motivo": reason if value is None else None,
        **metadata,
    }


@dataclass(frozen=True)
class Policy:
    start: date
    train_end: date
    end: date
    version: str = "atributos-v1"
    reference_min: int = 20
    reference_purchases_min: int = 10
    train_min: int = 100
    test_min: int = 30
    train_purchases_min: int = 20
    test_purchases_min: int = 10
    max_per_purchase: int = 5
    max_purchase_share: Decimal = Decimal("0.10")
    window_days: int = 365

    def __post_init__(self):
        if not self.start <= self.train_end < self.end:
            raise ValueError("Exigir início <= fim do treino < fim da avaliação")

    def manifest(self):
        return json.loads(canonical(asdict(self)))


def reference_row(raw):
    catalog = text(raw.get("codigoItemCatalogo"), True)
    purchase = text(raw.get("idCompra"), True)
    item = text(raw.get("idItemCompra"), True)
    supplier = text(raw.get("niFornecedor"), True)
    form = text(raw.get("forma"), True)
    if not catalog.isdigit() or not purchase.isdigit() or not item.isdigit():
        raise ValueError("IDENTIFICADOR_INVALIDO")
    price = money(raw.get("precoUnitario"), positive=True)
    if price is None:
        raise ValueError("PRECO_AUSENTE")
    description = normalize(raw.get("descricaoDetalhadaItem"))
    unit = normalize(raw.get("siglaUnidadeFornecimento"))
    capacity = money(raw.get("capacidadeUnidadeFornecimento"))
    if not unit or not description:
        raise ValueError("UNIDADE_OU_ESPECIFICACAO_AUSENTE")
    if unit not in {"un", "unidade", "unidades"} and (capacity is None or capacity <= 0):
        raise ValueError("CAPACIDADE_EMBALAGEM_AUSENTE")
    key = (purchase, item, supplier, form)
    group = (
        catalog,
        description,
        unit,
        str(capacity.normalize()) if capacity else "0" if capacity == 0 else None,
        normalize(raw.get("siglaUnidadeMedida")),
    )
    return {
        "id": digest(key)[:20],
        "chave": key,
        "catalogo": catalog,
        "compra": purchase,
        "item_fonte": item,
        "item_oficial": text(raw.get("idCompraItem")),
        "fornecedor_hash": digest(supplier)[:16],
        "orgao": text(raw.get("codigoOrgao")),
        "grupo": digest(group)[:16],
        "especificacao": group,
        "data_compra": day(raw.get("dataCompra"), True),
        "data_resultado": day(raw.get("dataResultado")),
        "preco_unitario": price,
        "quantidade": money(raw.get("quantidade")),
        "atualizacoes": [raw.get("dataHoraAtualizacaoItem"), raw.get("dataHoraAtualizacaoCompra")],
    }


def median(values):
    values = sorted(values)
    if not values:
        raise ValueError("Mediana sem observações")
    middle = len(values) // 2
    with localcontext() as ctx:
        ctx.prec = 50
        return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def divide(a, b):
    with localcontext() as ctx:
        ctx.prec = 50
        return a / b


def prepare_references(rows, policy, exclusions):
    """A mediana é ajustada no treino; avaliação não altera nenhum grupo/referência de treino."""
    original_train = {r["compra"] for r in rows if r["data_compra"] <= policy.train_end}
    for row in rows:
        cut = policy.train_end if row["data_compra"] <= policy.train_end else policy.end
        reasons = []
        if not policy.start <= row["data_compra"] <= policy.end:
            reasons.append("FORA_PERIODO")
        if row["data_resultado"] is None:
            reasons.append("DATA_RESULTADO_AUSENTE")
        elif row["data_resultado"] > cut:
            reasons.append("RESULTADO_POSTERIOR_AO_CORTE")
        if row["id"] in exclusions:
            reasons.append("DIVERGENCIA_DOCUMENTAL_SUSPENSA")
        if row["quantidade"] is None:
            reasons.append("QUANTIDADE_AUSENTE")
        row["particao"] = "treino" if cut == policy.train_end else "avaliacao"
        if row["particao"] == "avaliacao" and row["compra"] in original_train:
            reasons.append("COMPRA_COMPARTILHADA_COM_TREINO")
        row["motivos_exclusao"] = reasons
        row["snapshot_revisado_apos_corte"] = any(
            str(v or "")[:10] > str(cut) for v in row["atualizacoes"]
        )
    counts = Counter(
        (r["grupo"], r["particao"], r["compra"]) for r in rows if not r["motivos_exclusao"]
    )
    for row in rows:
        if counts[row["grupo"], row["particao"], row["compra"]] > policy.max_per_purchase:
            row["motivos_exclusao"].append("EXCESSO_REFERENCIAS_MESMA_COMPRA")
    groups = defaultdict(list)
    for row in rows:
        groups[row["grupo"]].append(row)
    reports = []
    for group, members in sorted(groups.items()):
        train = [r for r in members if r["particao"] == "treino" and not r["motivos_exclusao"]]
        test = [r for r in members if r["particao"] == "avaliacao" and not r["motivos_exclusao"]]
        purchases = Counter(r["compra"] for r in train)
        reference_ok = (
            len(train) >= policy.reference_min and len(purchases) >= policy.reference_purchases_min
        )
        med = median([r["preco_unitario"] for r in train]) if reference_ok else None
        limits = {
            "TREINO_INSUFICIENTE": len(train) >= policy.train_min,
            "AVALIACAO_INSUFICIENTE": len(test) >= policy.test_min,
            "COMPRAS_TREINO_INSUFICIENTES": len(purchases) >= policy.train_purchases_min,
            "COMPRAS_AVALIACAO_INSUFICIENTES": len({r["compra"] for r in test})
            >= policy.test_purchases_min,
            "ORGAOS_TREINO_INSUFICIENTES": len({r["orgao"] for r in train if r["orgao"]}) >= 3,
            "FORNECEDORES_TREINO_INSUFICIENTES": len({r["fornecedor_hash"] for r in train}) >= 3,
            "CONCENTRACAO_COMPRA_TREINO": bool(train)
            and divide(Decimal(max(purchases.values(), default=0)), Decimal(len(train)))
            <= policy.max_purchase_share,
        }
        blockers = [reason for reason, passed in limits.items() if not passed]
        for row in members:
            reason = (
                row["motivos_exclusao"][0]
                if row["motivos_exclusao"]
                else "AMOSTRA_REFERENCIA_INSUFICIENTE"
                if med is None
                else None
            )
            ratio = None if reason else divide(row["preco_unitario"], med)
            row["atributos"] = {
                "preco_mediana": feature(
                    ratio,
                    reason,
                    mediana=None if med is None else str(med),
                    referencias_treino=len(train),
                    compras_treino=len(purchases),
                    corte_referencia=str(policy.train_end),
                ),
                "log_preco_mediana": feature(
                    None if ratio is None else math.log(float(ratio)), reason
                ),
                "log_quantidade": feature(
                    None if row["quantidade"] is None else math.log1p(float(row["quantidade"])),
                    "QUANTIDADE_AUSENTE",
                ),
            }
        reports.append(
            {
                "grupo": group,
                "especificacao": members[0]["especificacao"],
                "treino": len(train),
                "avaliacao": len(test),
                "compras_treino": len(purchases),
                "compras_avaliacao": len({r["compra"] for r in test}),
                "mediana_treino": None if med is None else str(med),
                "elegivel_tecnicamente": not blockers,
                "impedimentos": blockers,
            }
        )
    return reports


def estimated_difference(estimated, actual, unit):
    if not unit:
        return feature(reason="UNIDADE_AUSENTE")
    if estimated is None or actual is None:
        return feature(reason="VALOR_UNITARIO_AUSENTE")
    if estimated <= 0:
        return feature(reason="ESTIMATIVA_NAO_POSITIVA")
    return feature(
        divide(actual - estimated, estimated),
        formula="(homologado_unitario-estimado_unitario)/estimado_unitario",
    )


def participant_count(rows, complete, as_of=None):
    if not complete or any(not r.get("identificacao_participante") for r in rows):
        return feature(reason="COBERTURA_PARTICIPANTES_NAO_COMPROVADA")
    if as_of is not None:
        timestamps = [
            r.get("alterado_na_origem_em") or r.get("incluido_na_origem_em") for r in rows
        ]
        if any(value is None or value.date() > as_of for value in timestamps):
            return feature(reason="DATA_PROPOSTA_AUSENTE_OU_POSTERIOR_AO_CORTE")
    return feature(len({r["identificacao_participante"] for r in rows}))


def concentration(events, *, start, end, exclude_process=None):
    """Todos os fornecedores do universo fornecido; nunca somente os sinalizados."""
    events = [e for e in events if not e["cancelado"] and e["processo_id"] != exclude_process]
    if any(e["data_resultado"] is None for e in events):
        return feature(reason="DATA_RESULTADO_AUSENTE_NO_UNIVERSO")
    selected = [e for e in events if start <= e["data_resultado"] <= end]
    if not selected:
        return feature(reason="SEM_RESULTADOS_NO_UNIVERSO")
    if any(e["valor_total_homologado"] is None for e in selected):
        return feature(reason="TOTAL_DESCONHECIDO_NO_UNIVERSO")
    values = defaultdict(Decimal)
    with localcontext() as ctx:
        ctx.prec = 50
        for event in selected:
            values[str(event["fornecedor_id"])] += event["valor_total_homologado"]
        total = sum(values.values())
        if total <= 0:
            return feature(reason="TOTAL_UNIVERSO_NAO_POSITIVO")
        shares = {key: value / total for key, value in values.items()}
        return feature(
            sum(s * s for s in shares.values()),
            total=str(total),
            fornecedores=len(shares),
            participacoes={k: str(v) for k, v in shares.items()},
        )


def frequency(events, supplier, *, start, end, exclude_process=None):
    events = [e for e in events if not e["cancelado"] and e["processo_id"] != exclude_process]
    if any(e["data_resultado"] is None for e in events):
        return feature(reason="DATA_RESULTADO_AUSENTE_NO_UNIVERSO")
    return feature(
        len(
            {
                e["processo_id"]
                for e in events
                if str(e["fornecedor_id"]) == str(supplier) and start <= e["data_resultado"] <= end
            }
        )
    )


def contract_interval(publication, contracts, cutoff):
    if publication is None:
        return feature(reason="PUBLICACAO_AUSENTE")
    if len(contracts) != 1:
        return feature(
            reason="SEM_CONTRATO_VINCULADO" if not contracts else "MULTIPLOS_CONTRATOS_SEM_POLITICA"
        )
    signature = contracts[0].get("data_assinatura")
    if signature is None:
        return feature(reason="ASSINATURA_AUSENTE")
    if signature > cutoff or publication > cutoff:
        return feature(reason="DATA_POSTERIOR_AO_CORTE")
    if signature < publication:
        return feature(reason="ASSINATURA_ANTERIOR_PUBLICACAO")
    return feature((signature - publication).days, contrato_versao_id=str(contracts[0]["id"]))


def event_window(result_date, policy):
    cutoff = min(result_date, policy.end) if result_date else policy.end
    return cutoff - timedelta(days=policy.window_days), cutoff - timedelta(days=1)
