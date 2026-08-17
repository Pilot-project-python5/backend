from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.3")]


@pytest.fixture(autouse=True)
def seeded_products() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_public_product_list_filters_category_and_paginates_stably() -> None:
    with TestClient(app) as client:
        first = client.get(
            "/api/v1/curation/products",
            params={"page": 1, "page_size": 2},
        )
        second = client.get(
            "/api/v1/curation/products",
            params={"page": 2, "page_size": 2},
        )
        multivitamin = client.get(
            "/api/v1/curation/products",
            params={"category": "multivitamin"},
        )

    assert first.status_code == 200
    assert [item["sku"] for item in first.json()["items"]] == [
        "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
        "ALIVE-ONCE-DAILY-MENS",
    ]
    assert first.json() | {"items": []} == {
        "items": [],
        "page": 1,
        "page_size": 2,
        "total": 32,
        "has_next": True,
    }
    assert [item["sku"] for item in second.json()["items"]] == [
        "ALIVE-ONCE-DAILY-WOMENS",
        "KORYO-EUNDAN-MEGADOSE-B",
    ]
    assert second.json()["has_next"] is True
    assert [item["sku"] for item in multivitamin.json()["items"]] == [
        "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
        "ALIVE-ONCE-DAILY-MENS",
        "ALIVE-ONCE-DAILY-WOMENS",
    ]


def test_unknown_category_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/curation/products",
            params={"category": "unknown"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"
