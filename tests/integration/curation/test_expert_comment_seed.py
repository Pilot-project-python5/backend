from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select, update

from allyakkkuk.curation.expert_comment_seeds import (
    EXPERT_COMMENT_SEED_ROWS,
    ExpertCommentSeedSet,
)
from allyakkkuk.curation.models import (
    ExpertComment,
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from allyakkkuk.curation.product_seeds import ProductSeedSet
from allyakkkuk.curation.seeds import ProductCategorySeedSet
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.1")]


@pytest.fixture(autouse=True)
def clean_catalog() -> Iterator[None]:
    with SessionFactory.begin() as session:
        session.execute(delete(ExpertComment))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))
    yield
    with SessionFactory.begin() as session:
        session.execute(delete(ExpertComment))
        session.execute(delete(ProductCategoryMapping))
        session.execute(delete(Product))
        session.execute(delete(ProductCategory))


def test_expert_comment_seed_is_deterministic_and_idempotent() -> None:
    with engine.begin() as connection:
        ProductCategorySeedSet().apply(connection)
        ProductSeedSet().apply(connection)
        seed = ExpertCommentSeedSet()
        assert seed.apply(connection) == len(EXPERT_COMMENT_SEED_ROWS)
        connection.execute(
            update(ExpertComment)
            .where(ExpertComment.id == EXPERT_COMMENT_SEED_ROWS[0].id)
            .values(content="변경됨", is_active=False, sort_order=999)
        )
        assert seed.apply(connection) == len(EXPERT_COMMENT_SEED_ROWS)
        assert seed.apply(connection) == len(EXPERT_COMMENT_SEED_ROWS)

    with SessionFactory() as session:
        stored = tuple(
            session.execute(select(ExpertComment).order_by(ExpertComment.id)).scalars()
        )
        sku_by_id = {
            product_id: sku
            for product_id, sku in session.execute(select(Product.id, Product.sku))
        }

    assert [
        (
            item.id,
            sku_by_id[item.product_id],
            item.author_label,
            item.content,
            item.is_active,
            item.sort_order,
        )
        for item in stored
    ] == [
        (
            row.id,
            row.product_sku,
            row.author_label,
            row.content,
            True,
            row.sort_order,
        )
        for row in sorted(EXPERT_COMMENT_SEED_ROWS, key=lambda value: value.id)
    ]
