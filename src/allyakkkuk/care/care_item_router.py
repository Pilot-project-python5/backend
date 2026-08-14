"""복용 제품 등록 API."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.auth.cookies import set_no_store_headers
from allyakkkuk.auth.current_user_dependencies import require_current_user
from allyakkkuk.auth.current_user_service import AuthenticatedUser
from allyakkkuk.care.care_item_repository import SQLAlchemyCareItemRepository
from allyakkkuk.care.care_item_schemas import (
    CareItemCreateRequest,
    CareItemExpirationResponse,
    CareItemExpirationUpdateRequest,
    CareItemListItemResponse,
    CareItemListResponse,
    CareItemResponse,
    ProductType,
    QuantityUnit,
    decimal_string,
)
from allyakkkuk.care.care_item_service import (
    CareItemManagementService,
    CareItemRegistrationCommand,
    CareItemService,
)
from allyakkkuk.care.daily_intake_repository import SQLAlchemyDailyIntakeRepository
from allyakkkuk.care.daily_intake_schemas import (
    DailyIntakeNutrientResponse,
    DailyIntakeResponse,
    NutrientUnit,
)
from allyakkkuk.care.daily_intake_service import DailyIntakeService
from allyakkkuk.care.nutrient_status_repository import (
    SQLAlchemyNutrientStatusRepository,
)
from allyakkkuk.care.nutrient_status_schemas import (
    NutrientStatusItemResponse,
    NutrientStatusResponse,
)
from allyakkkuk.care.nutrient_status_service import NutrientStatusService
from allyakkkuk.core.config import get_settings
from allyakkkuk.db.session import get_db_session
from allyakkkuk.ports.clock import SystemClock

router = APIRouter(prefix="/care", tags=["마이케어"])
_clock = SystemClock()
_settings = get_settings()
_time_zone = ZoneInfo(_settings.app_timezone)


def get_care_item_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CareItemService:
    return CareItemService(
        SQLAlchemyCareItemRepository(session),
        _clock,
        _time_zone,
    )


def get_care_item_management_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CareItemManagementService:
    return CareItemManagementService(
        SQLAlchemyCareItemRepository(session),
        _clock,
        _time_zone,
    )


def get_daily_intake_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> DailyIntakeService:
    return DailyIntakeService(SQLAlchemyDailyIntakeRepository(session))


def get_nutrient_status_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> NutrientStatusService:
    return NutrientStatusService(
        repository=SQLAlchemyNutrientStatusRepository(session),
        daily_intake_service=DailyIntakeService(
            SQLAlchemyDailyIntakeRepository(session)
        ),
        clock=_clock,
        time_zone=_time_zone,
        reference_version=_settings.nutrient_reference_version,
    )


def _error_response(
    description: str,
    code: str,
    message: str,
) -> dict[str, Any]:
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
        "description": "개인 건강 관련 응답 캐시 금지",
        "schema": {"type": "string", "example": "no-store"},
    }
}


@router.get(
    "/nutrient-status",
    response_model=NutrientStatusResponse,
    responses={
        200: {
            "description": (
                "등록된 보충제 복용 계획이 총 식이 기준량에서 차지하는 비율. "
                "실제 음식 섭취량이나 임상적 결핍·과잉 판정이 아닙니다."
            ),
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        503: _error_response(
            "기준 버전 또는 PostgreSQL 조회·단위 검증 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 영양성분 현황 조회",
    operation_id="care_get_nutrient_status",
)
def get_nutrient_status(
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[NutrientStatusService, Depends(get_nutrient_status_service)],
) -> NutrientStatusResponse:
    result = service.get_status(user_id=current.user_id)
    set_no_store_headers(response)
    return NutrientStatusResponse(
        as_of_date=result.as_of_date,
        age=result.age,
        gender=cast(Any, result.gender),
        reference_version=result.reference_version,
        reference_source_name=result.reference_source_name,
        reference_source_url=result.reference_source_url,
        nutrients=[
            NutrientStatusItemResponse(
                nutrient_id=item.nutrient_id,
                nutrient_code=item.nutrient_code,
                nutrient_name=item.nutrient_name,
                daily_amount=decimal_string(item.daily_amount),
                unit=cast(NutrientUnit, item.unit),
                reference_available=item.reference_available,
                reference_amount=(
                    decimal_string(item.reference_amount)
                    if item.reference_amount is not None
                    else None
                ),
                reference_type=cast(Any, item.reference_type),
                achievement_rate_percent=(
                    decimal_string(item.achievement_rate_percent)
                    if item.achievement_rate_percent is not None
                    else None
                ),
            )
            for item in result.nutrients
        ],
    )


@router.get(
    "/daily-intake",
    response_model=DailyIntakeResponse,
    responses={
        200: {
            "description": "활성 영양제 복용 계획의 성분별 일일 예정 섭취량",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 또는 단위 변환 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 일일 예정 섭취량 조회",
    operation_id="care_get_daily_intake",
)
def get_daily_intake(
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[DailyIntakeService, Depends(get_daily_intake_service)],
) -> DailyIntakeResponse:
    result = service.get_daily_intake(user_id=current.user_id)
    set_no_store_headers(response)
    return DailyIntakeResponse(
        nutrients=[
            DailyIntakeNutrientResponse(
                nutrient_id=item.nutrient_id,
                nutrient_code=item.nutrient_code,
                nutrient_name=item.nutrient_name,
                daily_amount=decimal_string(item.daily_amount),
                unit=cast(NutrientUnit, item.unit),
            )
            for item in result
        ]
    )


@router.get(
    "/items",
    response_model=CareItemListResponse,
    responses={
        200: {
            "description": "현재 사용자의 활성 복용 제품 페이지",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 활성 복용 제품 목록 조회",
    operation_id="care_list_items",
)
def list_care_items(
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        CareItemManagementService,
        Depends(get_care_item_management_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CareItemListResponse:
    result = service.list_items(
        user_id=current.user_id,
        page=page,
        page_size=page_size,
    )
    set_no_store_headers(response)
    return CareItemListResponse(
        items=[
            CareItemListItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_type=cast(ProductType, item.product_type),
                brand=item.brand,
                name=item.name,
                image_url=item.image_url,
                purchase_date=item.purchase_date,
                intake_start_date=item.intake_start_date,
                expected_depletion_date=item.expected_depletion_date,
                total_quantity=decimal_string(item.total_quantity),
                quantity_unit=cast(QuantityUnit, item.quantity_unit),
                dose_per_intake=decimal_string(item.dose_per_intake),
                intakes_per_day=item.intakes_per_day,
                days_until_depletion=item.days_until_depletion,
                inventory_status=item.inventory_status,
                created_at=item.created_at,
                expiration_date=item.expiration_date,
                days_until_expiration=item.days_until_expiration,
                expiration_status=item.expiration_status,
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.put(
    "/items/{care_item_id}/expiration",
    response_model=CareItemExpirationResponse,
    responses={
        200: {
            "description": "현재 사용자의 활성 복용 항목 유통기한 갱신",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response("access 인증 실패", "AUTH_REQUIRED", "인증이 필요합니다."),
        404: _error_response(
            "현재 사용자의 활성 복용 항목 없음",
            "CARE_ITEM_NOT_FOUND",
            "복용 항목을 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 복용 제품 유통기한 추가·교정",
    operation_id="care_update_item_expiration",
)
def update_care_item_expiration(
    care_item_id: UUID,
    payload: CareItemExpirationUpdateRequest,
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        CareItemManagementService,
        Depends(get_care_item_management_service),
    ],
) -> CareItemExpirationResponse:
    service.update_expiration(
        user_id=current.user_id,
        care_item_id=care_item_id,
        expiration_date=payload.expiration_date,
    )
    set_no_store_headers(response)
    return CareItemExpirationResponse(
        care_item_id=care_item_id,
        expiration_date=payload.expiration_date,
    )


@router.delete(
    "/items/{care_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        204: {
            "description": "복용 항목 소프트 삭제 성공",
            "headers": _PRIVATE_RESPONSE_HEADERS,
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        404: _error_response(
            "현재 사용자의 활성 복용 항목 없음",
            "CARE_ITEM_NOT_FOUND",
            "복용 항목을 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="내 복용 제품 삭제",
    operation_id="care_delete_item",
)
def delete_care_item(
    care_item_id: UUID,
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[
        CareItemManagementService,
        Depends(get_care_item_management_service),
    ],
) -> Response:
    service.delete_item(user_id=current.user_id, care_item_id=care_item_id)
    response.status_code = status.HTTP_204_NO_CONTENT
    set_no_store_headers(response)
    return response


@router.post(
    "/items",
    response_model=CareItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "복용 제품 등록 성공",
            "headers": {
                "Cache-Control": {
                    "description": "개인 건강 관련 응답 캐시 금지",
                    "schema": {"type": "string", "example": "no-store"},
                }
            },
        },
        401: _error_response(
            "access 인증 실패",
            "AUTH_REQUIRED",
            "인증이 필요합니다.",
        ),
        404: _error_response(
            "카탈로그 제품 없음",
            "PRODUCT_NOT_FOUND",
            "제품을 찾을 수 없습니다.",
        ),
        422: _error_response(
            "등록 값 검증 실패",
            "VALIDATION_FAILED",
            "요청 값을 확인해주세요.",
        ),
        503: _error_response(
            "PostgreSQL 처리 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="복용 제품 등록",
    operation_id="care_register_item",
)
def register_care_item(
    payload: CareItemCreateRequest,
    response: Response,
    current: Annotated[AuthenticatedUser, Depends(require_current_user)],
    service: Annotated[CareItemService, Depends(get_care_item_service)],
) -> CareItemResponse:
    result = service.register(
        user_id=current.user_id,
        command=CareItemRegistrationCommand(
            product_id=payload.product_id,
            purchase_date=payload.purchase_date,
            intake_start_date=payload.intake_start_date,
            total_quantity=payload.total_quantity,
            dose_per_intake=payload.dose_per_intake,
            intakes_per_day=payload.intakes_per_day,
            expiration_date=payload.expiration_date,
        ),
    )
    set_no_store_headers(response)
    return CareItemResponse(
        id=result.id,
        product_id=result.product_id,
        purchase_date=result.purchase_date,
        intake_start_date=result.intake_start_date,
        expected_depletion_date=result.expected_depletion_date,
        total_quantity=result.total_quantity,
        quantity_unit=cast(QuantityUnit, result.quantity_unit),
        dose_per_intake=result.dose_per_intake,
        intakes_per_day=result.intakes_per_day,
        created_at=result.created_at,
        expiration_date=result.expiration_date,
    )
