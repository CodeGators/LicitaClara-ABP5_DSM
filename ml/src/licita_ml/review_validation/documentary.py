"""Conferência por chaves exatas; não equivale a parecer humano independente."""

from decimal import Decimal, InvalidOperation

from licita_ml.experiments.data import canonical, normalized
from licita_ml.review_validation.acquisition import pages, snapshot

ENDPOINTS = {
    "compra": "/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id",
    "itens": "/modulo-contratacoes/2.1_consultarItensContratacoes_PNCP_14133_Id",
    "resultados": "/modulo-contratacoes/3.1_consultarResultadoItensContratacoes_PNCP_14133_Id",
}


def decimal(value):
    try:
        return Decimal(str(value)) if value is not None else None
    except InvalidOperation:
        return None


def latest(rows):
    if not rows:
        return []
    ranks = [
        str(row.get("dataAtualizacaoPncp") or row.get("dataInclusaoPncp") or "") for row in rows
    ]
    newest = max(ranks)
    selected = {
        canonical(row): row for row, rank in zip(rows, ranks, strict=True) if rank == newest
    }
    return list(selected.values())


def textual_purchase(raw):
    value = str(raw.get("idCompraItem") or "")
    item = str(raw.get("numeroItemCompra") or "")
    original = str(raw["idCompra"])
    uasg = str(raw.get("codigoUasg") or "")
    if (
        len(value) == 22
        and value.isdigit()
        and item.isdigit()
        and int(value[-5:]) == int(item)
        and int(value[:-5]) == int(original)
        and len(uasg) == 6
        and value[:6] == uasg
    ):
        return value[:-5]
    return original


def reconcile(raw, items, results):
    official = str(raw.get("idCompraItem") or "")
    purchase = textual_purchase(raw)
    item_matches = [
        r
        for r in items
        if str(r.get("idCompraItem")) == official and str(r.get("idCompra")) == purchase
    ]
    result_matches = [
        r
        for r in results
        if str(r.get("idCompraItem")) == official
        and str(r.get("idCompra")) == purchase
        and str(r.get("niFornecedor")) == str(raw.get("niFornecedor"))
        and not r.get("dataCancelamentoPncp")
        and r.get("situacaoCompraItemResultadoId") in (None, 1, "1")
    ]
    original_item_versions = len(item_matches)
    item_matches = latest(item_matches)
    if len({str(r.get("sequencialResultado")) for r in result_matches}) <= 1:
        result_matches = latest(result_matches)
    checks = {
        "versoes_item_encontradas": original_item_versions,
        "id_item_fonte": official,
        "itens_mesma_chave": len(item_matches),
        "resultados_mesma_chave_fornecedor": len(result_matches),
        "estado": "inconclusivo_sem_vinculo",
    }
    if len(item_matches) != 1 or len(result_matches) != 1:
        return checks
    item, result = item_matches[0], result_matches[0]
    price = decimal(result.get("valorUnitarioHomologado"))
    quantity = decimal(result.get("quantidadeHomologada"))
    unit = normalized(item.get("unidadeMedida"))
    expected_unit = normalized(raw.get("siglaUnidadeFornecimento"))
    # Somente sinônimo explícito do fornecimento, não conversão de embalagem.
    unit_matches = unit in {"un", "unidade", "unidades"} and expected_unit == "un"
    checks.update(
        preco_referencia=str(raw.get("precoUnitario")),
        preco_resultado=None if price is None else str(price),
        quantidade_referencia=str(raw.get("quantidade")),
        quantidade_homologada=None if quantity is None else str(quantity),
        quantidade_estimada_item=str(item.get("quantidade")),
        unidade_item=item.get("unidadeMedida"),
        unidade_compativel=unit_matches,
        descricao_item=item.get("descricaodetalhada") or item.get("descricaoResumida"),
        catalogo_item=item.get("codItemCatalogo"),
        preco_confere=price is not None and price == decimal(raw.get("precoUnitario")),
        quantidade_confere=quantity is not None and quantity == decimal(raw.get("quantidade")),
        atualizado_resultado=result.get("dataAtualizacaoPncp"),
        data_resultado=result.get("dataResultadoPncp"),
    )
    catalog = item.get("codItemCatalogo")
    checks["catalogo_complementar_status"] = (
        "ausente"
        if catalog is None
        else "confere"
        if str(catalog) == str(raw["codigoItemCatalogo"])
        else "divergente"
    )
    if checks["catalogo_complementar_status"] == "divergente":
        checks["estado"] = "nao_comparavel_documentado"
    elif not unit:
        checks["estado"] = "inconclusivo_documentacao"
    elif not unit_matches:
        checks["estado"] = "nao_comparavel_documentado"
    elif price is None or quantity is None:
        checks["estado"] = "inconclusivo_documentacao"
    elif not checks["preco_confere"] or not checks["quantidade_confere"]:
        checks["estado"] = "divergencia_entre_snapshots"
    else:
        checks["estado"] = "corroborado_estruturalmente"
    return checks


