"""공개 추천 제품 외부 구매 이동 API."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from yeongyangkkuk.api.schemas import ErrorResponse
from yeongyangkkuk.curation.purchase_link_repository import (
    SQLAlchemyPurchaseLinkRepository,
)
from yeongyangkkuk.curation.purchase_link_service import PurchaseLinkService
from yeongyangkkuk.db.session import get_db_session

router = APIRouter(prefix="/curation", tags=["큐레이션"])


def get_purchase_link_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PurchaseLinkService:
    return PurchaseLinkService(SQLAlchemyPurchaseLinkRepository(session))


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


def _not_found_response() -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": "공개 추천 제품 또는 활성 구매 링크 없음",
        "content": {
            "application/json": {
                "examples": {
                    "product_not_found": {
                        "summary": "공개 추천 제품 없음",
                        "value": {
                            "error": {
                                "code": "PRODUCT_NOT_FOUND",
                                "message": "제품을 찾을 수 없습니다.",
                                "fields": [],
                                "request_id": "opaque-request-id",
                            }
                        },
                    },
                    "purchase_link_not_found": {
                        "summary": "활성 구매 링크 없음",
                        "value": {
                            "error": {
                                "code": "PURCHASE_LINK_NOT_FOUND",
                                "message": "구매 링크를 찾을 수 없습니다.",
                                "fields": [],
                                "request_id": "opaque-request-id",
                            }
                        },
                    },
                }
            }
        },
    }


@router.get(
    "/products/{product_id}/purchase",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_class=RedirectResponse,
    responses={
        307: {
            "description": "활성 외부 구매 링크로 임시 이동",
            "headers": {
                "Location": {"schema": {"type": "string", "format": "uri"}},
                "Cache-Control": {"schema": {"type": "string"}},
                "Referrer-Policy": {"schema": {"type": "string"}},
            },
        },
        404: _not_found_response(),
        503: _error_response(
            "PostgreSQL 조회 또는 구매 URL 검증 실패",
            "SERVICE_UNAVAILABLE",
            "서비스가 아직 준비되지 않았습니다.",
        ),
    },
    summary="활성 외부 구매 링크로 이동",
    operation_id="curation_redirect_to_purchase",
)
def redirect_to_purchase(
    product_id: UUID,
    service: Annotated[PurchaseLinkService, Depends(get_purchase_link_service)],
) -> RedirectResponse:
    destination = service.get_destination(product_id)
    return RedirectResponse(
        url=destination,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )
