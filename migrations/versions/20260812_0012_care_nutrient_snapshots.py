"""복용 제품의 등록 시점 영양 성분 스냅샷을 추가한다.

Revision ID: 20260812_0012
Revises: 20260812_0011
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0012"
down_revision: str | None = "20260812_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "care_nutrient_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("care_item_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_name", sa.String(length=100), nullable=False),
        sa.Column("amount_per_unit", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.CheckConstraint(
            "char_length(btrim(nutrient_name)) BETWEEN 1 AND 100",
            name="ck_care_nutrient_snapshots_name_length",
        ),
        sa.CheckConstraint(
            "amount_per_unit > 0",
            name="ck_care_nutrient_snapshots_amount",
        ),
        sa.CheckConstraint(
            "unit IN ('MG', 'G', 'MCG', 'IU')",
            name="ck_care_nutrient_snapshots_unit",
        ),
        sa.ForeignKeyConstraint(
            ["care_item_id"],
            ["care_items.id"],
            name="fk_care_nutrient_snapshots_care_item_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["nutrient_id"],
            ["nutrients.id"],
            name="fk_care_nutrient_snapshots_nutrient_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_care_nutrient_snapshots"),
        sa.UniqueConstraint(
            "care_item_id",
            "nutrient_id",
            name="uq_care_nutrient_snapshots_item_nutrient",
        ),
    )
    op.create_index(
        "ix_care_nutrient_snapshots_nutrient_id",
        "care_nutrient_snapshots",
        ["nutrient_id"],
        unique=False,
    )

    # F-3.1에서 먼저 등록된 영양제는 배포 시점의 활성 카탈로그 값으로 1회 보정한다.
    op.execute(
        sa.text(
            """
            INSERT INTO care_nutrient_snapshots (
                id,
                care_item_id,
                nutrient_id,
                nutrient_name,
                amount_per_unit,
                unit
            )
            SELECT
                gen_random_uuid(),
                ci.id,
                n.id,
                n.name,
                pn.amount_per_unit,
                pn.unit
            FROM care_items AS ci
            JOIN products AS p ON p.id = ci.product_id
            JOIN product_nutrients AS pn ON pn.product_id = p.id
            JOIN nutrients AS n ON n.id = pn.nutrient_id
            WHERE p.product_type = 'SUPPLEMENT'
              AND n.is_active IS TRUE
            ON CONFLICT (care_item_id, nutrient_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_care_nutrient_snapshots_nutrient_id",
        table_name="care_nutrient_snapshots",
    )
    op.drop_table("care_nutrient_snapshots")
