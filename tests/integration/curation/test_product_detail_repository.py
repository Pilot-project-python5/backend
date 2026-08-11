from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from allyakkkuk.curation.models import (
    Nutrient,
    Product,
    ProductCategory,
    ProductCategoryMapping,
    ProductNutrient,
)
from allyakkkuk.curation.product_detail_repository import (
    SQLAlchemyProductDetailRepository,
)
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4")]

FIXED_TIME = datetime(2026, 8, 12, tzinfo=UTC)
PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000091")


@pytest.fixture(autouse=True)
def clean_catalog() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ProductNutrient))
        session.execute(delete(Nutrient))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def category(value: int, slug: str, *, active: bool = True) -> ProductCategory:
    return ProductCategory(
        id=UUID(f"21000000-0000-4000-8000-{value:012d}"),
        slug=slug,
        name=slug,
        is_active=active,
        sort_order=value * 10,
    )


def product(
    product_id: UUID = PRODUCT_ID,
    *,
    published: bool = True,
) -> Product:
    return Product(
        id=product_id,
        sku=f"DETAIL-{str(product_id)[-4:]}",
        product_type="SUPPLEMENT",
        brand="상세 브랜드",
        name="상세 제품",
        image_url="/static/products/detail.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("30.50"),
        display_price=12300,
        is_published=published,
        sort_order=10,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )


def nutrient(
    value: int,
    code: str,
    *,
    active: bool = True,
    unit: str = "MG",
) -> Nutrient:
    return Nutrient(
        id=UUID(f"23000000-0000-4000-8000-{value:012d}"),
        code=code,
        name=code,
        canonical_unit=unit,
        is_active=active,
    )


def test_repository_returns_active_categories_and_nutrients_in_stable_order() -> None:
    vitamin = category(1, "vitamin")
    protein = category(2, "protein")
    inactive_category = category(3, "inactive", active=False)
    item = product()
    zeta = nutrient(1, "ZETA")
    alpha = nutrient(2, "ALPHA")
    inactive_nutrient = nutrient(3, "INACTIVE", active=False)

    with SessionFactory.begin() as session:
        session.add_all([vitamin, protein, inactive_category, item])
        session.add_all([zeta, alpha, inactive_nutrient])
        session.add_all(
            [
                ProductCategoryMapping(product_id=item.id, category_id=protein.id),
                ProductCategoryMapping(product_id=item.id, category_id=vitamin.id),
                ProductCategoryMapping(
                    product_id=item.id,
                    category_id=inactive_category.id,
                ),
                ProductNutrient(
                    product_id=item.id,
                    nutrient_id=zeta.id,
                    amount_per_unit=Decimal("2.5000"),
                    unit="MG",
                    sort_order=20,
                ),
                ProductNutrient(
                    product_id=item.id,
                    nutrient_id=alpha.id,
                    amount_per_unit=Decimal("1.2500"),
                    unit="MG",
                    sort_order=10,
                ),
                ProductNutrient(
                    product_id=item.id,
                    nutrient_id=inactive_nutrient.id,
                    amount_per_unit=Decimal("9.0000"),
                    unit="MG",
                    sort_order=0,
                ),
            ]
        )

    with SessionFactory() as session:
        result = SQLAlchemyProductDetailRepository(session).get_published(item.id)

    assert result is not None
    assert result.category_slugs == ("vitamin", "protein")
    assert result.units_per_package == Decimal("30.50")
    assert [(value.code, value.amount_per_unit) for value in result.nutrients] == [
        ("ALPHA", Decimal("1.2500")),
        ("ZETA", Decimal("2.5000")),
    ]


def test_repository_returns_empty_nutrients_for_public_product() -> None:
    vitamin = category(1, "vitamin")
    item = product()
    with SessionFactory.begin() as session:
        session.add_all([vitamin, item])
        session.add(ProductCategoryMapping(product_id=item.id, category_id=vitamin.id))

    with SessionFactory() as session:
        result = SQLAlchemyProductDetailRepository(session).get_published(item.id)

    assert result is not None
    assert result.nutrients == ()


@pytest.mark.parametrize("visibility", ["missing", "unpublished", "inactive-category"])
def test_repository_hides_products_outside_public_conditions(visibility: str) -> None:
    product_id = PRODUCT_ID
    if visibility != "missing":
        active = visibility != "inactive-category"
        product_row = product(published=visibility != "unpublished")
        category_row = category(1, "vitamin", active=active)
        with SessionFactory.begin() as session:
            session.add_all([product_row, category_row])
            session.add(
                ProductCategoryMapping(
                    product_id=product_row.id,
                    category_id=category_row.id,
                )
            )

    with SessionFactory() as session:
        result = SQLAlchemyProductDetailRepository(session).get_published(product_id)

    assert result is None


def test_nutrient_schema_matches_constraints_foreign_keys_and_indexes() -> None:
    inspector = inspect(engine)
    nutrient_columns = {
        item["name"]: item for item in inspector.get_columns("nutrients")
    }
    nutrient_unique = {
        item["name"] for item in inspector.get_unique_constraints("nutrients")
    }
    nutrient_checks = {
        item["name"] for item in inspector.get_check_constraints("nutrients")
    }
    nutrient_indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("nutrients")
    }
    mapping_columns = {
        item["name"]: item for item in inspector.get_columns("product_nutrients")
    }
    mapping_pk = inspector.get_pk_constraint("product_nutrients")
    mapping_fks = inspector.get_foreign_keys("product_nutrients")
    mapping_checks = {
        item["name"] for item in inspector.get_check_constraints("product_nutrients")
    }
    mapping_indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("product_nutrients")
    }

    assert set(nutrient_columns) == {
        "id",
        "code",
        "name",
        "canonical_unit",
        "is_active",
    }
    assert all(not item["nullable"] for item in nutrient_columns.values())
    assert "uq_nutrients_code" in nutrient_unique
    assert nutrient_checks >= {
        "ck_nutrients_code_format",
        "ck_nutrients_name_length",
        "ck_nutrients_canonical_unit",
    }
    assert nutrient_indexes["ix_nutrients_active_code"] == ("is_active", "code")
    assert set(mapping_columns) == {
        "product_id",
        "nutrient_id",
        "amount_per_unit",
        "unit",
        "sort_order",
    }
    assert all(not item["nullable"] for item in mapping_columns.values())
    assert tuple(mapping_pk["constrained_columns"]) == (
        "product_id",
        "nutrient_id",
    )
    assert {item["options"].get("ondelete") for item in mapping_fks} == {
        "CASCADE",
        "RESTRICT",
    }
    assert mapping_checks >= {
        "ck_product_nutrients_amount_per_unit",
        "ck_product_nutrients_unit",
        "ck_product_nutrients_sort_order",
    }
    assert mapping_indexes["ix_product_nutrients_product_sort"] == (
        "product_id",
        "sort_order",
        "nutrient_id",
    )
