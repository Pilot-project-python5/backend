"""프로세스 생존과 PostgreSQL 준비 상태 API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from allyakkkuk.api.schemas import ErrorResponse, HealthResponse
from allyakkkuk.core.config import Settings, get_settings
from allyakkkuk.core.errors import AppError
from allyakkkuk.db.probe import DatabaseProbe, SQLAlchemyDatabaseProbe
from allyakkkuk.db.session import engine

router = APIRouter(prefix="/health", tags=["시스템"])


def get_database_probe() -> DatabaseProbe:
    return SQLAlchemyDatabaseProbe(engine)


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="API 프로세스 생존 확인",
    operation_id="system_liveness",
)
def liveness(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(service=settings.app_name, version=settings.app_version)


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse, "description": "PostgreSQL 연결 실패"}},
    summary="API와 PostgreSQL 준비 확인",
    operation_id="system_readiness",
)
def readiness(
    settings: Annotated[Settings, Depends(get_settings)],
    probe: Annotated[DatabaseProbe, Depends(get_database_probe)],
) -> HealthResponse:
    try:
        probe.check()
    except Exception as exc:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        ) from exc
    return HealthResponse(service=settings.app_name, version=settings.app_version)
