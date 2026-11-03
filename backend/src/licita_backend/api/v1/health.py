from fastapi import APIRouter, Request, Response

from licita_backend.schemas.health import HealthResponse
from licita_backend.services.readiness import database_is_ready

router = APIRouter(tags=["Operação"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def ready(request: Request, response: Response) -> HealthResponse:
    if database_is_ready(request.app.state.engine, request.state.request_id):
        return HealthResponse(status="ok", database="ok")
    response.status_code = 503
    return HealthResponse(status="unavailable", database="unavailable")
