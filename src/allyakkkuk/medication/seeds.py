"""F-3.10 로컬 의약품 제품·상세 결정적 시드."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert

from allyakkkuk.curation.models import Product
from allyakkkuk.medication.models import MedicationDetail

SEED_TIME = datetime(2026, 8, 14, tzinfo=UTC)
SOURCE_REVIEWED_ON = date(2026, 8, 14)


@dataclass(frozen=True, slots=True)
class MedicationSeedRow:
    id: UUID
    sku: str
    brand: str
    name: str
    image_url: str
    unit_form: str
    units_per_package: Decimal
    sort_order: int
    permit_code: str
    classification: str
    active_ingredients: str
    efficacy: str
    dosage_instructions: str
    precautions: str
    storage_instructions: str
    source_name: str
    source_url: str


_TEST_NOTICE = "실제 의약품 정보가 아닌 로컬 MVP API·UI 검증용 예시 데이터입니다."
MEDICATION_SEED_ROWS = (
    MedicationSeedRow(
        id=UUID("22000000-0000-4000-8000-000000000010"),
        sku="LOCAL-MED-001",
        brand="알약꾹 로컬 테스트",
        name="복용 관리 예시 의약품 A",
        image_url="/static/products/local-medication-a.svg",
        unit_form="TABLET",
        units_per_package=Decimal("20"),
        sort_order=110,
        permit_code="LOCAL-MED-001",
        classification="OTC",
        active_ingredients="개발용 예시 성분 A — 실사용 금지",
        efficacy=_TEST_NOTICE,
        dosage_instructions="실제 복용에 사용하지 말고 화면 흐름 검증에만 사용하세요.",
        precautions=(
            "운영 전 품목별 공식 허가정보 검토와 승인 데이터 교체가 필요합니다."
        ),
        storage_instructions="로컬 테스트 데이터이며 실제 보관 지침이 아닙니다.",
        source_name="알약꾹 로컬 테스트 시드(실사용 금지)",
        source_url=("https://example.invalid/allyakkkuk/medications/local-med-001"),
    ),
    MedicationSeedRow(
        id=UUID("22000000-0000-4000-8000-000000000011"),
        sku="LOCAL-MED-002",
        brand="알약꾹 로컬 테스트",
        name="복용 관리 예시 의약품 B",
        image_url="/static/products/local-medication-b.svg",
        unit_form="CAPSULE",
        units_per_package=Decimal("30"),
        sort_order=120,
        permit_code="LOCAL-MED-002",
        classification="PRESCRIPTION",
        active_ingredients="개발용 예시 성분 B — 실사용 금지",
        efficacy=_TEST_NOTICE,
        dosage_instructions="실제 복용에 사용하지 말고 화면 흐름 검증에만 사용하세요.",
        precautions=(
            "운영 전 품목별 공식 허가정보 검토와 승인 데이터 교체가 필요합니다."
        ),
        storage_instructions="로컬 테스트 데이터이며 실제 보관 지침이 아닙니다.",
        source_name="알약꾹 로컬 테스트 시드(실사용 금지)",
        source_url=("https://example.invalid/allyakkkuk/medications/local-med-002"),
    ),
)


def validate_medication_seed_rows(
    rows: tuple[MedicationSeedRow, ...] = MEDICATION_SEED_ROWS,
) -> None:
    if not rows:
        raise ValueError("의약품 시드는 한 행 이상이어야 합니다.")
    if len({row.sku for row in rows}) != len(rows):
        raise ValueError("의약품 시드 SKU가 중복되었습니다.")
    if len({row.permit_code for row in rows}) != len(rows):
        raise ValueError("의약품 시드 품목 추적 코드가 중복되었습니다.")
    for row in rows:
        if row.classification not in {"OTC", "PRESCRIPTION"}:
            raise ValueError(f"지원하지 않는 의약품 분류입니다: {row.classification}")
        required = (
            row.brand,
            row.name,
            row.active_ingredients,
            row.efficacy,
            row.dosage_instructions,
            row.precautions,
            row.storage_instructions,
            row.source_name,
        )
        if any(not value.strip() for value in required):
            raise ValueError(f"의약품 시드 필수 정보가 비어 있습니다: {row.sku}")
        if not row.source_url.startswith("https://"):
            raise ValueError(f"의약품 시드 출처는 HTTPS여야 합니다: {row.sku}")


class MedicationSeedSet:
    name = "medications"

    def apply(self, connection: Connection) -> int:
        validate_medication_seed_rows()
        product_values = [
            {
                "id": row.id,
                "sku": row.sku,
                "product_type": "MEDICATION",
                "brand": row.brand,
                "name": row.name,
                "image_url": row.image_url,
                "unit_form": row.unit_form,
                "units_per_package": row.units_per_package,
                "display_price": 0,
                "is_published": True,
                "sort_order": row.sort_order,
                "created_at": SEED_TIME,
                "updated_at": SEED_TIME,
            }
            for row in MEDICATION_SEED_ROWS
        ]
        product_insert = insert(Product).values(product_values)
        product_ids = {
            sku: product_id
            for product_id, sku in connection.execute(
                product_insert.on_conflict_do_update(
                    index_elements=[Product.sku],
                    set_={
                        "product_type": product_insert.excluded.product_type,
                        "brand": product_insert.excluded.brand,
                        "name": product_insert.excluded.name,
                        "image_url": product_insert.excluded.image_url,
                        "unit_form": product_insert.excluded.unit_form,
                        "units_per_package": (
                            product_insert.excluded.units_per_package
                        ),
                        "display_price": product_insert.excluded.display_price,
                        "is_published": product_insert.excluded.is_published,
                        "sort_order": product_insert.excluded.sort_order,
                        "updated_at": product_insert.excluded.updated_at,
                    },
                ).returning(Product.id, Product.sku)
            )
        }
        detail_values = [
            {
                "product_id": product_ids[row.sku],
                "permit_code": row.permit_code,
                "classification": row.classification,
                "active_ingredients": row.active_ingredients,
                "efficacy": row.efficacy,
                "dosage_instructions": row.dosage_instructions,
                "precautions": row.precautions,
                "storage_instructions": row.storage_instructions,
                "source_name": row.source_name,
                "source_url": row.source_url,
                "source_reviewed_on": SOURCE_REVIEWED_ON,
                "created_at": SEED_TIME,
                "updated_at": SEED_TIME,
            }
            for row in MEDICATION_SEED_ROWS
        ]
        detail_insert = insert(MedicationDetail).values(detail_values)
        connection.execute(
            detail_insert.on_conflict_do_update(
                index_elements=[MedicationDetail.product_id],
                set_={
                    "permit_code": detail_insert.excluded.permit_code,
                    "classification": detail_insert.excluded.classification,
                    "active_ingredients": detail_insert.excluded.active_ingredients,
                    "efficacy": detail_insert.excluded.efficacy,
                    "dosage_instructions": detail_insert.excluded.dosage_instructions,
                    "precautions": detail_insert.excluded.precautions,
                    "storage_instructions": (
                        detail_insert.excluded.storage_instructions
                    ),
                    "source_name": detail_insert.excluded.source_name,
                    "source_url": detail_insert.excluded.source_url,
                    "source_reviewed_on": detail_insert.excluded.source_reviewed_on,
                    "updated_at": detail_insert.excluded.updated_at,
                },
            )
        )
        return len(MEDICATION_SEED_ROWS)
