"""F-2.2 결정적 제품 카테고리 개발 시드."""

from __future__ import annotations

from sqlalchemy import Connection, update
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.catalog_seed_data import PRODUCT_CATEGORY_SEED_ROWS
from allyakkkuk.curation.models import ProductCategory

LEGACY_CATEGORY_SLUGS = ("vitamin", "protein")


class ProductCategorySeedSet:
    name = "product_categories"

    def apply(self, connection: Connection) -> int:
        connection.execute(
            update(ProductCategory)
            .where(ProductCategory.slug.in_(LEGACY_CATEGORY_SLUGS))
            .values(is_active=False)
        )
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
