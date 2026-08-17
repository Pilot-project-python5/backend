"""공개 추천 제품 상세 API."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.curation.product_detail_repository import (
    SQLAlchemyProductDetailRepository,
)
from yeongyangkkuk.curation.product_detail_service import ProductDetailService
from yeongyangkkuk.curation.product_schemas import (
    ExpertCommentResponse,
    NutrientUnit,
    ProductDetailResponse,
    ProductNutrientResponse,
    ProductPackageResponse,
    UnitForm,
    decimal_string,
)
from yeongyangkkuk.db.session import get_db_session

router = APIRouter(prefix="/curation", tags=["큐레이션"])


def get_product_detail_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductDetailService:
    return ProductDetailService(SQLAlchemyProductDetailRepository(session))


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


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailResponse,
    responses={
        200: {"description": "게시 추천 제품 상세"},
        404: _error_response(
            "공개 추천 제품 없음",
            "PRODUCT_NOT_FOUND",
            "제품을 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="게시 추천 제품 상세 조회",
    operation_id="curation_get_recommended_product",
)
def get_recommended_product(
    product_id: UUID,
    service: Annotated[ProductDetailService, Depends(get_product_detail_service)],
) -> ProductDetailResponse:
    result = service.get_product(product_id)
    return ProductDetailResponse(
        id=result.id,
        sku=result.sku,
        product_type=result.product_type,
        brand=result.brand,
        name=result.name,
        image_url=result.image_url,
        display_price=result.display_price,
        category_slugs=list(result.category_slugs),
        package=ProductPackageResponse(
            unit_form=cast(UnitForm, result.unit_form),
            units_per_package=decimal_string(result.units_per_package),
        ),
        nutrients=[
            ProductNutrientResponse(
                code=item.code,
                name=item.name,
                amount_per_unit=decimal_string(item.amount_per_unit),
                unit=cast(NutrientUnit, item.unit),
            )
            for item in result.nutrients
        ],
        expert_comments=[
            ExpertCommentResponse(
                id=item.id,
                author_label=item.author_label,
                content=item.content,
            )
            for item in result.expert_comments
        ],
    )
