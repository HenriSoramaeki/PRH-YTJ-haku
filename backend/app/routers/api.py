"""REST API routes."""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_region_config
from app.models.api_schemas import (
    ExportRequest,
    HealthResponse,
    RegionInfo,
    SearchRequest,
    SearchResponse,
)
from app.services.export_service import to_csv_bytes, to_xlsx_bytes
from app.services.search_service import run_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/region", response_model=RegionInfo)
def region_info() -> RegionInfo:
    cfg = get_region_config()
    return RegionInfo(
        name=str(cfg.get("region_name_fi", "Etelä-Karjala")),
        municipalities=list(cfg.get("municipalities") or []),
    )


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest) -> SearchResponse:
    try:
        return run_search(date_from=body.date_from, mode=body.mode)
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=502, detail=f"Haku epäonnistui: {e}") from e


def _export_filename(prefix: str, ext: str) -> str:
    return f"{prefix}-{date.today().isoformat()}.{ext}"


@router.post("/export/csv")
def export_csv(body: ExportRequest) -> Response:
    data = to_csv_bytes(body.companies)
    fn = _export_filename("yritykset", "csv")
    cd = f"attachment; filename=\"{fn}\"; filename*=UTF-8''{quote(fn)}"
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": cd},
    )


@router.post("/export/xlsx")
def export_xlsx(body: ExportRequest) -> Response:
    data = to_xlsx_bytes(body.companies)
    fn = _export_filename("yritykset", "xlsx")
    cd = f"attachment; filename=\"{fn}\"; filename*=UTF-8''{quote(fn)}"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": cd},
    )
