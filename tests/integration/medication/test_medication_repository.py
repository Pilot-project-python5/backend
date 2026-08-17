from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, inspect

from yeongyangkkuk.curation.models import Product
from yeongyangkkuk.db.session import SessionFactory, engine
from yeongyangkkuk.medication.models import MedicationDetail
from yeongyangkkuk.medication.repository import SQLAlchemyMedicationRepository

pytestmark = [pytest.mark.integration, pytest.mark.feature("F-3.10")]

NOW = datetime(2026, 8, 14, tzinfo=UTC)
PRODUCT_IDS = tuple(
    UUID(f"22000000-0000-4000-8000-{index:012d}") for index in range(310, 314)
)


@pytest.fixture(autouse=True)
def catalog_rows() -> Iterator[None]:
    _clean()
    with SessionFactory.begin() as session:
        session.add_all(
            [
                _product(PRODUCT_IDS[0], "MED-REPO-B", "MEDICATION", True, 20),
                _product(PRODUCT_IDS[1], "MED-REPO-A", "MEDICATION", True, 10),
                _product(PRODUCT_IDS[2], "MED-REPO-HIDDEN", "MEDICATION", False, 1),
                _product(PRODUCT_IDS[3], "SUP-REPO", "SUPPLEMENT", True, 1),
            ]
        )
        session.flush()
        session.add_all(
            [
                _detail(PRODUCT_IDS[0], "REPO-B", "PRESCRIPTION"),
                _detail(PRODUCT_IDS[1], "REPO-A", "OTC"),
                _detail(PRODUCT_IDS[2], "REPO-HIDDEN", "OTC"),
                _detail(PRODUCT_IDS[3], "REPO-SUPPLEMENT", "OTC"),
            ]
        )
    yield
    _clean()


def _clean() -> None:
    with SessionFactory.begin() as session:
        session.execute(
            delete(MedicationDetail).where(MedicationDetail.product_id.in_(PRODUCT_IDS))
        )
        session.execute(delete(Product).where(Product.id.in_(PRODUCT_IDS)))


def _product(
    product_id: UUID, sku: str, product_type: str, published: bool, sort_order: int
) -> Product:
    return Product(
        id=product_id,
        sku=sku,
        product_type=product_type,
        brand="저장소 테스트",
        name=sku,
        image_url="/static/products/local-medication-a.svg",
        unit_form="TABLET",
        units_per_package=Decimal("20"),
        display_price=0,
        is_published=published,
        sort_order=sort_order,
        created_at=NOW,
        updated_at=NOW,
    )


def _detail(product_id: UUID, code: str, classification: str) -> MedicationDetail:
    return MedicationDetail(
        product_id=product_id,
        permit_code=code,
        classification=classification,
        active_ingredients=f"{code} 성분",
        efficacy="저장소 통합 테스트 효능",
        dosage_instructions="저장소 통합 테스트 용법",
        precautions="저장소 통합 테스트 주의",
        storage_instructions="저장소 통합 테스트 보관",
        source_name="저장소 통합 테스트",
        source_url=f"https://example.invalid/{code.lower()}",
        source_reviewed_on=date(2026, 8, 14),
        created_at=NOW,
        updated_at=NOW,
    )


def test_repository_filters_and_stably_pages_published_medications() -> None:
    with SessionFactory() as session:
        repository = SQLAlchemyMedicationRepository(session)
        first = repository.list_published(page=1, page_size=1)
        second = repository.list_published(page=2, page_size=1)
        empty = repository.list_published(page=3, page_size=1)

    assert first.total == 2
    assert [item.sku for item in first.items] == ["MED-REPO-A"]
    assert [item.sku for item in second.items] == ["MED-REPO-B"]
    assert empty.items == ()


def test_repository_detail_hides_supplement_and_unpublished_rows() -> None:
    with SessionFactory() as session:
        repository = SQLAlchemyMedicationRepository(session)
        visible = repository.get_published(PRODUCT_IDS[0])
        hidden = repository.get_published(PRODUCT_IDS[2])
        supplement = repository.get_published(PRODUCT_IDS[3])

    assert visible is not None
    assert visible.permit_code == "REPO-B"
    assert hidden is None
    assert supplement is None


def test_medication_detail_schema_matches_orm_and_erd_contract() -> None:
    inspector = inspect(engine)
    columns = {
        item["name"]: item for item in inspector.get_columns("medication_details")
    }
    checks = {
        item["name"] for item in inspector.get_check_constraints("medication_details")
    }
    foreign_keys = {
        item["name"]: item for item in inspector.get_foreign_keys("medication_details")
    }
    indexes = {
        item["name"]: tuple(item["column_names"])
        for item in inspector.get_indexes("medication_details")
    }

    assert set(columns) == {
        "product_id",
        "permit_code",
        "classification",
        "active_ingredients",
        "efficacy",
        "dosage_instructions",
        "precautions",
        "storage_instructions",
        "source_name",
        "source_url",
        "source_reviewed_on",
        "created_at",
        "updated_at",
    }
    assert all(not column["nullable"] for column in columns.values())
    assert checks >= {
        "ck_medication_details_permit_code_format",
        "ck_medication_details_classification",
        "ck_medication_details_source_url_https",
        "ck_medication_details_updated_at",
    }
    assert (
        foreign_keys["fk_medication_details_product_id_products"]["options"]["ondelete"]
        == "CASCADE"
    )
    assert indexes["ix_medication_details_classification_product"] == (
        "classification",
        "product_id",
    )
