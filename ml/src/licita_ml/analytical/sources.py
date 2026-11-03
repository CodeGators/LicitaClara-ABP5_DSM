"""Leitura de aquisições registradas; originais, ordinais e conflitos permanecem rastreáveis."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from licita_ml.analytical.rules import reference_row
from licita_ml.readers import staged


def timestamp(value):
    if not value:
        return "ausente", ""
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return "local_sem_fuso", parsed.isoformat()
    return "com_fuso", parsed.astimezone(timezone.utc).isoformat()


def read_history(objects, files, settings, max_rows=20000):
    candidates = defaultdict(list)
    rejects, sources = [], []
    totals, discarded = Counter(), Counter()
    for file in sorted(files, key=lambda f: str(f["id"])):
        file_id = str(file["id"])
        if file["fonte"] != "comprasgov" or not file["modulo"].startswith("historico/material/"):
            raise ValueError("Arquivo não é histórico operacional de materiais")
        with staged(objects, file, settings) as stream:
            envelope = json.load(stream, parse_float=Decimal)
        if (
            envelope.get("schema") != "licita-json-v1"
            or envelope.get("kind") != "material_historico_api"
        ):
            raise ValueError("Contrato do histórico incompatível")
        sources.append(
            {
                "arquivo_id": file_id,
                "sha256": file["sha256"],
                "bytes": file["tamanho_bytes"],
                "chave_objeto": file["chave_objeto"],
                "url": file["url_origem"],
                "registrado_em": str(file["coletado_em"]),
                "consulta": envelope["query"],
            }
        )
        for expected_page, page in enumerate(envelope["paginas"], 1):
            if page["pagina"] != expected_page or "resposta_original" not in page:
                raise ValueError("Página sem original ou sequência inválida")
            raw = page["resposta_original"].encode()
            original = json.loads(raw, parse_float=Decimal)
            if (
                page.get("origem_cache", {}).get("sha256", hashlib.sha256(raw).hexdigest())
                != hashlib.sha256(raw).hexdigest()
            ):
                raise ValueError("Original diverge do hash do cache")
            for ordinal, record in enumerate(original["resultado"], 1):
                totals[file_id] += 1
                if sum(totals.values()) > max_rows:
                    raise ValueError(
                        "Histórico excede limite de 20 mil referências; reduzir recorte"
                    )
                origin = {
                    "arquivo_id": file_id,
                    "membro": f"pagina-{expected_page}.json",
                    "ordinal": ordinal,
                    "pagina_sha256": hashlib.sha256(raw).hexdigest(),
                }
                try:
                    row = reference_row(record)
                    if row["catalogo"] != envelope["query"]["catalogo"]:
                        raise ValueError("CATALOGO_DIVERGENTE_DA_CONSULTA")
                    row["proveniencias"] = [origin]
                    row["_rank"] = tuple(timestamp(v) for v in row["atualizacoes"])
                    candidates[row["chave"]].append(row)
                except (ValueError, TypeError, KeyError, ArithmeticError) as error:
                    reason = getattr(
                        error, "code", str(error) if str(error).isupper() else "CAMPO_INVALIDO"
                    )
                    rejects.append({**origin, "motivo": reason})
    resolved = []
    for versions in candidates.values():
        mixed = any(
            len({r["_rank"][i][0] for r in versions if r["_rank"][i][0] != "ausente"}) > 1
            for i in (0, 1)
        )
        if mixed:
            for row in versions:
                rejects.append(
                    {**row["proveniencias"][0], "motivo": "FUSOS_INCOMPARAVEIS_ENTRE_VERSOES"}
                )
            continue
        newest = max(r["_rank"] for r in versions)
        latest = [r for r in versions if r["_rank"] == newest]

        def semantic(row):
            return {
                k: v for k, v in row.items() if k not in {"_rank", "proveniencias", "atualizacoes"}
            }

        if any(semantic(r) != semantic(latest[0]) for r in latest):
            for row in versions:
                rejects.append({**row["proveniencias"][0], "motivo": "CONFLITO_SEM_PRECEDENCIA"})
            continue
        chosen = dict(latest[0])
        chosen.pop("_rank")
        chosen["proveniencias"] = [origin for r in latest for origin in r["proveniencias"]]
        resolved.append(chosen)
        winner = latest[0]["proveniencias"][0]
        for row in versions:
            origin = row["proveniencias"][0]
            if origin != winner:
                discarded[origin["arquivo_id"]] += 1
    accepted = Counter(r["proveniencias"][0]["arquivo_id"] for r in resolved)
    rejected = Counter(r["arquivo_id"] for r in rejects)
    reconciliation = {
        file_id: {
            "total": total,
            "aceitos": accepted[file_id],
            "rejeitados": rejected[file_id],
            "descartados": discarded[file_id],
        }
        for file_id, total in totals.items()
    }
    assert all(
        r["total"] == r["aceitos"] + r["rejeitados"] + r["descartados"]
        for r in reconciliation.values()
    )
    return sorted(resolved, key=lambda r: r["id"]), rejects, sources, reconciliation
