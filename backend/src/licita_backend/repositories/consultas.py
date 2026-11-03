"""Consultas de snapshots imutáveis, sempre limitadas à base selecionada."""

from collections import defaultdict

import sqlalchemy as sa

from licita_backend.api.errors import QueryError
from licita_backend.models import collection as c
from licita_backend.models import complementary as k
from licita_backend.models import procurement as p

PV, IV, RI = p.processos_versoes, p.itens_versoes, p.resultados_itens


class QueryRepository:
    def __init__(self, session):
        self.session = session

    def base(self, base_id=None, optional=False):
        query = sa.select(c.versoes_base).where(c.versoes_base.c.status == "validada")
        if base_id is not None:
            query = query.where(c.versoes_base.c.id == base_id)
        row = (
            self.session.execute(
                query.order_by(c.versoes_base.c.criado_em.desc(), c.versoes_base.c.id.desc()).limit(
                    1
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None and not optional:
            raise QueryError("base_nao_encontrada", "Não há base validada para esta consulta.")
        return row

    def page(self, query, filters, base_id):
        total = self.session.scalar(
            sa.select(sa.func.count()).select_from(query.order_by(None).subquery())
        )
        rows = (
            self.session.execute(
                query.limit(filters.tamanho_pagina).offset(
                    (filters.pagina - 1) * filters.tamanho_pagina
                )
            )
            .mappings()
            .all()
        )
        return {
            "dados": [dict(row) for row in rows],
            "meta": {
                "base_id": base_id,
                "pagina": filters.pagina,
                "tamanho_pagina": filters.tamanho_pagina,
                "total": total,
                "total_paginas": (total + filters.tamanho_pagina - 1) // filters.tamanho_pagina,
            },
        }

    def process_query(self, base_id):
        # Subconsultas independentes impedem produto entre itens, resultados e anexos.
        item_count = (
            sa.select(sa.func.count())
            .where(IV.c.processo_versao_id == PV.c.id, IV.c.base_id == base_id)
            .correlate(PV)
            .scalar_subquery()
        )
        amount = (
            sa.select(
                sa.case(
                    (
                        sa.func.count(RI.c.id) == sa.func.count(RI.c.valor_total_homologado),
                        sa.func.sum(RI.c.valor_total_homologado),
                    ),
                    else_=None,
                )
            )
            .select_from(
                IV.join(RI, (RI.c.item_versao_id == IV.c.id) & (RI.c.base_id == IV.c.base_id))
            )
            .where(
                IV.c.processo_versao_id == PV.c.id,
                IV.c.base_id == base_id,
                RI.c.cancelado.is_(False),
            )
            .correlate(PV)
            .scalar_subquery()
        )
        latest_result = (
            sa.select(sa.func.max(RI.c.data_resultado))
            .select_from(
                IV.join(RI, (RI.c.item_versao_id == IV.c.id) & (RI.c.base_id == IV.c.base_id))
            )
            .where(
                IV.c.processo_versao_id == PV.c.id,
                IV.c.base_id == base_id,
                RI.c.cancelado.is_(False),
            )
            .correlate(PV)
            .scalar_subquery()
        )
        missing_amount = (
            sa.select(sa.func.count())
            .select_from(
                IV.join(RI, (RI.c.item_versao_id == IV.c.id) & (RI.c.base_id == IV.c.base_id))
            )
            .where(
                IV.c.processo_versao_id == PV.c.id,
                IV.c.base_id == base_id,
                RI.c.cancelado.is_(False),
                RI.c.valor_total_homologado.is_(None),
            )
            .correlate(PV)
            .scalar_subquery()
        )
        return (
            sa.select(
                PV.c.processo_id.label("id"),
                PV.c.id.label("processo_versao_id"),
                p.processos.c.fonte,
                p.processos.c.chave_oficial,
                PV.c.numero_compra,
                PV.c.numero_processo,
                PV.c.numero_controle_pncp,
                PV.c.ano,
                PV.c.objeto,
                PV.c.situacao,
                PV.c.orgao_id,
                PV.c.orgao_nome,
                PV.c.modalidade_id,
                p.modalidades.c.nome.label("modalidade_nome"),
                PV.c.data_publicacao,
                PV.c.data_resultado,
                latest_result.label("ultima_data_resultado_itens_recorte"),
                PV.c.valor_estimado.label("valor_estimado_processo"),
                PV.c.valor_homologado.label("valor_homologado_processo"),
                amount.label("valor_homologado_itens_recorte"),
                missing_amount.label("resultados_sem_valor_total_recorte"),
                item_count.label("quantidade_itens_recorte"),
                PV.c.codigo_unidade,
                PV.c.nome_unidade,
                PV.c.data_abertura,
                PV.c.orcamento_sigiloso,
            )
            .select_from(
                PV.join(p.processos, p.processos.c.id == PV.c.processo_id).outerjoin(
                    p.modalidades, p.modalidades.c.id == PV.c.modalidade_id
                )
            )
            .where(PV.c.base_id == base_id)
        )

    def result_exists(self, base_id, *conditions):
        return (
            sa.select(1)
            .select_from(
                IV.join(RI, (RI.c.item_versao_id == IV.c.id) & (RI.c.base_id == IV.c.base_id))
            )
            .where(
                IV.c.base_id == base_id,
                IV.c.processo_versao_id == PV.c.id,
                RI.c.cancelado.is_(False),
                *conditions,
            )
            .correlate(PV)
            .exists()
        )

    def suppliers(self, rows, base_id):
        if not rows:
            return
        ids = [row["processo_versao_id"] for row in rows]
        selected = self.session.execute(
            sa.select(IV.c.processo_versao_id, RI.c.fornecedor_id, RI.c.fornecedor_nome)
            .select_from(
                IV.join(RI, (RI.c.item_versao_id == IV.c.id) & (RI.c.base_id == IV.c.base_id))
            )
            .where(
                IV.c.processo_versao_id.in_(ids), IV.c.base_id == base_id, RI.c.cancelado.is_(False)
            )
            .order_by(RI.c.data_resultado.desc().nulls_last(), RI.c.id.desc())
        ).mappings()
        grouped = defaultdict(dict)
        for row in selected:
            grouped[row["processo_versao_id"]].setdefault(
                row["fornecedor_id"],
                {
                    "id": row["fornecedor_id"],
                    "nome": row["fornecedor_nome"],
                },
            )
        for row in rows:
            row["fornecedores"] = sorted(
                grouped[row["processo_versao_id"]].values(), key=lambda s: (s["nome"], str(s["id"]))
            )

    def processes(self, base_id, filters):
        query = self.process_query(base_id)
        for field in ("orgao_id", "modalidade_id"):
            if (value := getattr(filters, field)) is not None:
                query = query.where(PV.c[field] == value)
        result_conditions = []
        if filters.fornecedor_id is not None:
            result_conditions.append(RI.c.fornecedor_id == filters.fornecedor_id)
        if filters.homologacao_inicio is not None:
            result_conditions.append(RI.c.data_resultado >= filters.homologacao_inicio)
        if filters.homologacao_fim is not None:
            result_conditions.append(RI.c.data_resultado <= filters.homologacao_fim)
        if result_conditions:
            query = query.where(self.result_exists(base_id, *result_conditions))
        value_column = (
            PV.c.valor_homologado
            if filters.escopo_valor == "processo"
            else query.selected_columns["valor_homologado_itens_recorte"]
        )
        if filters.valor_minimo is not None:
            query = query.where(value_column >= filters.valor_minimo)
        if filters.valor_maximo is not None:
            query = query.where(value_column <= filters.valor_maximo)
        if filters.busca and (search := filters.busca.strip()):
            item_match = (
                sa.select(1)
                .where(
                    IV.c.processo_versao_id == PV.c.id,
                    IV.c.base_id == base_id,
                    IV.c.descricao.icontains(search, autoescape=True),
                )
                .correlate(PV)
                .exists()
            )
            query = query.where(
                sa.or_(
                    *(
                        col.icontains(search, autoescape=True)
                        for col in (
                            PV.c.objeto,
                            PV.c.numero_processo,
                            PV.c.numero_compra,
                            p.processos.c.chave_oficial,
                        )
                    ),
                    item_match,
                    self.result_exists(
                        base_id, RI.c.fornecedor_nome.icontains(search, autoescape=True)
                    ),
                )
            )
        orders = {
            "publicacao_desc": PV.c.data_publicacao.desc().nulls_last(),
            "publicacao_asc": PV.c.data_publicacao.asc().nulls_last(),
            "valor_desc": value_column.desc().nulls_last(),
            "valor_asc": value_column.asc().nulls_last(),
            "objeto_asc": PV.c.objeto.asc(),
        }
        result = self.page(
            query.order_by(orders[filters.ordenacao], PV.c.processo_id), filters, base_id
        )
        self.suppliers(result["dados"], base_id)
        return result

    def process(self, base_id, process_id):
        row = (
            self.session.execute(self.process_query(base_id).where(PV.c.processo_id == process_id))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise QueryError("processo_nao_encontrado", "Processo não encontrado nesta base.")
        data = dict(row)
        self.suppliers([data], base_id)
        return data

    def lookups(self, base_id, filters, kind):
        if kind == "orgaos":
            # Um ID por órgão, com nome do snapshot de publicação mais recente na base.
            selected = (
                sa.select(
                    p.orgaos.c.id.label("id"),
                    PV.c.orgao_nome.label("nome"),
                    p.orgaos.c.chave_oficial,
                    p.orgaos.c.cnpj,
                )
                .select_from(p.orgaos.join(PV, PV.c.orgao_id == p.orgaos.c.id))
                .where(PV.c.base_id == base_id)
                .distinct(p.orgaos.c.id)
                .order_by(p.orgaos.c.id, PV.c.data_publicacao.desc().nulls_last(), PV.c.id.desc())
                .subquery()
            )
            query = sa.select(selected)
            name = selected.c.nome
        elif kind == "fornecedores":
            selected = (
                sa.select(RI.c.fornecedor_id.label("id"), RI.c.fornecedor_nome.label("nome"))
                .where(RI.c.base_id == base_id, RI.c.cancelado.is_(False))
                .distinct(RI.c.fornecedor_id)
                .order_by(
                    RI.c.fornecedor_id, RI.c.data_resultado.desc().nulls_last(), RI.c.id.desc()
                )
                .subquery()
            )
            query = sa.select(selected)
            name = selected.c.nome
        else:
            query = sa.select(p.modalidades).where(
                sa.select(1)
                .where(PV.c.modalidade_id == p.modalidades.c.id, PV.c.base_id == base_id)
                .exists()
            )
            name = p.modalidades.c.nome
        if filters.busca and filters.busca.strip():
            query = query.where(name.icontains(filters.busca.strip(), autoescape=True))
        return self.page(query.order_by("nome", "id"), filters, base_id)

    def items(self, base_id, process_id, filters):
        snapshot = self.process(base_id, process_id)["processo_versao_id"]
        query = (
            sa.select(
                IV.c.item_id.label("id"),
                IV.c.id.label("item_versao_id"),
                IV.c.numero_item,
                IV.c.descricao,
                IV.c.unidade_medida,
                IV.c.quantidade,
                IV.c.valor_unitario_estimado,
                IV.c.orcamento_sigiloso,
                p.itens_catalogo.c.catalogo,
                p.itens_catalogo.c.codigo.label("codigo_catalogo"),
            )
            .select_from(IV.outerjoin(p.itens_catalogo, p.itens_catalogo.c.id == IV.c.catalogo_id))
            .where(IV.c.base_id == base_id, IV.c.processo_versao_id == snapshot)
            .order_by(IV.c.numero_item, IV.c.item_id)
        )
        result = self.page(query, filters, base_id)
        self.item_results(result["dados"], base_id)
        return result

    def item_results(self, rows, base_id):
        ids = [row["item_versao_id"] for row in rows]
        grouped = defaultdict(list)
        if ids:
            for row in self.session.execute(
                sa.select(RI)
                .where(RI.c.base_id == base_id, RI.c.item_versao_id.in_(ids))
                .order_by(RI.c.sequencial_resultado, RI.c.id)
            ).mappings():
                grouped[row["item_versao_id"]].append(dict(row))
        for row in rows:
            row["resultados"] = grouped[row["item_versao_id"]]

    def item_query(self, base_id):
        # Agregar antes dos joins mantém uma linha por item, inclusive com vários vencedores.
        totals = (
            sa.select(
                RI.c.item_versao_id,
                sa.func.count().label("resultados_ativos"),
                (sa.func.count() - sa.func.count(RI.c.valor_total_homologado)).label(
                    "resultados_sem_valor_total"
                ),
                sa.case(
                    (
                        sa.func.count() == sa.func.count(RI.c.valor_total_homologado),
                        sa.func.sum(RI.c.valor_total_homologado),
                    ),
                    else_=None,
                ).label("valor_homologado_item"),
                sa.func.max(RI.c.data_resultado).label("ultima_data_resultado"),
            )
            .where(RI.c.base_id == base_id, RI.c.cancelado.is_(False))
            .group_by(RI.c.item_versao_id)
            .subquery()
        )
        context = {
            "id": PV.c.processo_id,
            "processo_versao_id": PV.c.id,
            "fonte": p.processos.c.fonte,
            "chave_oficial": p.processos.c.chave_oficial,
            "numero_compra": PV.c.numero_compra,
            "numero_processo": PV.c.numero_processo,
            "numero_controle_pncp": PV.c.numero_controle_pncp,
            "objeto": PV.c.objeto,
            "orgao_id": PV.c.orgao_id,
            "orgao_nome": PV.c.orgao_nome,
            "modalidade_id": PV.c.modalidade_id,
            "modalidade_nome": p.modalidades.c.nome,
            "data_publicacao": PV.c.data_publicacao,
        }
        return (
            sa.select(
                IV.c.item_id.label("id"),
                IV.c.id.label("item_versao_id"),
                p.itens_processo.c.chave_oficial,
                IV.c.numero_item,
                IV.c.descricao,
                IV.c.unidade_medida,
                IV.c.quantidade,
                IV.c.valor_unitario_estimado,
                IV.c.orcamento_sigiloso,
                p.itens_catalogo.c.catalogo,
                p.itens_catalogo.c.codigo.label("codigo_catalogo"),
                totals.c.valor_homologado_item,
                sa.func.coalesce(totals.c.resultados_ativos, 0).label("resultados_ativos"),
                sa.func.coalesce(totals.c.resultados_sem_valor_total, 0).label(
                    "resultados_sem_valor_total"
                ),
                totals.c.ultima_data_resultado,
                *(column.label("processo_" + key) for key, column in context.items()),
            )
            .select_from(
                IV.join(
                    PV,
                    (PV.c.id == IV.c.processo_versao_id) & (PV.c.base_id == IV.c.base_id),
                )
                .join(p.processos, p.processos.c.id == PV.c.processo_id)
                .join(
                    p.itens_processo,
                    (p.itens_processo.c.id == IV.c.item_id)
                    & (p.itens_processo.c.processo_id == PV.c.processo_id),
                )
                .outerjoin(p.modalidades, p.modalidades.c.id == PV.c.modalidade_id)
                .outerjoin(p.itens_catalogo, p.itens_catalogo.c.id == IV.c.catalogo_id)
                .outerjoin(totals, totals.c.item_versao_id == IV.c.id)
            )
            .where(IV.c.base_id == base_id, PV.c.base_id == base_id)
        )

    def finish_items(self, rows, base_id):
        self.item_results(rows, base_id)
        for row in rows:
            keys = [key for key in row if key.startswith("processo_")]
            row["processo"] = {key.removeprefix("processo_"): row.pop(key) for key in keys}

    def catalog_items(self, base_id, filters):
        query = self.item_query(base_id)
        for field in ("orgao_id", "modalidade_id"):
            if (value := getattr(filters, field)) is not None:
                query = query.where(PV.c[field] == value)
        if filters.processo_id is not None:
            query = query.where(PV.c.processo_id == filters.processo_id)
        for field, column in (
            ("catalogo", p.itens_catalogo.c.catalogo),
            ("codigo_catalogo", p.itens_catalogo.c.codigo),
        ):
            if (value := getattr(filters, field)) is not None:
                query = query.where(column == value)

        def result_match(*conditions):
            return (
                sa.select(1)
                .where(
                    RI.c.item_versao_id == IV.c.id,
                    RI.c.base_id == base_id,
                    RI.c.cancelado.is_(False),
                    *conditions,
                )
                .correlate(IV)
                .exists()
            )

        conditions = []
        if filters.fornecedor_id is not None:
            conditions.append(RI.c.fornecedor_id == filters.fornecedor_id)
        if filters.homologacao_inicio is not None:
            conditions.append(RI.c.data_resultado >= filters.homologacao_inicio)
        if filters.homologacao_fim is not None:
            conditions.append(RI.c.data_resultado <= filters.homologacao_fim)
        if conditions:
            query = query.where(result_match(*conditions))
        amount = query.selected_columns["valor_homologado_item"]
        if filters.valor_minimo is not None:
            query = query.where(amount >= filters.valor_minimo)
        if filters.valor_maximo is not None:
            query = query.where(amount <= filters.valor_maximo)
        if filters.busca and (search := filters.busca.strip()):
            query = query.where(
                sa.or_(
                    *(
                        column.icontains(search, autoescape=True)
                        for column in (
                            IV.c.descricao,
                            IV.c.numero_item,
                            p.itens_processo.c.chave_oficial,
                            PV.c.objeto,
                            PV.c.numero_compra,
                            PV.c.numero_processo,
                            p.processos.c.chave_oficial,
                        )
                    ),
                    result_match(RI.c.fornecedor_nome.icontains(search, autoescape=True)),
                )
            )
        orders = {
            "publicacao_desc": PV.c.data_publicacao.desc().nulls_last(),
            "publicacao_asc": PV.c.data_publicacao.asc().nulls_last(),
            "valor_desc": amount.desc().nulls_last(),
            "valor_asc": amount.asc().nulls_last(),
            "descricao_asc": IV.c.descricao.asc(),
        }
        result = self.page(
            query.order_by(orders[filters.ordenacao], IV.c.item_id), filters, base_id
        )
        self.finish_items(result["dados"], base_id)
        return result

    def item(self, base_id, item_id):
        row = (
            self.session.execute(self.item_query(base_id).where(IV.c.item_id == item_id))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise QueryError("item_nao_encontrado", "Item não encontrado nesta base.")
        data = dict(row)
        self.finish_items([data], base_id)
        return data

    def documents(self, base_id, process_id, filters):
        snapshot = self.process(base_id, process_id)["processo_versao_id"]
        linked = (
            sa.select(1)
            .where(
                k.contratos_processos.c.base_id == base_id,
                k.contratos_processos.c.processo_versao_id == snapshot,
                k.contratos_processos.c.contrato_versao_id == k.documentos.c.contrato_versao_id,
            )
            .correlate(k.documentos)
            .exists()
        )
        query = (
            sa.select(k.documentos)
            .where(
                k.documentos.c.base_id == base_id,
                sa.or_(k.documentos.c.processo_versao_id == snapshot, linked),
            )
            .order_by(k.documentos.c.publicado_na_origem_em.desc().nulls_last(), k.documentos.c.id)
        )
        result = self.page(query, filters, base_id)
        for row in result["dados"]:
            row["binario_registrado"] = row["chave_objeto"] is not None
        return result

    def base_status(self, base):
        if base is None:
            return {
                "status": "sem_base",
                "base": None,
                "cobertura": None,
                "ultima_importacao_concluida_em": None,
                "ultima_coleta_dos_arquivos_em": None,
            }
        base_id = base["id"]

        def count(table, *conditions, expression=None):
            return self.session.scalar(
                sa.select(
                    sa.func.count()
                    if expression is None
                    else sa.func.count(sa.distinct(expression))
                )
                .select_from(table)
                .where(table.c.base_id == base_id, *conditions)
            )

        coverage = {
            "processos": count(PV),
            "itens": count(IV),
            "resultados_ativos": count(RI, RI.c.cancelado.is_(False)),
            "resultados_cancelados": count(RI, RI.c.cancelado.is_(True)),
            "fornecedores_resultados_ativos": count(
                RI, RI.c.cancelado.is_(False), expression=RI.c.fornecedor_id
            ),
            "orgaos": count(PV, expression=PV.c.orgao_id),
            "referencias_precos": count(p.referencias_precos),
            "documentos": count(k.documentos),
            "itens_sem_unidade": count(
                IV, sa.or_(IV.c.unidade_medida.is_(None), sa.func.trim(IV.c.unidade_medida) == "")
            ),
            "processos_sem_data_resultado": count(PV, PV.c.data_resultado.is_(None)),
            "processos_sem_valor_homologado": count(PV, PV.c.valor_homologado.is_(None)),
        }
        times = (
            self.session.execute(
                sa.select(
                    sa.func.max(c.importacoes.c.concluido_em).label("importacao"),
                    sa.func.max(c.arquivos_coletados.c.coletado_em).label("coleta"),
                )
                .select_from(c.base_importacoes.join(c.importacoes).join(c.arquivos_coletados))
                .where(c.base_importacoes.c.base_id == base_id)
            )
            .mappings()
            .one()
        )
        return {
            "status": "disponivel",
            "base": dict(base),
            "cobertura": coverage,
            "ultima_importacao_concluida_em": times["importacao"],
            "ultima_coleta_dos_arquivos_em": times["coleta"],
        }
