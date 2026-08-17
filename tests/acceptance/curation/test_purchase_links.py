from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from yeongyangkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
    PurchaseLink,
)
from yeongyangkkuk.curation.product_seeds import ProductSeedSet
from yeongyangkkuk.curation.purchase_link_seeds import PurchaseLinkSeedSet
from yeongyangkkuk.curation.seeds import ProductCategorySeedSet
from yeongyangkkuk.db.session import SessionFactory, engine
from yeongyangkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.2")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000101")
DESTINATION = "https://www.coupang.com/vp/products/6743604050"


@pytest.fixture(autouse=True)
def seeded_purchase_links() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(PurchaseLink))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        PurchaseLinkSeedSet().apply(connection)
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(PurchaseLink))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_visitor_moves_to_seeded_purchase_link_without_tracking_write() -> None:
    with SessionFactory() as session:
        count_before = session.scalar(select(func.count()).select_from(PurchaseLink))

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/curation/products/{PRODUCT_ID}/purchase",
            follow_redirects=False,
        )

    with SessionFactory() as session:
        count_after = session.scalar(select(func.count()).select_from(PurchaseLink))

    assert response.status_code == 307
    assert response.headers["location"] == DESTINATION
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert count_after == count_before == 32
