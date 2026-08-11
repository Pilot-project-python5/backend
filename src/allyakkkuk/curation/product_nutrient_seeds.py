"""F-2.4 결정적 성분 기준과 제품별 단위당 함량 시드."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, delete, select
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import Nutrient, Product, ProductNutrient


@dataclass(frozen=True, slots=True)
class NutrientSeedRow:
    id: UUID
    code: str
    name: str
    canonical_unit: str


@dataclass(frozen=True, slots=True)
class ProductNutrientSeedRow:
    product_sku: str
    nutrient_code: str
    amount_per_unit: Decimal
    unit: str
    sort_order: int


NUTRIENT_SEED_ROWS = (
    NutrientSeedRow(
        id=UUID("23000000-0000-4000-8000-000000000001"),
        code="VITAMIN_C",
        name="비타민 C",
        canonical_unit="MG",
    ),
    NutrientSeedRow(
        id=UUID("23000000-0000-4000-8000-000000000002"),
        code="VITAMIN_D",
        name="비타민 D",
        canonical_unit="MCG",
    ),
    NutrientSeedRow(
        id=UUID("23000000-0000-4000-8000-000000000003"),
        code="PROTEIN",
        name="단백질",
        canonical_unit="G",
    ),
    NutrientSeedRow(
        id=UUID("23000000-0000-4000-8000-000000000004"),
        code="OMEGA_3",
        name="오메가3",
        canonical_unit="MG",
    ),
)

PRODUCT_NUTRIENT_SEED_ROWS = (
    ProductNutrientSeedRow(
        product_sku="LIFE-TWO-PER-DAY",
        nutrient_code="VITAMIN_C",
        amount_per_unit=Decimal("235"),
        unit="MG",
        sort_order=10,
    ),
    ProductNutrientSeedRow(
        product_sku="LIFE-TWO-PER-DAY",
        nutrient_code="VITAMIN_D",
        amount_per_unit=Decimal("25"),
        unit="MCG",
        sort_order=20,
    ),
    ProductNutrientSeedRow(
        product_sku="BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        nutrient_code="PROTEIN",
        amount_per_unit=Decimal("25"),
        unit="G",
        sort_order=10,
    ),
    ProductNutrientSeedRow(
        product_sku="SPORTS-RESEARCH-OMEGA-3",
        nutrient_code="OMEGA_3",
        amount_per_unit=Decimal("1040"),
        unit="MG",
        sort_order=10,
    ),
)


class ProductNutrientSeedSet:
    name = "product_nutrients"

    def apply(self, connection: Connection) -> int:
        values = [
            {
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "canonical_unit": row.canonical_unit,
                "is_active": True,
            }
            for row in NUTRIENT_SEED_ROWS
        ]
        insert_statement = insert(Nutrient).values(values)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[Nutrient.code],
            set_={
                "name": insert_statement.excluded.name,
                "canonical_unit": insert_statement.excluded.canonical_unit,
                "is_active": insert_statement.excluded.is_active,
            },
        ).returning(Nutrient.id, Nutrient.code)
        nutrient_ids = {
            code: nutrient_id
            for nutrient_id, code in connection.execute(upsert_statement)
        }

        product_skus = tuple(
            dict.fromkeys(row.product_sku for row in PRODUCT_NUTRIENT_SEED_ROWS)
        )
        products = {
            sku: (product_id, product_type)
            for product_id, sku, product_type in connection.execute(
                select(Product.id, Product.sku, Product.product_type).where(
                    Product.sku.in_(product_skus)
                )
            )
        }
        missing_products = set(product_skus) - set(products)
        if missing_products:
            raise ValueError(
                f"성분 시드에 필요한 제품이 없습니다: {sorted(missing_products)}"
            )
        invalid_products = sorted(
            sku
            for sku, (_, product_type) in products.items()
            if product_type != "SUPPLEMENT"
        )
        if invalid_products:
            raise ValueError(
                f"의약품에는 영양 성분 시드를 연결할 수 없습니다: {invalid_products}"
            )

        canonical_units = {row.code: row.canonical_unit for row in NUTRIENT_SEED_ROWS}
        invalid_units = sorted(
            row.nutrient_code
            for row in PRODUCT_NUTRIENT_SEED_ROWS
            if canonical_units[row.nutrient_code] != row.unit
        )
        if invalid_units:
            raise ValueError(
                f"성분 기준 단위와 제품 함량 단위가 다릅니다: {invalid_units}"
            )

        seeded_product_ids = tuple(product_id for product_id, _ in products.values())
        connection.execute(
            delete(ProductNutrient).where(
                ProductNutrient.product_id.in_(seeded_product_ids)
            )
        )
        connection.execute(
            insert(ProductNutrient).values(
                [
                    {
                        "product_id": products[row.product_sku][0],
                        "nutrient_id": nutrient_ids[row.nutrient_code],
                        "amount_per_unit": row.amount_per_unit,
                        "unit": row.unit,
                        "sort_order": row.sort_order,
                    }
                    for row in PRODUCT_NUTRIENT_SEED_ROWS
                ]
            )
        )
        return len(NUTRIENT_SEED_ROWS)
