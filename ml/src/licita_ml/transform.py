"""Transformações v1; chaves oficiais são texto, preços não são imputados."""

import re

from licita_ml.normalize import RowError, boolean, day, instant, integer, money, text


def snake(key):
    return re.sub(
        r"([a-z0-9])([A-Z])", r"\1_\2", re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    ).lower()


def canonical_row(kind, raw, query):
    r = {snake(k): v for k, v in raw.items()}

    def req(k):
        return text(r.get(k), True)

    def val(k):
        return text(r.get(k))

    def num(k):
        return money(r.get(k))

    source_rank = 2 if kind.endswith("_api") else 1
    rank = (
        text(
            r.get("data_atualizacao_pncp")
            or r.get("data_hora_atualizacao_item")
            or r.get("data_hora_alteracao")
            or r.get("data_atualizacao")
            or r.get("data_hora_inclusao")
            or r.get("data_publicacao_pncp")
        )
        or ""
    )
    if rank:
        rank = instant(rank).isoformat()
    if kind in ("compra", "compra_api"):
        key = req("id_compra")
        values = dict(
            orgao_codigo=req("codigo_orgao"),
            orgao_nome=req("orgao_entidade_razao_social"),
            cnpj=val("orgao_entidade_cnpj"),
            modalidade_codigo=val("codigo_modalidade"),
            modalidade_nome=val("modalidade_nome"),
            numero_compra=req("numero_compra"),
            numero_controle_pncp=val("numero_controle_pncp"),
            numero_processo=val("processo"),
            ano=integer(r.get("ano_compra_pncp"), True),
            objeto=req("objeto_compra"),
            situacao=val("situacao_compra_nome_pncp") or "desconhecida",
            codigo_unidade=req("unidade_orgao_codigo_unidade"),
            nome_unidade=val("unidade_orgao_nome_unidade"),
            data_publicacao=day(r.get("data_publicacao_pncp")),
            data_abertura=day(r.get("data_abertura_proposta_pncp")),
            valor_estimado=num("valor_total_estimado"),
            valor_homologado=num("valor_total_homologado"),
        )
        domain = "processo"
    elif kind in ("compra_item", "itens_api"):
        key = req("id_compra_item")
        values = dict(
            compra=req("id_compra"),
            numero_item=req("numero_item_pncp"),
            descricao=text(
                r.get("descricao_detalhada")
                or r.get("descricaodetalhada")
                or r.get("descricao_resumida"),
                True,
            ),
            unidade_medida=val("unidade_medida"),
            quantidade=num("quantidade"),
            valor_unitario_estimado=num("valor_unitario_estimado"),
            orcamento_sigiloso=boolean(r.get("orcamento_sigiloso")),
            catalogo=val("cod_item_catalogo"),
        )
        domain = "item"
    elif kind in ("item_resultado", "resultados_api"):
        seq = integer(r.get("sequencial_resultado"), True)
        key = "|".join([req("id_compra_item"), req("ni_fornecedor"), str(seq)])
        values = dict(
            compra=req("id_compra"),
            item=req("id_compra_item"),
            fornecedor=req("ni_fornecedor"),
            fornecedor_nome=req("nome_razao_social_fornecedor"),
            sequencial_resultado=seq,
            chave_origem=val("srk_item_resultado") or key,
            situacao=val("situacao_compra_item_resultado_nome") or "desconhecida",
            cancelado=bool(val("data_cancelamento_pncp")),
            quantidade_homologada=num("quantidade_homologada"),
            valor_unitario_homologado=num("valor_unitario_homologado"),
            valor_total_homologado=num("valor_total_homologado"),
            data_resultado=day(r.get("data_resultado_pncp")),
        )
        domain = "resultado"
    elif kind == "material":
        key = "|".join(
            [req("id_compra"), req("id_item_compra"), req("ni_fornecedor"), req("forma")]
        )
        price = money(r.get("preco_unitario"), positive=True)
        if price is None:
            raise RowError("PRECO_AUSENTE")
        values = dict(
            compra=req("id_compra"),
            item=req("id_compra_item"),
            id_item_oficial=req("id_item_compra"),
            catalogo=req("codigo_item_catalogo"),
            descricao=req("descricao_item"),
            fornecedor=req("ni_fornecedor"),
            fornecedor_nome=req("nome_fornecedor"),
            unidade_fornecimento=val("nome_unidade_fornecimento"),
            sigla_unidade_fornecimento=val("sigla_unidade_fornecimento"),
            capacidade_fornecimento=num("capacidade_unidade_fornecimento"),
            sigla_medida=val("sigla_unidade_medida"),
            quantidade=num("quantidade"),
            preco_unitario=price,
            data_compra=day(r.get("data_compra"), True),
            codigo_grupo=val("codigo_grupo"),
            codigo_classe=val("codigo_classe"),
            codigo_pdm=val("codigo_pdm"),
        )
        domain = "referencia"
    elif kind == "propostas":
        key = req("id")
        classification = integer(r.get("classificacao"))
        if classification is not None and classification < 1:
            raise RowError("CLASSIFICACAO_INVALIDA")
        values = dict(
            compra=req("id_compra"),
            item=req("id_compra_item"),
            fornecedor=val("identificacao_participante"),
            fornecedor_nome=val("nome_participante"),
            valor_proposta=num("valor_proposta_calculado"),
            valor_lance=num("valor_lance_calculado"),
            valor_negociado=num("valor_negociado_julgamento_calculado"),
            classificacao=classification,
            situacao_proposta=val("situacao_proposta"),
            situacao_item=val("situacao_item"),
            homologado=boolean(r.get("homologado")),
            incluido_na_origem_em=instant(r.get("data_hora_inclusao")),
            alterado_na_origem_em=instant(r.get("data_hora_alteracao")),
        )
        domain = "participacao"
    elif kind == "contratos_api":
        key = req("numero_controle_pncp_contrato")
        values = dict(
            compra=req("id_compra"),
            controle_compra=val("numero_controle_pncp_compra"),
            numero_contrato=req("numero_contrato"),
            numero_controle_pncp=key,
            fornecedor=val("ni_fornecedor"),
            fornecedor_nome=val("nome_razao_social_fornecedor"),
            objeto=val("objeto"),
            codigo_unidade_gestora=val("codigo_unidade_gestora"),
            data_vigencia_inicio=day(r.get("data_vigencia_inicial")),
            data_vigencia_fim=day(r.get("data_vigencia_final")),
            valor_global=num("valor_global"),
            valor_acumulado=num("valor_acumulado"),
            excluido=boolean(r.get("contrato_excluido")),
        )
        domain = "contrato"
    elif kind == "contrato_pncp":
        key = req("numero_controle_pncp")
        values = dict(
            data_assinatura=day(r.get("data_assinatura")),
            controle_compra=val("numero_controle_pncp_compra"),
        )
        domain = "detalhe_contrato"
    else:
        seq = integer(r.get("sequencial_documento"), True)
        if seq < 1:
            raise RowError("SEQUENCIAL_INVALIDO")
        parent = "compras" if kind == "documentos_compra" else "contratos"
        prefix = f"orgaos/{query['cnpj']}/{parent}/{query['ano']}/{query['sequencial']}"
        key = f"{prefix}/arquivos/{seq}"
        values = dict(
            parent_kind=parent,
            parent_control=(
                f"{query['cnpj']}-{'1' if parent == 'compras' else '2'}-"
                f"{int(query['sequencial']):06d}/{query['ano']}"
            ),
            sequencial_documento=seq,
            tipo_codigo=val("tipo_documento_id"),
            tipo_nome=val("tipo_documento_nome"),
            titulo=val("titulo"),
            url_origem=req("url"),
            ativo=boolean(r.get("status_ativo")),
            publicado_na_origem_em=instant(r.get("data_publicacao_pncp")),
        )
        domain = "documento"
    return domain, key, (rank, source_rank), values
