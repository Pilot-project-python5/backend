"""F-2.3 결정적 추천 제품과 카테고리 매핑 시드."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Connection, delete, select, update
from sqlalchemy.dialects.postgresql import insert

from yeongyangkkuk.curation.catalog_seed_data import (
    PRODUCT_SEED_ROWS as PRODUCT_SEED_ROWS,
)
from yeongyangkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)

SEED_TIME = datetime(2026, 8, 12, tzinfo=UTC)
LEGACY_PRODUCT_SKUS = ("LIFE-TWO-PER-DAY", "SPORTS-RESEARCH-OMEGA-3")


class ProductSeedSet:
    name = "recommended_products"

    def apply(self, connection: Connection) -> int:
        connection.execute(
            update(Product)
            .where(Product.sku.in_(LEGACY_PRODUCT_SKUS))
            .values(is_published=False, updated_at=SEED_TIME)
        )
        values = [
            {
                "id": row.id,
                "sku": row.sku,
                "product_type": row.product_type,
                "brand": row.brand,
                "name": row.name,
                "image_url": row.image_url,
                "unit_form": row.unit_form,
                "units_per_package": row.units_per_package,
                "display_price": row.display_price,
                "is_published": True,
                "sort_order": row.sort_order,
                "created_at": SEED_TIME,
                "updated_at": SEED_TIME,
            }
            for row in PRODUCT_SEED_ROWS
        ]
        insert_statement = insert(Product).values(values)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[Product.sku],
            set_={
                "product_type": insert_statement.excluded.product_type,
                "brand": insert_statement.excluded.brand,
                "name": insert_statement.excluded.name,
                "image_url": insert_statement.excluded.image_url,
                "unit_form": insert_statement.excluded.unit_form,
                "units_per_package": insert_statement.excluded.units_per_package,
                "display_price": insert_statement.excluded.display_price,
                "is_published": insert_statement.excluded.is_published,
                "sort_order": insert_statement.excluded.sort_order,
                "updated_at": insert_statement.excluded.updated_at,
            },
        ).returning(Product.id, Product.sku)
        product_ids = {
            sku: product_id for product_id, sku in connection.execute(upsert_statement)
        }

        category_slugs = tuple(row.category_slug for row in PRODUCT_SEED_ROWS)
        category_ids = {
            slug: category_id
            for category_id, slug in connection.execute(
                select(ProductCategory.id, ProductCategory.slug).where(
                    ProductCategory.slug.in_(category_slugs)
                )
            )
        }
        missing = set(category_slugs) - set(category_ids)
        if missing:
            raise ValueError(
                f"제품 시드에 필요한 카테고리가 없습니다: {sorted(missing)}"
            )

        seeded_product_ids = tuple(product_ids.values())
        connection.execute(
            delete(ProductCategoryMapping).where(
                ProductCategoryMapping.product_id.in_(seeded_product_ids)
            )
        )
        connection.execute(
            insert(ProductCategoryMapping).values(
                [
                    {
                        "product_id": product_ids[row.sku],
                        "category_id": category_ids[row.category_slug],
                    }
                    for row in PRODUCT_SEED_ROWS
                ]
            )
        )
        return len(PRODUCT_SEED_ROWS)
