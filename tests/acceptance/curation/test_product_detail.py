from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from allyakkkuk.care.nutrient_reference_models import NutrientReferenceVersion
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

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000101")


@pytest.fixture(autouse=True)
def seeded_product_detail() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(NutrientReferenceVersion))
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
        session.execute(delete(NutrientReferenceVersion))
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
    assert body["sku"] == "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE"
    assert body["category_slugs"] == ["multivitamin"]
    assert body["package"] == {
        "unit_form": "TABLET",
        "units_per_package": "60",
    }
    assert body["nutrients"] == [
        {
            "code": "VITAMIN_A_RE",
            "name": "비타민 A(레티놀 활성당량)",
            "amount_per_unit": "350",
            "unit": "MCG",
        },
        {
            "code": "VITAMIN_C",
            "name": "비타민 C",
            "amount_per_unit": "100",
            "unit": "MG",
        },
        {
            "code": "VITAMIN_D",
            "name": "비타민 D",
            "amount_per_unit": "10",
            "unit": "MCG",
        },
        {
            "code": "VITAMIN_E",
            "name": "비타민 E",
            "amount_per_unit": "5.5",
            "unit": "MG",
        },
        {
            "code": "VITAMIN_K",
            "name": "비타민 K",
            "amount_per_unit": "70",
            "unit": "MCG",
        },
        {"code": "CALCIUM", "name": "칼슘", "amount_per_unit": "230", "unit": "MG"},
        {
            "code": "MAGNESIUM",
            "name": "마그네슘",
            "amount_per_unit": "104",
            "unit": "MG",
        },
        {"code": "ZINC", "name": "아연", "amount_per_unit": "8.5", "unit": "MG"},
    ]
