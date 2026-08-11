"""F-2.3 결정적 추천 제품과 카테고리 매핑 시드."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, delete, select
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import (
    Product,
    ProductCategory,
    ProductCategoryMapping,
)

SEED_TIME = datetime(2026, 8, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ProductSeedRow:
    id: UUID
    sku: str
    product_type: str
    brand: str
    name: str
    image_url: str
    unit_form: str
    units_per_package: Decimal
    display_price: int
    sort_order: int
    category_slug: str


PRODUCT_SEED_ROWS = (
    ProductSeedRow(
        id=UUID("22000000-0000-4000-8000-000000000001"),
        sku="LIFE-TWO-PER-DAY",
        product_type="SUPPLEMENT",
        brand="Life Extension",
        name="라이프익스텐션 투퍼데이",
        image_url="/static/products/life-extension-two-per-day.svg",
        unit_form="TABLET",
        units_per_package=Decimal("120"),
        display_price=28400,
        sort_order=10,
        category_slug="vitamin",
    ),
    ProductSeedRow(
        id=UUID("22000000-0000-4000-8000-000000000002"),
        sku="BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        product_type="SUPPLEMENT",
        brand="BSN",
        name="신타6 아이솔레이트 초코맛",
        image_url="/static/products/bsn-syntha-6-isolate.svg",
        unit_form="SCOOP",
        units_per_package=Decimal("48"),
        display_price=72150,
        sort_order=20,
        category_slug="protein",
    ),
    ProductSeedRow(
        id=UUID("22000000-0000-4000-8000-000000000003"),
        sku="SPORTS-RESEARCH-OMEGA-3",
        product_type="SUPPLEMENT",
        brand="Sports Research",
        name="스포츠리서치 트리플 스트렝스",
        image_url="/static/products/sports-research-omega-3.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("90"),
        display_price=38900,
        sort_order=30,
        category_slug="omega-3",
    ),
)


class ProductSeedSet:
    name = "recommended_products"

    def apply(self, connection: Connection) -> int:
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
