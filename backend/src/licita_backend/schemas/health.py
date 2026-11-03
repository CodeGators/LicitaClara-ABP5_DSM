from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    service: str = "licita-backend"
    database: Literal["ok", "unavailable"] | None = None
