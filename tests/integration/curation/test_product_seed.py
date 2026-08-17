from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from yeongyangkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from yeongyangkkuk.curation.product_seeds import PRODUCT_SEED_ROWS, ProductSeedSet
from yeongyangkkuk.curation.seeds import ProductCategorySeedSet
from yeongyangkkuk.db.session import SessionFactory, engine
from yeongyangkkuk.main import app

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.3")]


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


def test_product_seed_is_deterministic_idempotent_and_restores_mappings() -> None:
    category_seed = ProductCategorySeedSet()
    product_seed = ProductSeedSet()
    with engine.begin() as connection:
        category_seed.apply(connection)
        assert product_seed.apply(connection) == len(PRODUCT_SEED_ROWS)
        connection.execute(
            update(Product)
            .where(Product.sku == PRODUCT_SEED_ROWS[0].sku)
            .values(name="변경됨", is_published=False, sort_order=999)
        )
        connection.execute(delete(ProductCategoryMapping))
        assert product_seed.apply(connection) == len(PRODUCT_SEED_ROWS)
        assert product_seed.apply(connection) == len(PRODUCT_SEED_ROWS)

    with SessionFactory() as session:
        stored = (
            session.execute(select(Product).order_by(Product.sort_order))
            .scalars()
            .all()
        )
        mappings = tuple(
            (sku, slug)
            for sku, slug in session.execute(
                select(Product.sku, ProductCategory.slug)
                .join(
                    ProductCategoryMapping,
                    ProductCategoryMapping.product_id == Product.id,
                )
                .join(
                    ProductCategory,
                    ProductCategory.id == ProductCategoryMapping.category_id,
                )
                .order_by(Product.sort_order, ProductCategory.sort_order)
            )
        )

    assert [
        (
            item.id,
            item.sku,
            item.name,
            item.display_price,
            item.is_published,
            item.sort_order,
        )
        for item in stored
    ] == [
        (
            row.id,
            row.sku,
            row.name,
            row.display_price,
            True,
            row.sort_order,
        )
        for row in PRODUCT_SEED_ROWS
    ]
    assert mappings == tuple((row.sku, row.category_slug) for row in PRODUCT_SEED_ROWS)

    with TestClient(app) as client:
        for row in PRODUCT_SEED_ROWS:
            response = client.get(row.image_url)
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("image/svg+xml")
