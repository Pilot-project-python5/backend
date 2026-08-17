from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from yeongyangkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
    PurchaseLink,
)
from yeongyangkkuk.curation.purchase_link_repository import (
    SQLAlchemyPurchaseLinkRepository,
)
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.2")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000092")
FIXED_TIME = datetime(2026, 8, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_catalog() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(PurchaseLink))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(PurchaseLink))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def category(*, active: bool = True) -> ProductCategory:
    return ProductCategory(
        id=UUID("21000000-0000-4000-8000-000000000092"),
        slug="purchase-test",
        name="구매 테스트",
        is_active=active,
        sort_order=10,
    )


def product(*, published: bool = True) -> Product:
    return Product(
        id=PRODUCT_ID,
        sku="PURCHASE-TEST",
        product_type="SUPPLEMENT",
        brand="구매 브랜드",
        name="구매 제품",
        image_url="/static/products/purchase.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("30"),
        display_price=10000,
        is_published=published,
        sort_order=10,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )


def link(value: int, *, active: bool = True, sort_order: int = 10) -> PurchaseLink:
    return PurchaseLink(
        id=UUID(f"25000000-0000-4000-8000-{value:012d}"),
        product_id=PRODUCT_ID,
        provider_name=f"판매처 {value}",
        url=f"https://example.com/products/{value}",
        is_active=active,
        sort_order=sort_order,
    )


def add_public_product(*, published: bool = True, category_active: bool = True) -> None:
    item = product(published=published)
    group = category(active=category_active)
    with SessionFactory.begin() as session:
        session.add_all([item, group])
        session.add(ProductCategoryMapping(product_id=item.id, category_id=group.id))


def test_repository_selects_first_active_link_in_stable_order() -> None:
    add_public_product()
    with SessionFactory.begin() as session:
        session.add_all(
            [
                link(2, sort_order=10),
                link(1, sort_order=10),
                link(3, active=False, sort_order=0),
            ]
        )

    with SessionFactory() as session:
        result = SQLAlchemyPurchaseLinkRepository(session).get_first_for_public_product(
            PRODUCT_ID
        )

    assert result is not None
    assert result.product_exists is True
    assert result.url == "https://example.com/products/1"


def test_repository_distinguishes_public_product_without_active_link() -> None:
    add_public_product()
    with SessionFactory.begin() as session:
        session.add(link(1, active=False))

    with SessionFactory() as session:
        result = SQLAlchemyPurchaseLinkRepository(session).get_first_for_public_product(
            PRODUCT_ID
        )

    assert result is not None
    assert result.product_exists is True
    assert result.url is None


@pytest.mark.parametrize("visibility", ["missing", "unpublished", "inactive-category"])
def test_repository_hides_products_outside_public_conditions(visibility: str) -> None:
    if visibility != "missing":
        add_public_product(
            published=visibility != "unpublished",
            category_active=visibility != "inactive-category",
        )

    with SessionFactory() as session:
        result = SQLAlchemyPurchaseLinkRepository(session).get_first_for_public_product(
            PRODUCT_ID
        )

    assert result is None


def test_purchase_link_schema_matches_constraints_foreign_key_and_index() -> None:
    inspector = inspect(engine)
    columns = {item["name"]: item for item in inspector.get_columns("purchase_links")}
    checks = {
        item["name"] for item in inspector.get_check_constraints("purchase_links")
    }
    foreign_keys = inspector.get_foreign_keys("purchase_links")
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("purchase_links")
    }

    assert set(columns) == {
        "id",
        "product_id",
        "provider_name",
        "url",
        "is_active",
        "sort_order",
    }
    assert all(not item["nullable"] for item in columns.values())
    assert checks >= {
        "ck_purchase_links_provider_name_length",
        "ck_purchase_links_url_length",
        "ck_purchase_links_url_https",
        "ck_purchase_links_url_no_userinfo",
        "ck_purchase_links_sort_order",
    }
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["options"].get("ondelete") == "CASCADE"
    assert indexes["ix_purchase_links_product_active_sort"] == (
        "product_id",
        "is_active",
        "sort_order",
        "id",
    )
