"""Atributos do snapshot operacional; nenhuma escrita em processos ou análises."""

from collections import defaultdict

import sqlalchemy as sa

from licita_ml.analytical.rules import (
    concentration,
    contract_interval,
    digest,
    estimated_difference,
    event_window,
    feature,
    frequency,
    normalize,
    participant_count,
)


def read_base(repository, connection, base_id, max_rows=20000):
    tables = repository.tables
    base = (
        connection.execute(
            sa.select(tables["versoes_base"]).where(
                tables["versoes_base"].c.id == base_id,
                tables["versoes_base"].c.status == "validada",
            )
        )
        .mappings()
        .one_or_none()
    )
    if base is None:
        raise ValueError("Base operacional não encontrada ou não validada")
    data = {}
    for name in [
        "processos_versoes",
        "itens_versoes",
        "resultados_itens",
        "participacoes",
        "contratos_versoes",
        "contratos_processos",
        "proveniencias_registros",
    ]:
        rows = (
            connection.execute(
                sa.select(tables[name]).where(tables[name].c.base_id == base_id).limit(max_rows + 1)
            )
            .mappings()
            .all()
        )
        if len(rows) > max_rows:
            raise ValueError("Snapshot operacional excede limite analítico; reduzir recorte")
        data[name] = [dict(row) for row in rows]
    import_ids = {r["importacao_id"] for r in data["proveniencias_registros"]}
    data["importacoes"] = {
        row.id: row.arquivo_id
        for row in connection.execute(
            sa.select(tables["importacoes"].c.id, tables["importacoes"].c.arquivo_id).where(
                tables["importacoes"].c.id.in_(import_ids)
            )
        )
    }
    catalogue_ids = {row["catalogo_id"] for row in data["itens_versoes"] if row["catalogo_id"]}
    data["catalogos"] = {
        row.id: row.codigo
        for row in connection.execute(
            sa.select(tables["itens_catalogo"].c.id, tables["itens_catalogo"].c.codigo).where(
                tables["itens_catalogo"].c.id.in_(catalogue_ids)
            )
        )
    }
    return dict(base), data


