"""F-2.4.2 결정적 제품별 외부 구매 링크 시드."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import Product, PurchaseLink
from allyakkkuk.curation.purchase_link_urls import validate_purchase_url


@dataclass(frozen=True, slots=True)
class PurchaseLinkSeedRow:
    id: UUID
    product_sku: str
    provider_name: str
    url: str
    sort_order: int


PURCHASE_LINK_SEED_ROWS = (
    PurchaseLinkSeedRow(
        id=UUID("25000000-0000-4000-8000-000000000001"),
        product_sku="LIFE-TWO-PER-DAY",
        provider_name="개발용 구매처",
        url="https://example.com/allyakkkuk/products/life-two-per-day",
        sort_order=10,
    ),
    PurchaseLinkSeedRow(
        id=UUID("25000000-0000-4000-8000-000000000002"),
        product_sku="BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        provider_name="개발용 구매처",
        url="https://example.com/allyakkkuk/products/bsn-syntha-6-isolate",
        sort_order=10,
    ),
    PurchaseLinkSeedRow(
        id=UUID("25000000-0000-4000-8000-000000000003"),
        product_sku="SPORTS-RESEARCH-OMEGA-3",
        provider_name="개발용 구매처",
        url="https://example.com/allyakkkuk/products/sports-research-omega-3",
        sort_order=10,
    ),
)


class PurchaseLinkSeedSet:
    name = "purchase_links"

    def apply(self, connection: Connection) -> int:
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
