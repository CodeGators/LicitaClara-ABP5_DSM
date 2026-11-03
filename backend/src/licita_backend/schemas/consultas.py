"""Contratos públicos de leitura; dinheiro decimal e base explícita."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

Money = Annotated[Decimal, PlainSerializer(lambda v: format(v, "f"), return_type=str)]
AmountFilter = Annotated[Decimal, Field(ge=0, max_digits=28, decimal_places=8)]
T = TypeVar("T")


class BaseSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_id: UUID | None = None


class Pagination(BaseSelection):
    pagina: int = Field(default=1, ge=1, le=1_000_000)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)


class LookupFilters(Pagination):
    busca: str | None = Field(default=None, max_length=200)


class ProcessFilters(LookupFilters):
    orgao_id: UUID | None = None
    fornecedor_id: UUID | None = None
    modalidade_id: UUID | None = None
    homologacao_inicio: date | None = None
    homologacao_fim: date | None = None
    valor_minimo: AmountFilter | None = None
    valor_maximo: AmountFilter | None = None
    escopo_valor: Literal["processo", "itens_recorte"] = "processo"
    ordenacao: Literal[
        "publicacao_desc", "publicacao_asc", "valor_desc", "valor_asc", "objeto_asc"
    ] = "publicacao_desc"

    @model_validator(mode="after")
    def ordered_ranges(self):
        if (
            self.homologacao_inicio is not None
            and self.homologacao_fim is not None
            and self.homologacao_inicio > self.homologacao_fim
        ):
            raise ValueError("Início deve ser anterior ou igual ao fim")
        if (
            self.valor_minimo is not None
            and self.valor_maximo is not None
            and self.valor_minimo > self.valor_maximo
        ):
            raise ValueError("Valor mínimo deve ser menor ou igual ao máximo")
        return self


class PageMeta(BaseModel):
    base_id: UUID
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int


class Page(BaseModel, Generic[T]):
    dados: list[T]
    meta: PageMeta


class AnalysisUnavailable(BaseModel):
    status: Literal["nao_publicada"] = "nao_publicada"
    score: None = None
    prioridade: None = None


class SupplierBrief(BaseModel):
    id: UUID
    nome: str


class ProcessSummary(BaseModel):
    id: UUID
    processo_versao_id: UUID
    fonte: str
    chave_oficial: str
    numero_compra: str
    numero_processo: str | None
    numero_controle_pncp: str | None
    ano: int
    objeto: str
    situacao: str
    orgao_id: UUID
    orgao_nome: str
    modalidade_id: UUID | None
    modalidade_nome: str | None
    data_publicacao: date | None
    data_resultado: date | None
    ultima_data_resultado_itens_recorte: date | None
    valor_estimado_processo: Money | None
    valor_homologado_processo: Money | None
    valor_homologado_itens_recorte: Money | None
    resultados_sem_valor_total_recorte: int
    quantidade_itens_recorte: int
    fornecedores: list[SupplierBrief]
    analise: AnalysisUnavailable = Field(default_factory=AnalysisUnavailable)


class ProcessDetail(ProcessSummary):
    codigo_unidade: str
    nome_unidade: str | None
    data_abertura: date | None
    orcamento_sigiloso: bool | None


class ProcessResponse(BaseModel):
    base_id: UUID
    processo: ProcessDetail


class Lookup(BaseModel):
    id: UUID
    nome: str


class Organization(Lookup):
    chave_oficial: str
    cnpj: str | None


class Modality(Lookup):
    codigo: str


class ItemResult(BaseModel):
    id: UUID
    fornecedor_id: UUID
    fornecedor_nome: str
    sequencial_resultado: int
    situacao: str
    cancelado: bool
    quantidade_homologada: Money | None
    valor_unitario_homologado: Money | None
    valor_total_homologado: Money | None
    data_resultado: date | None


class Item(BaseModel):
    id: UUID
    item_versao_id: UUID
    numero_item: str
    descricao: str
    unidade_medida: str | None
    quantidade: Money | None
    valor_unitario_estimado: Money | None
    orcamento_sigiloso: bool | None
    catalogo: str | None
    codigo_catalogo: str | None
    resultados: list[ItemResult]
    analise: AnalysisUnavailable = Field(default_factory=AnalysisUnavailable)


class Document(BaseModel):
    id: UUID
    fonte: str
    titulo: str | None
    tipo_codigo: str | None
    tipo_nome: str | None
    url_origem: str
    ativo: bool | None
    publicado_na_origem_em: datetime | None
    contrato_versao_id: UUID | None
    binario_registrado: bool


class BaseInfo(BaseModel):
    id: UUID
    versao: str
    status: Literal["validada"]
    periodo_inicio: date
    periodo_fim: date
    recorte: dict
    criado_em: datetime


class Coverage(BaseModel):
    processos: int
    itens: int
    resultados_ativos: int
    resultados_cancelados: int
    fornecedores_resultados_ativos: int
    orgaos: int
    referencias_precos: int
    documentos: int
    itens_sem_unidade: int
    processos_sem_data_resultado: int
    processos_sem_valor_homologado: int


class BaseStatus(BaseModel):
    status: Literal["disponivel", "sem_base"]
    base: BaseInfo | None
    cobertura: Coverage | None
    ultima_importacao_concluida_em: datetime | None
    ultima_coleta_dos_arquivos_em: datetime | None
    analise: AnalysisUnavailable = Field(default_factory=AnalysisUnavailable)


class ErrorDetail(BaseModel):
    campo: str
    tipo: str


class ErrorInfo(BaseModel):
    codigo: str
    mensagem: str
    request_id: str
    detalhes: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    erro: ErrorInfo
