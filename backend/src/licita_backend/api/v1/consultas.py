from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from licita_backend.db.session import get_session
from licita_backend.repositories.consultas import QueryRepository
from licita_backend.schemas.consultas import (
    BaseSelection,
    BaseStatus,
    Document,
    ErrorResponse,
    Item,
    ItemFilters,
    ItemResponse,
    ItemSummary,
    LookupFilters,
    Modality,
    Organization,
    Page,
    Pagination,
    ProcessFilters,
    ProcessResponse,
    ProcessSummary,
)

router = APIRouter(
    tags=["Consultas"], responses={code: {"model": ErrorResponse} for code in (404, 422, 500, 503)}
)
DB = Annotated[Session, Depends(get_session)]


@router.get("/base/status", response_model=BaseStatus)
def base_status(session: DB, params: Annotated[BaseSelection, Query()]):
    repository = QueryRepository(session)
    base = repository.base(params.base_id, optional=params.base_id is None)
    return repository.base_status(base)


@router.get("/orgaos", response_model=Page[Organization])
def organizations(session: DB, params: Annotated[LookupFilters, Query()]):
    repository = QueryRepository(session)
    return repository.lookups(repository.base(params.base_id)["id"], params, "orgaos")


@router.get("/modalidades", response_model=Page[Modality])
def modalities(session: DB, params: Annotated[LookupFilters, Query()]):
    repository = QueryRepository(session)
    return repository.lookups(repository.base(params.base_id)["id"], params, "modalidades")


@router.get("/processos", response_model=Page[ProcessSummary])
def processes(session: DB, params: Annotated[ProcessFilters, Query()]):
    repository = QueryRepository(session)
    return repository.processes(repository.base(params.base_id)["id"], params)


@router.get("/processos/{processo_id}", response_model=ProcessResponse)
def process(processo_id: UUID, session: DB, params: Annotated[BaseSelection, Query()]):
    repository = QueryRepository(session)
    base_id = repository.base(params.base_id)["id"]
    return {"base_id": base_id, "processo": repository.process(base_id, processo_id)}


@router.get("/processos/{processo_id}/itens", response_model=Page[Item])
def items(processo_id: UUID, session: DB, params: Annotated[Pagination, Query()]):
    repository = QueryRepository(session)
    return repository.items(repository.base(params.base_id)["id"], processo_id, params)


@router.get("/processos/{processo_id}/documentos", response_model=Page[Document])
def documents(processo_id: UUID, session: DB, params: Annotated[Pagination, Query()]):
    repository = QueryRepository(session)
    return repository.documents(repository.base(params.base_id)["id"], processo_id, params)


@router.get("/itens", response_model=Page[ItemSummary])
def catalog_items(session: DB, params: Annotated[ItemFilters, Query()]):
    repository = QueryRepository(session)
    return repository.catalog_items(repository.base(params.base_id)["id"], params)


@router.get("/itens/{item_id}", response_model=ItemResponse)
def item(item_id: UUID, session: DB, params: Annotated[BaseSelection, Query()]):
    repository = QueryRepository(session)
    base_id = repository.base(params.base_id)["id"]
    return {"base_id": base_id, "item": repository.item(base_id, item_id)}
