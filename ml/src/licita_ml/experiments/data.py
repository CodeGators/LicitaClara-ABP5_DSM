"""Dados e controles do ensaio; não publica bases nem faz alterações no PostgreSQL."""

import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import urlopen

API = "https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
START, TRAIN_END, END = date(2025, 10, 1), date(2026, 6, 30), date(2026, 9, 30)


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalized(value):
    value = (
        unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def history(catalog, root, offline=False):
    root.mkdir(parents=True, exist_ok=True)
    rows, sources, seen = [], [], set()
    expected = None
    for page in range(1, 101):
        params = dict(
            tipo="codigoItemCatalogo",
            codigo=catalog,
            dataCompraInicio=str(START),
            dataCompraFim=str(END),
            pagina=page,
            tamanhoPagina=500,
        )
        url = API + "?" + urlencode(params)
        path = root / f"historico_{catalog}_pagina_{page}.json"
        meta_path = path.with_suffix(".meta.json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            raw = path.read_bytes()
            if meta["sha256"] != hashlib.sha256(raw).hexdigest() or meta["url"] != url:
                raise ValueError("Cache divergente: hash ou URL não corresponde ao protocolo")
        else:
            if offline:
                raise ValueError("Página ausente em modo offline")
            for attempt in range(3):
                try:
                    with urlopen(url, timeout=35) as response:
                        raw = response.read(16 * 1024**2 + 1)
                        if len(raw) > 16 * 1024**2:
                            raise ValueError("Resposta ultrapassa limite do ensaio")
                    break
                except OSError:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
            meta = dict(
                url=url,
                status=200,
                bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                coletado_em_utc=datetime.now(timezone.utc).isoformat(),
            )
            path.write_bytes(raw)
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
        payload = json.loads(raw, parse_float=Decimal)
        if not isinstance(payload.get("resultado"), list):
            raise ValueError("Resposta incompatível")
        total, pages = int(payload["totalRegistros"]), int(payload["totalPaginas"])
        if expected is not None and expected != total:
            raise ValueError("Total mudou entre páginas")
        expected = total
        fingerprint = digest(payload["resultado"])
        if payload["resultado"] and fingerprint in seen:
            raise ValueError("API repetiu página")
        seen.add(fingerprint)
        rows.extend(payload["resultado"])
        sources.append(meta)
        if page >= pages:
            break
    else:
        raise ValueError("Limite de paginação atingido")
    if len(rows) != expected:
        raise ValueError("Contagem não reconcilia")
    return rows, sources


def numeric(value, positive=False):
    if value is None or str(value).strip() == "":
        return None
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError("Valor inválido")
    return result


def clean(rows, catalog, *, start=START, end=END):
    accepted, reasons, seen, conflicts = [], Counter(), {}, set()
    for ordinal, raw in enumerate(rows, 1):
        try:
            if str(raw.get("codigoItemCatalogo")) != str(catalog):
                raise ValueError("CATALOGO_DIVERGENTE")
            when = date.fromisoformat(str(raw["dataCompra"])[:10])
            if not start <= when <= end:
                raise ValueError("FORA_DO_PERIODO")
            price = numeric(raw.get("precoUnitario"), positive=True)
            if price is None:
                raise ValueError("PRECO_AUSENTE")
            quantity = numeric(raw.get("quantidade"))
            unit = normalized(raw.get("siglaUnidadeFornecimento"))
            description = normalized(raw.get("descricaoDetalhadaItem"))
            if not unit:
                raise ValueError("UNIDADE_AUSENTE")
            if not description:
                raise ValueError("ESPECIFICACAO_AUSENTE")
            capacity = numeric(raw.get("capacidadeUnidadeFornecimento"))
            measure = normalized(raw.get("siglaUnidadeMedida"))
            purchase = str(raw["idCompra"]).strip()
            item = str(raw["idItemCompra"]).strip()
            supplier = str(raw.get("niFornecedor") or "").strip()
            form = str(raw.get("forma") or "").strip()
            if not purchase.isdigit() or not item.isdigit() or not supplier or not form:
                raise ValueError("CHAVE_INCOMPLETA")
            group = (
                str(catalog),
                description,
                unit,
                None if capacity is None else format(capacity.normalize(), "f"),
                measure,
            )
            key = (purchase, item, supplier, form)
            rank = tuple(
                str(raw.get(k) or "")
                for k in ["dataHoraAtualizacaoItem", "dataHoraAtualizacaoCompra"]
            )
            row = dict(
                id=digest(key)[:20],
                key=key,
                group=group,
                purchase=purchase,
                item=item,
                supplier_hash=digest(supplier)[:16],
                organ=str(raw.get("codigoOrgao") or ""),
                date=when,
                price=price,
                quantity=quantity,
                source_ordinal=ordinal,
                rank=rank,
                source_updated=str(raw.get("dataHoraAtualizacaoItem") or ""),
                official_item=str(raw.get("idCompraItem") or ""),
                catalog=str(catalog),
                description=str(raw["descricaoDetalhadaItem"]),
                unit=unit,
                capacity=None if capacity is None else str(capacity),
                measure=measure,
            )
            compare = {
                k: v
                for k, v in row.items()
                if k not in ("source_ordinal", "rank", "source_updated")
            }
            previous = seen.get(key)
            if previous is None or rank > previous["rank"]:
                if previous:
                    reasons["VERSAO_SUPERADA"] += 1
                seen[key] = row
                conflicts.discard(key)
            elif rank < previous["rank"]:
                reasons["VERSAO_SUPERADA"] += 1
            elif canonical(compare) == canonical(
                {
                    k: v
                    for k, v in previous.items()
                    if k not in ("source_ordinal", "rank", "source_updated")
                }
            ):
                reasons["DUPLICATA_EQUIVALENTE"] += 1
            else:
                conflicts.add(key)
                reasons["CONFLITO_DE_VERSAO"] += 1
        except (ValueError, TypeError, KeyError, InvalidOperation) as error:
            reason = (
                str(error)
                if isinstance(error, ValueError) and str(error).isupper()
                else "CAMPO_INVALIDO"
            )
            reasons[reason] += 1
    for key, row in seen.items():
        if key not in conflicts:
            accepted.append(row)
    return sorted(accepted, key=lambda r: (r["date"], r["id"])), dict(reasons)


def split_groups(rows, *, train_end=TRAIN_END):
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(row)
    original_train_purchases = {r["purchase"] for r in rows if r["date"] <= train_end}
    result = []
    for group, members in sorted(groups.items(), key=lambda p: canonical(p[0])):
        before = [r for r in members if r["date"] <= train_end]
        after = [r for r in members if r["date"] > train_end]
        # Não usa frequência futura para selecionar treino.
        before_counts = Counter(r["purchase"] for r in before)
        after_counts = Counter(r["purchase"] for r in after)
        train = [
            r for r in before if before_counts[r["purchase"]] <= 5 and r["quantity"] is not None
        ]
        test = [
            r
            for r in after
            if after_counts[r["purchase"]] <= 5
            and r["purchase"] not in original_train_purchases
            and r["quantity"] is not None
        ]
        purchases = Counter(r["purchase"] for r in train)
        issues = []
        limits = [
            ("treino_menor_100", len(train) >= 100),
            ("teste_menor_30", len(test) >= 30),
            ("compras_treino_menor_20", len(purchases) >= 20),
            ("compras_teste_menor_10", len({r["purchase"] for r in test}) >= 10),
            ("orgaos_treino_menor_3", len({r["organ"] for r in train if r["organ"]}) >= 3),
            ("fornecedores_treino_menor_3", len({r["supplier_hash"] for r in train}) >= 3),
            (
                "compra_acima_10pct",
                bool(train) and max(purchases.values(), default=0) / len(train) <= 0.10,
            ),
        ]
        issues = [name for name, passed in limits if not passed]
        exploratory = (
            len(train) >= 20
            and len(test) >= 5
            and len(purchases) >= 10
            and len({r["purchase"] for r in test}) >= 3
        )
        result.append(
            dict(
                id=digest(group)[:16],
                group=group,
                train=train,
                test=test,
                eligible=not issues,
                exploratory=exploratory,
                blockers=issues,
                raw_train=len(before),
                raw_test=len(after),
                excluded_bulk_train=sum(before_counts[r["purchase"]] > 5 for r in before),
                excluded_bulk_test=sum(after_counts[r["purchase"]] > 5 for r in after),
                excluded_cross_purchase=sum(
                    r["purchase"] in original_train_purchases for r in after
                ),
                train_updates_after_cut=sum(
                    r["source_updated"][:10] > str(train_end) for r in train
                ),
            )
        )
    return result
