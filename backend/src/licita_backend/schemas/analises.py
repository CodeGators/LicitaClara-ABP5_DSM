"""Consultas experimentais explícitas; nenhuma prioridade validada é inferida."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from licita_backend.schemas.consultas import Money


class AnalysisSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_id: UUID


class AnalysisPage(AnalysisSelection):
    pagina: int = Field(default=1, ge=1, le=1_000_000)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)


class Run(BaseModel):
    id: UUID
    base_id: UUID
    status: Literal["concluida"]
    experimental: Literal[True] = True
    politica: str
    contagens: dict[str, Any]
    manifesto: dict[str, Any]
    modelos: list[dict[str, Any]]
    criado_em: datetime
    concluido_em: datetime
    prioridade_auditoria: None = None


class ActivePublication(BaseModel):
    base_id: UUID
    canal: Literal["experimental"] = "experimental"
    status: Literal["nao_publicada", "publicada_experimental"]
    execucao_id: UUID | None = None
    experimental: Literal[True] = True
    prioridade_auditoria: None = None


class ResultScore(BaseModel):
    id: UUID
    modelo_id: UUID
    algoritmo: str
    resultado_item_id: UUID
    score_bruto: Money
    indice_experimental: Money
    normalizacao: str
    atributos: dict[str, Any]
    explicacao: dict[str, Any]


class ItemAnalysis(BaseModel):
    id: UUID
    item_versao_id: UUID
    processo_versao_id: UUID
    status: Literal["nao_analisado", "parcial", "analisado_experimental"]
    cobertura: list[dict[str, Any]]
    resultados: list[ResultScore]
    prioridade: None = None
    score_processo: None = None


class AnalysisItemPage(BaseModel):
    execucao_id: UUID
    base_id: UUID
    experimental: Literal[True] = True
    dados: list[ItemAnalysis]
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int


class RunPage(BaseModel):
    dados: list[Run]
    base_id: UUID
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int
