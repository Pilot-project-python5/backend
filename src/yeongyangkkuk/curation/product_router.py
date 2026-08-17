"""게시 추천 제품 공개 목록 API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.curation.product_repository import SQLAlchemyProductRepository
from yeongyangkkuk.curation.product_schemas import (
    ProductListItemResponse,
    ProductListResponse,
)
from yeongyangkkuk.curation.product_service import ProductService
from yeongyangkkuk.db.session import get_db_session

router = APIRouter(prefix="/curation", tags=["큐레이션"])


def get_product_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductService:
    return ProductService(SQLAlchemyProductRepository(session))


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
    "/products",
    response_model=ProductListResponse,
    responses={
        200: {"description": "게시 추천 제품 페이지"},
        404: _error_response(
            "활성 카테고리 없음",
            "CATEGORY_NOT_FOUND",
            "카테고리를 찾을 수 없습니다.",
        ),
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="게시 추천 제품 목록 조회",
    operation_id="curation_list_recommended_products",
)
def list_recommended_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    category: Annotated[
        str,
        Query(
            min_length=1,
            max_length=50,
            pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        ),
    ] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductListResponse:
    result = service.list_products(
        category=category,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(
        items=[
            ProductListItemResponse(
                id=item.id,
                sku=item.sku,
                product_type=item.product_type,
                brand=item.brand,
                name=item.name,
                image_url=item.image_url,
                display_price=item.display_price,
                category_slugs=list(item.category_slugs),
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )
