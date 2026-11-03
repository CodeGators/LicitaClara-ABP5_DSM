from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from licita_backend.db.session import get_session
from licita_backend.repositories.analises import AnalysisRepository
from licita_backend.schemas.analises import (
    ActivePublication,
    AnalysisItemPage,
    AnalysisPage,
    AnalysisSelection,
    Run,
    RunPage,
)
from licita_backend.schemas.consultas import ErrorResponse

router = APIRouter(
    prefix="/analises",
    tags=["Análises experimentais"],
    responses={code: {"model": ErrorResponse} for code in (404, 422, 500, 503)},
)
DB = Annotated[Session, Depends(get_session)]


@router.get("/publicacao", response_model=ActivePublication)
def publication(session: DB, params: Annotated[AnalysisSelection, Query()]):
    return AnalysisRepository(session).active(params.base_id)


@router.get("/execucoes", response_model=RunPage)
def executions(session: DB, params: Annotated[AnalysisPage, Query()]):
    return AnalysisRepository(session).runs(params)


@router.get("/execucoes/{execution_id}", response_model=Run)
def execution(execution_id: UUID, session: DB, params: Annotated[AnalysisSelection, Query()]):
    repository = AnalysisRepository(session)
    return repository.serialize_run(repository.execution(params.base_id, execution_id))


@router.get("/execucoes/{execution_id}/itens", response_model=AnalysisItemPage)
def items(execution_id: UUID, session: DB, params: Annotated[AnalysisPage, Query()]):
    repository = AnalysisRepository(session)
    return repository.items(repository.execution(params.base_id, execution_id), params)


@router.get("/execucoes/{execution_id}/itens/{item_id}", response_model=AnalysisItemPage)
def item(
    execution_id: UUID, item_id: UUID, session: DB, params: Annotated[AnalysisSelection, Query()]
):
    repository = AnalysisRepository(session)
    return repository.items(
        repository.execution(params.base_id, execution_id),
        AnalysisPage(base_id=params.base_id),
        item_id,
    )
