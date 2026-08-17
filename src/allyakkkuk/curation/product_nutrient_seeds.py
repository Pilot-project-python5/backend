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


def _nutrient(value: int, code: str, name: str, unit: str) -> NutrientSeedRow:
    return NutrientSeedRow(
        id=UUID(f"23000000-0000-4000-8000-{value:012d}"),
        code=code,
        name=name,
        canonical_unit=unit,
    )


NUTRIENT_SEED_ROWS = (
    _nutrient(1, "VITAMIN_C", "비타민 C", "MG"),
    _nutrient(2, "VITAMIN_D", "비타민 D", "MCG"),
    _nutrient(3, "PROTEIN", "단백질", "G"),
    _nutrient(4, "OMEGA_3", "오메가3(EPA+DHA)", "MG"),
    _nutrient(101, "VITAMIN_A_RE", "비타민 A(레티놀 활성당량)", "MCG"),
    _nutrient(102, "VITAMIN_E", "비타민 E", "MG"),
    _nutrient(103, "VITAMIN_K", "비타민 K", "MCG"),
    _nutrient(104, "VITAMIN_B1", "비타민 B1", "MG"),
    _nutrient(105, "VITAMIN_B2", "비타민 B2", "MG"),
    _nutrient(106, "VITAMIN_B6", "비타민 B6", "MG"),
    _nutrient(107, "VITAMIN_B12", "비타민 B12", "MCG"),
    _nutrient(108, "NIACIN", "나이아신", "MG"),
    _nutrient(109, "PANTOTHENIC_ACID", "판토텐산", "MG"),
    _nutrient(110, "FOLATE", "엽산", "MCG"),
    _nutrient(111, "BIOTIN", "비오틴", "MCG"),
    _nutrient(112, "CALCIUM", "칼슘", "MG"),
    _nutrient(113, "MAGNESIUM", "마그네슘", "MG"),
    _nutrient(114, "ZINC", "아연", "MG"),
    _nutrient(115, "SELENIUM", "셀렌", "MCG"),
    _nutrient(116, "BCAA", "BCAA", "G"),
    _nutrient(117, "CARBOHYDRATE", "탄수화물", "G"),
    _nutrient(118, "FAT", "지방", "G"),
    _nutrient(119, "CREATINE", "크레아틴", "G"),
    _nutrient(120, "BETA_ALANINE", "베타알라닌", "G"),
    _nutrient(121, "BETAINE", "베타인", "G"),
    _nutrient(122, "CAFFEINE", "카페인", "MG"),
    _nutrient(123, "CREATINE_NITRATE", "크레아틴 나이트레이트", "G"),
    _nutrient(124, "MELATONIN", "멜라토닌", "MG"),
)


def _mappings(
    product_sku: str, values: tuple[tuple[str, str, str], ...]
) -> tuple[ProductNutrientSeedRow, ...]:
    return tuple(
        ProductNutrientSeedRow(
            product_sku=product_sku,
            nutrient_code=code,
            amount_per_unit=Decimal(amount),
            unit=unit,
            sort_order=position * 10,
        )
        for position, (code, amount, unit) in enumerate(values, start=1)
    )


