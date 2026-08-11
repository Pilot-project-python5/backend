from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from allyakkkuk.curation.models import (
    Nutrient,
    Product,
    ProductCategory,
    ProductCategoryMapping,
    ProductNutrient,
)
from allyakkkuk.curation.product_nutrient_seeds import ProductNutrientSeedSet
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine
from allyakkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000001")


@pytest.fixture(autouse=True)
def seeded_product_detail() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        ProductNutrientSeedSet().apply(connection)
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_visitor_reads_seeded_product_package_and_nutrients() -> None:
    with TestClient(app) as client:
        response = client.get(f"/api/v1/curation/products/{PRODUCT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "LIFE-TWO-PER-DAY"
    assert body["category_slugs"] == ["vitamin"]
    assert body["package"] == {
        "unit_form": "TABLET",
        "units_per_package": "120",
    }
    assert body["nutrients"] == [
        {
            "code": "VITAMIN_C",
            "name": "비타민 C",
            "amount_per_unit": "235",
            "unit": "MG",
        },
        {
            "code": "VITAMIN_D",
            "name": "비타민 D",
            "amount_per_unit": "25",
            "unit": "MCG",
        },
    ]
