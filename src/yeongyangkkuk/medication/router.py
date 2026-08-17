"""로그인 사용자용 의약품 카탈로그 API."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.auth.cookies import set_no_store_headers
from yeongyangkkuk.auth.current_user_dependencies import require_current_user
from yeongyangkkuk.auth.current_user_service import AuthenticatedUser
from yeongyangkkuk.db.session import get_db_session
from yeongyangkkuk.medication.repository import SQLAlchemyMedicationRepository
from yeongyangkkuk.medication.schemas import (
    MedicationClassification,
    MedicationDetailResponse,
    MedicationListItemResponse,
    MedicationListResponse,
    MedicationPackageResponse,
    MedicationSourceResponse,
    UnitForm,
)
from yeongyangkkuk.medication.service import (
    MedicationDetail,
    MedicationService,
    MedicationSummary,
)

router = APIRouter(prefix="/medications", tags=["의약품"])


def get_medication_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> MedicationService:
    return MedicationService(SQLAlchemyMedicationRepository(session))


def _error_response(description: str, code: str, message: str) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": code,
                        "message": message,
                        "fields": [],
                        "request_id": "opaque-request-id",
                    }
                }
            }
        },
    }


_PRIVATE_RESPONSE_HEADERS = {
    "Cache-Control": {
        "description": "인증 응답 캐시 금지",
        "schema": {"type": "string", "example": "no-store"},
    }
}


def _summary_response(item: MedicationSummary) -> MedicationListItemResponse:
    return MedicationListItemResponse(
        id=item.id,
        sku=item.sku,
        brand=item.brand,
        name=item.name,
        image_url=item.image_url,
        package=MedicationPackageResponse(
            unit_form=cast(UnitForm, item.unit_form),
            units_per_package=_decimal_string(item.units_per_package),
        ),
        permit_code=item.permit_code,
        classification=cast(MedicationClassification, item.classification),
        active_ingredients=item.active_ingredients,
    )


def _decimal_string(value: object) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


@router.get(
    "",
    response_model=MedicationListResponse,
    responses={
        200: {
            "description": "게시된 시드 의약품 페이지",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="의약품 카탈로그 목록 조회",
    operation_id="medication_list_catalog",
)
def list_medications(
    response: Response,
    _current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MedicationListResponse:
    result = service.list_medications(page=page, page_size=page_size)
    set_no_store_headers(response)
    return MedicationListResponse(
        items=[_summary_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get(
    "/{product_id}",
    response_model=MedicationDetailResponse,
    responses={
        200: {
            "description": "출처를 포함한 시드 의약품 상세",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        404: _error_response(
            "게시 의약품 상세 없음",
            "MEDICATION_NOT_FOUND",
            "의약품을 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="의약품 카탈로그 상세 조회",
    operation_id="medication_get_catalog_item",
)
def get_medication(
    product_id: UUID,
    response: Response,
    _current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[MedicationService, Depends(get_medication_service)],
) -> MedicationDetailResponse:
    result: MedicationDetail = service.get_medication(product_id)
    summary = _summary_response(result)
    set_no_store_headers(response)
    return MedicationDetailResponse(
        **summary.model_dump(),
        efficacy=result.efficacy,
        dosage_instructions=result.dosage_instructions,
        precautions=result.precautions,
        storage_instructions=result.storage_instructions,
        source=MedicationSourceResponse(
            name=result.source_name,
            url=result.source_url,
            reviewed_on=result.source_reviewed_on,
        ),
    )
