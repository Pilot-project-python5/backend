"""외부 구매 연결 애플리케이션 서비스."""

from __future__ import annotations

from uuid import UUID

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.purchase_link_repository import (
    PurchaseLinkPersistenceError,
    PurchaseLinkRepository,
)
from yeongyangkkuk.curation.purchase_link_urls import validate_purchase_url


class PurchaseLinkService:
    def __init__(self, repository: PurchaseLinkRepository) -> None:
        self._repository = repository

    def get_destination(self, product_id: UUID) -> str:
        try:
            result = self._repository.get_first_for_public_product(product_id)
        except PurchaseLinkPersistenceError as exc:
            raise self._service_unavailable() from exc

        if result is None or not result.product_exists:
            raise AppError(
                status_code=404,
                code="PRODUCT_NOT_FOUND",
                message="제품을 찾을 수 없습니다.",
            )
        if result.url is None:
            raise AppError(
                status_code=404,
                code="PURCHASE_LINK_NOT_FOUND",
                message="구매 링크를 찾을 수 없습니다.",
            )
        try:
            return validate_purchase_url(result.url)
        except ValueError as exc:
            raise self._service_unavailable() from exc

    @staticmethod
    def _service_unavailable() -> AppError:
        return AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="서비스가 아직 준비되지 않았습니다.",
        )