def operational_features(base, data, references, policy):
    processes = {r["id"]: r for r in data["processos_versoes"]}
    items = {r["id"]: r for r in data["itens_versoes"]}
    events, participants, links, contracts, origins = (
        [],
        defaultdict(list),
        defaultdict(list),
        {},
        defaultdict(list),
    )
    for row in data["resultados_itens"]:
        events.append(
            {
                **row,
                "processo_id": items[row["item_versao_id"]]["processo_versao_id"],
                "orgao_id": processes[items[row["item_versao_id"]]["processo_versao_id"]][
                    "orgao_id"
                ],
            }
        )
    for row in data["participacoes"]:
        participants[row["item_versao_id"]].append(row)
    for row in data["contratos_versoes"]:
        contracts[row["id"]] = row
    for row in data["contratos_processos"]:
        links[row["processo_versao_id"]].append(contracts[row["contrato_versao_id"]])
    for row in data["proveniencias_registros"]:
        for key in ["item_versao_id", "resultado_item_id"]:
            if row[key] is not None:
                origins[row[key]].append(
                    {
                        "importacao_id": str(row["importacao_id"]),
                        "arquivo_id": str(data["importacoes"][row["importacao_id"]]),
                        "membro": row["membro_arquivo"],
                        "ordinal": row["numero_linha"],
                    }
                )
    output = []
    for event in events:
        item = items[event["item_versao_id"]]
        parent = processes[item["processo_versao_id"]]
        window_start, window_end = event_window(event["data_resultado"], policy)
        same_organ = [r for r in events if r["orgao_id"] == parent["orgao_id"]]
        attributes = {
            "diferenca_estimado_homologado_unitario": estimated_difference(
                item["valor_unitario_estimado"],
                event["valor_unitario_homologado"],
                item["unidade_medida"],
            ),
            "numero_participantes": participant_count(
                participants[item["id"]],
                base["qualidade"].get("historico_participantes_completo") is True,
                as_of=min(event["data_resultado"], policy.end)
                if event["data_resultado"]
                else policy.end,
            ),
            "frequencia_fornecedor_orgao_recorte": frequency(
                same_organ,
                event["fornecedor_id"],
                start=window_start,
                end=window_end,
                exclude_process=item["processo_versao_id"],
            ),
            "hhi_orgao_recorte": concentration(
                same_organ,
                start=window_start,
                end=window_end,
                exclude_process=item["processo_versao_id"],
            ),
            "frequencia_fornecedor_orgao_completa": feature(
                reason="UNIVERSO_COMPLETO_ORGAO_NAO_COMPROVADO"
            ),
            "hhi_orgao_completo": feature(reason="UNIVERSO_COMPLETO_ORGAO_NAO_COMPROVADO"),
            "publicacao_assinatura_dias": contract_interval(
                parent["data_publicacao"],
                links[parent["id"]],
                min(event["data_resultado"], policy.end) if event["data_resultado"] else policy.end,
            ),
            "preco_mediana": feature(reason="COMPARABILIDADE_DOCUMENTAL_NAO_COMPROVADA"),
        }
        # Vínculo de referência só por ID oficial preservado no snapshot bruto do item.
        official = str(
            item["atributos_origem"].get("idCompraItem")
            or item["atributos_origem"].get("id_compra_item")
            or ""
        )
        matches = [
            r for r in references if r["item_oficial"] == official and not r["motivos_exclusao"]
        ]
        supplier = event["atributos_origem"].get("niFornecedor") or event["atributos_origem"].get(
            "ni_fornecedor"
        )
        matching_spec = [
            r
            for r in matches
            if supplier is not None
            and r["catalogo"] == data["catalogos"].get(item["catalogo_id"])
            and r["fornecedor_hash"] == digest(str(supplier))[:16]
            and normalize(item["descricao"]) == r["especificacao"][1]
            and normalize(item["unidade_medida"]) == r["especificacao"][2]
            and r["preco_unitario"] == event["valor_unitario_homologado"]
            and r["quantidade"] == event["quantidade_homologada"]
            and event["data_resultado"] is not None
            and r["data_resultado"] <= event["data_resultado"]
        ]
        same_result = [
            r
            for r in events
            if not r["cancelado"]
            and r["item_versao_id"] == item["id"]
            and r["fornecedor_id"] == event["fornecedor_id"]
            and r["valor_unitario_homologado"] == event["valor_unitario_homologado"]
            and r["quantidade_homologada"] == event["quantidade_homologada"]
        ]
        if not matching_spec:
            attributes["preco_mediana"] = feature(
                reason="SEM_REFERENCIA_COM_VINCULO_E_ESPECIFICACAO_EXATOS"
            )
        # Não transfere a mediana congelada de treino para compras anteriores ao corte.
        elif (
            event["data_resultado"] is not None
            and event["data_resultado"] > policy.train_end
            and len(matching_spec) == 1
            and len(same_result) == 1
        ):
            attributes["preco_mediana"] = {
                **matching_spec[0]["atributos"]["preco_mediana"],
                "comparabilidade_documental": "nao_verificada",
            }
        if (
            event["cancelado"]
            or event["data_resultado"] is None
            or event["data_resultado"] > policy.end
            or event["data_resultado"] < policy.start
        ):
            reason = (
                "RESULTADO_CANCELADO"
                if event["cancelado"]
                else "DATA_RESULTADO_AUSENTE"
                if event["data_resultado"] is None
                else "RESULTADO_ANTERIOR_AO_PERIODO"
                if event["data_resultado"] < policy.start
                else "RESULTADO_POSTERIOR_AO_CORTE"
            )
            attributes = {key: feature(reason=reason) for key in attributes}
        output.append(
            {
                "id": str(event["id"]),
                "item_id": str(item["item_id"]),
                "item_versao_id": str(item["id"]),
                "processo_versao_id": str(parent["id"]),
                "fornecedor_id": str(event["fornecedor_id"]),
                "data_resultado": event["data_resultado"],
                "atributos": attributes,
                "proveniencias": origins[event["id"]] + origins[item["id"]],
                "universo": {
                    "tipo": "somente_recorte_da_base",
                    "recorte": base["recorte"],
                    "data_da_janela": "data_resultado",
                    "base_id": str(base["id"]),
                    "periodo_base": [str(base["periodo_inicio"]), str(base["periodo_fim"])],
                    "inicio_janela": str(window_start),
                    "fim_janela": str(window_end),
                    "compra_atual_excluida": True,
                    "mesmo_dia_excluido": True,
                },
            }
        )
    covered_items = {event["item_versao_id"] for event in events}
    names = [
        "diferenca_estimado_homologado_unitario",
        "numero_participantes",
        "frequencia_fornecedor_orgao_recorte",
        "hhi_orgao_recorte",
        "frequencia_fornecedor_orgao_completa",
        "hhi_orgao_completo",
        "publicacao_assinatura_dias",
        "preco_mediana",
    ]
    for item in items.values():
        if item["id"] not in covered_items:
            output.append(
                {
                    "id": str(item["id"]) + ":sem-resultado",
                    "item_id": str(item["item_id"]),
                    "item_versao_id": str(item["id"]),
                    "processo_versao_id": str(item["processo_versao_id"]),
                    "fornecedor_id": None,
                    "data_resultado": None,
                    "atributos": {key: feature(reason="SEM_RESULTADO_CONHECIDO") for key in names},
                    "proveniencias": origins[item["id"]],
                    "universo": {"tipo": "somente_recorte_da_base", "base_id": str(base["id"])},
                }
            )
    return sorted(output, key=lambda row: row["id"])
