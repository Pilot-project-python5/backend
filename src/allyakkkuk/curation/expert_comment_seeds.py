"""F-2.4.1 결정적 제품별 전문가 코멘트 시드."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, select, update
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.catalog_seed_data import (
    PRODUCT_SEED_ROWS,
    coach_comment_for,
)
from allyakkkuk.curation.models import ExpertComment, Product


@dataclass(frozen=True, slots=True)
class ExpertCommentSeedRow:
    id: UUID
    product_sku: str
    author_label: str
    content: str
    sort_order: int


LEGACY_EXPERT_COMMENT_IDS = tuple(
    UUID(f"24000000-0000-4000-8000-{value:012d}") for value in range(1, 4)
)

EXPERT_COMMENT_SEED_ROWS = tuple(
    ExpertCommentSeedRow(
        id=UUID(f"24000000-0000-4000-8000-{100 + position:012d}"),
        product_sku=product.sku,
        author_label="MJ's COMMENT",
        content=coach_comment_for(product.category_slug),
        sort_order=10,
    )
    for position, product in enumerate(PRODUCT_SEED_ROWS, start=1)
)


class ExpertCommentSeedSet:
    name = "expert_comments"

    def apply(self, connection: Connection) -> int:
        connection.execute(
            update(ExpertComment)
            .where(ExpertComment.id.in_(LEGACY_EXPERT_COMMENT_IDS))
            .values(is_active=False)
        )
        product_skus = tuple(row.product_sku for row in EXPERT_COMMENT_SEED_ROWS)
        product_ids = {
            sku: product_id
            for product_id, sku in connection.execute(
                select(Product.id, Product.sku).where(Product.sku.in_(product_skus))
            )
        }
        missing = set(product_skus) - set(product_ids)
        if missing:
            raise ValueError(
                f"전문가 코멘트 시드에 필요한 제품이 없습니다: {sorted(missing)}"
            )

        values = [
            {
                "id": row.id,
                "product_id": product_ids[row.product_sku],
                "author_label": row.author_label,
                "content": row.content,
                "is_active": True,
                "sort_order": row.sort_order,
            }
            for row in EXPERT_COMMENT_SEED_ROWS
        ]
        statement = insert(ExpertComment).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[ExpertComment.id],
            set_={
                "product_id": statement.excluded.product_id,
                "author_label": statement.excluded.author_label,
                "content": statement.excluded.content,
                "is_active": statement.excluded.is_active,
                "sort_order": statement.excluded.sort_order,
            },
        )
        connection.execute(statement)
        return len(EXPERT_COMMENT_SEED_ROWS)
