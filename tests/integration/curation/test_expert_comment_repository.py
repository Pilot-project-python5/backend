from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from allyakkkuk.curation.models import (
    ExpertComment,
    Product,
    ProductCategory,
    ProductCategoryMapping,
)
from allyakkkuk.curation.product_detail_repository import (
    SQLAlchemyProductDetailRepository,
)
from allyakkkuk.db.session import SessionFactory, engine

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-2.4.1")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000091")
FIXED_TIME = datetime(2026, 8, 12, tzinfo=UTC)


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


def comment(
    value: int,
    *,
    active: bool = True,
    sort_order: int = 10,
) -> ExpertComment:
    return ExpertComment(
        id=UUID(f"24000000-0000-4000-8000-{value:012d}"),
        product_id=PRODUCT_ID,
        author_label=f"전문가 {value}",
        content=f"코멘트 {value}",
        is_active=active,
        sort_order=sort_order,
    )


def category(value: int, slug: str) -> ProductCategory:
    return ProductCategory(
        id=UUID(f"21000000-0000-4000-8000-{value:012d}"),
        slug=slug,
        name=slug,
        is_active=True,
        sort_order=value * 10,
    )


def product() -> Product:
    return Product(
        id=PRODUCT_ID,
        sku="DETAIL-0091",
        product_type="SUPPLEMENT",
        brand="상세 브랜드",
        name="상세 제품",
        image_url="/static/products/detail.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("30.50"),
        display_price=12300,
        is_published=True,
        sort_order=10,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )


def test_repository_returns_only_active_comments_in_stable_order() -> None:
    vitamin = category(1, "vitamin")
    item = product()
    with SessionFactory.begin() as session:
        session.add_all([vitamin, item])
        session.add(ProductCategoryMapping(product_id=item.id, category_id=vitamin.id))
        session.flush()
        session.add_all(
            [
                comment(2, sort_order=10),
                comment(1, sort_order=10),
                comment(3, active=False, sort_order=0),
            ]
        )

    with SessionFactory() as session:
        result = SQLAlchemyProductDetailRepository(session).get_published(item.id)

    assert result is not None
    assert [value.id for value in result.expert_comments] == [
        comment(1).id,
        comment(2).id,
    ]


def test_repository_returns_empty_comments_for_public_product() -> None:
    vitamin = category(1, "vitamin")
    item = product()
    with SessionFactory.begin() as session:
        session.add_all([vitamin, item])
        session.add(ProductCategoryMapping(product_id=item.id, category_id=vitamin.id))

    with SessionFactory() as session:
        result = SQLAlchemyProductDetailRepository(session).get_published(item.id)

    assert result is not None
    assert result.expert_comments == ()


def test_expert_comment_schema_matches_constraints_foreign_key_and_index() -> None:
    inspector = inspect(engine)
    columns = {item["name"]: item for item in inspector.get_columns("expert_comments")}
    checks = {
        item["name"] for item in inspector.get_check_constraints("expert_comments")
    }
    foreign_keys = inspector.get_foreign_keys("expert_comments")
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("expert_comments")
    }

    assert set(columns) == {
        "id",
        "product_id",
        "author_label",
        "content",
        "is_active",
        "sort_order",
    }
    assert all(not item["nullable"] for item in columns.values())
    assert checks >= {
        "ck_expert_comments_author_label_length",
        "ck_expert_comments_content_length",
        "ck_expert_comments_sort_order",
    }
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["options"].get("ondelete") == "CASCADE"
    assert indexes["ix_expert_comments_product_active_sort"] == (
        "product_id",
        "is_active",
        "sort_order",
        "id",
    )