PRODUCT_NUTRIENT_SEED_ROWS = (
    *_mappings(
        "KORYO-EUNDAN-MULTIVITAMIN-ALL-IN-ONE",
        (
            ("VITAMIN_A_RE", "350", "MCG"),
            ("VITAMIN_C", "100", "MG"),
            ("VITAMIN_D", "10", "MCG"),
            ("VITAMIN_E", "5.5", "MG"),
            ("VITAMIN_K", "70", "MCG"),
            ("CALCIUM", "230", "MG"),
            ("MAGNESIUM", "104", "MG"),
            ("ZINC", "8.5", "MG"),
        ),
    ),
    *_mappings(
        "ALIVE-ONCE-DAILY-MENS",
        (
            ("VITAMIN_A_RE", "555", "MCG"),
            ("VITAMIN_C", "200", "MG"),
            ("VITAMIN_D", "10", "MCG"),
            ("VITAMIN_B1", "35", "MG"),
            ("VITAMIN_B2", "30", "MG"),
            ("VITAMIN_B6", "45", "MG"),
            ("VITAMIN_B12", "150", "MCG"),
            ("ZINC", "20", "MG"),
            ("SELENIUM", "135", "MCG"),
        ),
    ),
    *_mappings(
        "ALIVE-ONCE-DAILY-WOMENS",
        (
            ("VITAMIN_A_RE", "555", "MCG"),
            ("VITAMIN_C", "200", "MG"),
            ("VITAMIN_D", "10", "MCG"),
            ("VITAMIN_B1", "30", "MG"),
            ("VITAMIN_B2", "25", "MG"),
            ("VITAMIN_B6", "40", "MG"),
            ("VITAMIN_B12", "150", "MCG"),
            ("CALCIUM", "210", "MG"),
            ("MAGNESIUM", "100", "MG"),
            ("ZINC", "15", "MG"),
        ),
    ),
    *_mappings(
        "KORYO-EUNDAN-MEGADOSE-B",
        (
            ("VITAMIN_B1", "50", "MG"),
            ("VITAMIN_B2", "60", "MG"),
            ("VITAMIN_B6", "50", "MG"),
            ("VITAMIN_B12", "50", "MCG"),
            ("NIACIN", "65", "MG"),
            ("PANTOTHENIC_ACID", "50", "MG"),
            ("FOLATE", "500", "MCG"),
            ("BIOTIN", "300", "MCG"),
        ),
    ),
    *_mappings(
        "THORNE-BASIC-B-COMPLEX",
        (
            ("VITAMIN_B1", "110", "MG"),
            ("VITAMIN_B2", "10", "MG"),
            ("NIACIN", "140", "MG"),
            ("PANTOTHENIC_ACID", "110", "MG"),
            ("VITAMIN_B6", "10", "MG"),
            ("FOLATE", "667", "MCG"),
            ("VITAMIN_B12", "400", "MCG"),
            ("BIOTIN", "400", "MCG"),
        ),
    ),
    *_mappings(
        "SOLGAR-B-COMPLEX-100",
        (
            ("VITAMIN_B1", "100", "MG"),
            ("VITAMIN_B2", "100", "MG"),
            ("NIACIN", "100", "MG"),
            ("PANTOTHENIC_ACID", "100", "MG"),
            ("VITAMIN_B6", "100", "MG"),
            ("VITAMIN_B12", "100", "MCG"),
            ("BIOTIN", "100", "MCG"),
            ("FOLATE", "400", "MCG"),
        ),
    ),
    *_mappings("KORYO-EUNDAN-VITAMIN-C-1000", (("VITAMIN_C", "1000", "MG"),)),
    *_mappings("CHONGKUNDANG-PREMIUM-VITA-C-1000-PLUS", (("VITAMIN_C", "1000", "MG"),)),
    *_mappings("SOLGAR-VITAMIN-C-1000", (("VITAMIN_C", "1000", "MG"),)),
    *_mappings("CHONGKUNDANG-VITAMIN-D-2000-IU", (("VITAMIN_D", "50", "MCG"),)),
    *_mappings("CHONGKUNDANG-VITAMIN-D-1000-IU", (("VITAMIN_D", "25", "MCG"),)),
    *_mappings("SOLGAR-VITAMIN-D3-1000-IU", (("VITAMIN_D", "25", "MCG"),)),
    *_mappings(
        "OPTIMUM-NUTRITION-GOLD-STANDARD-WHEY",
        (("PROTEIN", "24", "G"), ("BCAA", "5.5", "G")),
    ),
    *_mappings(
        "BSN-SYNTHA-6-ISOLATE-CHOCOLATE",
        (
            ("PROTEIN", "22", "G"),
            ("CARBOHYDRATE", "15", "G"),
            ("FAT", "6", "G"),
        ),
    ),
    *_mappings(
        "SELEX-PROFIT-WPI",
        (("PROTEIN", "20", "G"), ("BCAA", "4.8", "G")),
    ),
    *_mappings(
        "EVL-ENGN-PRE-WORKOUT",
        (
            ("CREATINE", "3", "G"),
            ("BETA_ALANINE", "1.6", "G"),
            ("BETAINE", "1", "G"),
            ("CAFFEINE", "300", "MG"),
        ),
    ),
    *_mappings(
        "CELLUCOR-C4-ORIGINAL",
        (
            ("BETA_ALANINE", "1.6", "G"),
            ("CREATINE_NITRATE", "1", "G"),
            ("CAFFEINE", "150", "MG"),
        ),
    ),
    *_mappings("NOW-CREATINE-MONOHYDRATE", (("CREATINE", "5", "G"),)),
    *_mappings("SAMDAEOBAEK-CREATINE-MONOHYDRATE", (("CREATINE", "3", "G"),)),
    *_mappings("JAMBBAEK-JUST-CREATINE", (("CREATINE", "3", "G"),)),
    *_mappings("CHONGKUNDANG-LACTO-FIT-GOLD", (("ZINC", "2.55", "MG"),)),
    *_mappings(
        "GQ-LAB-PROBIOTICS-GOLD",
        (("ZINC", "12", "MG"), ("SELENIUM", "16.5", "MCG")),
    ),
    *_mappings(
        "CHONGKUNDANG-PROMEGA-OMEGA-3-TRIPLE",
        (("OMEGA_3", "450", "MG"), ("VITAMIN_E", "5.5", "MG")),
    ),
    *_mappings(
        "DR-LIN-RTG-OMEGA-3-ALPHA",
        (("OMEGA_3", "600", "MG"), ("VITAMIN_E", "11", "MG")),
    ),
    *_mappings("NUTRI-D-DAY-RTG-OMEGA-3-GOLD", (("OMEGA_3", "600", "MG"),)),
    *_mappings(
        "SOLGAR-MAGNESIUM-WITH-B6",
        (("MAGNESIUM", "133.3333", "MG"), ("VITAMIN_B6", "8.3333", "MG")),
    ),
    *_mappings("DOCTORS-BEST-HIGH-ABSORPTION-MAGNESIUM", (("MAGNESIUM", "100", "MG"),)),
    *_mappings("NOW-MAGNESIUM-GLYCINATE", (("MAGNESIUM", "100", "MG"),)),
    *_mappings("NUTRIJEONG-PLANT-MELATONIN-2MG", (("MELATONIN", "1", "MG"),)),
    *_mappings("NUTRIJEONG-PLANT-MELATONIN-5MG", (("MELATONIN", "2.5", "MG"),)),
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
