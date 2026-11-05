import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from licita_backend.api.errors import QueryError
from licita_backend.db.session import get_session
from licita_backend.services.reports import csv_file, snapshot

router = APIRouter(prefix="/relatorios", tags=["Relatórios de anomalias"])
DB = Annotated[Session, Depends(get_session)]


class ReportSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_id: UUID
    execucao_id: UUID | None = None
    titulo: str = Field(default="Relatório de anomalias", min_length=1, max_length=120)

    @field_validator("titulo")
    @classmethod
    def title(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Título deve ser texto em uma linha")
        return value.strip()


class DownloadSelection(ReportSelection):
    formato: Literal["pdf", "csv"]
    snapshot_sha256: str = Field(pattern="^[0-9a-f]{64}$")


@router.get("/processos/{process_id}/previa")
def preview(process_id: UUID, session: DB, params: Annotated[ReportSelection, Query()]):
    return Response(
        content=json.dumps(snapshot(session, process_id, params), ensure_ascii=False),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/processos/{process_id}/arquivo")
def download(process_id: UUID, session: DB, params: Annotated[DownloadSelection, Query()]):
    data = snapshot(session, process_id, params)
    if data["snapshot_sha256"] != params.snapshot_sha256:
        raise QueryError(
            "previa_desatualizada", "Os dados diferem da prévia. Atualize antes de exportar.", 409
        )
    if params.formato == "pdf":
        from licita_backend.services.report_pdf import pdf_file

        raw, media = pdf_file(data), "application/pdf"
    else:
        raw, media = csv_file(data), "text/csv; charset=utf-8"
    filename = f"licita-clara-{str(process_id)[:8]}.{params.formato}"
    return Response(
        content=raw,
        media_type=media,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Snapshot-SHA256": data["snapshot_sha256"],
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
