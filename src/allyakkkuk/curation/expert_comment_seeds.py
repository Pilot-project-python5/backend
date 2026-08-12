"""F-2.4.1 결정적 제품별 전문가 코멘트 시드."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import ExpertComment, Product


@dataclass(frozen=True, slots=True)
class ExpertCommentSeedRow:
    id: UUID
    product_sku: str
    author_label: str
    content: str
    sort_order: int


EXPERT_COMMENT_SEED_ROWS = (
    ExpertCommentSeedRow(
        id=UUID("24000000-0000-4000-8000-000000000001"),
        product_sku="LIFE-TWO-PER-DAY",
        author_label="MJ's COMMENT",
        content=(
            "비타민 B군의 함량 구성이 안정적인 개발용 추천 제품입니다. "
            "개인별 건강 상태에 따라 선택 기준은 달라질 수 있습니다."
        ),
        sort_order=10,
    ),
    ExpertCommentSeedRow(
        id=UUID("24000000-0000-4000-8000-000000000002"),
        product_sku="BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        author_label="MJ's COMMENT",
        content=(
            "맛과 성분 구성을 함께 확인할 수 있는 개발용 단백질 제품입니다. "
            "알레르기와 개인별 섭취 조건은 제품 표시를 확인해야 합니다."
        ),
        sort_order=10,
    ),
    ExpertCommentSeedRow(
        id=UUID("24000000-0000-4000-8000-000000000003"),
        product_sku="SPORTS-RESEARCH-OMEGA-3",
        author_label="MJ's COMMENT",
        content=(
            "제품별 오메가3 함량과 섭취 단위를 비교하기 위한 개발용 추천 제품입니다. "
            "의약품 복용 중이라면 전문가와 상의가 필요할 수 있습니다."
        ),
        sort_order=10,
    ),
)


class ExpertCommentSeedSet:
    name = "expert_comments"

    def apply(self, connection: Connection) -> int:
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
