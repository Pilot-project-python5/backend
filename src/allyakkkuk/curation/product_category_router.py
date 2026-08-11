"""제품 카테고리 공개 조회 API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from allyakkkuk.api.schemas import ErrorResponse
from allyakkkuk.curation.product_category_repository import (
    SQLAlchemyProductCategoryRepository,
)
from allyakkkuk.curation.product_category_schemas import (
    ProductCategoryListResponse,
    ProductCategoryResponseItem,
)
from allyakkkuk.curation.product_category_service import ProductCategoryService
from allyakkkuk.db.session import get_db_session

router = APIRouter(prefix="/curation", tags=["큐레이션"])


def get_product_category_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductCategoryService:
    return ProductCategoryService(SQLAlchemyProductCategoryRepository(session))


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
    "/categories",
    response_model=ProductCategoryListResponse,
    responses={
        200: {"description": "가상 전체와 활성 제품 카테고리 목록"},
        503: _error_response(
            "PostgreSQL 조회 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="활성 제품 카테고리 조회",
    operation_id="curation_list_product_categories",
)
def list_product_categories(
    service: Annotated[ProductCategoryService, Depends(get_product_category_service)],
) -> ProductCategoryListResponse:
    return ProductCategoryListResponse(
        items=[
            ProductCategoryResponseItem(slug=item.slug, name=item.name)
            for item in service.list_categories()
        ]
    )
