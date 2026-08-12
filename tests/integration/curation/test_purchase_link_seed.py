from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select, update

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
    PurchaseLink,
)
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.purchase_link_seeds import (
    PURCHASE_LINK_SEED_ROWS,
    PurchaseLinkSeedSet,
)
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.2")]


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


def test_purchase_link_seed_is_deterministic_and_idempotent() -> None:
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        seed = PurchaseLinkSeedSet()
        assert seed.apply(connection) == len(PURCHASE_LINK_SEED_ROWS)
        connection.execute(
            update(PurchaseLink)
            .where(PurchaseLink.id == PURCHASE_LINK_SEED_ROWS[0].id)
            .values(
                provider_name="변경됨",
                url="https://example.com/changed",
                is_active=False,
            )
        )
        assert seed.apply(connection) == len(PURCHASE_LINK_SEED_ROWS)
        assert seed.apply(connection) == len(PURCHASE_LINK_SEED_ROWS)

    with SessionFactory() as session:
        stored = tuple(
            session.execute(select(PurchaseLink).order_by(PurchaseLink.id)).scalars()
        )
        sku_by_id = {
            product_id: sku
            for product_id, sku in session.execute(select(Product.id, Product.sku))
        }

    assert [
        (
            item.id,
            sku_by_id[item.product_id],
            item.provider_name,
            item.url,
            item.is_active,
            item.sort_order,
        )
        for item in stored
    ] == [
        (
            row.id,
            row.product_sku,
            row.provider_name,
            row.url,
            True,
            row.sort_order,
        )
        for row in sorted(PURCHASE_LINK_SEED_ROWS, key=lambda value: value.id)
    ]
