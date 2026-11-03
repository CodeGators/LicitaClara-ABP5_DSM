"""Erros uniformes sem SQL, credenciais ou conteúdo de entradas nos logs."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from starlette.exceptions import HTTPException

logger = logging.getLogger("licita.api")


class QueryError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 404):
        super().__init__(status_code, {"codigo": code, "mensagem": message})


def error_response(request, status, code, message, details=None, headers=None):
    request_id = getattr(request.state, "request_id", "indisponivel")
    return JSONResponse(
        status_code=status,
        content={
            "erro": {
                "codigo": code,
                "mensagem": message,
                "request_id": request_id,
                "detalhes": details or [],
            }
        },
        headers={**(headers or {}), "X-Request-ID": request_id},
    )


def register_errors(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        detail = error.detail if isinstance(error.detail, dict) else {}
        return error_response(
            request,
            error.status_code,
            detail.get("codigo", "requisicao_recusada"),
            detail.get("mensagem", "Não foi possível atender à requisição."),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        details = [
            {"campo": ".".join(map(str, e["loc"])), "tipo": e["type"]} for e in error.errors()
        ]
        return error_response(
            request, 422, "parametros_invalidos", "Confira os parâmetros da consulta.", details
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError):
        unavailable = isinstance(error, (OperationalError, DisconnectionError, SQLTimeoutError))
        logger.error(
            "database_query_failed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "error_type": type(error).__name__,
            },
        )
        return error_response(
            request,
            503 if unavailable else 500,
            "banco_indisponivel" if unavailable else "erro_interno",
            "Dados temporariamente indisponíveis."
            if unavailable
            else "Não foi possível concluir a consulta.",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logger.error(
            "request_failed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "error_type": type(error).__name__,
            },
        )
        return error_response(request, 500, "erro_interno", "Não foi possível concluir a consulta.")