def review_case(case, raw):
    sources, failures, payloads = [], [], {}
    purchase = textual_purchase(raw)
    for kind, endpoint in ENDPOINTS.items():
        try:
            rows, provenance = pages(endpoint, {"tipo": "idCompra", "codigo": purchase})
            payloads[kind] = rows
            sources.extend(provenance)
        except (OSError, ValueError, KeyError) as error:
            payloads[kind] = []
            failures.append({"modulo": kind, "tipo": type(error).__name__, "motivo": str(error)})
    check = reconcile(raw, payloads["itens"], payloads["resultados"])
    contracts = [r for r in payloads["compra"] if str(r.get("idCompra")) == purchase]
    documents = []
    pncp_url = None
    if len(contracts) == 1:
        contract = contracts[0]
        check["orgao"] = contract.get("orgaoEntidadeRazaoSocial")
        check["uf"] = contract.get("unidadeOrgaoUfSigla")
        check["objeto"] = contract.get("objetoCompra")
        check["processo"] = contract.get("processo")
        control = contract.get("numeroControlePNCP")
        if control:
            try:
                cnpj, _, rest = control.split("-")
                sequence, year = rest.split("/")
                pncp_url = f"https://pncp.gov.br/app/editais/{cnpj}/{year}/{int(sequence)}"
                url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{year}/{int(sequence)}/arquivos"
                docs, meta = snapshot(url)
                sources.append(meta)
                if not isinstance(docs, list):
                    raise ValueError("Lista de documentos incompatível")
                documents = docs
                if (
                    check["estado"] == "inconclusivo_sem_vinculo"
                    and check["itens_mesma_chave"] == 1
                ):
                    item_number = int(str(raw["idCompraItem"])[-5:])
                    result_url = (
                        f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/"
                        f"{year}/{int(sequence)}/itens/{item_number}/resultados"
                    )
                    direct_results, result_meta = snapshot(result_url)
                    sources.append(result_meta)
                    if not isinstance(direct_results, list):
                        raise ValueError("Resultados PNCP incompatíveis")
                    normalized_results = [
                        result
                        | {
                            "idCompra": purchase,
                            "idCompraItem": str(raw["idCompraItem"]),
                            "dataCancelamentoPncp": result.get("dataCancelamento"),
                            "dataAtualizacaoPncp": result.get("dataAtualizacao"),
                            "dataResultadoPncp": result.get("dataResultado"),
                        }
                        for result in direct_results
                        if int(result.get("numeroItem", -1)) == item_number
                        and result.get("numeroControlePNCPCompra") == control
                    ]
                    direct_check = reconcile(raw, payloads["itens"], normalized_results)
                    check.update(direct_check)
                    check["modulo_resultado"] = "pncp_direto_por_controle_e_numero_item"
                    check["vinculo_resultado_url"] = result_url
            except (OSError, ValueError, KeyError) as error:
                failures.append(
                    {"modulo": "documentos", "tipo": type(error).__name__, "motivo": str(error)}
                )
    return {
        "id": case["id"],
        "id_compra": purchase,
        "id_compra_original": case["id_compra"],
        "vinculo_textual_explicito": purchase != case["id_compra"],
        "conferencia": check,
        "pncp_url": pncp_url,
        "documentos": documents,
        "fontes": sources,
        "falhas": failures,
        "tipo_revisao": "assistida_nao_cega_sem_parecer_humano",
        "utilidade_rotulada": False,
    }
