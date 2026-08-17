"""F-2.4.2 결정적 제품별 외부 구매 링크 시드."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, select, update
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.catalog_seed_data import PRODUCT_SEED_ROWS
from allyakkkuk.curation.models import Product, PurchaseLink
from allyakkkuk.curation.purchase_link_urls import validate_purchase_url


@dataclass(frozen=True, slots=True)
class PurchaseLinkSeedRow:
    id: UUID
    product_sku: str
    provider_name: str
    url: str
    sort_order: int


LEGACY_PURCHASE_LINK_IDS = tuple(
    UUID(f"25000000-0000-4000-8000-{value:012d}") for value in range(1, 4)
)

PURCHASE_LINK_SEED_ROWS = tuple(
    PurchaseLinkSeedRow(
        id=UUID(f"25000000-0000-4000-8000-{100 + position:012d}"),
        product_sku=product.sku,
        provider_name="쿠팡",
        url=product.purchase_url,
        sort_order=10,
    )
    for position, product in enumerate(PRODUCT_SEED_ROWS, start=1)
)


class PurchaseLinkSeedSet:
    name = "purchase_links"

    def apply(self, connection: Connection) -> int:
        connection.execute(
            update(PurchaseLink)
            .where(PurchaseLink.id.in_(LEGACY_PURCHASE_LINK_IDS))
            .values(is_active=False)
        )
        product_skus = tuple(row.product_sku for row in PURCHASE_LINK_SEED_ROWS)
        product_ids = {
            sku: product_id
            for product_id, sku in connection.execute(
                select(Product.id, Product.sku).where(Product.sku.in_(product_skus))
            )
        }
        missing = set(product_skus) - set(product_ids)
        if missing:
            raise ValueError(
                f"구매 링크 시드에 필요한 제품이 없습니다: {sorted(missing)}"
            )

        values = [
            {
                "id": row.id,
                "product_id": product_ids[row.product_sku],
                "provider_name": row.provider_name,
                "url": validate_purchase_url(row.url),
                "is_active": True,
                "sort_order": row.sort_order,
            }
            for row in PURCHASE_LINK_SEED_ROWS
        ]
        statement = insert(PurchaseLink).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[PurchaseLink.id],
            set_={
                "product_id": statement.excluded.product_id,
                "provider_name": statement.excluded.provider_name,
                "url": statement.excluded.url,
                "is_active": statement.excluded.is_active,
                "sort_order": statement.excluded.sort_order,
            },
        )
        connection.execute(statement)
        return len(PURCHASE_LINK_SEED_ROWS)
