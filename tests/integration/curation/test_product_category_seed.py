from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select, update

from yeongyangkkuk.curation.models import ProductCategory
from yeongyangkkuk.curation.seeds import (
    PRODUCT_CATEGORY_SEED_ROWS,
    ProductCategorySeedSet,
)
from yeongyangkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.2")]


@pytest.fixture(autouse=True)
def clean_categories() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ProductCategory))


def test_category_seed_is_deterministic_idempotent_and_restores_values() -> None:
    seed = ProductCategorySeedSet()
    with engine.begin() as connection:
        assert seed.apply(connection) == len(PRODUCT_CATEGORY_SEED_ROWS)
        connection.execute(
            update(ProductCategory)
            .where(ProductCategory.slug == PRODUCT_CATEGORY_SEED_ROWS[0].slug)
            .values(name="변경됨", is_active=False, sort_order=999)
        )
        assert seed.apply(connection) == len(PRODUCT_CATEGORY_SEED_ROWS)
        assert seed.apply(connection) == len(PRODUCT_CATEGORY_SEED_ROWS)

    with SessionFactory() as session:
        stored = (
            session.execute(
                select(ProductCategory).order_by(ProductCategory.sort_order)
            )
            .scalars()
            .all()
        )

    assert [
        (item.id, item.slug, item.name, item.is_active, item.sort_order)
        for item in stored
    ] == [
        (row.id, row.slug, row.name, True, row.sort_order)
        for row in PRODUCT_CATEGORY_SEED_ROWS
    ]
