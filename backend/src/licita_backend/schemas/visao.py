"""Recorte comum para painel, ranking e fornecedores; índices não são risco."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from licita_backend.schemas.consultas import Money, ProcurementFilters


class ViewFilters(ProcurementFilters):
    base_id: UUID
    execucao_id: UUID | None = None
    modelo_id: UUID | None = None
    analise: Literal["todos", "analisados", "parcial", "nao_analisados"] = "todos"
    ordenacao: Literal["indice_desc", "descricao_asc", "valor_desc"] = "indice_desc"

    @model_validator(mode="after")
    def selection(self):
        if self.modelo_id is not None and self.execucao_id is None:
            raise ValueError("Selecionar execução antes do modelo")
        return self


class ViewContext(BaseModel):
    base_id: UUID
    execucao_id: UUID | None
    modelo_id: UUID | None
    experimental: Literal[True] = True
    universo: dict[str, Any]
    resumo: dict[str, Any]


class Dashboard(ViewContext):
    distribuicao: list[dict[str, Any]]
    evolucao: list[dict[str, Any]]
    motivos_indisponibilidade: dict[str, int]


class ViewPage(ViewContext):
    dados: list[dict[str, Any]]
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int


class SupplierView(ViewContext):
    fornecedor: dict[str, Any]
    relacoes: list[dict[str, Any]]
    itens: dict[str, Any]


class TenderRow(BaseModel):
    id: UUID
    processo: dict[str, Any]
    descricao: str
    score_medio: Money | None
    maior_score: Money | None
    itens_importados: int
    itens_com_score: int
    itens_analise_completa: int
    itens_analise_parcial: int
    itens_sem_score: int
    itens_oficiais: None = None
    status_analise: Literal["analisados", "parcial", "nao_analisados"]
    valor_homologado: Money | None
    valor_estimado: Money | None
    valores_itens_importados: dict[str, Any]


class TenderPage(ViewPage):
    dados: list[TenderRow]


class TenderDetail(ViewContext):
    licitacao: TenderRow
    itens: dict[str, Any]
