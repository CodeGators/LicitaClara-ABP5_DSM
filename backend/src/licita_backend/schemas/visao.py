"""Recorte comum para painel, ranking e fornecedores; índices não são risco."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from licita_backend.schemas.consultas import ProcurementFilters


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
