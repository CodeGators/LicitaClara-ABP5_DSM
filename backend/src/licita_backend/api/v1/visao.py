from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from licita_backend.db.session import get_session
from licita_backend.repositories.visao import ViewRepository
from licita_backend.schemas.consultas import ErrorResponse
from licita_backend.schemas.visao import Dashboard, SupplierView, ViewFilters, ViewPage

router = APIRouter(
    prefix="/visao",
    tags=["Painel e fornecedores"],
    responses={code: {"model": ErrorResponse} for code in (404, 422, 500, 503)},
)
DB = Annotated[Session, Depends(get_session)]


@router.get("/painel", response_model=Dashboard)
def dashboard(session: DB, params: Annotated[ViewFilters, Query()]):
    return ViewRepository(session).dashboard(params)


@router.get("/ranking", response_model=ViewPage)
def ranking(session: DB, params: Annotated[ViewFilters, Query()]):
    return ViewRepository(session).ranking(params)


@router.get("/fornecedores", response_model=ViewPage)
def suppliers(session: DB, params: Annotated[ViewFilters, Query()]):
    return ViewRepository(session).suppliers(params)


@router.get("/fornecedores/{supplier_id}", response_model=SupplierView)
def supplier(supplier_id: UUID, session: DB, params: Annotated[ViewFilters, Query()]):
    return ViewRepository(session).supplier(params, supplier_id)
