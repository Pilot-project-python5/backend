from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from allyakkkuk.core.errors import AppError
from allyakkkuk.medication.repository import (
    MedicationDetailRecord,
    MedicationPageRecord,
    MedicationPersistenceError,
    MedicationSummaryRecord,
)
from allyakkkuk.medication.service import MedicationService

pytestmark = [pytest.mark.unit, pytest.mark.feature("F-3.10")]

PRODUCT_ID = UUID("22000000-0000-4000-8000-000000000010")


def summary() -> MedicationSummaryRecord:
    return MedicationSummaryRecord(
        id=PRODUCT_ID,
        sku="LOCAL-MED-001",
        brand="알약꾹 로컬 테스트",
        name="복용 관리 예시 의약품 A",
        image_url="/static/products/local-medication-a.svg",
        unit_form="TABLET",
        units_per_package=Decimal("20"),
        permit_code="LOCAL-MED-001",
        classification="OTC",
        active_ingredients="개발용 예시 성분 A",
    )


def detail() -> MedicationDetailRecord:
    return MedicationDetailRecord(
        **asdict(summary()),
        efficacy="실제 의약품 정보가 아닌 로컬 테스트 문구입니다.",
        dosage_instructions="실제 복용에 사용하지 마세요.",
        precautions="API·UI 검증에만 사용하세요.",
        storage_instructions="로컬 테스트 데이터입니다.",
        source_name="알약꾹 로컬 테스트 시드(실사용 금지)",
        source_url="https://example.invalid/allyakkkuk/medications/local-med-001",
        source_reviewed_on=date(2026, 8, 14),
    )


class StubRepository:
    def __init__(self) -> None:
        self.page = MedicationPageRecord((summary(),), 1)
        self.detail: MedicationDetailRecord | None = detail()
        self.failure = False

    def list_published(self, *, page: int, page_size: int) -> MedicationPageRecord:
        assert (page, page_size) == (1, 20)
        if self.failure:
            raise MedicationPersistenceError
        return self.page

    def get_published(self, product_id: UUID) -> MedicationDetailRecord | None:
        assert product_id == PRODUCT_ID
        if self.failure:
            raise MedicationPersistenceError
        return self.detail


def test_lists_published_medications_with_page_metadata() -> None:
    result = MedicationService(StubRepository()).list_medications(page=1, page_size=20)

    assert result.items[0].permit_code == "LOCAL-MED-001"
    assert result.total == 1
    assert result.has_next is False


def test_returns_complete_medication_detail() -> None:
    result = MedicationService(StubRepository()).get_medication(PRODUCT_ID)

    assert result.id == PRODUCT_ID
    assert result.source_reviewed_on == date(2026, 8, 14)
    assert result.classification == "OTC"


def test_missing_medication_uses_stable_not_found_error() -> None:
    repository = StubRepository()
    repository.detail = None

    with pytest.raises(AppError) as error:
        MedicationService(repository).get_medication(PRODUCT_ID)

    assert error.value.status_code == 404
    assert error.value.code == "MEDICATION_NOT_FOUND"


@pytest.mark.parametrize("operation", ["list", "detail"])
def test_repository_failure_uses_service_unavailable(operation: str) -> None:
    repository = StubRepository()
    repository.failure = True
    service = MedicationService(repository)

    with pytest.raises(AppError) as error:
        if operation == "list":
            service.list_medications(page=1, page_size=20)
        else:
            service.get_medication(PRODUCT_ID)

    assert error.value.status_code == 503
    assert error.value.code == "SERVICE_UNAVAILABLE"
