from __future__ import annotations

from uuid import UUID

import pytest

from yeongyangkkuk.core.errors import AppError
from yeongyangkkuk.curation.purchase_link_repository import (
    PurchaseLinkPersistenceError,
    PurchaseLinkRecord,
    PurchaseLinkRepository,
)
from yeongyangkkuk.curation.purchase_link_service import PurchaseLinkService
from yeongyangkkuk.curation.purchase_link_urls import validate_purchase_url

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-2.4.2")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")
VALID_URL = "https://example.com/yeongyangkkuk/products/life-two-per-day?from=curation"


class FakePurchaseLinkRepository(PurchaseLinkRepository):
    def __init__(
        self,
        result: PurchaseLinkRecord | None,
        *,
        fails: bool = False,
    ) -> None:
        self.result = result
        self.fails = fails
        self.calls: list[UUID] = []

    def get_first_for_public_product(
        self, product_id: UUID
    ) -> PurchaseLinkRecord | None:
        self.calls.append(product_id)
        if self.fails:
            raise PurchaseLinkPersistenceError
        return self.result


def test_get_destination_returns_valid_https_url() -> None:
    repository = FakePurchaseLinkRepository(
        PurchaseLinkRecord(product_exists=True, url=VALID_URL)
    )

    result = PurchaseLinkService(repository).get_destination(PRODUCT_ID)

    assert result == VALID_URL
    assert repository.calls == [PRODUCT_ID]


@pytest.mark.parametrize(
    ("record", "code"),
    [
        (None, "PRODUCT_NOT_FOUND"),
        (
            PurchaseLinkRecord(product_exists=True, url=None),
            "PURCHASE_LINK_NOT_FOUND",
        ),
    ],
)
def test_get_destination_maps_missing_product_or_link(
    record: PurchaseLinkRecord | None,
    code: str,
) -> None:
    service = PurchaseLinkService(FakePurchaseLinkRepository(record))

    with pytest.raises(AppError) as captured:
        service.get_destination(PRODUCT_ID)

    assert captured.value.status_code == 404
    assert captured.value.code == code


def test_get_destination_maps_database_failure() -> None:
    service = PurchaseLinkService(FakePurchaseLinkRepository(None, fails=True))

    with pytest.raises(AppError) as captured:
        service.get_destination(PRODUCT_ID)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"


def test_get_destination_rejects_unsafe_stored_url() -> None:
    service = PurchaseLinkService(
        FakePurchaseLinkRepository(
            PurchaseLinkRecord(product_exists=True, url="http://example.com/product")
        )
    )

    with pytest.raises(AppError) as captured:
        service.get_destination(PRODUCT_ID)

    assert captured.value.status_code == 503
    assert captured.value.code == "SERVICE_UNAVAILABLE"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/product",
        "https://user:password@example.com/product",
        "https://example.com/product#details",
        "https://example.com/product#",
        "https://example.com/a path",
        "https:///missing-host",
        "https://example.com/" + "a" * 2030,
    ],
)
def test_validate_purchase_url_rejects_unsafe_url(url: str) -> None:
    with pytest.raises(ValueError):
        validate_purchase_url(url)


def test_validate_purchase_url_accepts_https_query() -> None:
    assert validate_purchase_url(VALID_URL) == VALID_URL
