from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from allyakkkuk.curation.product_repository import SQLAlchemyProductRepository
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.3")]

FIXED_TIME = datetime(2026, 8, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_catalog() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
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
    value: int,
    *,
    sku: str,
    published: bool = True,
    sort_order: int = 10,
) -> Product:
    return Product(
        id=UUID(f"22000000-0000-4000-8000-{value:012d}"),
        sku=sku,
        product_type="SUPPLEMENT",
        brand="샘플 브랜드",
        name=f"샘플 제품 {value}",
        image_url=f"/static/products/product-{value}.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("30"),
        display_price=1000 * value,
        is_published=published,
        sort_order=sort_order,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )


def mapping(product_id: UUID, category_id: UUID) -> ProductCategoryMapping:
    return ProductCategoryMapping(product_id=product_id, category_id=category_id)


def test_repository_filters_published_active_mappings_deduplicates_and_sorts() -> None:
    vitamin = category(1, "vitamin")
    protein = category(2, "protein")
    inactive = category(3, "inactive", active=False)
    alpha = product(1, sku="ALPHA", sort_order=10)
    zeta = product(2, sku="ZETA", sort_order=10)
    hidden = product(3, sku="HIDDEN", published=False, sort_order=0)
    inactive_only = product(4, sku="INACTIVE-ONLY", sort_order=0)
    no_category = product(5, sku="NO-CATEGORY", sort_order=0)

    with SessionFactory.begin() as session:
        session.add_all([vitamin, protein, inactive])
        session.add_all([alpha, zeta, hidden, inactive_only, no_category])
        session.add_all(
            [
                mapping(alpha.id, vitamin.id),
                mapping(alpha.id, protein.id),
                mapping(zeta.id, vitamin.id),
                mapping(hidden.id, vitamin.id),
                mapping(inactive_only.id, inactive.id),
            ]
        )

    with SessionFactory() as session:
        repository = SQLAlchemyProductRepository(session)
        all_page = repository.list_published(
            category_slug=None,
            page=1,
            page_size=20,
        )
        vitamin_page = repository.list_published(
            category_slug="vitamin",
            page=1,
            page_size=20,
        )

    assert all_page.total == 2
    assert [(item.sku, item.category_slugs) for item in all_page.items] == [
        ("ALPHA", ("vitamin", "protein")),
        ("ZETA", ("vitamin",)),
    ]
    assert [item.sku for item in vitamin_page.items] == ["ALPHA", "ZETA"]


def test_repository_category_activity_and_empty_page_boundary() -> None:
    with SessionFactory.begin() as session:
        session.add_all([category(1, "vitamin"), category(2, "inactive", active=False)])

    with SessionFactory() as session:
        repository = SQLAlchemyProductRepository(session)
        assert repository.category_is_active("vitamin") is True
        assert repository.category_is_active("inactive") is False
        assert repository.category_is_active("unknown") is False
        result = repository.list_published(
            category_slug=None,
            page=999,
            page_size=20,
        )

    assert result.items == ()
    assert result.total == 0


def test_product_schema_matches_approved_constraints_foreign_keys_and_indexes() -> None:
    inspector = inspect(engine)

    product_columns = {item["name"]: item for item in inspector.get_columns("products")}
    unique_names = {
        item["name"] for item in inspector.get_unique_constraints("products")
    }
    check_names = {item["name"] for item in inspector.get_check_constraints("products")}
    product_indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("products")
    }
    mapping_pk = inspector.get_pk_constraint("product_category_mappings")
    mapping_fks = inspector.get_foreign_keys("product_category_mappings")
    mapping_indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("product_category_mappings")
    }

    assert set(product_columns) == {
        "id",
        "sku",
        "product_type",
        "brand",
        "name",
        "image_url",
        "unit_form",
        "units_per_package",
        "display_price",
        "is_published",
        "sort_order",
        "created_at",
        "updated_at",
    }
    assert all(not item["nullable"] for item in product_columns.values())
    assert "uq_products_sku" in unique_names
    assert check_names >= {
        "ck_products_sku_format",
        "ck_products_product_type",
        "ck_products_brand_length",
        "ck_products_name_length",
        "ck_products_image_url_length",
        "ck_products_unit_form",
        "ck_products_units_per_package",
        "ck_products_display_price",
        "ck_products_sort_order",
        "ck_products_updated_at",
    }
    assert product_indexes["ix_products_published_sort"] == (
        "is_published",
        "sort_order",
        "sku",
    )
    assert tuple(mapping_pk["constrained_columns"]) == (
        "product_id",
        "category_id",
    )
    assert {item["options"].get("ondelete") for item in mapping_fks} == {"CASCADE"}
    assert mapping_indexes["ix_product_category_mappings_category_product"] == (
        "category_id",
        "product_id",
    )
