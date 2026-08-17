from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from yeongyangkkuk.curation.models import ProductCategory
from yeongyangkkuk.curation.product_category_repository import (
    SQLAlchemyProductCategoryRepository,
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


def category(
    value: int,
    *,
    slug: str,
    name: str,
    active: bool = True,
    sort_order: int = 10,
) -> ProductCategory:
    return ProductCategory(
        id=UUID(f"00000000-0000-4000-8000-{value:012d}"),
        slug=slug,
        name=name,
        is_active=active,
        sort_order=sort_order,
    )


def test_repository_excludes_inactive_and_reserved_all_then_sorts_stably() -> None:
    with SessionFactory.begin() as session:
        session.add_all(
            [
                category(1, slug="zeta", name="제타", sort_order=10),
                category(2, slug="alpha", name="알파", sort_order=10),
                category(3, slug="inactive", name="비활성", active=False),
                category(4, slug="all", name="잘못 저장된 전체", sort_order=0),
                category(5, slug="later", name="나중", sort_order=20),
            ]
        )

    with SessionFactory() as session:
        records = SQLAlchemyProductCategoryRepository(session).list_active()

    assert [(record.slug, record.name, record.sort_order) for record in records] == [
        ("alpha", "알파", 10),
        ("zeta", "제타", 10),
        ("later", "나중", 20),
    ]


def test_product_categories_schema_matches_approved_constraints_and_index() -> None:
    inspector = inspect(engine)

    columns = {
        item["name"]: item for item in inspector.get_columns("product_categories")
    }
    unique_names = {
        item["name"] for item in inspector.get_unique_constraints("product_categories")
    }
    check_names = {
        item["name"] for item in inspector.get_check_constraints("product_categories")
    }
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("product_categories")
    }

    assert set(columns) == {"id", "slug", "name", "is_active", "sort_order"}
    assert all(not item["nullable"] for item in columns.values())
    assert "uq_product_categories_slug" in unique_names
    assert check_names >= {
        "ck_product_categories_slug_format",
        "ck_product_categories_name_length",
        "ck_product_categories_sort_order",
    }
    assert indexes["ix_product_categories_active_sort"] == (
        "is_active",
        "sort_order",
        "slug",
    )
