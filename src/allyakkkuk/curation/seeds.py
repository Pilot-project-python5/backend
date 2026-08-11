"""F-2.2 결정적 제품 카테고리 개발 시드."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import ProductCategory


@dataclass(frozen=True, slots=True)
class ProductCategorySeedRow:
    id: UUID
    slug: str
    name: str
    sort_order: int


PRODUCT_CATEGORY_SEED_ROWS = (
    ProductCategorySeedRow(
        id=UUID("21000000-0000-4000-8000-000000000001"),
        slug="vitamin",
        name="비타민",
        sort_order=10,
    ),
    ProductCategorySeedRow(
        id=UUID("21000000-0000-4000-8000-000000000002"),
        slug="protein",
        name="단백질",
        sort_order=20,
    ),
    ProductCategorySeedRow(
        id=UUID("21000000-0000-4000-8000-000000000003"),
        slug="omega-3",
        name="오메가3",
        sort_order=30,
    ),
)


class ProductCategorySeedSet:
    name = "product_categories"

    def apply(self, connection: Connection) -> int:
        values = [
            {
                "id": row.id,
                "slug": row.slug,
                "name": row.name,
                "is_active": True,
                "sort_order": row.sort_order,
            }
            for row in PRODUCT_CATEGORY_SEED_ROWS
        ]
        statement = insert(ProductCategory).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[ProductCategory.slug],
            set_={
                "name": statement.excluded.name,
                "is_active": statement.excluded.is_active,
                "sort_order": statement.excluded.sort_order,
            },
        )
        connection.execute(statement)
        return len(PRODUCT_CATEGORY_SEED_ROWS)
