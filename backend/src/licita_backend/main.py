import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from licita_backend.api.errors import register_errors
from licita_backend.api.v1.analises import router as analises_router
from licita_backend.api.v1.consultas import router as consultas_router
from licita_backend.api.v1.health import router
from licita_backend.api.v1.relatorios import router as relatorios_router
from licita_backend.api.v1.visao import router as visao_router
from licita_backend.core.config import Settings
from licita_backend.core.logging import configure_logging
from licita_backend.db.session import build_engine, build_session_factory
from licita_backend.storage.local import LocalObjectStorage

logger = logging.getLogger("licita.http")


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = build_engine(config)
        app.state.engine = engine
        app.state.sessions = build_session_factory(engine)
        app.state.storage = LocalObjectStorage(config.storage_root)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Licita Clara API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started, status = perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )

    register_errors(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(consultas_router, prefix="/api/v1")
    app.include_router(analises_router, prefix="/api/v1")
    app.include_router(visao_router, prefix="/api/v1")
    app.include_router(relatorios_router, prefix="/api/v1")
    return app
